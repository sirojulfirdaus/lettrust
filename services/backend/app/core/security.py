# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: SA §8.1; PRD NFR-01.01, NFR-01.02
"""Hash password (bcrypt), JWT HS256, dan hash/perbandingan token constant-time."""

import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.schemas import ErrorCode

JWT_ALGORITHM = "HS256"
# bcrypt hanya memakai 72 byte pertama; bcrypt>=5 menolak input lebih panjang sehingga dipotong eksplisit.
BCRYPT_MAX_BYTES = 72


# Menyiapkan byte password untuk bcrypt (dipotong ke 72 byte, perilaku bcrypt klasik).
def _password_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:BCRYPT_MAX_BYTES]


# Menghasilkan hash bcrypt (cost default library) untuk password.
def hash_password(password: str) -> str:
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt()).decode("ascii")


# Memverifikasi password terhadap hash bcrypt; False untuk hash yang tidak valid.
def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_password_bytes(password), password_hash.encode("ascii"))
    except ValueError:
        return False


# Membuat JWT HS256 berisi sub, role, iat, exp; mengembalikan token dan masa berlaku (detik).
def create_access_token(user_id: str, role: str) -> tuple[str, int]:
    settings = get_settings()
    now = datetime.now(UTC)
    expires_in = settings.jwt_expires_minutes * 60
    claims = {"sub": user_id, "role": role, "iat": now, "exp": now + timedelta(seconds=expires_in)}
    token = jwt.encode(claims, settings.jwt_secret.get_secret_value(), algorithm=JWT_ALGORITHM)
    return token, expires_in


# Mendekode dan memvalidasi JWT; token tidak valid/kedaluwarsa menghasilkan 401 UNAUTHENTICATED.
def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            get_settings().jwt_secret.get_secret_value(),
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "role", "iat", "exp"]},
        )
    except jwt.PyJWTError as exc:
        raise AppError(ErrorCode.UNAUTHENTICATED) from exc


# Menghitung SHA-256 hex dari token (penyimpanan token partner).
def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# Membandingkan dua string rahasia secara constant-time.
def secrets_equal(left: str, right: str) -> bool:
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))
