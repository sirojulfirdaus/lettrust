# Owner: B (PIC 5) | Status: COMPLETE | Ref: PRD FR-05.02–FR-05.04, FR-06.06; SA §7.2, §10.8 (I-01)
"""Router I-01 document-extractions (hanya backend, X-Internal-Token)."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, UploadFile
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.core.auth import internal_caller
from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode
from app.extraction import service
from app.schemas import ExtractionResponse


# Menolak unggahan jamak sebelum validasi field wajib, termasuk bila nama field bukan `file`.
async def validate_single_file(request: Request) -> None:
    form = await request.form()
    if sum(isinstance(value, StarletteUploadFile) for _, value in form.multi_items()) > 1:
        raise AppError(ErrorCode.MULTIPLE_FILES)


router = APIRouter(tags=["extraction"], dependencies=[Depends(internal_caller), Depends(validate_single_file)])


# I-01: ekstraksi teks PDF dan OCR; NO_CONTENT dikembalikan dengan HTTP 200.
@router.post("/document-extractions", response_model=ExtractionResponse, operation_id="extractDocument")
async def extract_document(file: Annotated[UploadFile, File(description="Satu berkas PDF.")]) -> ExtractionResponse:
    settings = get_settings()
    try:
        file_bytes = await file.read(settings.max_upload_bytes + 1)
    finally:
        await file.close()
    if not file_bytes:
        raise AppError(ErrorCode.EMPTY_FILE)
    if len(file_bytes) > settings.max_upload_bytes:
        raise AppError(ErrorCode.FILE_TOO_LARGE)
    if not file_bytes.startswith(b"%PDF-"):
        raise AppError(ErrorCode.UNSUPPORTED_MEDIA_TYPE)
    return await run_in_threadpool(service.extract_document, file_bytes, settings)
