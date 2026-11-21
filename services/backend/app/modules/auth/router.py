# Owner: Zan (PIC 3) | Status: STUB | Ref: PRD FR-01.01, FR-01.02, FR-01.04; SA §10.4, §10.5
# TODO: Ganti `raise not_implemented()` dengan pemanggilan auth.service.
"""Router endpoint akun: S-01 register, S-02 login, S-03 me."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import error_responses, not_implemented
from app.core.schemas import ErrorCode
from app.modules.auth.dependencies import current_user
from app.modules.auth.models import User
from app.modules.auth.schemas import LoginRequest, LoginResponse, MeResponse, RegisterAccountRequest, UserSummary

router = APIRouter(prefix="/auth", tags=["auth"])


# S-01: registrasi akun HR (publik).
@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=UserSummary,
    operation_id="registerAccount",
    responses=error_responses(ErrorCode.EMAIL_ALREADY_REGISTERED),
)
async def register_account(payload: RegisterAccountRequest, db: Annotated[Session, Depends(get_db)]) -> UserSummary:
    raise not_implemented()


# S-02: login email + password (publik).
@router.post(
    "/login",
    response_model=LoginResponse,
    operation_id="login",
    responses=error_responses(ErrorCode.INVALID_CREDENTIALS),
)
async def login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> LoginResponse:
    raise not_implemented()


# S-03: profil sesi dan membership (JWT).
@router.get(
    "/me",
    response_model=MeResponse,
    operation_id="getSession",
    responses=error_responses(ErrorCode.UNAUTHENTICATED),
)
async def get_session(
    user: Annotated[User, Depends(current_user)], db: Annotated[Session, Depends(get_db)]
) -> MeResponse:
    raise not_implemented()
