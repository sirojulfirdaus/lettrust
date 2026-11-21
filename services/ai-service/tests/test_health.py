# Owner: B (PIC 5) | Status: COMPLETE | Ref: SA §7.1, §8.2, TOI-09
"""Test health ai-service dan penegakan X-Internal-Token."""

from conftest import INTERNAL_TOKEN

PDF = ("offer.pdf", b"%PDF-1.4\n%synthetic\n", "application/pdf")


# Health melaporkan Tesseract dengan bahasa ind dan eng serta LLM unconfigured tanpa API key.
def test_health_reports_tesseract_and_llm(client):
    response = client.get("/internal/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["tesseract"]["available"] is True
    assert {"ind", "eng"} <= set(body["tesseract"]["languages"])
    assert body["tesseract"]["missingLanguages"] == []
    assert body["llm"] == "unconfigured"
    assert body["model"] == "openai/gpt-oss-120b"
    assert body["status"] == "degraded"


# Endpoint internal tanpa token atau dengan token salah ditolak 401 dengan envelope.
def test_internal_endpoints_require_token(client):
    for headers in ({}, {"X-Internal-Token": "salah"}):
        risk = client.post("/internal/v1/risk-analyses", json={"documentContent": "teks"}, headers=headers)
        extraction = client.post("/internal/v1/document-extractions", files={"file": PDF}, headers=headers)
        for response in (risk, extraction):
            assert response.status_code == 401
            assert response.json()["error"]["code"] == "UNAUTHENTICATED"
            assert response.json()["requestId"].startswith("req_")


# Dengan token valid, endpoint stub mengembalikan 501 NOT_IMPLEMENTED.
def test_stub_endpoints_return_501(client):
    headers = {"X-Internal-Token": INTERNAL_TOKEN, "X-Request-ID": "req_FROMBACKEND00001"}
    risk = client.post("/internal/v1/risk-analyses", json={"documentContent": "teks"}, headers=headers)
    extraction = client.post("/internal/v1/document-extractions", files={"file": PDF}, headers=headers)
    for response in (risk, extraction):
        assert response.status_code == 501
        assert response.json()["error"]["code"] == "NOT_IMPLEMENTED"
        assert response.json()["requestId"] == "req_FROMBACKEND00001"
