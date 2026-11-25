# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: PRD FR-02.07, FR-06.09; SA §8.1, §8.2, §9.2, §9.5, §17.4
"""Test dependency partner_client lewat route uji, dengan basis data SQLite terpisah per modul."""

import logging
import secrets
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.cli import add_demo_seed
from app.core.config import get_settings
from app.core.db import Base, get_db, init_db
from app.core.ids import new_partner_id
from app.core.security import create_access_token, hash_token
from app.main import create_app
from app.modules.partners import dependencies
from app.modules.partners.dependencies import partner_client
from app.modules.partners.models import Partner


# App nyata ditambah route uji yang hanya memakai partner_client; get_db diarahkan ke SQLite sementara.
@pytest.fixture(scope="module")
def partner_env(tmp_path_factory) -> Iterator[tuple[TestClient, sessionmaker[Session]]]:
    init_db()  # mendaftarkan seluruh model ke metadata
    db_path: Path = tmp_path_factory.mktemp("partners") / "partners.db"
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    # Session per request pada basis data uji.
    def test_db() -> Iterator[Session]:
        with factory() as session:
            yield session

    app = create_app()

    # Route uji: mengembalikan identitas partner hasil autentikasi.
    async def whoami(partner: Annotated[Partner, Depends(partner_client)]) -> dict:
        return {"partnerId": partner.id, "name": partner.name}

    app.add_api_route("/test/partner", whoami, methods=["POST"])
    app.dependency_overrides[get_db] = test_db
    with TestClient(app) as client:
        yield client, factory
    engine.dispose()


# Membuat partner langsung di basis data uji dan mengembalikan (id, token mentah).
def make_partner(factory: sessionmaker[Session], *, active: bool = True) -> tuple[str, str]:
    token = f"synthetic-partner-{secrets.token_urlsafe(24)}"
    partner_id = new_partner_id()
    with factory.begin() as db:
        db.add(
            Partner(
                id=partner_id,
                name="Partner Uji",
                token_hash=hash_token(token),
                active=active,
                created_at=datetime.now(UTC),
            )
        )
    return partner_id, token


# Memastikan respons 401 UNAUTHENTICATED ber-envelope SA §10.2.
def assert_unauthenticated(response) -> None:
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "UNAUTHENTICATED"
    assert body["error"]["details"] == []
    assert body["requestId"] == response.headers["X-Request-ID"]


# Token valid milik partner aktif → objek partner.
def test_valid_token_returns_partner(partner_env):
    client, factory = partner_env
    partner_id, token = make_partner(factory)
    response = client.post("/test/partner", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {"partnerId": partner_id, "name": "Partner Uji"}


# Partner hasil seed T3-01 (token_hash = SHA-256 PARTNER_TOKEN) dapat diautentikasi dengan PARTNER_TOKEN.
def test_seeded_partner_authenticates(partner_env):
    client, factory = partner_env
    with factory.begin() as db:
        add_demo_seed(db)
    with factory() as db:
        seeded = db.scalar(select(Partner).where(Partner.name == "Portal Karier Mitra (Simulasi)"))
    token = get_settings().partner_token.get_secret_value()
    response = client.post("/test/partner", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["partnerId"] == seeded.id


# Header tidak ada, skema bukan Bearer, atau nilai kosong → 401.
@pytest.mark.parametrize("headers", [{}, {"Authorization": "Basic dXNlcjpwYXNz"}, {"Authorization": "Bearer "}])
def test_missing_or_malformed_header_rejected(partner_env, headers):
    client, _ = partner_env
    assert_unauthenticated(client.post("/test/partner", headers=headers))


# Token tidak terdaftar → 401.
def test_wrong_token_rejected(partner_env):
    client, factory = partner_env
    make_partner(factory)
    assert_unauthenticated(client.post("/test/partner", headers={"Authorization": "Bearer token-salah-sintetis"}))


# Token partner nonaktif → 401.
def test_inactive_partner_rejected(partner_env):
    client, factory = partner_env
    _, token = make_partner(factory, active=False)
    assert_unauthenticated(client.post("/test/partner", headers={"Authorization": f"Bearer {token}"}))


# JWT Console yang valid tidak cocok dengan hash partner → 401 (SA §8.2).
def test_console_jwt_rejected(partner_env):
    client, _ = partner_env
    jwt_token, _ = create_access_token("USR-ADM9N7Q2", "ADMIN")
    assert_unauthenticated(client.post("/test/partner", headers={"Authorization": f"Bearer {jwt_token}"}))


# Token dibandingkan sebagai SHA-256 hex lewat secrets_equal (constant-time), bukan nilai mentah.
def test_compares_hashes_with_constant_time_helper(partner_env, monkeypatch):
    client, factory = partner_env
    _, token = make_partner(factory)
    calls: list[tuple[str, str]] = []
    original = dependencies.secrets_equal

    # Mencatat argumen lalu meneruskan ke helper asli.
    def spy(left: str, right: str) -> bool:
        calls.append((left, right))
        return original(left, right)

    monkeypatch.setattr(dependencies, "secrets_equal", spy)
    response = client.post("/test/partner", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert calls and all(right == hash_token(token) for _, right in calls)
    assert all(token not in pair for pair in calls)


# Token, benar maupun salah, tidak muncul di log aplikasi.
def test_token_never_logged(partner_env, caplog, capfd):
    client, factory = partner_env
    _, token = make_partner(factory)
    wrong = f"synthetic-wrong-{secrets.token_urlsafe(16)}"
    with caplog.at_level(logging.DEBUG):
        client.post("/test/partner", headers={"Authorization": f"Bearer {token}"})
        client.post("/test/partner", headers={"Authorization": f"Bearer {wrong}"})
    captured = capfd.readouterr()
    for text in (caplog.text, captured.out, captured.err):
        assert token not in text
        assert wrong not in text
