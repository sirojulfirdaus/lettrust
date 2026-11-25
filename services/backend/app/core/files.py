# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: PRD FR-03.01, FR-06.06, NFR-02.01; SA §5.2, §5.6, §10.3
"""Validasi berkas unggahan bersama API-04 dan API-07: tepat satu PDF, dibaca di memori, SHA-256 dari byte asli.

Batas transport (body_limit.py) tetap berlaku lebih dulu; modul ini memvalidasi berkas per permintaan.
"""

import hashlib
from dataclasses import dataclass

from fastapi import Request
from starlette.datastructures import UploadFile

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.schemas import ErrorCode

FILE_FIELD = "file"
PDF_SIGNATURE = b"%PDF-"


@dataclass(frozen=True, slots=True)
class ValidatedFile:
    """Berkas PDF lolos validasi: byte asli di memori dan SHA-256-nya (64 hex huruf kecil, tanpa `0x`)."""

    content: bytes
    sha256: str


# Mengambil berkas field `file` dari form multipart request lalu memvalidasinya (SA §5.2 langkah 6).
# Mengembalikan None bila tidak ada berkas; melempar AppError MULTIPLE_FILES/EMPTY_FILE/FILE_TOO_LARGE/
# UNSUPPORTED_MEDIA_TYPE. Form sudah di-parse dan di-cache FastAPI, sehingga body tidak dibaca ulang.
async def read_uploaded_pdf(request: Request) -> ValidatedFile | None:
    form = await request.form()
    # Parameter `file: UploadFile` di router hanya menerima satu nilai; berkas lain dihitung dari seluruh form.
    if sum(isinstance(value, UploadFile) for _, value in form.multi_items()) > 1:
        raise AppError(ErrorCode.MULTIPLE_FILES)
    upload = next((value for value in form.getlist(FILE_FIELD) if isinstance(value, UploadFile)), None)
    if upload is None:
        return None
    max_bytes = get_settings().max_upload_bytes
    await upload.seek(0)
    # Membaca paling banyak batas + 1 byte: cukup untuk mendeteksi berkas yang terlalu besar.
    return validate_pdf_bytes(await upload.read(max_bytes + 1), max_bytes)


# Memvalidasi byte berkas dengan urutan SA §5.2 (kosong 400, ukuran 413, tanda tangan PDF 415) lalu menghitung
# SHA-256 atas byte asli. Isi PDF tidak diperiksa: PDF rusak berheader valid tetap lolos (SCN-11(d), FR-06.06/AC-04).
def validate_pdf_bytes(content: bytes, max_bytes: int) -> ValidatedFile:
    if not content:
        raise AppError(ErrorCode.EMPTY_FILE)
    if len(content) > max_bytes:
        raise AppError(ErrorCode.FILE_TOO_LARGE)
    if not content.startswith(PDF_SIGNATURE):
        raise AppError(ErrorCode.UNSUPPORTED_MEDIA_TYPE)
    return ValidatedFile(content=content, sha256=hashlib.sha256(content).hexdigest())
