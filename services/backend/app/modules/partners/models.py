# Owner: Zan (PIC 3) | Status: COMPLETE | Ref: SA §9.2 (partners), §8.1
"""Model tabel client partner (job portal mitra)."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Partner(Base):
    """Client partner API-07; token hanya disimpan sebagai SHA-256 hex."""

    __tablename__ = "partners"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    token_hash: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
