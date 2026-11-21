# Owner: Zan (PIC 3) | Status: COMPLETE | Ref: SA §9.2 (issuers, issuer_memberships), §9.4
"""Model tabel penerbit dan afiliasi HR."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Issuer(Base):
    """Penerbit (perusahaan); issuer_ref dihitung saat registrasi dan tidak berubah."""

    __tablename__ = "issuers"
    __table_args__ = (
        CheckConstraint("status IN ('PENDING', 'VERIFIED', 'REJECTED')", name="ck_issuers_status"),
        CheckConstraint("length(issuer_ref) = 64", name="ck_issuers_issuer_ref_len"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    company_name: Mapped[str] = mapped_column(String, nullable=False)
    registration_number: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    contact_email: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    issuer_ref: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    registered_by: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    evidence_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    review_note: Mapped[str | None] = mapped_column(String, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class IssuerMembership(Base):
    """Afiliasi HR ke penerbit; PK user_id menegakkan satu akun satu penerbit."""

    __tablename__ = "issuer_memberships"
    __table_args__ = (
        CheckConstraint(
            "authorization_status IN ('NOT_AUTHORIZED', 'AUTHORIZED')", name="ck_memberships_authorization_status"
        ),
    )

    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), primary_key=True)
    issuer_id: Mapped[str] = mapped_column(String, ForeignKey("issuers.id"), nullable=False, index=True)
    authorization_status: Mapped[str] = mapped_column(String, nullable=False)
    authorized_by: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"), nullable=True)
    authorized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
