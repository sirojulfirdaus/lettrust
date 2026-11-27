# Owner: Sat (PIC 6) | Status: COMPLETE | Ref: T6-06; PRD SCN-15/16/20; SA §18.3
"""Helper khusus skenario registry; memakai helper bersama tanpa mengubah common.py."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic, sleep
from typing import Any

import httpx

from common import (
    ROOT,
    ScenarioError,
    _read_env,
    load_settings,
    login_seed_hr,
    new_request_id,
    print_expected_actual,
    run_dev_service,
    save_evidence,
    verify_offer,
)
from scn14_authz_negative import Registry, command_result, local_url, require_compose_port

API = "/api/v1"
PROOFS = f"{API}/proofs"
EVENTS = {
    "ProofIssued": (
        "ProofIssued(bytes32 indexed proofId,bytes32 indexed issuerRef,bytes32 documentHash,uint64 issuedAt)"
    ),
    "ProofRevoked": "ProofRevoked(bytes32 indexed proofId,bytes32 indexed issuerRef,uint64 revokedAt)",
}
JsonObject = dict[str, Any]


def json_object(response: httpx.Response) -> JsonObject:
    """Membaca objek JSON tanpa menyertakan body mentah pada pesan kegagalan."""
    try:
        body = response.json()
    except ValueError:
        raise ScenarioError("Respons API bukan JSON yang valid.") from None
    if not isinstance(body, dict):
        raise ScenarioError("Respons API bukan objek JSON.")
    return body


def number(value: Any) -> int:
    """Membaca bilangan receipt Cast baik dalam representasi heksadesimal maupun desimal."""
    if isinstance(value, bool):
        raise ScenarioError("Bilangan registry tidak valid.")
    return int(value, 16) if isinstance(value, str) and value.startswith("0x") else int(value)


def fixture(path: Path) -> bytes:
    """Membaca fixture PDF asli tanpa mengubah byte yang dipakai untuk hashing dan unggahan."""
    content = path.read_bytes()
    if not content.startswith(b"%PDF-") or not 0 < len(content) <= 5 * 1024 * 1024:
        raise ScenarioError("Fixture bukan PDF dalam batas unggahan.")
    return content


class Scenario:
    """Konteks satu run registry dengan akun terisolasi, pemeriksaan eksplisit, dan evidence tersanitasi."""

    def __init__(
        self,
        client: httpx.Client,
        partner: httpx.Client,
        registry: Registry,
        report: JsonObject,
        sensitive: list[str],
    ) -> None:
        """Memisahkan klien HR dan partner; credential hanya berada di memori selama run."""
        self.client, self.partner, self.registry = client, partner, registry
        self.report, self.sensitive = report, sensitive
        self.token = ""
        self.fx01 = ROOT / "fixtures" / "FX-01.pdf"
        self.fx02 = ROOT / "fixtures" / "FX-02.pdf"

    def check(self, name: str, expected: Any, actual: Any) -> None:
        """Menyimpan expected/actual lalu menghentikan run gagal tanpa mengisi status TC otomatis."""
        matches = actual == expected
        self.report["checks"].append({"name": name, "expected": expected, "actual": actual, "matches": matches})
        if not matches:
            raise ScenarioError(f"Pemeriksaan {name} tidak sesuai expected result.")

    def request(
        self,
        method: str,
        path: str,
        *,
        key: str | None = None,
        pdf: Path | None = None,
        payload: JsonObject | None = None,
    ) -> httpx.Response:
        """Mencatat operasi bukti dengan request ringkas tanpa header auth, isi file, atau alasan bebas."""
        headers = {"Authorization": f"Bearer {self.token}", "X-Request-ID": new_request_id()}
        if key is not None:
            headers["Idempotency-Key"] = key
        options: JsonObject = {"headers": headers}
        if pdf is not None:
            content = fixture(pdf)
            options["files"] = {"file": (pdf.name, content, "application/pdf")}
        elif payload is not None:
            options["json"] = payload
        response = self.client.request(method, path, **options)
        body = json_object(response)
        reference = body.get("referenceCode")
        if isinstance(reference, str):
            self.sensitive.append(reference)
        self.report["requests"].append(
            {
                "request": {
                    "method": method,
                    "path": path,
                    "requestId": headers["X-Request-ID"],
                    "hasIdempotencyKey": key is not None,
                    "fixtureSha256": hashlib.sha256(content).hexdigest() if pdf is not None else None,
                },
                "response": {"status": response.status_code, "body": body},
            }
        )
        return response

    def expect(self, name: str, response: httpx.Response, status: int, code: str | None = None) -> JsonObject:
        """Membandingkan status HTTP dan kode error tanpa mencetak pesan atau respons mentah."""
        body = json_object(response)
        error = body.get("error")
        actual_code = error.get("code") if isinstance(error, dict) else None
        self.check(name, {"status": status, "code": code}, {"status": response.status_code, "code": actual_code})
        return body

    def setup(self, admin_password: str) -> None:
        """Membuat HR/penerbit sintetis baru agar fixture sama dapat dipakai pada run berulang."""
        run_id = self.report["runId"]
        settings = load_settings()
        login_seed_hr(self.client, settings)
        admin = self.client.post(f"{API}/auth/login", json={"email": "admin@lettrust.test", "password": admin_password})
        admin_token = self.expect("setup-admin", admin, 200)["accessToken"]
        self.sensitive.append(admin_token)
        email, password = f"scn-registry-{run_id}@lettrust.test", secrets.token_urlsafe(24)
        self.sensitive.append(password)
        self.expect(
            "setup-register",
            self.client.post(
                f"{API}/auth/register", json={"displayName": "HR Uji Registry", "email": email, "password": password}
            ),
            201,
        )
        session = self.expect(
            "setup-login", self.client.post(f"{API}/auth/login", json={"email": email, "password": password}), 200
        )
        self.token = session["accessToken"]
        self.sensitive.append(self.token)
        hr = {"Authorization": f"Bearer {self.token}"}
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        issuer = self.expect(
            "setup-issuer",
            self.client.post(
                f"{API}/issuers",
                headers=hr,
                json={"companyName": "PT Uji Registry Sintetis", "registrationNumber": run_id, "contactEmail": email},
            ),
            201,
        )
        issuer_id = issuer["issuerId"]
        verified = self.expect(
            "setup-verify",
            self.client.patch(
                f"{API}/issuers/{issuer_id}/verification",
                headers=admin_headers,
                json={"decision": "VERIFIED", "evidenceRef": f"T6-06-{run_id}"},
            ),
            200,
        )
        self.check("issuer-verified", "VERIFIED", verified["issuerStatus"])
        authorized = self.expect(
            "setup-authorize",
            self.client.post(
                f"{API}/issuers/{issuer_id}/hr-authorizations",
                headers=admin_headers,
                json={"hrId": session["user"]["userId"]},
            ),
            201,
        )
        self.check("hr-authorized", "AUTHORIZED", authorized["authorizationStatus"])
        self.report["issuerId"] = issuer_id

    def events(self, proof_id: str, event: str) -> list[JsonObject]:
        """Membaca event Anvil terfilter proofId untuk mendeteksi transaksi ganda."""
        if not re.fullmatch(r"0x[0-9a-f]{64}", proof_id) or event not in EVENTS:
            raise ScenarioError("Filter event registry tidak valid.")
        logs = json.loads(
            self.registry.cast(
                "logs",
                "--address",
                self.registry.address,
                "--from-block",
                "0",
                "--to-block",
                "latest",
                "--json",
                EVENTS[event],
                proof_id,
            )
        )
        if not isinstance(logs, list) or any(not isinstance(item, dict) for item in logs):
            raise ScenarioError("Respons event registry tidak valid.")
        return logs

    def confirmed(self, body: JsonObject, event: str) -> None:
        """Mencocokkan referensi API dengan receipt sukses dan tepat satu event bukti pada Anvil nyata."""
        proof_id, transaction = body["proofId"], body["transaction"]
        tx_hash = transaction["hash"]
        if not isinstance(tx_hash, str) or not re.fullmatch(r"0x[0-9a-f]{64}", tx_hash):
            raise ScenarioError("Hash transaksi API tidak valid.")
        receipt = json.loads(self.registry.cast("receipt", tx_hash, "--json"))
        self.check(f"{event}-receipt", 1, number(receipt["status"]))
        self.check(f"{event}-hash", tx_hash, receipt["transactionHash"].lower())
        self.check(f"{event}-block", transaction["blockNumber"], number(receipt["blockNumber"]))
        self.check(f"{event}-contract", self.registry.address.lower(), receipt["to"].lower())
        logs = self.events(proof_id, event)
        self.check(f"{event}-count", 1, len(logs))
        self.check(f"{event}-transaction", tx_hash, logs[0]["transactionHash"].lower())
        self.check(f"{event}-event-block", transaction["blockNumber"], number(logs[0]["blockNumber"]))
        self.report["transactions"].append(
            {"proofId": proof_id, "event": event, "hash": tx_hash, "blockNumber": number(receipt["blockNumber"])}
        )

    def issue(self, path: Path, key: str) -> JsonObject:
        """Menerbitkan byte fixture asli dan memeriksa status ACTIVE, hash, serta receipt terkonfirmasi."""
        body = self.expect("issue", self.request("POST", PROOFS, key=key, pdf=path), 201)
        self.check("issued-active", "ACTIVE", body["lifecycleStatus"])
        self.check("issued-document-hash", hashlib.sha256(fixture(path)).hexdigest(), body["documentHash"])
        self.confirmed(body, "ProofIssued")
        self.check("issued-on-chain", "ACTIVE", self.registry.snapshot(body["proofId"])["lifecycleStatus"])
        return body

    def revoke(self, proof_id: str, key: str | None) -> httpx.Response:
        """Mencabut melalui API-06 dengan alasan enum yang tetap off-chain."""
        return self.request(
            "POST", f"{PROOFS}/{proof_id}/revocations", key=key, payload={"reasonCode": "OFFER_WITHDRAWN"}
        )

    def read(self, proof_id: str) -> JsonObject:
        """Membaca API-05 dan memastikan sumber lifecycle merupakan registry."""
        body = self.expect("read-proof", self.request("GET", f"{PROOFS}/{proof_id}"), 200)
        self.check("status-source", "REGISTRY", body["source"])
        return body

    def verify(self, issued: JsonObject, path: Path, lifecycle: str) -> None:
        """Memastikan lookup kode dan hash tetap benar tanpa meminta analisis AI pada skenario registry."""
        response = verify_offer(self.partner, issued["referenceCode"], path, include_risk=False)
        body = self.expect("verify-offer", response, 200)
        self.report["requests"].append(
            {
                "request": {"method": "POST", "path": f"{API}/verifications", "includeRisk": False},
                "response": {"status": response.status_code, "body": body},
            }
        )
        self.check("lookup-found", "FOUND", body["proofCheck"]["lookup"])
        self.check("lookup-status", lifecycle, body["proofCheck"]["lifecycleStatus"])
        self.check("integrity-match", "MATCH", body["integrityCheck"]["result"])
        self.check("ai-not-requested", "NOT_REQUESTED", body["riskAnalysis"]["state"])

    def wait_ready(self, timeout: float = 90) -> None:
        """Menunggu database dan registry siap setelah restart, dengan tenggat polling terbatas."""
        deadline = monotonic() + timeout
        while monotonic() < deadline:
            try:
                response = self.client.get(f"{API}/health", timeout=8)
                components = json_object(response).get("components", {})
                if response.status_code == 200 and components.get("database") == components.get("registry") == "ok":
                    return
            except (httpx.HTTPError, ScenarioError):
                pass
            sleep(1)
        raise ScenarioError("Database/registry belum siap setelah batas waktu pemulihan.")

    @contextmanager
    def chain_outage(self) -> Iterator[None]:
        """Selalu mencoba memulihkan chain melalui helper dev.py, termasuk ketika pemeriksaan gagal."""
        try:
            run_dev_service("stop", "chain")
            yield
        finally:
            run_dev_service("start", "chain")
            self.wait_ready()

    def restart_stack(self) -> None:
        """Melakukan down/up normal tanpa reset atau penghapusan volume, dan memulihkan saat down gagal."""
        try:
            self.dev("down")
        finally:
            self.dev("up")
            self.wait_ready()

    def dev(self, action: str) -> None:
        """Membatasi operasi seluruh stack ke down/up dengan keluaran tertangkap tanpa log aplikasi."""
        if action not in {"down", "up"}:
            raise ScenarioError("Operasi stack tidak diizinkan.")
        try:
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "dev.py"), action],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=900,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ScenarioError(f"dev.py {action} gagal ({type(exc).__name__}).") from None
        if result.returncode != 0:
            raise ScenarioError(f"dev.py {action} gagal; periksa health stack lokal.")

    def no_reactivation(self, proof_id: str) -> None:
        """Membandingkan API live dan ABI serta mensimulasikan selector reaktivasi tanpa transaksi."""
        schema = json_object(self.client.get("/openapi.json"))
        mutations = {
            (path, method)
            for path, methods in schema["paths"].items()
            if path.startswith(PROOFS)
            for method in methods
            if method in {"post", "patch", "put", "delete"}
        }
        self.check(
            "proof-mutation-endpoints",
            sorted([f"POST {PROOFS}", f"POST {PROOFS}/{{proofId}}/revocations"]),
            sorted(f"{method.upper()} {path}" for path, method in mutations),
        )
        abi_path = ROOT / "services/backend/app/modules/registry/abi/OfferProofRegistry.json"
        artifact = json.loads(abi_path.read_text())
        abi = artifact if isinstance(artifact, list) else artifact["abi"]
        functions = sorted(item["name"] for item in abi if item.get("type") == "function")
        self.check("registry-functions", ["getProof", "issueProof", "registrar", "revokeProof"], functions)
        self.report["abiSha256"] = hashlib.sha256(abi_path.read_bytes()).hexdigest()
        result = command_result(
            *self.registry.cast_command,
            "call",
            self.registry.address,
            "reactivateProof(bytes32)",
            proof_id,
            "--from",
            self.registry.registrar,
            *self.registry.rpc_args,
        )
        self.check("reactivation-call-rejected", True, result.returncode != 0 and "revert" in result.stderr.lower())


def run_cli(scenario_id: str, tc_id: str, execute: Callable[[Scenario], None]) -> int:
    """Menjalankan satu skenario lokal dan tetap menyimpan hasil parsial tanpa secret ketika gagal."""
    parser = argparse.ArgumentParser(
        description=f"{scenario_id}: registry nyata; service lokal akan dihentikan sementara."
    )
    parser.add_argument(
        "--allow-service-interruption", action="store_true", help="Izinkan stop/start chain atau down/up stack lokal."
    )
    parser.add_argument("--compose-project", default=os.getenv("COMPOSE_PROJECT_NAME", "lettrust"))
    args = parser.parse_args()
    if not args.allow_service_interruption:
        parser.error("Tambahkan --allow-service-interruption pada stack lokal khusus pengujian.")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", args.compose_project):
        parser.error("Nama project Compose tidak valid.")
    os.environ["COMPOSE_PROJECT_NAME"] = args.compose_project
    run_id = secrets.token_hex(8)
    report: JsonObject = {
        "scenario": scenario_id,
        "testCaseId": tc_id,
        "runId": run_id,
        "startedAt": datetime.now(UTC).isoformat(),
        "composeProject": args.compose_project,
        "checks": [],
        "requests": [],
        "transactions": [],
        "completed": False,
    }
    sensitive: list[str] = []
    try:
        settings, values = load_settings(), _read_env(ROOT / ".env")
        secret_keys = (
            "SEED_HR_PASSWORD",
            "SEED_ADMIN_PASSWORD",
            "PARTNER_TOKEN",
            "INTERNAL_API_TOKEN",
            "JWT_SECRET",
            "REGISTRY_SIGNER_PRIVATE_KEY",
            "LLM_API_KEY",
        )
        sensitive.extend(value for key in secret_keys if (value := os.getenv(key, values.get(key, ""))))
        admin_password = os.getenv("SEED_ADMIN_PASSWORD", values.get("SEED_ADMIN_PASSWORD", ""))
        sensitive.extend([settings.seed_hr_password, settings.partner_token, admin_password])
        if not admin_password:
            raise ScenarioError("SEED_ADMIN_PASSWORD belum dikonfigurasi.")
        url = local_url(settings.api_base_url)
        require_compose_port(args.compose_project, "backend", 8000, url)
        address = os.getenv("REGISTRY_CONTRACT_ADDRESS", values.get("REGISTRY_CONTRACT_ADDRESS", ""))
        registry = Registry(args.compose_project, address)
        report.update(registryAddress=registry.address, chainId=31337)
        with (
            httpx.Client(base_url=url, timeout=45, trust_env=False) as client,
            httpx.Client(
                base_url=url, timeout=45, trust_env=False, headers={"Authorization": f"Bearer {settings.partner_token}"}
            ) as partner,
        ):
            scenario = Scenario(client, partner, registry, report, sensitive)
            scenario.wait_ready()
            scenario.setup(admin_password)
            execute(scenario)
            report["completed"] = True
    except (ScenarioError, httpx.HTTPError, OSError, ValueError, KeyError, TypeError) as exc:
        report["failure"] = {"type": type(exc).__name__}
        print(
            f"{scenario_id} belum selesai ({type(exc).__name__}); periksa evidence dan health stack.", file=sys.stderr
        )
    except KeyboardInterrupt:
        report["failure"] = {"type": "KeyboardInterrupt"}
    report["finishedAt"] = datetime.now(UTC).isoformat()
    filename = f"{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{run_id}.json"
    try:
        path = save_evidence(tc_id, filename, report, sensitive_values=tuple(sensitive))
    except (OSError, TypeError, ValueError):
        print("Evidence tidak dapat disimpan.", file=sys.stderr)
        return 1
    print_expected_actual(
        {"scenario": scenario_id, "completed": True, "allChecksMatch": True},
        {
            "scenario": scenario_id,
            "completed": report["completed"],
            "allChecksMatch": all(item["matches"] for item in report["checks"]),
            "checks": len(report["checks"]),
            "evidence": str(path.relative_to(ROOT)),
        },
    )
    return 0 if report["completed"] else 1
