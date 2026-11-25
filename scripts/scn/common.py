# Owner: Pash (PIC 4) | Status: COMPLETE | Ref: SA §18.3, §21.2; PRD §12.5
"""Helper bersama untuk skrip skenario API Lettrust."""

from __future__ import annotations

import json
import os
import re
import secrets
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_ROOT = ROOT / "docs" / "testing" / "evidence"
SERVICES = {"chain", "backend", "ai-service", "issuer-console", "partner-portal"}
REDACTED_KEYS = {
    "accessToken",
    "authorization",
    "evidence",
    "password",
    "partnerToken",
    "referenceCode",
    "token",
}


class ScenarioError(RuntimeError):
    """Kesalahan skenario yang aman ditampilkan tanpa membocorkan konfigurasi."""


@dataclass(frozen=True)
class ScenarioSettings:
    """Pengaturan koneksi dan akun sintetis; credential disembunyikan dari repr."""

    api_base_url: str
    seed_hr_email: str
    seed_hr_password: str = field(repr=False)
    partner_token: str = field(repr=False)


def _read_env(path: Path) -> dict[str, str]:
    """Membaca pasangan KEY=VALUE dari `.env` tanpa menampilkan nilainya."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) > 1 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key.strip()] = value
    return values


def load_settings() -> ScenarioSettings:
    """Memuat alamat API dan credential lokal dengan environment sebagai override."""
    values = _read_env(ROOT / ".env")

    def get_value(key: str, default: str = "") -> str:
        return os.environ.get(key, values.get(key, default)).strip()

    missing = [key for key in ("SEED_HR_PASSWORD", "PARTNER_TOKEN") if not get_value(key)]
    if missing:
        raise ScenarioError(f"Konfigurasi {', '.join(missing)} belum tersedia; jalankan `python scripts/dev.py up`.")
    port = get_value("BACKEND_HOST_PORT", "8000")
    base_url = get_value("LETTRUST_TEST_API_URL", f"http://127.0.0.1:{port}").rstrip("/")
    return ScenarioSettings(
        api_base_url=base_url,
        seed_hr_email=get_value("SEED_HR_EMAIL", "hr.sinar@lettrust.test"),
        seed_hr_password=get_value("SEED_HR_PASSWORD"),
        partner_token=get_value("PARTNER_TOKEN"),
    )


def new_request_id() -> str:
    """Membuat request ID acak dengan awalan yang disepakati arsitektur."""
    return f"req_{secrets.token_hex(8).upper()}"


def login_seed_hr(client: httpx.Client, settings: ScenarioSettings) -> str:
    """Login akun HR seed dan mengembalikan JWT tanpa mencetaknya."""
    try:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": settings.seed_hr_email, "password": settings.seed_hr_password},
            headers={"X-Request-ID": new_request_id()},
        )
    except httpx.HTTPError as exc:
        raise ScenarioError(f"Login HR seed gagal menghubungi API ({type(exc).__name__}).") from None
    if response.status_code != 200:
        code = _response_error_code(response)
        suffix = f" ({code})" if code else ""
        raise ScenarioError(f"Login HR seed gagal: HTTP {response.status_code}{suffix}.")
    try:
        token = response.json().get("accessToken")
    except (ValueError, AttributeError):
        token = None
    if not isinstance(token, str) or not token:
        raise ScenarioError("Respons login HR seed tidak memuat accessToken.")
    return token


def create_api07_client(settings: ScenarioSettings) -> httpx.Client:
    """Membuat klien API-07 dengan token partner dari `.env`."""
    return httpx.Client(
        base_url=settings.api_base_url,
        timeout=httpx.Timeout(120.0),
        headers={"Authorization": f"Bearer {settings.partner_token}"},
    )


def verify_offer(
    client: httpx.Client,
    reference_code: str,
    file_path: Path,
    *,
    include_risk: bool = False,
) -> httpx.Response:
    """Mengirim PDF dan kode ke API-07 dengan multipart tanpa mencatat input."""
    try:
        with file_path.open("rb") as document:
            return client.post(
                "/api/v1/verifications",
                headers={"X-Request-ID": new_request_id()},
                data={"referenceCode": reference_code, "includeRisk": str(include_risk).lower()},
                files={"file": (file_path.name, document, "application/pdf")},
            )
    except OSError as exc:
        raise ScenarioError(f"Tidak dapat membaca berkas uji ({type(exc).__name__}).") from None


def run_dev_service(action: str, service: str) -> None:
    """Menjalankan perintah stop/start dev.py untuk service yang diizinkan."""
    if action not in {"stop", "start"} or service not in SERVICES:
        raise ScenarioError("Perintah atau nama service dev.py tidak dikenal.")
    command = [sys.executable, str(ROOT / "scripts" / "dev.py"), action, service]
    try:
        subprocess.run(command, cwd=ROOT, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ScenarioError(f"Perintah dev.py {action} {service} gagal ({type(exc).__name__}).") from None


def save_evidence(
    test_case_id: str,
    filename: str,
    payload: dict[str, Any],
    *,
    sensitive_values: tuple[str, ...] = (),
) -> Path:
    """Menyimpan evidence JSON setelah redaksi kode, credential, dan kutipan."""
    if not re.fullmatch(r"TC-[0-9]{3}", test_case_id):
        raise ScenarioError("Test case ID harus berformat TC-xxx.")
    if not re.fullmatch(r"[a-z0-9-]+\.json", filename):
        raise ScenarioError("Nama file evidence tidak valid.")
    target_dir = EVIDENCE_ROOT / test_case_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / filename
    safe_payload = _sanitize(payload, sensitive_values)
    target.write_text(json.dumps(safe_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def print_expected_actual(expected: dict[str, Any], actual: dict[str, Any]) -> None:
    """Mencetak perbandingan hasil untuk penilaian manual tanpa mengisi status TC."""
    print("Expected:")
    print(json.dumps(expected, ensure_ascii=False, indent=2))
    print("Actual:")
    print(json.dumps(actual, ensure_ascii=False, indent=2))


def _response_error_code(response: httpx.Response) -> str | None:
    """Mengambil kode error saja agar pesan upstream mentah tidak ikut tercetak."""
    try:
        code = response.json().get("error", {}).get("code")
    except (ValueError, AttributeError):
        return None
    return code if isinstance(code, str) else None


def _sanitize(value: Any, sensitive_values: tuple[str, ...]) -> Any:
    """Menghapus field terlarang dan nilai credential dari struktur evidence."""
    if isinstance(value, dict):
        redacted = {key.lower() for key in REDACTED_KEYS}
        return {
            key: "[DIHAPUS]" if key.lower() in redacted else _sanitize(item, sensitive_values)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize(item, sensitive_values) for item in value]
    if isinstance(value, str):
        for secret in sensitive_values:
            if secret:
                value = value.replace(secret, "[DIHAPUS]")
    return value
