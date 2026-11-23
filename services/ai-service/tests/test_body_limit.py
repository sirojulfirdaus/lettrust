# Owner: B (PIC 5) | Status: COMPLETE | Ref: PRD NFR-02.01, BR-05.03; SA §10.2, §10.3
"""Test guard transport: spool multipart di memori dan penolakan body melebihi batas dengan 413 FILE_TOO_LARGE."""

import asyncio
import json

from conftest import INTERNAL_TOKEN
from fastapi.testclient import TestClient
from starlette.formparsers import MultiPartParser

from app.core.body_limit import MULTIPART_OVERHEAD_BYTES, BodySizeLimitMiddleware, request_body_limit
from app.core.config import get_settings

LIMIT = request_body_limit(get_settings().max_upload_bytes)
AUTH = {"X-Internal-Token": INTERNAL_TOKEN}


# Batas transport = MAX_UPLOAD_BYTES + 64 KiB; ambang spool lebih besar sehingga unggahan diterima tidak ke disk.
def test_spool_threshold_above_transport_limit(client):
    assert LIMIT == get_settings().max_upload_bytes + MULTIPART_OVERHEAD_BYTES
    assert MultiPartParser.spool_max_size > LIMIT


# Content-Length melebihi batas → 413 FILE_TOO_LARGE dengan envelope dan requestId sebelum parsing.
def test_declared_content_length_over_limit(client):
    response = client.post(
        "/internal/v1/document-extractions",
        content=b"x" * (LIMIT + 1),
        headers={**AUTH, "Content-Type": "application/octet-stream"},
    )
    assert response.status_code == 413
    body = response.json()
    assert body["error"]["code"] == "FILE_TOO_LARGE"
    assert body["requestId"].startswith("req_")
    assert response.headers["X-Request-ID"] == body["requestId"]


# Body di bawah batas (berkas 2 MB) mencapai ekstraksi; PDF rusak dipetakan ke NO_CONTENT.
def test_body_under_limit_reaches_route(client: TestClient) -> None:
    pdf = b"%PDF-1.4\n" + b"0" * (2 * 1024 * 1024)
    response = client.post(
        "/internal/v1/document-extractions",
        headers=AUTH,
        files={"file": ("offer.pdf", pdf, "application/pdf")},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "NO_CONTENT"
    assert response.json()["reasonDetail"] == "PDF_UNREADABLE"


# Body stream tanpa Content-Length dihitung saat diterima; melewati batas → 413 dan respons app dibuang.
def test_streamed_body_over_limit_rejected():
    sent: list[dict] = []

    # App minimal yang membaca seluruh body lalu membalas 200.
    async def inner_app(scope, receive, send):
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                raise RuntimeError("client disconnected")
            if not message.get("more_body", False):
                break
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    chunks = [{"type": "http.request", "body": b"x" * 6, "more_body": True} for _ in range(5)]

    # Mengalirkan potongan body tanpa header Content-Length.
    async def receive():
        return chunks.pop(0) if chunks else {"type": "http.request", "body": b"", "more_body": False}

    # Menangkap pesan respons.
    async def send(message):
        sent.append(message)

    state = {"request_id": "req_STREAMTEST000001"}
    scope = {"type": "http", "method": "POST", "path": "/", "headers": [], "state": state}
    asyncio.run(BodySizeLimitMiddleware(inner_app, max_body_bytes=10)(scope, receive, send))
    assert sent[0]["status"] == 413
    body = json.loads(sent[1]["body"])
    assert body == {
        "requestId": "req_STREAMTEST000001",
        "error": {"code": "FILE_TOO_LARGE", "message": body["error"]["message"], "details": []},
    }
    assert len(sent) == 2


# Body stream di bawah batas diteruskan apa adanya ke app.
def test_streamed_body_under_limit_passes():
    sent: list[dict] = []

    # App minimal yang membaca body lalu membalas 200.
    async def inner_app(scope, receive, send):
        await receive()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    # Satu potongan body kecil.
    async def receive():
        return {"type": "http.request", "body": b"small", "more_body": False}

    # Menangkap pesan respons.
    async def send(message):
        sent.append(message)

    asyncio.run(BodySizeLimitMiddleware(inner_app, max_body_bytes=10)({"type": "http", "headers": []}, receive, send))
    assert sent[0]["status"] == 200
