# Owner: Dws (PIC 1) | Status: STUB | Ref: PRD FR-02.07, FR-01.07/AC-04; SA §8.1, §8.2
# TODO: Hash token Bearer (core.security.hash_token), cocokkan constant-time dengan token_hash aktif; gagal 401.
"""Dependency autentikasi client partner untuk API-07."""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import not_implemented
from app.modules.partners.models import Partner

partner_bearer = HTTPBearer(
    auto_error=False,
    scheme_name="PartnerToken",
    description="Token partner statis; hanya dipegang server portal mitra (BFF).",
)


# Mengembalikan partner aktif pemilik token; JWT atau token salah ditolak 401 UNAUTHENTICATED.
def partner_client(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(partner_bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> Partner:
    raise not_implemented()
