# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: PRD FR-03.01/AC-02, FR-06.06, NFR-02.01; SA §5.2, §10.3; SCN-11
"""Test validasi berkas bersama (core/files.py) lewat route uji yang meniru parameter API-04 dan API-07."""

import hashlib
from collections.abc import Iterator
from typing import Annotated

import pytest
from fastapi import File, Form, Request, UploadFile
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.files import ValidatedFile, read_uploaded_pdf, validate_pdf_bytes
from app.core.schemas import ErrorCode
from app.main import create_app

MAX_BYTES = get_settings().max_upload_bytes
VALID_PDF = b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n%%EOF\n"
# Setara FX-10: header PDF valid, isi rusak (FX-10 asli dari T5-06 belum tersedia).
CORRUPT_PDF = b"%PDF-1.4\n\x00\xff\x13garbage-not-a-pdf-object-tree\xde\xad\xbe\xef"


# Respons route uji: hash dan ukuran berkas tervalidasi, atau null bila tidak ada berkas.
def _summary(validated: ValidatedFile | None) -> dict:
    if validated is None:
        return {"file": None}
    return {"file": {"sha256": validated.sha256, "size": len(validated.content)}}


# Klien untuk app nyata (middleware dan handler error asli) ditambah dua route uji yang meniru router.
@pytest.fixture(scope="module")
def files_client() -> Iterator[TestClient]:
    app = create_app()

    # Meniru API-04: satu berkas wajib.
    async def required_file(request: Request, file: Annotated[UploadFile, File()]) -> dict:
        return _summary(await read_uploaded_pdf(request))

    # Meniru API-07: berkas opsional bersama field form lain.
    async def optional_file(
        request: Request,
        reference_code: Annotated[str | None, Form(alias="referenceCode")] = None,
        file: Annotated[UploadFile | None, File()] = None,
    ) -> dict:
        return _summary(await read_uploaded_pdf(request))

    app.add_api_route("/test/required-file", required_file, methods=["POST"])
    app.add_api_route("/test/optional-file", optional_file, methods=["POST"])
    with TestClient(app) as client:
        yield client


# Memastikan respons berupa envelope error SA §10.2 dengan kode dan status yang diharapkan.
def _assert_error(response, status: int, code: ErrorCode) -> None:
    assert response.status_code == status
    body = response.json()
    assert body["error"]["code"] == code.value
    assert body["requestId"] == response.headers["X-Request-ID"]


# PDF valid: lolos di kedua bentuk route; SHA-256 dihitung dari byte asli.
@pytest.mark.parametrize("path", ["/test/required-file", "/test/optional-file"])
def test_valid_pdf_returns_hash_of_raw_bytes(files_client, path):
    response = files_client.post(path, files={"file": ("offer.pdf", VALID_PDF, "application/pdf")})
    assert response.status_code == 200
    assert response.json() == {"file": {"sha256": hashlib.sha256(VALID_PDF).hexdigest(), "size": len(VALID_PDF)}}


# Tanpa berkas pada API-07 → None (kombinasi input divalidasi orkestrator, bukan modul ini).
def test_no_file_returns_none(files_client):
    response = files_client.post("/test/optional-file", data={"referenceCode": "LTR-7K3M-9QX2-H4TD"})
    assert response.status_code == 200
    assert response.json() == {"file": None}


# Lebih dari satu berkas, termasuk berkas di field lain → 400 MULTIPLE_FILES.
@pytest.mark.parametrize("path", ["/test/required-file", "/test/optional-file"])
@pytest.mark.parametrize("second_field", ["file", "attachment"])
def test_multiple_files_rejected(files_client, path, second_field):
    files = [
        ("file", ("a.pdf", VALID_PDF, "application/pdf")),
        (second_field, ("b.pdf", VALID_PDF, "application/pdf")),
    ]
    _assert_error(files_client.post(path, files=files), 400, ErrorCode.MULTIPLE_FILES)


# Berkas kosong → 400 EMPTY_FILE.
def test_empty_file_rejected(files_client):
    response = files_client.post("/test/optional-file", files={"file": ("offer.pdf", b"", "application/pdf")})
    _assert_error(response, 400, ErrorCode.EMPTY_FILE)


# Tepat di batas diterima; satu byte di atas batas (masih di bawah batas transport) → 413 FILE_TOO_LARGE.
def test_size_limit_boundary(files_client):
    at_limit = VALID_PDF + b"0" * (MAX_BYTES - len(VALID_PDF))
    response = files_client.post("/test/required-file", files={"file": ("offer.pdf", at_limit, "application/pdf")})
    assert response.status_code == 200
    assert response.json()["file"]["size"] == MAX_BYTES
    over = at_limit + b"0"
    response = files_client.post("/test/required-file", files={"file": ("offer.pdf", over, "application/pdf")})
    _assert_error(response, 413, ErrorCode.FILE_TOO_LARGE)


# Tanpa tanda tangan `%PDF-` di awal → 415, terlepas dari nama berkas dan content type yang dikirim.
@pytest.mark.parametrize("content", [b"PK\x03\x04docx", b"\x89PNG\r\n\x1a\n", b" %PDF-1.4\n", b"%PDF1.4"])
def test_non_pdf_signature_rejected(files_client, content):
    response = files_client.post("/test/required-file", files={"file": ("offer.pdf", content, "application/pdf")})
    _assert_error(response, 415, ErrorCode.UNSUPPORTED_MEDIA_TYPE)


# Setara FX-10 (SCN-11(d)): header PDF valid tetapi isi rusak tetap lolos dan hash dihitung dari byte.
def test_corrupt_pdf_with_valid_header_passes(files_client):
    response = files_client.post("/test/optional-file", files={"file": ("rusak.pdf", CORRUPT_PDF, "text/plain")})
    assert response.status_code == 200
    assert response.json()["file"]["sha256"] == hashlib.sha256(CORRUPT_PDF).hexdigest()


# Urutan pemeriksaan SA §5.2: kosong sebelum ukuran, ukuran sebelum tanda tangan.
def test_validation_order():
    with pytest.raises(AppError) as empty:
        validate_pdf_bytes(b"", max_bytes=4)
    assert empty.value.code is ErrorCode.EMPTY_FILE
    with pytest.raises(AppError) as too_large:
        validate_pdf_bytes(b"not-a-pdf", max_bytes=4)
    assert too_large.value.code is ErrorCode.FILE_TOO_LARGE
    validated = validate_pdf_bytes(b"%PDF-", max_bytes=5)
    assert validated == ValidatedFile(content=b"%PDF-", sha256=hashlib.sha256(b"%PDF-").hexdigest())
