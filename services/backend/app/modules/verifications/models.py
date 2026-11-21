# Owner: Zan (PIC 3) | Status: COMPLETE | Ref: SA §9.2 (verification_logs, P1); PRD FR-06.08
"""Model log verifikasi minimal: hanya enum hasil, tanpa kode referensi, hash, teks, atau berkas."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class VerificationLog(Base):
    """Satu baris per verifikasi API-07 berisi enum hasil komponen dan durasi."""

    __tablename__ = "verification_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    partner_id: Mapped[str] = mapped_column(String, ForeignKey("partners.id"), nullable=False)
    mode: Mapped[str] = mapped_column(String, nullable=False)
    lookup: Mapped[str] = mapped_column(String, nullable=False)
    lifecycle_status: Mapped[str | None] = mapped_column(String, nullable=True)
    integrity_result: Mapped[str] = mapped_column(String, nullable=False)
    risk_state: Mapped[str] = mapped_column(String, nullable=False)
    risk_category: Mapped[str | None] = mapped_column(String, nullable=True)
    proof_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    integrity_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    risk_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
