# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: PRD FR-03.11; SA §5.3.2
"""Test tabel keputusan integritas SA §5.3.2 dengan data bukti dari tests/fakes/proofs.py."""

import pytest
from fakes.proofs import (
    MATCHING_FILE_BYTES,
    MISMATCHING_FILE_BYTES,
    found_active,
    found_revoked,
    not_found,
    not_requested,
    registry_unavailable,
)

from app.core.config import get_settings
from app.core.files import validate_pdf_bytes
from app.modules.verifications.integrity import integrity_from
from app.modules.verifications.schemas import VerificationMode

REF = VerificationMode.REFERENCE_CHECK
# SHA-256 berkas diambil dari ValidatedFile (T1-02), sama seperti yang akan dilakukan orkestrator.
MATCHING_SHA = validate_pdf_bytes(MATCHING_FILE_BYTES, get_settings().max_upload_bytes).sha256
MISMATCHING_SHA = validate_pdf_bytes(MISMATCHING_FILE_BYTES, get_settings().max_upload_bytes).sha256


# Menjalankan integrity_from untuk satu hasil fake proof reader dan mengembalikan JSON kontrak.
def check(mode: VerificationMode, read, file_sha256: str | None) -> dict:
    result = integrity_from(mode, read.proof_check, read.registry_document_hash, file_sha256)
    return result.model_dump(by_alias=True, mode="json")


# Setiap baris tabel SA §5.3.2.
@pytest.mark.parametrize(
    ("mode", "read", "file_sha256", "expected"),
    [
        (VerificationMode.AI_ONLY, not_requested(), MATCHING_SHA, ("NOT_CHECKED", "NO_REFERENCE_CODE", None)),
        (REF, found_active(), None, ("NOT_CHECKED", "NO_FILE", None)),
        (REF, found_active(), MATCHING_SHA, ("MATCH", None, "SHA-256")),
        (REF, found_active(), MISMATCHING_SHA, ("MISMATCH", None, "SHA-256")),
        (REF, found_revoked(), MATCHING_SHA, ("MATCH", None, "SHA-256")),
        (REF, found_revoked(), MISMATCHING_SHA, ("MISMATCH", None, "SHA-256")),
        (REF, not_found(), MATCHING_SHA, ("NOT_CHECKED", "PROOF_NOT_FOUND", None)),
        (REF, not_found(), None, ("NOT_CHECKED", "PROOF_NOT_FOUND", None)),
        (REF, registry_unavailable(), MATCHING_SHA, ("NOT_CHECKED", "REGISTRY_UNAVAILABLE", None)),
        (REF, registry_unavailable(), None, ("NOT_CHECKED", "REGISTRY_UNAVAILABLE", None)),
    ],
    ids=[
        "ai-only",
        "found-no-file",
        "active-match",
        "active-mismatch",
        "revoked-match",
        "revoked-mismatch",
        "not-found-file",
        "not-found-no-file",
        "unavailable-file",
        "unavailable-no-file",
    ],
)
def test_integrity_table(mode, read, file_sha256, expected):
    result = check(mode, read, file_sha256)
    assert (result["result"], result["reason"], result["hashAlgorithm"]) == expected


# Mode Tanpa Kode tidak pernah menghasilkan MATCH/MISMATCH walau hash berkas tersedia.
def test_ai_only_ignores_hash_even_if_present():
    assert check(VerificationMode.AI_ONLY, found_active(), MATCHING_SHA)["result"] == "NOT_CHECKED"


# Kombinasi yang tidak mungkin dari pemanggil (REFERENCE_CHECK + NOT_REQUESTED, FOUND tanpa hash) → ValueError.
def test_inconsistent_proof_check_rejected():
    with pytest.raises(ValueError):
        check(REF, not_requested(), MATCHING_SHA)
    found = found_active()
    with pytest.raises(ValueError):
        integrity_from(REF, found.proof_check, None, MATCHING_SHA)
