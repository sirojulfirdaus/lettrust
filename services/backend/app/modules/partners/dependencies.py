# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: PRD FR-02.07, FR-06.09, FR-01.07/AC-04; SA §8.1, §8.2, §9.2, §17.4
"""Dependency autentikasi client partner untuk API-07."""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import AppError
from app.core.schemas import ErrorCode
from app.core.security import hash_token, secrets_equal
from app.modules.partners.models import Partner

partner_bearer = HTTPBearer(
    auto_error=False,
    scheme_name="PartnerToken",
    description="Token partner statis; hanya dipegang server portal mitra (BFF).",
)


# Mengembalikan partner aktif pemilik token Bearer; token tidak ada, salah, nonaktif, atau JWT ditolak
# 401 UNAUTHENTICATED. Token hanya dibandingkan sebagai SHA-256 hex secara constant-time dan tidak pernah dicatat.
def partner_client(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(partner_bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> Partner:
    if credentials is None or not credentials.credentials:
        raise AppError(ErrorCode.UNAUTHENTICATED)
    presented_hash = hash_token(credentials.credentials)
    for partner in db.scalars(select(Partner).where(Partner.active.is_(True))):
        if secrets_equal(partner.token_hash, presented_hash):
            return partner
    raise AppError(ErrorCode.UNAUTHENTICATED)
