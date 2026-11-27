# Owner: Zan (PIC 3) | Status: COMPLETE | Ref: T3-06, PRD SCN-14, SA §18.3
"""Memeriksa penolakan operasi tanpa hak pada stack Lettrust lokal."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from common import ScenarioError, _read_env, load_settings, new_request_id, print_expected_actual, save_evidence

ROOT = Path(__file__).resolve().parents[2]
API = "/api/v1"
PROOFS = f"{API}/proofs"
ISSUERS = f"{API}/issuers"
UNAUTHENTICATED = (401, "UNAUTHENTICATED")
FORBIDDEN = (403, "FORBIDDEN_OPERATION")
NOT_FOUND = (404, "PROOF_NOT_FOUND")
DECIDED = (409, "ISSUER_DECISION_ALREADY_MADE")
PARTNER_CONTROL = (400, "INVALID_INPUT_COMBINATION")
ADDRESS_PATTERN = r"0x[0-9a-fA-F]{40}"
WORD_PATTERN = r"0x[0-9a-fA-F]{64}"
PROOF_EVENTS = ("ProofIssued(bytes32,bytes32,bytes32,uint64)", "ProofRevoked(bytes32,bytes32,uint64)")
JsonObject = dict[str, Any]


def local_url(value: str) -> str:
    """Membatasi pengiriman kredensial seed dan token ke HTTP loopback."""
    try:
        url = httpx.URL(value)
    except httpx.InvalidURL:
        raise ScenarioError("Alamat stack bukan URL yang valid.") from None
    if url.scheme != "http" or url.host not in {"localhost", "127.0.0.1", "::1"} or url.userinfo:
        raise ScenarioError("Alamat stack harus berupa HTTP loopback tanpa kredensial.")
    if url.path not in {"", "/"} or url.query or url.fragment:
        raise ScenarioError("Alamat stack harus berupa origin HTTP tanpa path atau query.")
    if url.host == "localhost":
        url = url.copy_with(host="127.0.0.1")
    return str(url).rstrip("/")


def command_result(*command: str) -> subprocess.CompletedProcess[str]:
    """Menjalankan Docker atau Cast dengan keluaran tertangkap dan batas waktu."""
    try:
        return subprocess.run(command, capture_output=True, text=True, timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ScenarioError(f"Perintah {command[0]} gagal ({type(exc).__name__}).") from None


def require_compose_port(project: str, service: str, container_port: int, url: str) -> None:
    """Menolak URL yang tidak menunjuk ke port loopback milik project Compose yang dipilih."""
    origin = httpx.URL(url)
    port = origin.port if origin.port is not None else 80
    result = command_result("docker", "port", f"{project}-{service}-1", f"{container_port}/tcp")
    host = "[::1]" if origin.host == "::1" else origin.host
    if result.returncode != 0 or f"{host}:{port}" not in result.stdout.splitlines():
        raise ScenarioError(f"Alamat {service} tidak cocok dengan port project Compose yang dipilih.")


class Registry:
    """Membaca registry pada Anvil Compose dan melakukan simulasi revoke tanpa transaksi."""

    def __init__(self, project: str, configured_address: str) -> None:
        """Mengambil alamat dari konfigurasi atau deployment backend pada project yang sama."""
        self.cast_command = ("docker", "exec", f"{project}-chain-1", "cast")
        self.rpc_args = ("--rpc-url", "http://127.0.0.1:8545")
        address = configured_address
        if not address:
            result = command_result("docker", "exec", f"{project}-backend-1", "cat", "/shared/deployments/local.json")
            try:
                address = json.loads(result.stdout)["contractAddress"] if result.returncode == 0 else ""
            except (ValueError, KeyError, TypeError):
                raise ScenarioError("Metadata deployment registry tidak valid.") from None
        if not isinstance(address, str) or not re.fullmatch(ADDRESS_PATTERN, address):
            raise ScenarioError("Alamat registry tidak tersedia atau tidak valid.")
        self.address = address
        if self.cast("chain-id") != "31337":
            raise ScenarioError("Chain yang dituju bukan chain Anvil lokal Lettrust (31337).")
        self.registrar = self.cast("call", self.address, "registrar()(address)")
        if not re.fullmatch(ADDRESS_PATTERN, self.registrar):
            raise ScenarioError("Alamat registrar dari contract tidak valid.")

    def cast(self, *args: str) -> str:
        """Mengembalikan stdout Cast yang sukses; stderr RPC mentah tetap tertutup."""
        result = command_result(*self.cast_command, *args, *self.rpc_args)
        if result.returncode != 0:
            raise ScenarioError(f"Cast {args[0]} gagal pada registry lokal.")
        return result.stdout.strip()

    def snapshot(self, proof_id: str) -> JsonObject:
        """Membaca blok, nonce registrar, dan state bukti untuk pembanding fase negatif."""
        block = int(self.cast("block-number"))
        nonce = int(self.cast("nonce", self.registrar, "--block", "pending"))
        raw = self.cast("call", self.address, "getProof(bytes32)", proof_id, "--block", str(block))
        if not re.fullmatch(r"0x[0-9a-fA-F]{384}", raw):
            raise ScenarioError("Respons getProof tidak sesuai ABI registry.")
        fields = [raw[offset : offset + 64].lower() for offset in range(2, 386, 64)]
        return {
            "block": block,
            "registrarNonce": nonce,
            "exists": int(fields[0], 16) == 1,
            "documentHash": fields[1],
            "issuerRef": fields[2],
            "lifecycleStatus": {1: "ACTIVE", 2: "REVOKED"}.get(int(fields[3], 16), "NONE"),
            "issuedAt": int(fields[4], 16),
            "revokedAt": int(fields[5], 16),
        }

    def issuer_mismatch(self, proof_id: str, issuer_a: str) -> bool:
        """Memastikan revert IssuerMismatch dengan alamat registrar publik sebagai from pada eth_call."""
        issuer_ref = "0x" + hashlib.sha256(f"lettrust:issuer:{issuer_a}".encode()).hexdigest()
        selector = command_result(*self.cast_command, "sig", "IssuerMismatch()")
        signature = selector.stdout.strip()
        if selector.returncode != 0 or not re.fullmatch(r"0x[0-9a-fA-F]{8}", signature):
            raise ScenarioError("Cast gagal menghitung selector IssuerMismatch.")
        result = command_result(
            *self.cast_command,
            "call",
            self.address,
            "revokeProof(bytes32,bytes32)",
            proof_id,
            issuer_ref,
            "--from",
            self.registrar,
            *self.rpc_args,
        )
        return (
            result.returncode != 0
            and "revert" in result.stderr.lower()
            and re.search(rf"\b{signature}\b", result.stderr, re.IGNORECASE) is not None
        )

    def event_counts(self, first_block: int, last_block: int) -> dict[str, int]:
        """Menghitung event mutasi selama fase negatif, terlepas dari proofId yang dipakai."""
        counts = {}
        for event in PROOF_EVENTS:
            logs = []
            if first_block <= last_block:
                raw = self.cast(
                    "logs",
                    "--address",
                    self.address,
                    "--from-block",
                    str(first_block),
                    "--to-block",
                    str(last_block),
                    "--json",
                    event,
                )
                logs = json.loads(raw)
                if not isinstance(logs, list):
                    raise ScenarioError("Respons log registry bukan daftar event.")
            counts[event.partition("(")[0]] = len(logs)
        return counts


def json_object(response: httpx.Response) -> JsonObject:
    """Mengurai objek respons tanpa menampilkan body ketika formatnya salah."""
    try:
        value = response.json()
    except ValueError:
        value = None
    if not isinstance(value, dict):
        raise ScenarioError("Respons stack bukan objek JSON.")
    return value


def request(
    client: httpx.Client, method: str, path: str, *, token: str | None = None, **kwargs: Any
) -> tuple[str, httpx.Response]:
    """Mengirim satu request dengan ID lokal, opsional Bearer, dan header tambahan (mis. Idempotency-Key)."""
    request_id = new_request_id()
    headers = {**kwargs.pop("headers", {}), "X-Request-ID": request_id}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    return request_id, client.request(method, path, headers=headers, **kwargs)


def setup_request(client: httpx.Client, method: str, path: str, status: int, **kwargs: Any) -> JsonObject:
    """Menghentikan setup jika endpoint tidak memberikan status sukses yang diharapkan."""
    request_id, response = request(client, method, path, **kwargs)
    if response.status_code != status:
        raise ScenarioError(f"Setup {method} mendapat HTTP {response.status_code} ({request_id}).")
    return json_object(response)


# Batas generasi kunci pengganti; setiap generasi hanya dipakai lagi bila bukti generasi sebelumnya sudah dicabut.
MAX_SETUP_GENERATIONS = 20


def setup_idempotency_key(issuer_id: str, digest: str, generation: int = 0) -> str:
    """Kunci setup stabil per (penerbit, dokumen, generasi) agar run berikutnya memulihkan penerbitan yang timeout."""
    suffix = "" if generation == 0 else f":{generation}"
    return "scn14-setup-" + hashlib.sha256(f"{issuer_id}:{digest}{suffix}".encode()).hexdigest()[:24]


def find_or_issue_active(client: httpx.Client, token: str, pdf: bytes, issuer_id: str) -> JsonObject:
    """Memakai bukti ACTIVE FX-01 milik penerbit token ini bila ada; menerbitkan hanya bila belum ada.

    Run berulang tidak menerbitkan FX-01 kedua yang akan ditolak DUPLICATE_ACTIVE_DOCUMENT (FR-03.06). Seluruh halaman
    daftar dan detail diperiksa; kegagalan daftar atau detail menghentikan setup tanpa penerbitan baru.

    Penerbitan memakai kunci stabil: bila receipt sebelumnya timeout (mirror PENDING, belum ada di daftar ACTIVE), run
    berikutnya mengulang dengan kunci yang sama sehingga backend memulihkan bukti yang sama. Bila kunci itu ternyata
    milik bukti yang sudah dicabut (status terkini dibaca lewat API-05), generasi kunci berikutnya yang juga stabil
    dipakai sehingga penerbitan pengganti tetap dapat dipulihkan setelah timeout.
    """
    digest = hashlib.sha256(pdf).hexdigest()
    offset = 0
    while True:
        page = setup_request(
            client, "GET", PROOFS, 200, token=token, params={"status": "ACTIVE", "limit": 100, "offset": offset}
        )
        items, total = page.get("items"), page.get("total")
        if not isinstance(items, list) or not isinstance(total, int):
            raise ScenarioError("Daftar bukti penerbit tidak berformat benar; setup dihentikan.")
        for item in items:
            detail = setup_request(client, "GET", f"{PROOFS}/{item['proofId']}", 200, token=token)
            if detail.get("documentHash") == digest and detail.get("lifecycleStatus") == "ACTIVE":
                # Detail API-05 memuat field yang sama dengan respons API-04 (proofId, issuerId, ...); transaksi
                # penerbitan dinamai issueTransaction sehingga disalin ke kunci `transaction`.
                return {**detail, "transaction": detail["issueTransaction"]}
        offset += len(items)
        if not items or offset >= total:
            break
    upload = {"files": {"file": ("FX-01.pdf", pdf, "application/pdf")}}
    for generation in range(MAX_SETUP_GENERATIONS):
        headers = {"Idempotency-Key": setup_idempotency_key(issuer_id, digest, generation)}
        issued = setup_request(client, "POST", PROOFS, 201, token=token, headers=headers, **upload)
        # Replay API-04 mengembalikan hasil penerbitan historis (ACTIVE) walau bukti sudah dicabut; status terkini
        # dibaca dari registry lewat API-05.
        current = setup_request(client, "GET", f"{PROOFS}/{issued['proofId']}", 200, token=token)
        if current.get("lifecycleStatus") == "ACTIVE":
            return {**current, "transaction": current["issueTransaction"]}
    raise ScenarioError("Seluruh generasi kunci setup FX-01 sudah dipakai bukti yang dicabut; setup dihentikan.")


def login(client: httpx.Client, email: str, password: str) -> tuple[str, JsonObject]:
    """Membaca token dan identitas dari login dan /auth/me tanpa menyimpan kredensial sebagai bukti."""
    session = setup_request(client, "POST", f"{API}/auth/login", 200, json={"email": email, "password": password})
    token = session["accessToken"]
    if not isinstance(token, str) or not token:
        raise ScenarioError("Token sesi tidak tersedia pada respons login.")
    profile = setup_request(client, "GET", f"{API}/auth/me", 200, token=token)
    return token, profile


def record_http(
    cases: list[JsonObject],
    case: str,
    expected: tuple[tuple[int, str], ...],
    result: tuple[str, httpx.Response],
) -> JsonObject:
    """Mencatat field aman dan mengembalikan envelope tanpa request ID hanya untuk pembandingan."""
    request_id, response = result
    try:
        body = json_object(response)
    except ScenarioError:
        body = {}
    error = body.get("error")
    code = error.get("code") if isinstance(error, dict) else None
    codes = {pair[1] for pair in (*expected, UNAUTHENTICATED, FORBIDDEN, NOT_FOUND, DECIDED)}
    cases.append(
        {
            "case": case,
            "expected": [{"status": status, "code": expected_code} for status, expected_code in expected],
            "actual": {
                "status": response.status_code,
                "code": code if isinstance(code, str) and code in codes else None,
                "requestId": request_id,
            },
            "matches": (response.status_code, code) in expected,
        }
    )
    if isinstance(error, dict):
        body["error"] = {key: value for key, value in error.items() if key != "requestId"}
    return {key: value for key, value in body.items() if key != "requestId"}


def prepare_issuer(client: httpx.Client, admin: str, run_id: str) -> tuple[str, JsonObject]:
    """Mencatat keputusan pertama untuk penerbit sintetis baru agar pengujian dapat diulang."""
    email = f"scn14-{run_id}@lettrust.test"
    password = secrets.token_urlsafe(24)
    setup_request(
        client,
        "POST",
        f"{API}/auth/register",
        201,
        json={
            "displayName": "HR SCN-14",
            "email": email,
            "password": password,
        },
    )
    token, _ = login(client, email, password)
    issuer = setup_request(
        client,
        "POST",
        ISSUERS,
        201,
        token=token,
        json={
            "companyName": "PT Uji Otorisasi SCN-14",
            "registrationNumber": f"SCN14-{run_id}",
            "contactEmail": email,
        },
    )
    if issuer["issuerStatus"] != "PENDING":
        raise ScenarioError("Penerbit sintetis untuk (k) tidak berstatus PENDING.")
    path = f"{ISSUERS}/{issuer['issuerId']}/verification"
    first = setup_request(
        client,
        "PATCH",
        path,
        200,
        token=admin,
        json={
            "decision": "VERIFIED",
            "evidenceRef": f"SCN14-{run_id}",
        },
    )
    if first["issuerStatus"] != "VERIFIED":
        raise ScenarioError("Keputusan pertama untuk (k) tidak menghasilkan VERIFIED.")
    return issuer["issuerId"], first


def run_scenario(
    client: httpx.Client,
    ai: httpx.Client,
    registry: Registry,
    pdf: bytes,
    run_id: str,
    hr_password: str,
    admin_password: str,
    partner_token: str,
    evidence: JsonObject,
) -> bool:
    """Menyiapkan kontrol positif, menjalankan (a)–(k), dan memeriksa perubahan registry."""
    cases = evidence["cases"]
    # Request kosong mencapai validasi input hanya bila token partner diterima; registry dan AI tidak dipanggil.
    record_http(
        cases, "h-control", (PARTNER_CONTROL,), request(client, "POST", f"{API}/verifications", token=partner_token)
    )
    if not cases[-1]["matches"]:
        raise ScenarioError("Token partner tidak lolos kontrol autentikasi API-07.")

    admin, admin_profile = login(client, "admin@lettrust.test", admin_password)
    if admin_profile["role"] != "ADMIN":
        raise ScenarioError("Akun admin seed tidak berperan ADMIN.")
    seed_accounts = (
        ("a", "hr.pending", "PENDING", "NOT_AUTHORIZED"),
        ("b", "hr.rejected", "REJECTED", "NOT_AUTHORIZED"),
        ("c", "hr2.sinar", "VERIFIED", "NOT_AUTHORIZED"),
        ("owner-a", "hr.sinar", "VERIFIED", "AUTHORIZED"),
        ("owner-b", "hr.nusantara", "VERIFIED", "AUTHORIZED"),
    )
    tokens = {}
    profiles = {}
    for name, username, issuer_status, authorization_status in seed_accounts:
        token, profile = login(client, f"{username}@lettrust.test", hr_password)
        member = profile["membership"]
        if not isinstance(member, dict) or (profile["role"], member["issuerStatus"], member["authorizationStatus"]) != (
            "HR",
            issuer_status,
            authorization_status,
        ):
            raise ScenarioError(f"Role atau status akun seed untuk {name} berbeda dari prasyarat.")
        tokens[name], profiles[name] = token, profile

    issuer_a = profiles["owner-a"]["membership"]["issuerId"]
    issuer_b = profiles["owner-b"]["membership"]["issuerId"]
    if issuer_a == issuer_b or issuer_a != profiles["c"]["membership"]["issuerId"]:
        raise ScenarioError("Afiliasi seed A/B tidak sesuai prasyarat.")
    upload = {"files": {"file": ("FX-01.pdf", pdf, "application/pdf")}}
    issued = find_or_issue_active(client, tokens["owner-b"], pdf, issuer_b)
    proof_id = issued["proofId"]
    transaction = issued["transaction"]
    if not isinstance(proof_id, str) or not re.fullmatch(WORD_PATTERN, proof_id):
        raise ScenarioError("Setup FX-01 tidak menghasilkan proofId yang valid.")
    tx_hash = transaction["hash"]
    tx_block = transaction["blockNumber"]
    if not isinstance(tx_hash, str) or not re.fullmatch(WORD_PATTERN, tx_hash) or type(tx_block) is not int:
        raise ScenarioError("Setup FX-01 tidak menghasilkan referensi transaksi yang valid.")
    target_issuer, first_decision = prepare_issuer(client, admin, run_id)

    before = registry.snapshot(proof_id)
    issuer_b_ref = hashlib.sha256(f"lettrust:issuer:{issuer_b}".encode()).hexdigest()
    if (
        issued["issuerId"] != issuer_b
        or issued["lifecycleStatus"] != "ACTIVE"
        or not before["exists"]
        or before["issuerRef"] != issuer_b_ref
        or before["documentHash"] != hashlib.sha256(pdf).hexdigest()
        or before["lifecycleStatus"] != "ACTIVE"
    ):
        raise ScenarioError("Bukti setup belum ACTIVE untuk penerbit B pada registry yang diuji.")

    evidence["setup"] = {"issueTransaction": {"hash": tx_hash, "blockNumber": tx_block}}
    for case in ("a", "b", "c"):
        record_http(cases, case, (FORBIDDEN,), request(client, "POST", PROOFS, token=tokens[case], **upload))

    revoke = {"json": {"reasonCode": "OFFER_WITHDRAWN"}, "token": tokens["owner-a"]}
    foreign = record_http(
        cases, "d", (NOT_FOUND,), request(client, "POST", f"{PROOFS}/{proof_id}/revocations", **revoke)
    )
    unknown_id = "0x" + secrets.token_hex(32)
    unknown = record_http(
        cases, "d-control", (NOT_FOUND,), request(client, "POST", f"{PROOFS}/{unknown_id}/revocations", **revoke)
    )
    equivalent = bool(unknown) and foreign == unknown
    cases[-2]["actual"]["sameErrorAsUnknownProof"] = equivalent
    cases[-2]["matches"] &= equivalent

    rejected = registry.issuer_mismatch(proof_id, issuer_a)
    cases.append(
        {
            "case": "e",
            "expected": {"revert": "IssuerMismatch", "method": "eth_call"},
            "actual": {"revert": "IssuerMismatch" if rejected else None, "method": "eth_call"},
            "matches": rejected,
        }
    )
    record_http(cases, "f", (FORBIDDEN,), request(client, "POST", PROOFS, token=admin, **upload))
    pending_issuer = profiles["a"]["membership"]["issuerId"]
    record_http(
        cases,
        "g-api02",
        (FORBIDDEN,),
        request(
            client,
            "PATCH",
            f"{ISSUERS}/{pending_issuer}/verification",
            token=tokens["owner-a"],
            json={"decision": "VERIFIED", "evidenceRef": "SCN14-G"},
        ),
    )
    record_http(
        cases,
        "g-api03",
        (FORBIDDEN,),
        request(
            client,
            "POST",
            f"{ISSUERS}/{issuer_a}/hr-authorizations",
            token=tokens["owner-a"],
            json={"hrId": profiles["c"]["userId"]},
        ),
    )
    for case, token, expected in (
        ("h", partner_token, (UNAUTHENTICATED, FORBIDDEN)),
        ("i-missing", None, (UNAUTHENTICATED,)),
        ("i-invalid", "invalid-scn14-token", (UNAUTHENTICATED,)),
    ):
        record_http(cases, case, expected, request(client, "POST", PROOFS, token=token, **upload))

    record_http(
        cases, "j-extraction", (UNAUTHENTICATED,), request(ai, "POST", "/internal/v1/document-extractions", **upload)
    )
    record_http(
        cases,
        "j-api08",
        (UNAUTHENTICATED,),
        request(
            ai, "POST", "/internal/v1/risk-analyses", json={"documentContent": "Surat penawaran kerja sintetis SCN-14."}
        ),
    )

    record_http(
        cases,
        "k",
        (DECIDED,),
        request(
            client,
            "PATCH",
            f"{ISSUERS}/{target_issuer}/verification",
            token=admin,
            json={"decision": "REJECTED", "evidenceRef": f"SCN14-{run_id}-REPEAT"},
        ),
    )
    final_issuer = setup_request(client, "GET", f"{ISSUERS}/{target_issuer}", 200, token=admin)
    decision_unchanged = (
        all(
            final_issuer[key] == first_decision[key]
            for key in (
                "issuerStatus",
                "reviewedBy",
                "reviewedAt",
            )
        )
        and final_issuer["evidenceRef"] == f"SCN14-{run_id}"
    )
    cases[-1]["actual"]["firstDecisionUnchanged"] = decision_unchanged
    cases[-1]["matches"] &= decision_unchanged

    after = registry.snapshot(proof_id)
    events = registry.event_counts(before["block"] + 1, after["block"])
    proof_unchanged = all(
        after[key] == value for key, value in before.items() if key not in {"block", "registrarNonce"}
    )
    no_transactions = (
        before["registrarNonce"] == after["registrarNonce"]
        and not any(events.values())
        and after["block"] >= before["block"]
    )
    evidence["registry"] = {
        "beforeBlock": before["block"],
        "afterBlock": after["block"],
        "beforeRegistrarNonce": before["registrarNonce"],
        "afterRegistrarNonce": after["registrarNonce"],
        "beforeProofStatus": before["lifecycleStatus"],
        "afterProofStatus": after["lifecycleStatus"],
        "events": events,
        "proofUnchanged": proof_unchanged,
        "noTransactions": no_transactions,
    }
    return all(case["matches"] for case in cases) and no_transactions and proof_unchanged


def main() -> int:
    """Menjalankan SCN-14 dan menyimpan ringkasan aman, termasuk hasil parsial saat terhambat."""
    parser = argparse.ArgumentParser(description="Jalankan SCN-14 pada project Compose lokal yang terisolasi.")
    parser.add_argument("--compose-project", help="Nama project Compose, default lettrust.")
    parser.add_argument("--tc-id", default="TC-014", help="ID direktori bukti, default TC-014.")
    args = parser.parse_args()
    if not re.fullmatch(r"TC-[0-9]{3}", args.tc_id):
        parser.error("--tc-id harus berformat TC-xxx.")

    run_id = secrets.token_hex(6)
    evidence: JsonObject = {
        "scenario": "SCN-14",
        "testCaseId": args.tc_id,
        "runId": run_id,
        "startedAt": datetime.now(UTC).isoformat(),
        "cases": [],
    }
    passed = False
    try:
        settings = load_settings()
        values = _read_env(ROOT / ".env")
        project = args.compose_project or os.getenv("COMPOSE_PROJECT_NAME", "lettrust")
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", project):
            raise ScenarioError("Nama project Compose tidak valid.")
        admin_password = os.getenv("SEED_ADMIN_PASSWORD", values.get("SEED_ADMIN_PASSWORD", "")).strip()
        if not admin_password:
            raise ScenarioError("Konfigurasi SEED_ADMIN_PASSWORD belum tersedia.")
        ai_port = os.getenv("AI_SERVICE_HOST_PORT", values.get("AI_SERVICE_HOST_PORT", "8001"))
        ai_url = local_url(os.getenv("LETTRUST_TEST_AI_URL", f"http://127.0.0.1:{ai_port}"))
        backend_url = local_url(settings.api_base_url)
        require_compose_port(project, "backend", 8000, backend_url)
        require_compose_port(project, "ai-service", 8001, ai_url)
        pdf = (ROOT / "fixtures" / "FX-01.pdf").read_bytes()
        if not pdf.startswith(b"%PDF-"):
            raise ScenarioError("Fixture FX-01 bukan PDF.")
        registry = Registry(
            project, os.getenv("REGISTRY_CONTRACT_ADDRESS", values.get("REGISTRY_CONTRACT_ADDRESS", ""))
        )
        with (
            httpx.Client(base_url=backend_url, timeout=30, trust_env=False) as client,
            httpx.Client(base_url=ai_url, timeout=30, trust_env=False) as ai,
        ):
            passed = run_scenario(
                client,
                ai,
                registry,
                pdf,
                run_id,
                settings.seed_hr_password,
                admin_password,
                settings.partner_token,
                evidence,
            )
    except ScenarioError as exc:
        evidence["error"] = str(exc)
    except (httpx.HTTPError, OSError, KeyError, TypeError, ValueError) as exc:
        evidence["error"] = f"Skenario terhenti ({type(exc).__name__})."

    evidence["finishedAt"] = datetime.now(UTC).isoformat()
    evidence["assertionsMatched"] = passed
    try:
        path = save_evidence(args.tc_id, f"scn14-{run_id}.json", evidence)
    except (OSError, ScenarioError):
        print("Bukti SCN-14 gagal disimpan.", file=sys.stderr)
        return 1
    print_expected_actual(
        {"scenario": "SCN-14", "cases": "(a)–(k)", "registryTransactions": 0},
        evidence,
    )
    print(f"Bukti: {path}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
