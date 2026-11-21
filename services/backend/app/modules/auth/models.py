# Owner: Zan (PIC 3) | Status: COMPLETE | Ref: SA §9.2 (users)
"""Model tabel akun HR dan Administrator."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class User(Base):
    """Akun HR/Admin; email disimpan lowercase, password hanya sebagai hash bcrypt."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('HR', 'ADMIN')", name="ck_users_role"),
        CheckConstraint("email = lower(email)", name="ck_users_email_lowercase"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
