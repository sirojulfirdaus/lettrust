# Owner: B (PIC 5) | Status: COMPLETE | Ref: PLAN T5-06; PRD §12.4.1; SA §5.2
"""Memeriksa byte fixture melalui validator unggahan backend nyata, tanpa registry atau LLM."""

import hashlib
from pathlib import Path

import pytest

from app.core.errors import AppError
from app.core.files import validate_pdf_bytes

FIXTURES = Path(__file__).resolve().parent
MAX_BYTES = 5_242_880


# Validator upload hanya memeriksa signature dan ukuran; FX-10 rusak tetap lolos ke ekstraksi.
@pytest.mark.parametrize("index", [1, 2, 3, 4, 5, 6, 7, 10])
def test_pdf_header_and_size_are_accepted(index: int) -> None:
    content = (FIXTURES / f"FX-{index:02}.pdf").read_bytes()
    upload = validate_pdf_bytes(content, MAX_BYTES)
    assert upload.content == content
    assert upload.sha256 == hashlib.sha256(content).hexdigest()


# FX-08 dan FX-09 memicu kode/status penolakan yang diperlukan SCN-11.
@pytest.mark.parametrize(
    "identifier, code, status", [("FX-08", "UNSUPPORTED_MEDIA_TYPE", 415), ("FX-09", "FILE_TOO_LARGE", 413)]
)
def test_invalid_upload_error(identifier: str, code: str, status: int) -> None:
    with pytest.raises(AppError) as failure:
        validate_pdf_bytes((FIXTURES / f"{identifier}.pdf").read_bytes(), MAX_BYTES)
    assert failure.value.code.value == code
    assert failure.value.status_code == status


# Pengubahan nominal gaji mengubah documentHash walaupun kedua berkas lolos validasi upload.
def test_changed_offer_has_different_raw_document_hash() -> None:
    original = validate_pdf_bytes((FIXTURES / "FX-01.pdf").read_bytes(), MAX_BYTES)
    changed = validate_pdf_bytes((FIXTURES / "FX-02.pdf").read_bytes(), MAX_BYTES)
    assert original.sha256 != changed.sha256
