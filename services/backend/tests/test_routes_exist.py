# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: SA §10.4
"""Setiap endpoint backend SA §10.4 ada dengan method yang benar; endpoint stub mengembalikan envelope 501."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.core.db import get_session_factory
from app.core.ids import new_user_id
from app.core.security import create_access_token, hash_password
from app.main import app
from app.modules.auth.models import User
from app.modules.auth.schemas import Role

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
    "API-04": {"files": {"file": PDF}},
    "S-06": {},
    "API-05": {},
    "API-06": {"json": {"reasonCode": "OFFER_WITHDRAWN"}},
}


# Mengumpulkan (method, path) dari skema OpenAPI aplikasi (API publik FastAPI, stabil lintas versi).
def registered_routes() -> set[tuple[str, str]]:
    return {(method.upper(), path) for path, ops in app.openapi()["paths"].items() for method in ops}


# Setiap endpoint terdaftar dengan method yang benar.
@pytest.mark.parametrize(("endpoint_id", "method", "path"), ENDPOINTS, ids=[e[0] for e in ENDPOINTS])
def test_route_registered(endpoint_id, method, path):
    assert (method, path) in registered_routes(), f"{endpoint_id} {method} {path} tidak terdaftar"


# Tidak ada endpoint /api/v1 tambahan di luar katalog (Never invent endpoints).
def test_no_extra_routes():
    assert registered_routes() == {(m, p) for _, m, p in ENDPOINTS}


@pytest.fixture(scope="module")
def stub_proof_headers(client: TestClient) -> dict[str, str]:
    """Membuat HR berwenang lewat Issuers API agar tes dapat mencapai handler Proofs yang masih stub."""
    user_ids = {Role.ADMIN: new_user_id(), Role.HR: new_user_id()}
    password_hash = hash_password("Stub#Demo2026")
    with get_session_factory().begin() as db:
        for role, user_id in user_ids.items():
            db.add(
                User(
                    id=user_id,
                    email=f"scaffold-{role.lower()}@lettrust.test",
                    display_name="Akun Demo Scaffold",
                    password_hash=password_hash,
                    role=role,
                    created_at=datetime.now(UTC),
                )
            )

    admin_token, _ = create_access_token(user_ids[Role.ADMIN], Role.ADMIN)
    hr_token, _ = create_access_token(user_ids[Role.HR], Role.HR)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    hr_headers = {"Authorization": f"Bearer {hr_token}"}
    registration = client.post(
        "/api/v1/issuers",
        headers=hr_headers,
        json={
            "companyName": "PT Demo Scaffold",
            "registrationNumber": "REG-SCAFFOLD-PROOFS",
            "contactEmail": "kontak@scaffold.test",
        },
    )
    assert registration.status_code == 201
    issuer_path = f"/api/v1/issuers/{registration.json()['issuerId']}"
    decision = client.patch(
        f"{issuer_path}/verification",
        headers=admin_headers,
        json={"decision": "VERIFIED", "evidenceRef": "EVD-SCAFFOLD-PROOFS"},
    )
    assert decision.status_code == 200
    authorization = client.post(
        f"{issuer_path}/hr-authorizations",
        headers=admin_headers,
        json={"hrId": user_ids[Role.HR]},
    )
    assert authorization.status_code == 201
    return hr_headers


# Endpoint stub mengembalikan 501 NOT_IMPLEMENTED dengan envelope SA §10.2 dan requestId.
@pytest.mark.parametrize("endpoint_id", list(STUB_REQUESTS))
def test_stub_returns_501_envelope(
    client: TestClient,
    endpoint_id: str,
    stub_proof_headers: dict[str, str],
) -> None:
    _, method, path = next(e for e in ENDPOINTS if e[0] == endpoint_id)
    proof_path = path.replace("{proofId}", PROOF_ID)
    response = client.request(method, proof_path, headers=stub_proof_headers, **STUB_REQUESTS[endpoint_id])
    assert response.status_code == 501, response.text
    body = response.json()
    assert body["error"]["code"] == "NOT_IMPLEMENTED"
    assert body["error"]["details"] == []
    assert body["requestId"].startswith("req_")
    assert response.headers["X-Request-ID"] == body["requestId"]


# D-05: 422 validasi bawaan FastAPI tidak ada di OpenAPI; 422 bisnis HR_NOT_AFFILIATED tetap ada di API-03 saja.
def test_openapi_keeps_only_business_422():
    schema = app.openapi()
    assert not {"HTTPValidationError", "ValidationError"} & set(schema["components"]["schemas"])
    with_422 = {
        (method.upper(), path): ops["responses"]["422"]
        for path, methods in schema["paths"].items()
        for method, ops in methods.items()
        if "422" in ops["responses"]
    }
    assert set(with_422) == {("POST", "/api/v1/issuers/{issuerId}/hr-authorizations")}
    response = with_422["POST", "/api/v1/issuers/{issuerId}/hr-authorizations"]
    assert response["description"] == "Kode error: HR_NOT_AFFILIATED"
    assert response["content"]["application/json"]["schema"]["$ref"].endswith("/ErrorEnvelope")


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
