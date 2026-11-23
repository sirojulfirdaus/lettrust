# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: PRD FR-02.07, FR-06.01–FR-06.06; SA §5.2, §10.4, §10.7
"""Router API-07 verifyOffer (hanya client partner)."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

from app.core.errors import error_responses
from app.core.files import read_uploaded_pdf
from app.core.schemas import ErrorCode
from app.modules.partners.dependencies import partner_client
from app.modules.partners.models import Partner
from app.modules.verifications import orchestrator
from app.modules.verifications.schemas import VerificationResponse

router = APIRouter(prefix="/verifications", tags=["verifications"])


# API-07 verifyOffer: HTTP 200 untuk setiap permintaan valid yang diproses, termasuk hasil parsial (DLT-14).
# Urutan SA §5.2: token partner (dependency) → kode dan kombinasi input → validasi berkas → orkestrasi; kegagalan
# validasi berhenti sebelum registry atau AI dipanggil. Parameter `file` hanya untuk OpenAPI dan penanda keberadaan
# berkas; isinya dibaca sekali oleh read_uploaded_pdf.
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
    request: Request,
    partner: Annotated[Partner, Depends(partner_client)],
    reference_code: Annotated[str | None, Form(alias="referenceCode")] = None,
    file: Annotated[UploadFile | None, File(description="PDF opsional, maks MAX_UPLOAD_BYTES.")] = None,
    include_risk: Annotated[bool, Form(alias="includeRisk")] = False,
) -> VerificationResponse:
    code = orchestrator.resolve_reference_code(reference_code, has_file=file is not None, include_risk=include_risk)
    validated = await read_uploaded_pdf(request)
    return await orchestrator.verify_offer(partner, code, validated, include_risk, request.state.request_id)
