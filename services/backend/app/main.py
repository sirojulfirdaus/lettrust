# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: SA §10.1, §10.2, §8.3, §16, §17.4
"""App factory FastAPI: router, request ID, CORS, dan handler error ber-envelope."""

import logging
import re
import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.body_limit import BodySizeLimitMiddleware, keep_multipart_in_memory, request_body_limit
from app.core.config import get_settings
from app.core.errors import DEFAULT_MESSAGES, ERROR_HTTP_STATUS, AppError
from app.core.ids import new_request_id
from app.core.logging import configure_logging, request_id_var
from app.core.schemas import ErrorBody, ErrorCode, ErrorDetail, ErrorEnvelope
from app.modules.auth.router import router as auth_router
from app.modules.health.router import router as health_router
from app.modules.issuers.router import router as issuers_router
from app.modules.proofs.router import router as proofs_router
from app.modules.verifications.router import router as verifications_router

logger = logging.getLogger("app.http")
REQUEST_ID_HEADER = "X-Request-ID"
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_HTTP_STATUS_CODES = {
    400: ErrorCode.VALIDATION_ERROR,
    404: ErrorCode.NOT_FOUND,
    405: ErrorCode.METHOD_NOT_ALLOWED,
    413: ErrorCode.FILE_TOO_LARGE,
}


# Mengambil requestId milik request saat ini (dibuat middleware).
def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or request_id_var.get() or new_request_id()


# Menyusun JSONResponse envelope error SA §10.2 beserta header X-Request-ID.
def error_response(
    request: Request,
    code: ErrorCode,
    message: str | None = None,
    details: list[ErrorDetail] | None = None,
    status_code: int | None = None,
) -> JSONResponse:
    request_id = _request_id(request)
    envelope = ErrorEnvelope(
        request_id=request_id,
        error=ErrorBody(code=code, message=message or DEFAULT_MESSAGES[code], details=details or []),
    )
    return JSONResponse(
        status_code=status_code or ERROR_HTTP_STATUS[code],
        content=envelope.model_dump(by_alias=True, mode="json"),
        headers={REQUEST_ID_HEADER: request_id},
    )


# Middleware: menerima/membuat X-Request-ID, menyimpannya untuk log, dan mencatat http.request tanpa body.
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
        # Probe liveness Compose (/healthz tiap 10 detik) tidak dicatat agar log tetap terbaca.
        if request.url.path != "/healthz":
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


# Handler AppError: kode dan pesan aman dari katalog. Setiap error dicatat `app.error` (kode dan status saja,
# requestId dari formatter) agar kategori kegagalan registry/AI dapat dibedakan di log (NFR-09.05).
async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    response = error_response(request, exc.code, exc.message, exc.details)
    logger.warning(
        "app.error",
        extra={"event": "app.error", "errorCode": exc.code.value, "status": response.status_code},
    )
    return response


# Handler validasi FastAPI: 422 bawaan diubah menjadi 400 VALIDATION_ERROR dengan rincian per field.
async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        ErrorDetail(
            field=".".join(str(part) for part in err.get("loc", ())[1:]) or str(err.get("loc", ("request",))[0]),
            issue=str(err.get("type", "invalid")),
        )
        for err in exc.errors()
    ]
    return error_response(request, ErrorCode.VALIDATION_ERROR, details=details)


# Handler HTTPException Starlette (route tidak ada, metode salah, body multipart rusak).
async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = _HTTP_STATUS_CODES.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
    return error_response(request, code, status_code=exc.status_code if code is not ErrorCode.INTERNAL_ERROR else 500)


# Handler exception tak tertangani: 500 INTERNAL_ERROR tanpa detail internal; hanya nama kelas yang dicatat.
async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "http.unhandled_exception", extra={"event": "http.unhandled_exception", "errorCode": type(exc).__name__}
    )
    return error_response(request, ErrorCode.INTERNAL_ERROR)


# Liveness sederhana untuk healthcheck Compose.
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


# Membungkus generator OpenAPI: respons 422 validasi bawaan FastAPI dihapus karena validasi dipetakan ke
# 400 VALIDATION_ERROR; 422 bisnis yang dideklarasikan lewat error_responses (mis. HR_NOT_AFFILIATED) tetap ada.
def _install_openapi_without_422(app: FastAPI) -> None:
    original = app.openapi

    # Menghasilkan (dan meng-cache) skema OpenAPI tanpa 422 bawaan dan skema validasi bawaan FastAPI.
    def openapi() -> dict:
        if app.openapi_schema is None:
            schema = original()
            for operations in schema.get("paths", {}).values():
                for operation in operations.values():
                    responses = operation.get("responses", {})
                    if _is_default_validation_response(responses.get("422")):
                        del responses["422"]
            for name in ("HTTPValidationError", "ValidationError"):
                schema.get("components", {}).get("schemas", {}).pop(name, None)
            app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = openapi


# Mengenali respons 422 yang ditambahkan FastAPI sendiri: deskripsi "Validation Error" atau skema HTTPValidationError.
def _is_default_validation_response(response: dict | None) -> bool:
    if response is None:
        return False
    ref = response.get("content", {}).get("application/json", {}).get("schema", {}).get("$ref", "")
    return response.get("description") == "Validation Error" or ref.endswith("/HTTPValidationError")


# Membuat aplikasi FastAPI; konfigurasi divalidasi saat start (gagal cepat bila env tidak lengkap).
def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, service="backend")
    app = FastAPI(
        title="Lettrust API",
        version="1.0.0",
        description="Kontrak API Lettrust D3 (SYSTEM_ARCHITECTURE §10). Endpoint publik/terautentikasi di /api/v1.",
    )
    body_limit = request_body_limit(settings.max_upload_bytes)
    keep_multipart_in_memory(body_limit)
    # Ditambahkan sebelum request_context agar berada di dalamnya (requestId sudah tersedia saat menolak).
    app.add_middleware(BodySizeLimitMiddleware, max_body_bytes=body_limit)
    app.middleware("http")(request_context_middleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", REQUEST_ID_HEADER],
        expose_headers=[REQUEST_ID_HEADER],
    )
    app.add_exception_handler(AppError, handle_app_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(Exception, handle_unexpected_error)
    for router in (auth_router, issuers_router, proofs_router, verifications_router, health_router):
        app.include_router(router, prefix="/api/v1")
    app.add_api_route("/healthz", healthz, methods=["GET"], include_in_schema=False)
    _install_openapi_without_422(app)
    return app


app = create_app()
