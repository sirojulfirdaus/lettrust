# Owner: Zan (PIC 3) | Status: STUB | Ref: PRD FR-03.01–FR-03.09, FR-04.01–FR-04.07; SA §10.4, §10.6, §8.3
# TODO: Ganti `raise not_implemented()` dengan proofs.service; berkas dibaca sekali ke memori (maks MAX_UPLOAD_BYTES+1).
"""Router SVC-02: API-04, S-06, API-05, API-06."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Header, Path, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import error_responses, not_implemented
from app.core.schemas import ErrorCode
from app.modules.issuers.dependencies import AuthorizedHrContext, authorized_hr
from app.modules.proofs.schemas import (
    IssueProofResponse,
    LifecycleStatus,
    ProofListResponse,
    ProofStatusResponse,
    RevokeProofRequest,
    RevokeProofResponse,
)

router = APIRouter(prefix="/proofs", tags=["proofs"])
ProofIdPath = Annotated[str, Path(alias="proofId")]
IdempotencyKeyHeader = Annotated[str | None, Header(alias="Idempotency-Key", max_length=100)]


# API-04 issueProof: HR berwenang mengunggah PDF final untuk dicatat di registry.
@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=IssueProofResponse,
    operation_id="issueProof",
    responses=error_responses(
        ErrorCode.EMPTY_FILE,
        ErrorCode.MULTIPLE_FILES,
        ErrorCode.UNAUTHENTICATED,
        ErrorCode.FORBIDDEN_OPERATION,
        ErrorCode.IDEMPOTENCY_KEY_CONFLICT,
        ErrorCode.DUPLICATE_ACTIVE_DOCUMENT,
        ErrorCode.FILE_TOO_LARGE,
        ErrorCode.UNSUPPORTED_MEDIA_TYPE,
        ErrorCode.REGISTRY_UNAVAILABLE,
        ErrorCode.REGISTRY_TRANSACTION_FAILED,
    ),
)
async def issue_proof(
    hr: Annotated[AuthorizedHrContext, Depends(authorized_hr)],
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File(description="Satu berkas PDF final, maks MAX_UPLOAD_BYTES.")],
    issuer_id: Annotated[str | None, Form(alias="issuerId")] = None,
    idempotency_key: IdempotencyKeyHeader = None,
) -> IssueProofResponse:
    raise not_implemented()


# S-06: daftar bukti milik penerbit HR.
@router.get(
    "",
    response_model=ProofListResponse,
    operation_id="listProofs",
    responses=error_responses(ErrorCode.UNAUTHENTICATED, ErrorCode.FORBIDDEN_OPERATION),
)
async def list_proofs(
    hr: Annotated[AuthorizedHrContext, Depends(authorized_hr)],
    db: Annotated[Session, Depends(get_db)],
    status_filter: Annotated[LifecycleStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ProofListResponse:
    raise not_implemented()


# API-05 getProofStatus: status bukti dibaca dari registry.
@router.get(
    "/{proofId}",
    response_model=ProofStatusResponse,
    operation_id="getProofStatus",
    responses=error_responses(
        ErrorCode.UNAUTHENTICATED,
        ErrorCode.FORBIDDEN_OPERATION,
        ErrorCode.PROOF_NOT_FOUND,
        ErrorCode.REGISTRY_UNAVAILABLE,
    ),
)
async def get_proof_status(
    proof_id: ProofIdPath,
    hr: Annotated[AuthorizedHrContext, Depends(authorized_hr)],
    db: Annotated[Session, Depends(get_db)],
) -> ProofStatusResponse:
    raise not_implemented()


# API-06 revokeProof: pencabutan bukti ACTIVE milik penerbit HR.
@router.post(
    "/{proofId}/revocations",
    status_code=status.HTTP_201_CREATED,
    response_model=RevokeProofResponse,
    operation_id="revokeProof",
    responses=error_responses(
        ErrorCode.UNAUTHENTICATED,
        ErrorCode.FORBIDDEN_OPERATION,
        ErrorCode.PROOF_NOT_FOUND,
        ErrorCode.PROOF_ALREADY_REVOKED,
        ErrorCode.IDEMPOTENCY_KEY_CONFLICT,
        ErrorCode.REGISTRY_UNAVAILABLE,
        ErrorCode.REGISTRY_TRANSACTION_FAILED,
    ),
)
async def revoke_proof(
    proof_id: ProofIdPath,
    payload: RevokeProofRequest,
    hr: Annotated[AuthorizedHrContext, Depends(authorized_hr)],
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: IdempotencyKeyHeader = None,
) -> RevokeProofResponse:
    raise not_implemented()
