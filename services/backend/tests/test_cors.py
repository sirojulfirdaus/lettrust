# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: PRD NFR-01.10; SA §8.3, §16
"""CORS hanya mengizinkan origin Console yang dikonfigurasi; origin lain (termasuk portal) tidak mendapat izin."""

import pytest

from app.core.config import get_settings

PREFLIGHT_HEADERS = {
    "Access-Control-Request-Method": "POST",
    "Access-Control-Request-Headers": "Authorization, Content-Type, Idempotency-Key",
}


# Preflight dari origin Console diizinkan dengan metode dan header yang dibutuhkan, tanpa kredensial cookie.
def test_console_origin_preflight_allowed(client) -> None:
    origin = get_settings().cors_origins[0]
    response = client.options("/api/v1/proofs", headers={"Origin": origin, **PREFLIGHT_HEADERS})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "idempotency-key" in response.headers["access-control-allow-headers"].lower()
    assert "access-control-allow-credentials" not in response.headers


# Origin lain ditolak pada preflight dan tidak menerima header izin pada request biasa.
@pytest.mark.parametrize("origin", ["http://localhost:3001", "http://evil.example", "null"])
def test_other_origins_rejected(client, origin: str) -> None:
    assert origin not in get_settings().cors_origins
    preflight = client.options("/api/v1/verifications", headers={"Origin": origin, **PREFLIGHT_HEADERS})
    assert preflight.status_code == 400
    assert "access-control-allow-origin" not in preflight.headers
    simple = client.get("/api/v1/health", headers={"Origin": origin})
    assert "access-control-allow-origin" not in simple.headers
