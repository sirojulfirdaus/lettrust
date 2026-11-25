# Owner: Zan (PIC 3) | Status: COMPLETE | Ref: PRD FR-01.03–FR-01.06; SA §10.5, §9.4
"""Logika bisnis SVC-01."""

from datetime import UTC, datetime

from sqlalchemy import func, select, true, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.ids import compute_issuer_ref, new_issuer_id
from app.core.schemas import ErrorCode, ErrorDetail
from app.modules.auth.models import User
from app.modules.auth.schemas import AuthorizationStatus, IssuerStatus, Role
from app.modules.issuers.models import Issuer, IssuerMembership
from app.modules.issuers.schemas import (
    AuthorizeHrRequest,
    AuthorizeHrResponse,
    IssuerDetailResponse,
    IssuerListItem,
    IssuerListResponse,
    IssuerMember,
    RegisterIssuerRequest,
    RegisterIssuerResponse,
    VerifyIssuerRequest,
    VerifyIssuerResponse,
)

# SQLite menyimpan OFFSET sebagai integer bertanda tangan 64-bit.
SQLITE_MAX_OFFSET = 2**63 - 1


def _require_issuer_text(value: str, field: str) -> str:
    """Merapikan spasi tepi dan memastikan kolom wajib berisi minimal tiga karakter."""
    trimmed = value.strip()
    if len(trimmed) < 3:
        raise AppError(
            ErrorCode.VALIDATION_ERROR,
            details=[ErrorDetail(field=field, issue="string_too_short")],
        )
    return trimmed


def _as_utc(value: datetime) -> datetime:
    """Memberi zona UTC pada timestamp yang dibaca kembali dari SQLite."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def register_issuer(db: Session, user: User, payload: RegisterIssuerRequest) -> RegisterIssuerResponse:
    """Menyimpan penerbit PENDING dan afiliasi NOT_AUTHORIZED dalam satu transaksi."""
    company_name = _require_issuer_text(payload.company_name, "companyName")
    issuer_id = new_issuer_id()
    user_id = user.id
    now = datetime.now(UTC)
    try:
        created_issuer = db.scalar(
            insert(Issuer)
            .values(
                id=issuer_id,
                company_name=company_name,
                registration_number=payload.registration_number,
                contact_email=payload.contact_email,
                status=IssuerStatus.PENDING,
                issuer_ref=compute_issuer_ref(issuer_id),
                registered_by=user_id,
                created_at=now,
            )
            .on_conflict_do_nothing(index_elements=[Issuer.registration_number])
            .returning(Issuer.id)
        )
        if created_issuer is None:
            has_membership = db.get(IssuerMembership, user_id) is not None
            db.rollback()
            code = (
                ErrorCode.ACCOUNT_ALREADY_AFFILIATED if has_membership else ErrorCode.REGISTRATION_NUMBER_ALREADY_EXISTS
            )
            raise AppError(code)

        created_member = db.scalar(
            insert(IssuerMembership)
            .values(
                user_id=user_id,
                issuer_id=issuer_id,
                authorization_status=AuthorizationStatus.NOT_AUTHORIZED,
                created_at=now,
            )
            .on_conflict_do_nothing(index_elements=[IssuerMembership.user_id])
            .returning(IssuerMembership.user_id)
        )
        if created_member is None:
            db.rollback()
            raise AppError(ErrorCode.ACCOUNT_ALREADY_AFFILIATED)

        db.commit()
    except DBAPIError:
        db.rollback()
        raise AppError(ErrorCode.INTERNAL_ERROR) from None

    return RegisterIssuerResponse(issuer_id=issuer_id, issuer_status=IssuerStatus.PENDING)


def list_issuers(db: Session, status: IssuerStatus | None, limit: int, offset: int) -> IssuerListResponse:
    """Membaca total dan halaman penerbit dalam satu snapshot SQLite."""
    filters = (Issuer.status == status,) if status is not None else ()
    total = select(func.count().label("total")).select_from(Issuer).where(*filters).subquery()
    page = (
        select(
            Issuer.id.label("issuer_id"),
            Issuer.company_name,
            Issuer.registration_number,
            Issuer.status.label("issuer_status"),
            Issuer.created_at,
        )
        .where(*filters)
        .order_by(Issuer.created_at.desc(), Issuer.id)
        .limit(limit)
        .offset(min(offset, SQLITE_MAX_OFFSET))
        .subquery()
    )
    member_count = (
        select(func.count())
        .select_from(IssuerMembership)
        .where(IssuerMembership.issuer_id == page.c.issuer_id)
        .correlate(page)
        .scalar_subquery()
    )
    # LEFT JOIN menjaga total tetap tersedia jika halaman kosong.
    rows = db.execute(
        select(page, member_count.label("member_count"), total.c.total)
        .select_from(total.outerjoin(page, true()))
        .order_by(page.c.created_at.desc(), page.c.issuer_id)
    ).all()
    items = [
        IssuerListItem(
            issuer_id=row.issuer_id,
            company_name=row.company_name,
            registration_number=row.registration_number,
            issuer_status=row.issuer_status,
            created_at=_as_utc(row.created_at),
            member_count=row.member_count,
        )
        for row in rows
        if row.issuer_id is not None
    ]
    return IssuerListResponse(items=items, total=rows[0].total)


def get_issuer_detail(db: Session, viewer: User, issuer_id: str) -> IssuerDetailResponse:
    """Membatasi detail pada Admin dan anggota, serta menyamarkan email anggota lain."""
    is_admin = viewer.role == Role.ADMIN
    if not is_admin:
        membership = db.get(IssuerMembership, viewer.id)
        if membership is None or membership.issuer_id != issuer_id:
            raise AppError(ErrorCode.ISSUER_NOT_FOUND)

    issuer = db.get(Issuer, issuer_id)
    if issuer is None:
        raise AppError(ErrorCode.ISSUER_NOT_FOUND)

    rows = db.execute(
        select(
            User.id,
            User.display_name,
            User.email,
            IssuerMembership.authorization_status,
            IssuerMembership.authorized_at,
        )
        .join(IssuerMembership, IssuerMembership.user_id == User.id)
        .where(IssuerMembership.issuer_id == issuer_id)
        .order_by(IssuerMembership.created_at, IssuerMembership.user_id)
    )
    members = [
        IssuerMember(
            hr_id=hr_id,
            display_name=display_name,
            email=email if is_admin or hr_id == viewer.id else None,
            authorization_status=AuthorizationStatus(authorization_status),
            authorized_at=_as_utc(authorized_at) if authorized_at is not None else None,
        )
        for hr_id, display_name, email, authorization_status, authorized_at in rows
    ]
    return IssuerDetailResponse(
        issuer_id=issuer.id,
        company_name=issuer.company_name,
        registration_number=issuer.registration_number,
        contact_email=issuer.contact_email,
        issuer_status=IssuerStatus(issuer.status),
        evidence_ref=issuer.evidence_ref,
        review_note=issuer.review_note,
        reviewed_by=issuer.reviewed_by,
        reviewed_at=_as_utc(issuer.reviewed_at) if issuer.reviewed_at is not None else None,
        created_at=_as_utc(issuer.created_at),
        members=members,
    )


def verify_issuer(db: Session, admin: User, issuer_id: str, payload: VerifyIssuerRequest) -> VerifyIssuerResponse:
    """Menyimpan keputusan final secara atomik hanya jika penerbit masih PENDING."""
    evidence_ref = _require_issuer_text(payload.evidence_ref, "evidenceRef")
    reviewed_at = datetime.now(UTC)
    issuer_status = IssuerStatus(payload.decision)
    admin_id = admin.id
    try:
        reviewed_issuer = db.scalar(
            update(Issuer)
            .where(Issuer.id == issuer_id, Issuer.status == IssuerStatus.PENDING)
            .values(
                status=issuer_status,
                evidence_ref=evidence_ref,
                review_note=payload.review_note,
                reviewed_by=admin_id,
                reviewed_at=reviewed_at,
            )
            .returning(Issuer.id)
        )
        if reviewed_issuer is None:
            exists = db.scalar(select(Issuer.id).where(Issuer.id == issuer_id)) is not None
            db.rollback()
            code = ErrorCode.ISSUER_DECISION_ALREADY_MADE if exists else ErrorCode.ISSUER_NOT_FOUND
            raise AppError(code)
        db.commit()
    except DBAPIError:
        db.rollback()
        raise AppError(ErrorCode.INTERNAL_ERROR) from None

    return VerifyIssuerResponse(
        issuer_id=issuer_id,
        issuer_status=issuer_status,
        reviewed_by=admin_id,
        reviewed_at=reviewed_at,
    )


def authorize_hr(db: Session, admin: User, issuer_id: str, payload: AuthorizeHrRequest) -> AuthorizeHrResponse:
    """Mengotorisasi anggota HR pada penerbit VERIFIED satu kali dan mencatat Admin pelaksana."""
    issuer_status = db.scalar(select(Issuer.status).where(Issuer.id == issuer_id))
    if issuer_status is None:
        raise AppError(ErrorCode.ISSUER_NOT_FOUND)
    if issuer_status != IssuerStatus.VERIFIED:
        raise AppError(ErrorCode.ISSUER_NOT_VERIFIED)

    membership_scope = (
        IssuerMembership.user_id == payload.hr_id,
        IssuerMembership.issuer_id == issuer_id,
    )
    member_status = db.scalar(
        select(IssuerMembership.authorization_status)
        .join(User, User.id == IssuerMembership.user_id)
        .where(*membership_scope, User.role == Role.HR)
    )
    if member_status is None:
        raise AppError(ErrorCode.HR_NOT_AFFILIATED)
    if member_status == AuthorizationStatus.AUTHORIZED:
        raise AppError(ErrorCode.HR_ALREADY_AUTHORIZED)

    try:
        authorized_user = db.scalar(
            update(IssuerMembership)
            .where(*membership_scope, IssuerMembership.authorization_status == AuthorizationStatus.NOT_AUTHORIZED)
            .values(
                authorization_status=AuthorizationStatus.AUTHORIZED,
                authorized_by=admin.id,
                authorized_at=datetime.now(UTC),
            )
            .returning(IssuerMembership.user_id)
        )
        if authorized_user is None:
            db.rollback()
            raise AppError(ErrorCode.HR_ALREADY_AUTHORIZED)
        db.commit()
    except DBAPIError:
        db.rollback()
        raise AppError(ErrorCode.INTERNAL_ERROR) from None

    return AuthorizeHrResponse(
        issuer_id=issuer_id, hr_id=authorized_user, authorization_status=AuthorizationStatus.AUTHORIZED
    )
