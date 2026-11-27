# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: PRD NFR-01.10; SA §8.3, §16
"""CORS hanya mengizinkan origin Console yang dikonfigurasi (localhost dan 127.0.0.1); origin lain, termasuk portal,
tidak mendapat izin."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import create_app

CONSOLE_ORIGINS = ("http://localhost:3000", "http://127.0.0.1:3000")
PREFLIGHT_HEADERS = {
    "Access-Control-Request-Method": "POST",
    "Access-Control-Request-Headers": "Authorization, Content-Type, Idempotency-Key",
}


# App baru dengan konfigurasi CORS default (tanpa override env mesin) agar test tidak bergantung pada .env lokal.
@pytest.fixture
def cors_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    get_settings.cache_clear()
    try:
        with TestClient(create_app()) as client:
            yield client
    finally:
        get_settings.cache_clear()


# Default konfigurasi memuat kedua alamat Console sehingga Console dapat dibuka lewat localhost maupun 127.0.0.1.
def test_default_allows_both_console_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    assert Settings().cors_origins == list(CONSOLE_ORIGINS)


# Preflight dari kedua origin Console diizinkan dengan metode dan header yang dibutuhkan, tanpa kredensial cookie.
@pytest.mark.parametrize("origin", CONSOLE_ORIGINS)
def test_console_origin_preflight_allowed(cors_client: TestClient, origin: str) -> None:
    response = cors_client.options("/api/v1/auth/login", headers={"Origin": origin, **PREFLIGHT_HEADERS})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "idempotency-key" in response.headers["access-control-allow-headers"].lower()
    assert "access-control-allow-credentials" not in response.headers


# Origin lain (portal 3001 di kedua host, domain asing, null) ditolak pada preflight dan request biasa.
@pytest.mark.parametrize(
    "origin", ["http://localhost:3001", "http://127.0.0.1:3001", "http://evil.example", "http://localhost", "null"]
)
def test_other_origins_rejected(cors_client: TestClient, origin: str) -> None:
    preflight = cors_client.options("/api/v1/verifications", headers={"Origin": origin, **PREFLIGHT_HEADERS})
    assert preflight.status_code == 400
    assert "access-control-allow-origin" not in preflight.headers
    simple = cors_client.get("/api/v1/health", headers={"Origin": origin})
    assert "access-control-allow-origin" not in simple.headers
