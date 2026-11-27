# Owner: Zan (PIC 3) | Status: COMPLETE | Ref: PRD FR-01.03, FR-01.07; SA §8.2
"""Dependency otorisasi berbasis afiliasi penerbit."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import AppError
from app.core.schemas import ErrorCode
from app.modules.auth.dependencies import require_hr
from app.modules.auth.models import User
from app.modules.auth.schemas import AuthorizationStatus, IssuerStatus
from app.modules.issuers.models import Issuer, IssuerMembership


@dataclass(frozen=True)
class AuthorizedHrContext:
    """Konteks HR berwenang: user, penerbit VERIFIED, dan issuerRef penerbit dari server."""

    user: User
    issuer_id: str
    issuer_ref: str


def require_unaffiliated_hr(
    user: Annotated[User, Depends(require_hr)], db: Annotated[Session, Depends(get_db)]
) -> User:
    """Membatasi registrasi perusahaan pada HR tanpa afiliasi; afiliasi yang sudah ada menghasilkan 409."""
    if db.get(IssuerMembership, user.id) is not None:
        raise AppError(ErrorCode.ACCOUNT_ALREADY_AFFILIATED)
    return user


def authorized_hr(
    user: Annotated[User, Depends(require_hr)], db: Annotated[Session, Depends(get_db)]
) -> AuthorizedHrContext:
    """Membatasi operasi bukti pada HR AUTHORIZED dari penerbit VERIFIED; status dibaca per request."""
    issuer = db.execute(
        select(Issuer.id, Issuer.issuer_ref)
        .join(IssuerMembership, IssuerMembership.issuer_id == Issuer.id)
        .where(
            IssuerMembership.user_id == user.id,
            IssuerMembership.authorization_status == AuthorizationStatus.AUTHORIZED,
            Issuer.status == IssuerStatus.VERIFIED,
        )
    ).one_or_none()
    if issuer is None:
        raise AppError(ErrorCode.FORBIDDEN_OPERATION)

    issuer_id, issuer_ref = issuer
    return AuthorizedHrContext(user=user, issuer_id=issuer_id, issuer_ref=issuer_ref)
