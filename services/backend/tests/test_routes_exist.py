# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: SA §10.4
"""Setiap endpoint backend SA §10.4 ada dengan method yang benar; endpoint stub mengembalikan envelope 501."""

import pytest

from app.main import app

PROOF_ID = "0x" + "ab" * 32
# (ID, method, path) dari SA §10.4; I-01, API-08, I-02 berada di ai-service.
ENDPOINTS = [
    ("S-01", "POST", "/api/v1/auth/register"),
    ("S-02", "POST", "/api/v1/auth/login"),
    ("S-03", "GET", "/api/v1/auth/me"),
    ("API-01", "POST", "/api/v1/issuers"),
    ("S-04", "GET", "/api/v1/issuers"),
    ("S-05", "GET", "/api/v1/issuers/{issuerId}"),
    ("API-02", "PATCH", "/api/v1/issuers/{issuerId}/verification"),
    ("API-03", "POST", "/api/v1/issuers/{issuerId}/hr-authorizations"),
    ("API-04", "POST", "/api/v1/proofs"),
    ("S-06", "GET", "/api/v1/proofs"),
    ("API-05", "GET", "/api/v1/proofs/{proofId}"),
    ("API-06", "POST", "/api/v1/proofs/{proofId}/revocations"),
    ("API-07", "POST", "/api/v1/verifications"),
    ("S-07", "GET", "/api/v1/health"),
]
PDF = ("offer.pdf", b"%PDF-1.4\n%synthetic\n", "application/pdf")
# Permintaan valid per endpoint stub agar validasi lolos dan stub tercapai.
STUB_REQUESTS = {
    "S-01": {"json": {"displayName": "Rina Demo", "email": "rina@lettrust.test", "password": "rahasia-demo-123"}},
    "S-02": {"json": {"email": "rina@lettrust.test", "password": "rahasia-demo-123"}},
    "S-03": {},
    "API-01": {
        "json": {"companyName": "PT Contoh", "registrationNumber": "REG-DEMO-001", "contactEmail": "hr@contoh.test"}
    },
    "S-04": {},
    "S-05": {},
    "API-02": {"json": {"decision": "VERIFIED", "evidenceRef": "EVD-DEMO-001"}},
    "API-03": {"json": {"hrId": "USR-7K3M9Q2H"}},
    "API-04": {"files": {"file": PDF}},
    "S-06": {},
    "API-05": {},
    "API-06": {"json": {"reasonCode": "OFFER_WITHDRAWN"}},
    "API-07": {"data": {"referenceCode": "LTR-7K3M-9QX2-H4TD", "includeRisk": "false"}, "files": {"file": PDF}},
}


# Mengumpulkan (method, path) dari skema OpenAPI aplikasi (API publik FastAPI, stabil lintas versi).
def registered_routes() -> set[tuple[str, str]]:
    return {(method.upper(), path) for path, ops in app.openapi()["paths"].items() for method in ops}


# Mengisi parameter path dengan nilai contoh.
def concrete(path: str) -> str:
    return path.replace("{issuerId}", "ISS-4D8N2P6R").replace("{proofId}", PROOF_ID)


# Setiap endpoint terdaftar dengan method yang benar.
@pytest.mark.parametrize(("endpoint_id", "method", "path"), ENDPOINTS, ids=[e[0] for e in ENDPOINTS])
def test_route_registered(endpoint_id, method, path):
    assert (method, path) in registered_routes(), f"{endpoint_id} {method} {path} tidak terdaftar"


# Tidak ada endpoint /api/v1 tambahan di luar katalog (Never invent endpoints).
def test_no_extra_routes():
    assert registered_routes() == {(m, p) for _, m, p in ENDPOINTS}


# Endpoint stub mengembalikan 501 NOT_IMPLEMENTED dengan envelope SA §10.2 dan requestId.
@pytest.mark.parametrize("endpoint_id", list(STUB_REQUESTS))
def test_stub_returns_501_envelope(client, endpoint_id):
    _, method, path = next(e for e in ENDPOINTS if e[0] == endpoint_id)
    response = client.request(
        method, concrete(path), headers={"Authorization": "Bearer dummy"}, **STUB_REQUESTS[endpoint_id]
    )
    assert response.status_code == 501, response.text
    body = response.json()
    assert body["error"]["code"] == "NOT_IMPLEMENTED"
    assert body["error"]["details"] == []
    assert body["requestId"].startswith("req_")
    assert response.headers["X-Request-ID"] == body["requestId"]


# Validasi FastAPI dipetakan ke 400 VALIDATION_ERROR dengan rincian field camelCase.
def test_validation_error_is_400(client):
    response = client.post("/api/v1/auth/register", json={"displayName": "R", "email": "bukan-email", "password": "x"})
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert {d["field"] for d in body["error"]["details"]} == {"displayName", "email", "password"}


# Route yang tidak ada tetap memakai envelope error.
def test_unknown_route_envelope(client):
    response = client.get("/api/v1/tidak-ada")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
