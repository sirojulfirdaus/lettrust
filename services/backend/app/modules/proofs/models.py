# Owner: Zan (PIC 3) | Status: COMPLETE | Ref: SA §9.2 (proofs), §6.5, §6.6, §9.4
"""Model tabel bukti: cermin tampilan status, pemetaan referenceCode, dan referensi transaksi."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Proof(Base):
    """Metadata bukti off-chain; status adalah cermin, sumber kebenaran tetap registry (AD-07)."""

    __tablename__ = "proofs"
    __table_args__ = (
        CheckConstraint("status IN ('PENDING', 'ACTIVE', 'REVOKED', 'FAILED')", name="ck_proofs_status"),
        CheckConstraint(
            "revoke_reason_code IS NULL OR revoke_reason_code IN "
            "('OFFER_WITHDRAWN', 'ISSUED_IN_ERROR', 'DOCUMENT_REPLACED', 'OTHER')",
            name="ck_proofs_revoke_reason_code",
        ),
        CheckConstraint("length(document_hash) = 64", name="ck_proofs_document_hash_len"),
        UniqueConstraint("issuer_id", "idempotency_key", name="uq_proofs_issuer_idempotency_key"),
        Index("ix_proofs_issuer_status", "issuer_id", "status"),
        Index("ix_proofs_issuer_document_hash", "issuer_id", "document_hash"),
    )

    proof_id: Mapped[str] = mapped_column(String, primary_key=True)
    reference_code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    issuer_id: Mapped[str] = mapped_column(String, ForeignKey("issuers.id"), nullable=False)
    document_hash: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String, nullable=False)
    issued_by: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    issue_tx_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    issue_block: Mapped[int | None] = mapped_column(Integer, nullable=True)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String, nullable=True)
    revoke_idempotency_key: Mapped[str | None] = mapped_column(String, nullable=True)
    revoke_reason_code: Mapped[str | None] = mapped_column(String, nullable=True)
    revoked_by: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"), nullable=True)
    revoke_tx_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    revoke_block: Mapped[int | None] = mapped_column(Integer, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
