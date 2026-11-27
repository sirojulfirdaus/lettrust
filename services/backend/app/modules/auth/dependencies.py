# Owner: Zan (PIC 3) | Status: COMPLETE | Ref: PRD FR-01.02, FR-01.07; SA §8.1, §8.2
"""Dependency FastAPI untuk autentikasi JWT Console dan pemeriksaan role."""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import AppError
from app.core.schemas import ErrorCode
from app.core.security import decode_access_token
from app.modules.auth.models import User
from app.modules.auth.schemas import Role

console_bearer = HTTPBearer(
    auto_error=False,
    scheme_name="ConsoleJWT",
    description="JWT HS256 dari S-02 login (Lettrust Console).",
)


# Mengembalikan user dari JWT valid; gagal 401 UNAUTHENTICATED (token partner juga ditolak).
def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(console_bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None:
        raise AppError(ErrorCode.UNAUTHENTICATED)

    claims = decode_access_token(credentials.credentials)
    user = db.get(User, claims["sub"])
    if user is None:
        raise AppError(ErrorCode.UNAUTHENTICATED)
    return user


# Mensyaratkan role ADMIN dari basis data; gagal 403 FORBIDDEN_OPERATION.
def require_admin(user: Annotated[User, Depends(current_user)]) -> User:
    if user.role != Role.ADMIN:
        raise AppError(ErrorCode.FORBIDDEN_OPERATION)
    return user


# Mensyaratkan role HR dari basis data; gagal 403 FORBIDDEN_OPERATION.
def require_hr(user: Annotated[User, Depends(current_user)]) -> User:
    if user.role != Role.HR:
        raise AppError(ErrorCode.FORBIDDEN_OPERATION)
    return user
