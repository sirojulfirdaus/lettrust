# Owner: Dws (PIC 1) | Status: STUB | Ref: PRD FR-02.07, FR-06.01–FR-06.06; SA §10.4, §10.7
# TODO: Ganti `raise not_implemented()` dengan validasi input/berkas lalu orchestrator.verify_offer.
"""Router API-07 verifyOffer (hanya client partner)."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.core.errors import error_responses, not_implemented
from app.core.schemas import ErrorCode
from app.modules.partners.dependencies import partner_client
from app.modules.partners.models import Partner
from app.modules.verifications.schemas import VerificationResponse

router = APIRouter(prefix="/verifications", tags=["verifications"])


# API-07 verifyOffer: HTTP 200 untuk setiap permintaan valid yang diproses, termasuk hasil parsial (DLT-14).
@router.post(
    "",
    response_model=VerificationResponse,
    operation_id="verifyOffer",
    responses=error_responses(
        ErrorCode.INVALID_INPUT_COMBINATION,
        ErrorCode.AI_ONLY_REQUIRES_INCLUDE_RISK,
        ErrorCode.INVALID_REFERENCE_CODE_FORMAT,
        ErrorCode.EMPTY_FILE,
        ErrorCode.MULTIPLE_FILES,
        ErrorCode.UNAUTHENTICATED,
        ErrorCode.FILE_TOO_LARGE,
        ErrorCode.UNSUPPORTED_MEDIA_TYPE,
        ErrorCode.RATE_LIMITED,
        ErrorCode.SERVICE_UNAVAILABLE,
    ),
)
async def verify_offer(
    partner: Annotated[Partner, Depends(partner_client)],
    reference_code: Annotated[str | None, Form(alias="referenceCode")] = None,
    file: Annotated[UploadFile | None, File(description="PDF opsional, maks MAX_UPLOAD_BYTES.")] = None,
    include_risk: Annotated[bool, Form(alias="includeRisk")] = False,
) -> VerificationResponse:
    raise not_implemented()
