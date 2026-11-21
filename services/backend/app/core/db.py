# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: SA §9.1, AD-03
"""Engine dan session SQLAlchemy 2.x untuk SQLite (WAL), Base model, dan init_db."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Basis deklaratif seluruh model tabel."""


# Mengaktifkan WAL dan foreign key pada setiap koneksi SQLite baru.
def _configure_sqlite(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# Membuat engine tunggal per proses dari DATABASE_URL.
@lru_cache
def get_engine() -> Engine:
    url = get_settings().database_url
    is_sqlite = url.startswith("sqlite")
    engine = create_engine(url, connect_args={"check_same_thread": False} if is_sqlite else {})
    if is_sqlite:
        event.listen(engine, "connect", _configure_sqlite)
    return engine


# Membuat factory session yang terikat ke engine.
@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


# Dependency FastAPI: menyediakan session per request dan menutupnya setelah selesai.
def get_db() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


# Mengimpor seluruh model agar terdaftar di metadata lalu membuat tabel (tanpa migrasi, AD-03).
def init_db() -> None:
    from app.modules.auth import models as _auth_models  # noqa: F401
    from app.modules.issuers import models as _issuer_models  # noqa: F401
    from app.modules.partners import models as _partner_models  # noqa: F401
    from app.modules.proofs import models as _proof_models  # noqa: F401
    from app.modules.verifications import models as _verification_models  # noqa: F401

    Base.metadata.create_all(get_engine())
