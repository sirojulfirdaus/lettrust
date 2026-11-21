# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: SA §17.3
"""Test health: komponen dilaporkan tanpa gagal keras; status degraded bila ada yang tidak ok."""

from app.modules.health import service as health_service
from app.modules.health.schemas import ComponentStatus


# Liveness /healthz selalu 200.
def test_healthz_ok(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# Registry dan ai-service tak terjangkau → HTTP 200, degraded, komponen unavailable; DB ok.
def test_health_reports_unavailable_components(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers["X-Request-ID"].startswith("req_")
    assert response.json() == {
        "status": "degraded",
        "components": {"database": "ok", "registry": "unavailable", "aiService": "unavailable"},
    }


# Seluruh komponen ok → status ok.
def test_health_all_ok(client, monkeypatch):
    async def ok() -> ComponentStatus:
        return ComponentStatus.OK

    monkeypatch.setattr(health_service, "check_registry", ok)
    monkeypatch.setattr(health_service, "check_ai_service", ok)
    body = client.get("/api/v1/health").json()
    assert body["status"] == "ok"
    assert set(body["components"].values()) == {"ok"}


# LLM belum dikonfigurasi pada ai-service → aiService `unconfigured` dan status degraded.
def test_health_ai_unconfigured(client, monkeypatch):
    async def unconfigured() -> ComponentStatus:
        return ComponentStatus.UNCONFIGURED

    monkeypatch.setattr(health_service, "check_ai_service", unconfigured)
    body = client.get("/api/v1/health").json()
    assert body["status"] == "degraded"
    assert body["components"]["aiService"] == "unconfigured"


# X-Request-ID yang aman dari client dipertahankan.
def test_request_id_propagated(client):
    response = client.get("/healthz", headers={"X-Request-ID": "req_FROMPORTAL0000001"})
    assert response.headers["X-Request-ID"] == "req_FROMPORTAL0000001"
