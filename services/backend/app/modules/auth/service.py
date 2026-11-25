# Owner: Zan (PIC 3) | Status: COMPLETE | Ref: PRD FR-01.01, FR-01.02, FR-01.04; SA §10.5 (S-01–S-03)
"""Logika bisnis akun dan sesi."""

from datetime import UTC, datetime
from sqlite3 import SQLITE_CONSTRAINT_UNIQUE

from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.ids import new_user_id
from app.core.schemas import ErrorCode
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.auth.models import User
from app.modules.auth.schemas import (
    LoginRequest,
    LoginResponse,
    Membership,
    MeResponse,
    RegisterAccountRequest,
    Role,
    UserSummary,
)
from app.modules.issuers.models import Issuer, IssuerMembership

# Hash bcrypt sintetis agar email yang tidak dikenal tetap melewati pemeriksaan password.
DUMMY_PASSWORD_HASH = "$2b$12$Lbbg/rQPWg.LN29YJ8YnW./8eRJRQeq6zcmDXnuj83.Kt4VMLcWL2"


# Membentuk ringkasan akun untuk response API tanpa mengekspos hash password.
def _user_summary(user: User) -> UserSummary:
    return UserSummary(user_id=user.id, email=user.email, display_name=user.display_name, role=Role(user.role))


# Membuat akun baru berrole HR tanpa membership; EMAIL_ALREADY_REGISTERED bila email sudah ada.
def register_account(db: Session, payload: RegisterAccountRequest) -> UserSummary:
    user = User(
        id=new_user_id(),
        email=payload.email.lower(),
        display_name=payload.display_name,
        password_hash=hash_password(payload.password),
        role=Role.HR,
        created_at=datetime.now(UTC),
    )
    db.add(user)
    try:
        db.commit()
    except DBAPIError as exc:
        db.rollback()
        # Constraint UNIQUE pada users berlaku untuk email; primary key memakai kode SQLite berbeda.
        if getattr(exc.orig, "sqlite_errorcode", None) == SQLITE_CONSTRAINT_UNIQUE:
            raise AppError(ErrorCode.EMAIL_ALREADY_REGISTERED) from None
        raise AppError(ErrorCode.INTERNAL_ERROR) from None

    return _user_summary(user)


# Memverifikasi kredensial dan menerbitkan JWT; pesan gagal tidak membedakan email/password.
def login(db: Session, payload: LoginRequest) -> LoginResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    password_hash = user.password_hash if user is not None else DUMMY_PASSWORD_HASH
    valid_password = verify_password(payload.password, password_hash)
    if user is None or not valid_password:
        raise AppError(ErrorCode.INVALID_CREDENTIALS)

    token, expires_in = create_access_token(user.id, user.role)
    return LoginResponse(access_token=token, token_type="Bearer", expires_in=expires_in, user=_user_summary(user))


# Menyusun profil sesi beserta membership yang dibaca dari DB per request.
def get_session_profile(db: Session, user: User) -> MeResponse:
    membership = None
    if user.role == Role.HR:
        row = (
            db.execute(
                select(
                    Issuer.id.label("issuer_id"),
                    Issuer.company_name,
                    Issuer.status.label("issuer_status"),
                    IssuerMembership.authorization_status,
                    Issuer.review_note,
                )
                .join_from(Issuer, IssuerMembership, IssuerMembership.issuer_id == Issuer.id)
                .where(IssuerMembership.user_id == user.id)
            )
            .mappings()
            .one_or_none()
        )
        if row is not None:
            membership = Membership.model_validate(row)

    return MeResponse(**_user_summary(user).model_dump(), membership=membership)
