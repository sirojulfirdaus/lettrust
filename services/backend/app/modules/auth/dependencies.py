# Owner: Zan (PIC 3) | Status: STUB | Ref: PRD FR-01.02, FR-01.07; SA §8.1, §8.2
# TODO: Verifikasi JWT (core.security.decode_access_token), muat user dari DB per request, tegakkan role.
"""Dependency FastAPI untuk autentikasi JWT Console dan pemeriksaan role."""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import not_implemented
from app.modules.auth.models import User

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
    raise not_implemented()


# Mensyaratkan role ADMIN; gagal 403 FORBIDDEN_OPERATION.
def require_admin(user: Annotated[User, Depends(current_user)]) -> User:
    raise not_implemented()


# Mensyaratkan role HR; gagal 403 FORBIDDEN_OPERATION.
def require_hr(user: Annotated[User, Depends(current_user)]) -> User:
    raise not_implemented()
