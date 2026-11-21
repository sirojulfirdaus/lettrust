# Owner: Zan (PIC 3) | Status: COMPLETE | Ref: SA §10.5 (API-01–API-03, S-04, S-05); PRD FR-01.03–FR-01.06
"""Skema kontrak endpoint SVC-01."""

from datetime import datetime
from enum import StrEnum

from pydantic import EmailStr, Field

from app.core.schemas import ApiModel
from app.modules.auth.schemas import AuthorizationStatus, IssuerStatus

ISSUER_ID_PATTERN = r"^ISS-[0-9A-HJKMNP-TV-Z]{8}$"
USER_ID_PATTERN = r"^USR-[0-9A-HJKMNP-TV-Z]{8}$"


class IssuerDecision(StrEnum):
    """Keputusan verifikasi Administrator (API-02)."""

    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class RegisterIssuerRequest(ApiModel):
    """API-01 registerIssuer."""

    company_name: str = Field(min_length=3, max_length=120)
    registration_number: str = Field(min_length=3, max_length=40, pattern=r"^[A-Za-z0-9./-]+$")
    contact_email: EmailStr


class RegisterIssuerResponse(ApiModel):
    """API-01: penerbit baru berstatus PENDING (sesuai D2)."""

    issuer_id: str = Field(pattern=ISSUER_ID_PATTERN)
    issuer_status: IssuerStatus


class IssuerListItem(ApiModel):
    """Baris daftar penerbit (S-04)."""

    issuer_id: str = Field(pattern=ISSUER_ID_PATTERN)
    company_name: str
    registration_number: str
    issuer_status: IssuerStatus
    created_at: datetime
    member_count: int = Field(ge=0)


class IssuerListResponse(ApiModel):
    """S-04: koleksi penerbit."""

    items: list[IssuerListItem]
    total: int = Field(ge=0)


class IssuerMember(ApiModel):
    """Anggota HR penerbit; email anggota lain tidak dikirim kepada sesama anggota (null)."""

    hr_id: str = Field(pattern=USER_ID_PATTERN)
    display_name: str
    email: str | None
    authorization_status: AuthorizationStatus
    authorized_at: datetime | None


class IssuerDetailResponse(ApiModel):
    """S-05: detail penerbit untuk Administrator atau anggota."""

    issuer_id: str = Field(pattern=ISSUER_ID_PATTERN)
    company_name: str
    registration_number: str
    contact_email: str
    issuer_status: IssuerStatus
    evidence_ref: str | None
    review_note: str | None
    reviewed_by: str | None
    reviewed_at: datetime | None
    created_at: datetime
    members: list[IssuerMember]


class VerifyIssuerRequest(ApiModel):
    """API-02 verifyIssuer."""

    decision: IssuerDecision
    evidence_ref: str = Field(min_length=3, max_length=120)
    review_note: str | None = Field(default=None, max_length=500)


class VerifyIssuerResponse(ApiModel):
    """API-02: hasil keputusan beserta peninjau dan waktu."""

    issuer_id: str = Field(pattern=ISSUER_ID_PATTERN)
    issuer_status: IssuerStatus
    reviewed_by: str = Field(pattern=USER_ID_PATTERN)
    reviewed_at: datetime


class AuthorizeHrRequest(ApiModel):
    """API-03 authorizeHR."""

    hr_id: str = Field(min_length=1, max_length=40)


class AuthorizeHrResponse(ApiModel):
    """API-03: HR berstatus AUTHORIZED (sesuai D2)."""

    issuer_id: str = Field(pattern=ISSUER_ID_PATTERN)
    hr_id: str = Field(pattern=USER_ID_PATTERN)
    authorization_status: AuthorizationStatus
