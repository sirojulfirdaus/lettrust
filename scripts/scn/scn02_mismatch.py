"""Menjalankan SCN-02 terhadap API-07 dengan FX-02 dan bukti FX-01 yang aktif."""

from __future__ import annotations

import argparse
import getpass
import hashlib
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from common import (
    ROOT,
    ScenarioError,
    load_settings,
    print_expected_actual,
    save_evidence,
    verify_offer,
)

REFERENCE_CODE_PATTERN = re.compile(r"^LTR-[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{4}$")
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def parse_args() -> argparse.Namespace:
    """Membaca path fixture tanpa menerima token atau kode referensi di argumen shell."""
    parser = argparse.ArgumentParser(description="Verifikasi mismatch SCN-02 pada stack Lettrust nyata.")
    parser.add_argument("--fx02", type=Path, default=ROOT / "fixtures" / "FX-02.pdf", help="Path ke fixture sintetis FX-02.")
    return parser.parse_args()


def validate_fixture(path: Path) -> tuple[Path, str]:
    """Memastikan fixture FX-02 berupa PDF kecil dan menghasilkan hash byte aslinya."""
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise ScenarioError(f"Fixture FX-02 tidak ditemukan: {resolved}.")
    if resolved.suffix.lower() != ".pdf":
        raise ScenarioError("Fixture FX-02 harus berekstensi .pdf.")
    content = resolved.read_bytes()
    if not content.startswith(b"%PDF-"):
        raise ScenarioError("Fixture FX-02 tidak memiliki header PDF.")
    if not content or len(content) > MAX_UPLOAD_BYTES:
        raise ScenarioError("Fixture FX-02 kosong atau melebihi batas unggah 5 MiB.")
    return resolved, hashlib.sha256(content).hexdigest()


def read_reference_code() -> str:
    """Meminta kode bukti SCN-01 tanpa menggemakannya ke terminal."""
    try:
        reference_code = getpass.getpass("Kode referensi dari penerbitan FX-01 (input disembunyikan): ").strip().upper()
    except (EOFError, KeyboardInterrupt):
        raise ScenarioError("Input kode referensi dibatalkan.") from None
    if not REFERENCE_CODE_PATTERN.fullmatch(reference_code):
        raise ScenarioError("Kode referensi tidak sesuai format LTR-XXXX-XXXX-XXXX.")
    return reference_code


def response_summary(response: httpx.Response) -> dict[str, Any]:
    """Meringkas status API-07 tanpa menyimpan kutipan model atau kode referensi."""
    summary: dict[str, Any] = {"httpStatus": response.status_code}
    try:
        body = response.json()
    except ValueError:
        summary["body"] = "Respons bukan JSON."
        return summary
    if not isinstance(body, dict):
        summary["body"] = "Bentuk respons bukan object JSON."
        return summary
    if isinstance(body.get("error"), dict):
        summary["errorCode"] = body["error"].get("code")
        return summary
    proof = body.get("proofCheck")
    integrity = body.get("integrityCheck")
    if isinstance(proof, dict):
        summary["proofLookup"] = proof.get("lookup")
        summary["lifecycleStatus"] = proof.get("lifecycleStatus")
    if isinstance(integrity, dict):
        summary["integrityResult"] = integrity.get("result")
    summary["verificationId"] = body.get("verificationId")
    return summary


def main() -> int:
    """Menjalankan request API-07, menyimpan evidence yang aman, dan melaporkan actual."""
    args = parse_args()
    try:
        fixture_path, fixture_hash = validate_fixture(args.fx02)
        reference_code = read_reference_code()
        settings = load_settings()
        expected = {
            "httpStatus": 200,
            "proofLookup": "FOUND",
            "lifecycleStatus": "ACTIVE",
            "integrityResult": "MISMATCH",
            "guidance": "G-04 ditampilkan di portal",
        }
        with httpx.Client(base_url=settings.api_base_url, timeout=httpx.Timeout(120.0)) as client:
            response = verify_offer(client, settings, reference_code, fixture_path, include_risk=False)
        actual = response_summary(response)
        print_expected_actual(expected, actual)

        evidence: dict[str, Any] = {
            "testCaseId": "TC-002",
            "scenario": "SCN-02",
            "executedAtUtc": datetime.now(UTC).isoformat(),
            "request": {
                "method": "POST",
                "path": "/api/v1/verifications",
                "referenceCode": reference_code,
                "includeRisk": False,
                "file": {"name": fixture_path.name, "sizeBytes": fixture_path.stat().st_size, "sha256": fixture_hash},
            },
            "expected": expected,
            "actual": actual,
            "response": response.json() if response.headers.get("content-type", "").startswith("application/json") else None,
        }
        filename = f"scn02-mismatch-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
        evidence_path = save_evidence(
            "TC-002",
            filename,
            evidence,
            sensitive_values=(settings.partner_token, reference_code),
        )
        print(f"Evidence tersimpan: {evidence_path.relative_to(ROOT).as_posix()}")
        matches = all(actual.get(key) == expected[key] for key in ("httpStatus", "proofLookup", "lifecycleStatus", "integrityResult"))
        return 0 if matches else 1
    except ScenarioError as exc:
        print(f"SCN-02 tidak dapat dijalankan: {exc}", file=sys.stderr)
        return 2
    except httpx.HTTPError as exc:
        print(f"SCN-02 gagal menghubungi API ({type(exc).__name__}).", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
