# Owner: B (PIC 5) | Status: COMPLETE | Ref: SA §7.1, §10.2, §17.4
"""App factory ai-service: router /internal/v1, request ID, dan handler error ber-envelope."""

import logging
import re
import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.body_limit import BodySizeLimitMiddleware, keep_multipart_in_memory, request_body_limit
from app.core.config import get_settings
from app.core.errors import (
    DEFAULT_MESSAGES,
    ERROR_HTTP_STATUS,
    AppError,
    ErrorBody,
    ErrorCode,
    ErrorDetail,
    ErrorEnvelope,
)
from app.core.logging import configure_logging, new_request_id, request_id_var
from app.routers.extractions import router as extractions_router
from app.routers.health import router as health_router
from app.routers.risk_analyses import router as risk_router

logger = logging.getLogger("app.http")
REQUEST_ID_HEADER = "X-Request-ID"
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_HTTP_STATUS_CODES = {
    400: ErrorCode.VALIDATION_ERROR,
    404: ErrorCode.NOT_FOUND,
    405: ErrorCode.METHOD_NOT_ALLOWED,
    413: ErrorCode.FILE_TOO_LARGE,
}


# Menyusun JSONResponse envelope error SA §10.2 beserta header X-Request-ID.
def error_response(
    request: Request,
    code: ErrorCode,
    message: str | None = None,
    details: list[ErrorDetail] | None = None,
    status_code: int | None = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None) or request_id_var.get() or new_request_id()
    envelope = ErrorEnvelope(
        request_id=request_id,
        error=ErrorBody(code=code, message=message or DEFAULT_MESSAGES[code], details=details or []),
    )
    return JSONResponse(
        status_code=status_code or ERROR_HTTP_STATUS[code],
        content=envelope.model_dump(by_alias=True, mode="json"),
        headers={REQUEST_ID_HEADER: request_id},
    )


# Middleware: propagasi X-Request-ID dari backend dan log http.request tanpa body (probe health tidak dicatat).
async def request_context_middleware(request: Request, call_next):
    incoming = request.headers.get(REQUEST_ID_HEADER, "")
    request_id = incoming if _SAFE_REQUEST_ID.fullmatch(incoming) else new_request_id()
    request.state.request_id = request_id
    token = request_id_var.set(request_id)
    started = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
    finally:
        if request.url.path != "/internal/v1/health":
            logger.info(
                "http.request",
                extra={
                    "event": "http.request",
                    "method": request.method,
                    "path": request.url.path,
                    "status": status_code,
                    "durationMs": round((time.perf_counter() - started) * 1000),
                },
            )
        request_id_var.reset(token)


# Handler AppError.
async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    return error_response(request, exc.code, exc.message, exc.details)


# Handler validasi: 422 bawaan diubah menjadi 400 VALIDATION_ERROR.
async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        ErrorDetail(
            field=".".join(str(p) for p in err.get("loc", ())[1:]) or "request", issue=str(err.get("type", "invalid"))
        )
        for err in exc.errors()
    ]
    return error_response(request, ErrorCode.VALIDATION_ERROR, details=details)


# Handler HTTPException Starlette (route tidak ada, metode salah, multipart rusak).
async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = _HTTP_STATUS_CODES.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
    return error_response(request, code, status_code=exc.status_code if code is not ErrorCode.INTERNAL_ERROR else 500)


# Handler exception tak tertangani: 500 tanpa detail internal.
async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "http.unhandled_exception", extra={"event": "http.unhandled_exception", "errorCode": type(exc).__name__}
    )
    return error_response(request, ErrorCode.INTERNAL_ERROR)


# Membuat aplikasi; konfigurasi divalidasi saat start (mock di luar test ditolak).
def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, service="ai-service")
    app = FastAPI(
        title="Lettrust AI Service",
        version="1.0.0",
        description="Endpoint internal ai-service (SYSTEM_ARCHITECTURE §7, §10.8).",
    )
    body_limit = request_body_limit(settings.max_upload_bytes)
    keep_multipart_in_memory(body_limit)
    # Ditambahkan sebelum request_context agar berada di dalamnya (requestId sudah tersedia saat menolak).
    app.add_middleware(BodySizeLimitMiddleware, max_body_bytes=body_limit)
    app.middleware("http")(request_context_middleware)
    app.add_exception_handler(AppError, handle_app_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(Exception, handle_unexpected_error)
    for router in (extractions_router, risk_router, health_router):
        app.include_router(router, prefix="/internal/v1")
    return app


app = create_app()
