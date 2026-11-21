# Owner: Zan (PIC 3) | Status: STUB | Ref: PRD FR-01.03–FR-01.06; SA §10.4, §10.5, §8.3
# TODO: Ganti `raise not_implemented()` dengan pemanggilan issuers.service.
"""Router SVC-01: API-01, S-04, S-05, API-02, API-03."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import error_responses, not_implemented
from app.core.schemas import ErrorCode
from app.modules.auth.dependencies import current_user, require_admin
from app.modules.auth.models import User
from app.modules.auth.schemas import IssuerStatus
from app.modules.issuers.dependencies import require_unaffiliated_hr
from app.modules.issuers.schemas import (
    AuthorizeHrRequest,
    AuthorizeHrResponse,
    IssuerDetailResponse,
    IssuerListResponse,
    RegisterIssuerRequest,
    RegisterIssuerResponse,
    VerifyIssuerRequest,
    VerifyIssuerResponse,
)

router = APIRouter(prefix="/issuers", tags=["issuers"])
IssuerIdPath = Annotated[str, Path(alias="issuerId")]


# API-01 registerIssuer: HR tidak terafiliasi mendaftarkan perusahaan.
@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=RegisterIssuerResponse,
    operation_id="registerIssuer",
    responses=error_responses(
        ErrorCode.UNAUTHENTICATED,
        ErrorCode.FORBIDDEN_OPERATION,
        ErrorCode.ACCOUNT_ALREADY_AFFILIATED,
        ErrorCode.REGISTRATION_NUMBER_ALREADY_EXISTS,
    ),
)
async def register_issuer(
    payload: RegisterIssuerRequest,
    user: Annotated[User, Depends(require_unaffiliated_hr)],
    db: Annotated[Session, Depends(get_db)],
) -> RegisterIssuerResponse:
    raise not_implemented()


# S-04: daftar penerbit untuk Administrator.
@router.get(
    "",
    response_model=IssuerListResponse,
    operation_id="listIssuers",
    responses=error_responses(ErrorCode.UNAUTHENTICATED, ErrorCode.FORBIDDEN_OPERATION),
)
async def list_issuers(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    status_filter: Annotated[IssuerStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> IssuerListResponse:
    raise not_implemented()


# S-05: detail penerbit untuk Administrator atau anggota penerbit.
@router.get(
    "/{issuerId}",
    response_model=IssuerDetailResponse,
    operation_id="getIssuer",
    responses=error_responses(ErrorCode.UNAUTHENTICATED, ErrorCode.ISSUER_NOT_FOUND),
)
async def get_issuer(
    issuer_id: IssuerIdPath,
    user: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> IssuerDetailResponse:
    raise not_implemented()


# API-02 verifyIssuer: keputusan verifikasi oleh Administrator.
@router.patch(
    "/{issuerId}/verification",
    response_model=VerifyIssuerResponse,
    operation_id="verifyIssuer",
    responses=error_responses(
        ErrorCode.UNAUTHENTICATED,
        ErrorCode.FORBIDDEN_OPERATION,
        ErrorCode.ISSUER_NOT_FOUND,
        ErrorCode.ISSUER_DECISION_ALREADY_MADE,
    ),
)
async def verify_issuer(
    issuer_id: IssuerIdPath,
    payload: VerifyIssuerRequest,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> VerifyIssuerResponse:
    raise not_implemented()


# API-03 authorizeHR: otorisasi HR terafiliasi oleh Administrator.
@router.post(
    "/{issuerId}/hr-authorizations",
    status_code=status.HTTP_201_CREATED,
    response_model=AuthorizeHrResponse,
    operation_id="authorizeHR",
    responses=error_responses(
        ErrorCode.UNAUTHENTICATED,
        ErrorCode.FORBIDDEN_OPERATION,
        ErrorCode.ISSUER_NOT_FOUND,
        ErrorCode.ISSUER_NOT_VERIFIED,
        ErrorCode.HR_NOT_AFFILIATED,
        ErrorCode.HR_ALREADY_AUTHORIZED,
    ),
)
async def authorize_hr(
    issuer_id: IssuerIdPath,
    payload: AuthorizeHrRequest,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> AuthorizeHrResponse:
    raise not_implemented()
