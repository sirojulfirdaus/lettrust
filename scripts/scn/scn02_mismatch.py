# Owner: Pash (PIC 4) | Status: COMPLETE | Ref: PRD SCN-02; SA §18.3, §21.2
"""Menjalankan SCN-02 dengan bukti FX-01 yang sudah diterbitkan dan FX-02."""

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
    create_api07_client,
    load_settings,
    print_expected_actual,
    save_evidence,
    verify_offer,
)

REFERENCE_CODE_PATTERN = re.compile(r"^LTR-[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{4}$")
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


# Membuat nama evidence berhuruf kecil yang lolos validasi common.save_evidence.
def evidence_filename() -> str:
    return f"scn02-mismatch-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S%f')}.json"


def parse_args() -> argparse.Namespace:
    """Membaca lokasi FX-02 tanpa menerima credential atau kode pada argumen."""
    parser = argparse.ArgumentParser(description="Jalankan SCN-02 pada API-07 stack nyata.")
    parser.add_argument(
        "--fx02",
        type=Path,
        default=ROOT / "fixtures" / "FX-02.pdf",
        help="Path fixture sintetis FX-02.",
    )
    return parser.parse_args()


def validate_fixture(path: Path) -> tuple[Path, str]:
    """Memastikan FX-02 PDF non-kosong dalam batas unggah dan menghitung hash byte asli."""
    resolved = path.expanduser().resolve()
    if not resolved.is_file() or resolved.suffix.lower() != ".pdf":
        raise ScenarioError(f"Fixture PDF FX-02 tidak ditemukan: {resolved}.")
    content = resolved.read_bytes()
    if not content.startswith(b"%PDF-") or not content or len(content) > MAX_UPLOAD_BYTES:
        raise ScenarioError("FX-02 harus berupa PDF valid dan berukuran maksimal 5 MiB.")
    return resolved, hashlib.sha256(content).hexdigest()


def read_reference_code() -> str:
    """Meminta kode bukti FX-01 tanpa menampilkannya di terminal."""
    try:
        code = getpass.getpass("Kode referensi dari bukti FX-01 (input disembunyikan): ").strip().upper()
    except (EOFError, KeyboardInterrupt):
        raise ScenarioError("Input kode referensi dibatalkan.") from None
    if not REFERENCE_CODE_PATTERN.fullmatch(code):
        raise ScenarioError("Kode referensi tidak sesuai format LTR-XXXX-XXXX-XXXX.")
    return code


def response_summary(response: httpx.Response) -> dict[str, Any]:
    """Meringkas field assertion API tanpa memasukkan kode atau kutipan ke terminal."""
    actual: dict[str, Any] = {"httpStatus": response.status_code}
    try:
        body = response.json()
    except ValueError:
        actual["responseFormat"] = "non-JSON"
        return actual
    if not isinstance(body, dict):
        actual["responseFormat"] = "invalid"
        return actual
    error = body.get("error")
    if isinstance(error, dict):
        actual["errorCode"] = error.get("code")
        return actual
    proof = body.get("proofCheck")
    integrity = body.get("integrityCheck")
    if isinstance(proof, dict):
        actual["proofLookup"] = proof.get("lookup")
        actual["lifecycleStatus"] = proof.get("lifecycleStatus")
    if isinstance(integrity, dict):
        actual["integrityResult"] = integrity.get("result")
    actual["verificationId"] = body.get("verificationId")
    return actual


def main() -> int:
    """Mengirim FX-02 ke API-07, menyimpan evidence aman, dan mengembalikan hasil assertion."""
    args = parse_args()
    try:
        fixture, fixture_hash = validate_fixture(args.fx02)
        reference_code = read_reference_code()
        settings = load_settings()
        expected = {
            "httpStatus": 200,
            "proofLookup": "FOUND",
            "lifecycleStatus": "ACTIVE",
            "integrityResult": "MISMATCH",
        }
        with create_api07_client(settings) as client:
            response = verify_offer(client, reference_code, fixture, include_risk=False)
        actual = response_summary(response)
        print_expected_actual(expected, actual)

        try:
            response_body: Any = response.json()
        except ValueError:
            response_body = None
        evidence = {
            "testCaseId": "TC-002",
            "scenario": "SCN-02",
            "executedAtUtc": datetime.now(UTC).isoformat(),
            "request": {
                "method": "POST",
                "path": "/api/v1/verifications",
                "referenceCode": reference_code,
                "includeRisk": False,
                "file": {"name": fixture.name, "sizeBytes": fixture.stat().st_size, "sha256": fixture_hash},
            },
            "expected": expected,
            "actual": actual,
            "response": response_body,
        }
        filename = evidence_filename()
        evidence_path = save_evidence(
            "TC-002",
            filename,
            evidence,
            sensitive_values=(settings.partner_token, reference_code),
        )
        print(f"Evidence tersimpan: {evidence_path.relative_to(ROOT).as_posix()}")
        assertions = ("httpStatus", "proofLookup", "lifecycleStatus", "integrityResult")
        return 0 if all(actual.get(key) == expected[key] for key in assertions) else 1
    except ScenarioError as exc:
        print(f"SCN-02 tidak dapat dijalankan: {exc}", file=sys.stderr)
        return 2
    except httpx.HTTPError as exc:
        print(f"Request API-07 gagal ({type(exc).__name__}).", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
