# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: PRD NFR-02.01, BR-05.03; SA §10.2, §10.3, §16
"""Guard transport: batas ukuran body sebelum parsing dan ambang spool multipart agar unggahan tetap di memori."""

import json

from starlette.formparsers import MultiPartParser
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import DEFAULT_MESSAGES, ERROR_HTTP_STATUS
from app.core.ids import new_request_id
from app.core.logging import request_id_var
from app.core.schemas import ErrorBody, ErrorCode, ErrorEnvelope

MULTIPART_OVERHEAD_BYTES = 64 * 1024


# Batas body transport: MAX_UPLOAD_BYTES (konfigurasi) + margin overhead multipart 64 KiB.
def request_body_limit(max_upload_bytes: int) -> int:
    return max_upload_bytes + MULTIPART_OVERHEAD_BYTES


# Menaikkan ambang spool Starlette (MultiPartParser.spool_max_size) di atas batas transport: berkas tidak ke disk.
def keep_multipart_in_memory(body_limit: int) -> None:
    MultiPartParser.spool_max_size = body_limit + 1


class BodySizeLimitMiddleware:
    """Middleware ASGI murni: menolak body melebihi batas (Content-Length atau hitungan stream) dengan 413."""

    # Menyimpan app berikutnya dan batas body dalam byte.
    def __init__(self, app: ASGIApp, max_body_bytes: int):
        self.app = app
        self.max_body_bytes = max_body_bytes

    # Memeriksa Content-Length lebih dulu, lalu menghitung byte stream; body tidak pernah dibuffer oleh middleware.
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        declared = _content_length(scope)
        if declared is not None and declared > self.max_body_bytes:
            await _send_rejection(scope, send)
            return

        received = 0
        exceeded = False
        response_started = False

        # Meneruskan pesan body sambil menghitung; saat batas terlampaui, app menerima disconnect.
        async def guarded_receive() -> Message:
            nonlocal received, exceeded
            if exceeded:
                return {"type": "http.disconnect"}
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_body_bytes:
                    exceeded = True
                    return {"type": "http.disconnect"}
            return message

        # Meneruskan respons app kecuali setelah batas terlampaui (respons penolakan dikirim middleware).
        async def guarded_send(message: Message) -> None:
            nonlocal response_started
            if exceeded:
                return
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, guarded_receive, guarded_send)
        except Exception:
            # Hanya kegagalan akibat disconnect yang disuntikkan guard yang ditelan; selain itu diteruskan.
            if not exceeded:
                raise
        if exceeded and not response_started:
            await _send_rejection(scope, send)


# Membaca header Content-Length sebagai int; None bila tidak ada atau tidak valid.
def _content_length(scope: Scope) -> int | None:
    for name, value in scope.get("headers", []):
        if name == b"content-length":
            return int(value) if value.isdigit() else None
    return None


# Mengirim envelope SA §10.2 FILE_TOO_LARGE (413) dengan requestId request saat ini.
async def _send_rejection(scope: Scope, send: Send) -> None:
    request_id = scope.get("state", {}).get("request_id") or request_id_var.get() or new_request_id()
    code = ErrorCode.FILE_TOO_LARGE
    envelope = ErrorEnvelope(request_id=request_id, error=ErrorBody(code=code, message=DEFAULT_MESSAGES[code]))
    body = json.dumps(envelope.model_dump(by_alias=True, mode="json")).encode("utf-8")
    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode("ascii")),
        (b"x-request-id", request_id.encode("ascii")),
        (b"connection", b"close"),
    ]
    await send({"type": "http.response.start", "status": ERROR_HTTP_STATUS[code], "headers": headers})
    await send({"type": "http.response.body", "body": body})
