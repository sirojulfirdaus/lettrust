# Owner: Zan (PIC 3) | Status: COMPLETE | Ref: SA §10.5 (S-01, S-02, S-03); PRD FR-01.01, FR-01.02, FR-01.04
"""Skema kontrak endpoint akun dan sesi."""

from enum import StrEnum
from typing import Literal

from pydantic import EmailStr, Field

from app.core.schemas import ApiModel


class Role(StrEnum):
    """Role akun; ditentukan server, tidak pernah dari input client."""

    HR = "HR"
    ADMIN = "ADMIN"


class IssuerStatus(StrEnum):
    """Status verifikasi penerbit."""

    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class AuthorizationStatus(StrEnum):
    """Status otorisasi HR pada penerbit."""

    NOT_AUTHORIZED = "NOT_AUTHORIZED"
    AUTHORIZED = "AUTHORIZED"


class RegisterAccountRequest(ApiModel):
    """S-01: registrasi akun HR (role selalu HR, tidak dikirim client)."""

    display_name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserSummary(ApiModel):
    """Identitas akun yang aman ditampilkan (tanpa password)."""

    user_id: str = Field(pattern=r"^USR-[0-9A-HJKMNP-TV-Z]{8}$")
    email: str
    display_name: str
    role: Role


class LoginRequest(ApiModel):
    """S-02: kredensial login."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class LoginResponse(ApiModel):
    """S-02: token sesi JWT beserta profil singkat."""

    access_token: str
    token_type: Literal["Bearer"]
    expires_in: int = Field(gt=0)
    user: UserSummary


class Membership(ApiModel):
    """Afiliasi HR ke penerbit beserta status penerbit dan otorisasi."""

    issuer_id: str = Field(pattern=r"^ISS-[0-9A-HJKMNP-TV-Z]{8}$")
    company_name: str
    issuer_status: IssuerStatus
    authorization_status: AuthorizationStatus
    review_note: str | None


class MeResponse(UserSummary):
    """S-03: profil sesi; membership null untuk HR tidak terafiliasi dan Administrator."""

    membership: Membership | None
