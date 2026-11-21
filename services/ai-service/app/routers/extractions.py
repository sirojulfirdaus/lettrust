# Owner: B (PIC 5) | Status: STUB | Ref: PRD FR-05.02–FR-05.04, FR-06.06; SA §7.2, §10.8 (I-01)
# TODO: Validasi berkas (kosong 400, >MAX_UPLOAD_BYTES 413, tanpa %PDF- 415) lalu extraction.service.extract_document.
"""Router I-01 document-extractions (hanya backend, X-Internal-Token)."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile

from app.core.auth import internal_caller
from app.core.errors import not_implemented
from app.schemas import ExtractionResponse

router = APIRouter(tags=["extraction"], dependencies=[Depends(internal_caller)])


# I-01: ekstraksi teks PDF dan OCR; NO_CONTENT dikembalikan dengan HTTP 200.
@router.post("/document-extractions", response_model=ExtractionResponse, operation_id="extractDocument")
async def extract_document(file: Annotated[UploadFile, File(description="Satu berkas PDF.")]) -> ExtractionResponse:
    raise not_implemented()
