"""Helper bersama untuk skrip skenario API Lettrust."""

from __future__ import annotations

import json
import os
import re
import secrets
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT / ".env"
EVIDENCE_ROOT = ROOT / "docs" / "testing" / "evidence"
ALLOWED_SERVICES = {
    "chain",
    "backend",
    "ai-service",
    "issuer-console",
    "partner-portal",
}
SENSITIVE_KEYS = {
    "accessToken",
    "authorization",
    "evidence",
    "indicators",
    "indicatorDetails",
    "password",
    "partnerToken",
    "referenceCode",
    "token",
}


class ScenarioError(RuntimeError):
    """Kesalahan skenario dengan pesan aman untuk ditampilkan di terminal."""


@dataclass(frozen=True)
class ScenarioSettings:
    """Konfigurasi endpoint dan akun sintetis; secret dikecualikan dari repr."""

    api_base_url: str
    seed_hr_email: str
    seed_hr_password: str = field(repr=False)
    partner_token: str = field(repr=False)


def _read_env_file(path: Path) -> dict[str, str]:
    """Membaca pasangan KEY=VALUE tanpa mencetak isi konfigurasi lokal."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key.strip()] = value
    return values


def load_settings() -> ScenarioSettings:
    """Memuat credential HR seed dan token partner tanpa menampilkan nilainya."""
    file_values = _read_env_file(ENV_FILE)

    def value(key: str, default: str = "") -> str:
        return os.environ.get(key, file_values.get(key, default)).strip()

    missing = [key for key in ("SEED_HR_PASSWORD", "PARTNER_TOKEN") if not value(key)]
    if missing:
        raise ScenarioError(
            f"Konfigurasi {', '.join(missing)} belum tersedia. Jalankan `python scripts/dev.py up` terlebih dahulu."
        )
    port = value("BACKEND_HOST_PORT", "8000")
    base_url = value("LETTRUST_TEST_API_URL", f"http://127.0.0.1:{port}").rstrip("/")
    return ScenarioSettings(
        api_base_url=base_url,
        seed_hr_email=value("SEED_HR_EMAIL", "hr.sinar@lettrust.test"),
        seed_hr_password=value("SEED_HR_PASSWORD"),
        partner_token=value("PARTNER_TOKEN"),
    )


def new_request_id() -> str:
    """Membuat ID request acak sesuai format request ID arsitektur."""
    return f"req_{secrets.token_hex(8).upper()}"


def login_seed_hr(client: httpx.Client, settings: ScenarioSettings) -> str:
    """Login sebagai HR seed dan mengembalikan JWT tanpa mencetaknya."""
    try:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": settings.seed_hr_email, "password": settings.seed_hr_password},
            headers={"X-Request-ID": new_request_id()},
        )
    except httpx.HTTPError as exc:
        raise ScenarioError(f"Login HR seed gagal menghubungi API ({type(exc).__name__}).") from None
    if response.status_code != 200:
        code = _error_code(response)
        suffix = f" ({code})" if code else ""
        raise ScenarioError(f"Login HR seed gagal: HTTP {response.status_code}{suffix}.")
    try:
        token = response.json().get("accessToken")
    except (ValueError, AttributeError):
        token = None
    if not isinstance(token, str) or not token:
        raise ScenarioError("Respons login HR seed tidak memuat accessToken.")
    return token


def api07_headers(partner_token: str) -> dict[str, str]:
    """Membentuk header API-07 tanpa mengekspos token ke output."""
    return {
        "Authorization": f"Bearer {partner_token}",
        "X-Request-ID": new_request_id(),
    }


def verify_offer(
    client: httpx.Client,
    settings: ScenarioSettings,
    reference_code: str,
    file_path: Path,
    *,
    include_risk: bool = False,
) -> httpx.Response:
    """Mengirim satu PDF ke API-07 dengan token partner dari konfigurasi lokal."""
    try:
        with file_path.open("rb") as document:
            return client.post(
                "/api/v1/verifications",
                headers=api07_headers(settings.partner_token),
                data={"referenceCode": reference_code, "includeRisk": str(include_risk).lower()},
                files={"file": (file_path.name, document, "application/pdf")},
            )
    except OSError as exc:
        raise ScenarioError(f"Tidak dapat membaca berkas uji ({type(exc).__name__}).") from None
    except httpx.HTTPError as exc:
        raise ScenarioError(f"Request API-07 gagal ({type(exc).__name__}).") from None


def stop_service(service: str) -> None:
    """Menghentikan service skenario melalui launcher resmi."""
    _run_dev_service_action("stop", service)


def start_service(service: str) -> None:
    """Menjalankan kembali service skenario melalui launcher resmi."""
    _run_dev_service_action("start", service)


def _run_dev_service_action(action: str, service: str) -> None:
    """Memvalidasi target sebelum memanggil dev.py tanpa shell."""
    if service not in ALLOWED_SERVICES:
        raise ScenarioError(f"Nama service tidak dikenal: {service}.")
    command = [sys.executable, str(ROOT / "scripts" / "dev.py"), action, service]
    try:
        subprocess.run(command, cwd=ROOT, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ScenarioError(f"Perintah dev.py {action} {service} gagal ({type(exc).__name__}).") from None


def save_evidence(
    test_case_id: str,
    filename: str,
    evidence: dict[str, Any],
    *,
    sensitive_values: tuple[str, ...] = (),
) -> Path:
    """Menyimpan JSON evidence setelah menghapus secret dan data terlarang."""
    if not re.fullmatch(r"TC-[0-9]{3}", test_case_id):
        raise ScenarioError("Test case ID evidence harus berformat TC-xxx.")
    if not re.fullmatch(r"[a-z0-9-]+\.json", filename):
        raise ScenarioError("Nama file evidence tidak valid.")
    target_dir = EVIDENCE_ROOT / test_case_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / filename
    cleaned = _sanitize(evidence, sensitive_values)
    target.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def print_expected_actual(expected: dict[str, Any], actual: dict[str, Any]) -> None:
    """Mencetak expected dan actual untuk penilaian manual, tanpa menandai dokumen PASS."""
    print("Expected:")
    print(json.dumps(expected, ensure_ascii=False, indent=2))
    print("Actual:")
    print(json.dumps(actual, ensure_ascii=False, indent=2))


def _error_code(response: httpx.Response) -> str | None:
    """Mengambil hanya kode error yang aman, bukan body pesan mentah."""
    try:
        code = response.json().get("error", {}).get("code")
    except (ValueError, AttributeError):
        return None
    return code if isinstance(code, str) else None


def _sanitize(value: Any, sensitive_values: tuple[str, ...]) -> Any:
    """Membersihkan field rahasia, kode referensi, dan kutipan dari struktur JSON."""
    if isinstance(value, dict):
        return {
            key: "[DIHAPUS]" if key.lower() in {item.lower() for item in SENSITIVE_KEYS} else _sanitize(item, sensitive_values)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize(item, sensitive_values) for item in value]
    if isinstance(value, str):
        cleaned = value
        for secret in sensitive_values:
            if secret:
                cleaned = cleaned.replace(secret, "[DIHAPUS]")
        return cleaned
    return value
