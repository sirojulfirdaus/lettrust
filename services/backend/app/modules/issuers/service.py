# Owner: Zan (PIC 3) | Status: STUB | Ref: PRD FR-01.03–FR-01.06; SA §10.5, §9.4
# TODO: Implementasikan SVC-01 (registrasi PENDING + membership NOT_AUTHORIZED, keputusan sekali, otorisasi HR).
"""Logika bisnis SVC-01."""

from sqlalchemy.orm import Session

from app.modules.auth.models import User
from app.modules.auth.schemas import IssuerStatus
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


# API-01: membuat penerbit PENDING, menghitung issuer_ref, dan mencatat pendaftar sebagai anggota NOT_AUTHORIZED.
def register_issuer(db: Session, user: User, payload: RegisterIssuerRequest) -> RegisterIssuerResponse:
    raise NotImplementedError("issuers.register_issuer belum diimplementasikan")


# S-04: daftar penerbit dengan filter status dan paginasi.
def list_issuers(db: Session, status: IssuerStatus | None, limit: int, offset: int) -> IssuerListResponse:
    raise NotImplementedError("issuers.list_issuers belum diimplementasikan")


# S-05: detail penerbit untuk Admin atau anggota; bukan anggota menerima 404.
def get_issuer_detail(db: Session, viewer: User, issuer_id: str) -> IssuerDetailResponse:
    raise NotImplementedError("issuers.get_issuer_detail belum diimplementasikan")


# API-02: keputusan VERIFIED/REJECTED hanya untuk penerbit PENDING.
def verify_issuer(db: Session, admin: User, issuer_id: str, payload: VerifyIssuerRequest) -> VerifyIssuerResponse:
    raise NotImplementedError("issuers.verify_issuer belum diimplementasikan")


# API-03: otorisasi HR dengan urutan pemeriksaan SA §10.5 (404 → 409 → 422 → 409).
def authorize_hr(db: Session, admin: User, issuer_id: str, payload: AuthorizeHrRequest) -> AuthorizeHrResponse:
    raise NotImplementedError("issuers.authorize_hr belum diimplementasikan")
