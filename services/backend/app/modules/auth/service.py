# Owner: Zan (PIC 3) | Status: STUB | Ref: PRD FR-01.01, FR-01.02, FR-01.04; SA §10.5 (S-01–S-03)
# TODO: Registrasi akun HR (email lowercase, bcrypt), login generik INVALID_CREDENTIALS, profil sesi + membership.
"""Logika bisnis akun dan sesi."""

from sqlalchemy.orm import Session

from app.modules.auth.models import User
from app.modules.auth.schemas import LoginRequest, LoginResponse, MeResponse, RegisterAccountRequest, UserSummary


# Membuat akun baru berrole HR tanpa membership; EMAIL_ALREADY_REGISTERED bila email sudah ada.
def register_account(db: Session, payload: RegisterAccountRequest) -> UserSummary:
    raise NotImplementedError("auth.register_account belum diimplementasikan")


# Memverifikasi kredensial dan menerbitkan JWT; pesan gagal tidak membedakan email/password.
def login(db: Session, payload: LoginRequest) -> LoginResponse:
    raise NotImplementedError("auth.login belum diimplementasikan")


# Menyusun profil sesi beserta membership yang dibaca dari DB per request.
def get_session_profile(db: Session, user: User) -> MeResponse:
    raise NotImplementedError("auth.get_session_profile belum diimplementasikan")
