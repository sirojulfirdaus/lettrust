# Owner: Zan (PIC 3) | Status: STUB | Ref: PRD FR-01.03, FR-01.07; SA §8.2
# TODO: Baca membership dan status penerbit dari DB per request; issuer dan role tidak pernah dari input client.
"""Dependency otorisasi berbasis afiliasi penerbit."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import not_implemented
from app.modules.auth.dependencies import require_hr
from app.modules.auth.models import User


@dataclass(frozen=True)
class AuthorizedHrContext:
    """Konteks HR berwenang: user, penerbit VERIFIED, dan issuerRef penerbit dari server."""

    user: User
    issuer_id: str
    issuer_ref: str


# Mensyaratkan HR tanpa membership; gagal 409 ACCOUNT_ALREADY_AFFILIATED.
def require_unaffiliated_hr(
    user: Annotated[User, Depends(require_hr)], db: Annotated[Session, Depends(get_db)]
) -> User:
    raise not_implemented()


# Mensyaratkan HR dengan membership AUTHORIZED pada penerbit VERIFIED; gagal 403 FORBIDDEN_OPERATION.
def authorized_hr(
    user: Annotated[User, Depends(require_hr)], db: Annotated[Session, Depends(get_db)]
) -> AuthorizedHrContext:
    raise not_implemented()
