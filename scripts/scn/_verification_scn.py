# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: T1-08; PRD §12.4 SCN-04/05/10/11/17, MET-16/17; SA §18.3
"""Helper skenario API-07 (T1-08) di atas common.py: permintaan fleksibel, bukti ACTIVE, dan evidence per langkah."""

from __future__ import annotations

import hashlib
import json
import secrets
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx

from common import (
    ROOT,
    ScenarioError,
    ScenarioSettings,
    create_api07_client,
    load_settings,
    login_seed_hr,
    new_request_id,
    print_expected_actual,
    save_evidence,
)

API = "/api/v1"
VERIFY_PATH = f"{API}/verifications"
PROOFS_PATH = f"{API}/proofs"
FIXTURES = ROOT / "fixtures"
JsonObject = dict[str, Any]


def fixture_bytes(name: str) -> bytes:
    """Membaca fixture apa adanya (termasuk FX-08/FX-10 yang sengaja tidak valid)."""
    path = FIXTURES / name
    if not path.is_file():
        raise ScenarioError(f"Fixture tidak ditemukan: fixtures/{name}.")
    return path.read_bytes()


def masked_code(code: str | None) -> str | None:
    """Menyamarkan kode referensi menjadi empat karakter terakhir (SA §17.4)."""
    return None if code is None else f"…{code[-4:]}"


def post_verification(
    client: httpx.Client,
    *,
    code: str | None = None,
    file: tuple[str, bytes] | None = None,
    include_risk: bool | None = None,
    request_id: str | None = None,
) -> tuple[httpx.Response, JsonObject, float]:
    """Mengirim API-07 dengan field opsional; mengembalikan respons, ringkasan request aman, dan durasi ms."""
    request_id = request_id or new_request_id()
    data: dict[str, str] = {}
    if code is not None:
        data["referenceCode"] = code
    if include_risk is not None:
        data["includeRisk"] = str(include_risk).lower()
    files = {"file": (file[0], file[1], "application/pdf")} if file is not None else None
    started = time.perf_counter()
    response = client.post(VERIFY_PATH, headers={"X-Request-ID": request_id}, data=data, files=files)
    elapsed_ms = (time.perf_counter() - started) * 1000
    summary = {
        "method": "POST",
        "path": VERIFY_PATH,
        "requestId": request_id,
        "referenceCode": masked_code(code),
        "includeRisk": include_risk,
        "file": None
        if file is None
        else {"name": file[0], "sizeBytes": len(file[1]), "sha256": hashlib.sha256(file[1]).hexdigest()},
    }
    return response, summary, elapsed_ms


def response_body(response: httpx.Response) -> Any:
    """Mengambil body JSON; None bila respons bukan JSON."""
    try:
        return response.json()
    except ValueError:
        return None


def indicator_codes(body: Any) -> list[str]:
    """Kode indikator dari riskAnalysis.indicatorDetails (bukan teks label/kutipan)."""
    risk = body.get("riskAnalysis") if isinstance(body, dict) else None
    details = risk.get("indicatorDetails") if isinstance(risk, dict) else None
    return [item.get("code") for item in details or [] if isinstance(item, dict)]


def summarize(response: httpx.Response) -> JsonObject:
    """Meringkas status HTTP, kode error, atau enum tiga komponen tanpa kode referensi dan kutipan."""
    body = response_body(response)
    actual: JsonObject = {"httpStatus": response.status_code}
    if not isinstance(body, dict):
        actual["responseFormat"] = "non-JSON"
        return actual
    error = body.get("error")
    if isinstance(error, dict):
        actual["errorCode"] = error.get("code")
        return actual
    proof, integrity, risk = (body.get(key) or {} for key in ("proofCheck", "integrityCheck", "riskAnalysis"))
    actual.update(
        mode=body.get("mode"),
        lookup=proof.get("lookup"),
        proofReason=proof.get("reason"),
        lifecycleStatus=proof.get("lifecycleStatus"),
        integrityResult=integrity.get("result"),
        integrityReason=integrity.get("reason"),
        riskState=risk.get("state"),
        riskReason=risk.get("reason"),
        category=risk.get("category"),
        indicatorCodes=indicator_codes(body),
    )
    return actual


def evidence_body(body: Any) -> Any:
    """Salinan body untuk evidence: teks `indicators` dipotong ke label agar kutipan surat tidak tersimpan."""
    if not isinstance(body, dict) or not isinstance(body.get("riskAnalysis"), dict):
        return body
    copy = json.loads(json.dumps(body))
    risk = copy["riskAnalysis"]
    risk["indicators"] = [str(item).split(":", 1)[0] for item in risk.get("indicators") or []]
    return copy


def ai_service_saw(request_id: str) -> bool:
    """True bila log ai-service memuat requestId ini (backend meneruskan X-Request-ID ke I-01/API-08)."""
    try:
        result = subprocess.run(
            ["docker", "compose", "logs", "--no-log-prefix", "ai-service"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise ScenarioError("Log ai-service tidak dapat dibaca.") from None
    if result.returncode != 0:
        raise ScenarioError("docker compose logs ai-service gagal.")
    return f'"requestId": "{request_id}"' in result.stdout


def active_llm_model() -> str | None:
    """Model LLM aktif di container ai-service (bukan secret) untuk identitas bukti AI."""
    try:
        result = subprocess.run(
            ["docker", "compose", "exec", "-T", "ai-service", "printenv", "LLM_MODEL"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def wait_health(client: httpx.Client, components: tuple[str, ...], timeout: float = 120) -> None:
    """Menunggu komponen health backend berstatus ok setelah service dijalankan ulang."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            body = client.get(f"{API}/health", timeout=10).json()
            if all(body.get("components", {}).get(name) == "ok" for name in components):
                return
        except (httpx.HTTPError, ValueError, AttributeError):
            pass
        time.sleep(2)
    raise ScenarioError(f"Komponen {', '.join(components)} belum sehat dalam {int(timeout)} detik.")


@dataclass
class ActiveProof:
    """Bukti ACTIVE milik penerbit HR seed; kode utuh hanya di memori."""

    reference_code: str = field(repr=False)
    proof_id: str
    document_sha256: str
    issue_transaction: JsonObject | None


def ensure_active_proof(settings: ScenarioSettings, fixture: str = "FX-01.pdf") -> ActiveProof:
    """Memakai bukti ACTIVE HR seed dengan hash fixture yang sama; menerbitkan baru hanya bila belum ada.

    Pencarian dilakukan lebih dulu agar run berulang tidak menambah bukti di registry (FR-03.06 tidak diandalkan).
    """
    content = fixture_bytes(fixture)
    digest = hashlib.sha256(content).hexdigest()
    with httpx.Client(base_url=settings.api_base_url, timeout=60, trust_env=False) as client:
        headers = {"Authorization": f"Bearer {login_seed_hr(client, settings)}"}
        listed = client.get(PROOFS_PATH, headers=headers, params={"status": "ACTIVE", "limit": 100})
        if listed.status_code != 200:
            raise ScenarioError(f"Daftar bukti HR seed gagal: HTTP {listed.status_code}.")
        for item in (response_body(listed) or {}).get("items", []):
            status = response_body(client.get(f"{PROOFS_PATH}/{item['proofId']}", headers=headers)) or {}
            if status.get("documentHash") == digest and status.get("lifecycleStatus") == "ACTIVE":
                return ActiveProof(status["referenceCode"], status["proofId"], digest, status.get("issueTransaction"))
        issued = client.post(
            PROOFS_PATH,
            headers={**headers, "X-Request-ID": new_request_id(), "Idempotency-Key": f"t108-{secrets.token_hex(8)}"},
            files={"file": (fixture, content, "application/pdf")},
        )
        body = response_body(issued) or {}
        if issued.status_code != 201:
            raise ScenarioError(f"Penerbitan {fixture} oleh HR seed gagal: HTTP {issued.status_code}.")
        return ActiveProof(body["referenceCode"], body["proofId"], digest, body.get("transaction"))


@dataclass
class Step:
    """Satu langkah skenario: hasil aktual dibandingkan dengan expected per field; `info` bukan syarat lulus."""

    name: str
    request: JsonObject
    expected: JsonObject
    actual: JsonObject
    response: Any = None
    info: JsonObject = field(default_factory=dict)

    @property
    def matches(self) -> bool:
        """Lulus bila setiap field expected sama dengan nilai aktual."""
        return all(self.actual.get(key) == value for key, value in self.expected.items())


def check_ai_subset(step: Step, expected_codes: set[str]) -> None:
    """LLM nyata: label wajib ada (subset); indikator tambahan hanya dicatat sebagai info."""
    codes = set(step.actual.get("indicatorCodes") or [])
    step.actual["labelIndicatorsPresent"] = expected_codes <= codes
    step.expected["labelIndicatorsPresent"] = True
    step.info["labelIndicators"] = sorted(expected_codes)
    step.info["extraIndicators"] = sorted(codes - expected_codes)


def run_scenario(
    scenario: str, test_case: str, slug: str, execute: Callable[[ScenarioSettings, httpx.Client], list[Step]]
) -> int:
    """Menjalankan langkah, menyimpan evidence tersanitasi, dan mencetak expected vs actual (tanpa mengisi TC)."""
    settings: ScenarioSettings | None = None
    steps: list[Step] = []
    failure = None
    started = datetime.now(UTC)
    try:
        settings = load_settings()
        with create_api07_client(settings) as client:
            steps = execute(settings, client)
    except ScenarioError as exc:
        failure = str(exc)
    except httpx.HTTPError as exc:
        failure = f"Request gagal ({type(exc).__name__})."
    evidence = {
        "testCaseId": test_case,
        "scenario": scenario,
        "startedAtUtc": started.isoformat(),
        "finishedAtUtc": datetime.now(UTC).isoformat(),
        "completed": failure is None,
        "failure": failure,
        "steps": [
            {
                "name": step.name,
                "request": step.request,
                "expected": step.expected,
                "actual": step.actual,
                "matches": step.matches,
                "info": step.info,
                "response": evidence_body(step.response),
            }
            for step in steps
        ],
    }
    secrets_to_hide = (settings.partner_token, settings.seed_hr_password) if settings else ()
    filename = f"{slug}-{started.strftime('%Y%m%d-%H%M%S%f')}.json"
    path = save_evidence(test_case, filename, evidence, sensitive_values=secrets_to_hide)
    print_expected_actual(
        {step.name: step.expected for step in steps},
        {
            step.name: {**step.actual, "matches": step.matches, **({"info": step.info} if step.info else {})}
            for step in steps
        },
    )
    print(f"Evidence tersimpan: {path.relative_to(ROOT).as_posix()}")
    if failure is not None:
        print(f"{scenario} tidak dapat diselesaikan: {failure}", file=sys.stderr)
        return 2
    return 0 if all(step.matches for step in steps) else 1
