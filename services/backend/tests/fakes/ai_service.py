# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: SA §5.3.3, §7.1, §8.2, §10.2, §10.3, §10.8
"""Fake ai-service untuk test backend (verifications/ai_client.py) berbasis httpx.MockTransport.

Respons diambil dari contracts/examples/internal/ sehingga sama dengan kontrak yang divalidasi ai-service.
Pemakaian: `fake = FakeAiService(analysis="quota_exceeded")` lalu
`httpx.AsyncClient(base_url=settings.ai_service_url, transport=fake.transport())`; inspeksi `fake.requests`.
"""

import json
import re

import httpx

from app.core.config import get_settings
from fakes.contracts import load_example

# Token internal environment test (diset tests/conftest.py); dibaca dari Settings agar tidak ada salinan kedua.
INTERNAL_TOKEN = get_settings().internal_api_token.get_secret_value()
EXTRACTION_PATH = "/internal/v1/document-extractions"
ANALYSIS_PATH = "/internal/v1/risk-analyses"
# Nilai extractionMethod API-08 yang diterima ai-service.
EXTRACTION_METHODS = {"TEXT_LAYER", "OCR", "MIXED"}
HEALTH_PATH = "/internal/v1/health"
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

# Mode sukses per endpoint → contoh internal.
SUCCESS_EXAMPLES = {
    EXTRACTION_PATH: {
        "ok": "internal/i-01.extraction-ok.json",
        "ok_truncated": "internal/i-01.extraction-ok-truncated.json",
        "no_content": "internal/i-01.extraction-no-content.json",
        "unreadable": "internal/i-01.extraction-unreadable.json",
    },
    ANALYSIS_PATH: {
        "high": "internal/api-08.response-high.json",
        "medium": "internal/api-08.response-medium.json",
        "low": "internal/api-08.response-low.json",
    },
    HEALTH_PATH: {
        "ok": "internal/i-02.health-ok.json",
        "unconfigured": "internal/i-02.health-unconfigured.json",
        "ocr_missing_language": "internal/i-02.health-ocr-missing-language.json",
    },
}
# Mode error HTTP (berlaku di semua endpoint) → (status, contoh envelope). Status sesuai katalog SA §10.3.
ERROR_EXAMPLES = {
    "validation_error": (400, "internal/error.validation-error.json"),
    "unauthorized": (401, "internal/error.unauthenticated.json"),
    "server_error": (500, "internal/error.internal-error.json"),
    "quota_exceeded": (503, "internal/error.ai-quota-exceeded.json"),
    "provider_error": (503, "internal/error.ai-provider-error.json"),
    "unconfigured": (503, "internal/error.ai-provider-unconfigured.json"),
    "output_invalid": (502, "internal/error.ai-output-invalid.json"),
    "provider_timeout": (504, "internal/error.ai-timeout.json"),
    "file_too_large": (413, "internal/error.file-too-large.json"),
    "unsupported_media_type": (415, "internal/error.unsupported-media-type.json"),
    "empty_file": (400, "internal/error.empty-file.json"),
}
# Mode kegagalan transport: client menerima exception httpx, bukan respons.
TRANSPORT_FAILURES = ("timeout", "unavailable")
# Error yang memang dapat dikembalikan tiap endpoint (SA §10.3): AI_* hanya API-08; health selalu 200.
ALLOWED_ERROR_MODES = {
    EXTRACTION_PATH: {
        "validation_error",
        "unauthorized",
        "server_error",
        "file_too_large",
        "unsupported_media_type",
        "empty_file",
    },
    ANALYSIS_PATH: {
        "validation_error",
        "unauthorized",
        "server_error",
        "quota_exceeded",
        "provider_error",
        "unconfigured",
        "output_invalid",
        "provider_timeout",
    },
    HEALTH_PATH: set(),
}


class FakeAiService:
    """ai-service palsu: memeriksa X-Internal-Token seperti aslinya, lalu merespons sesuai mode per endpoint."""

    # Menyimpan mode per endpoint dan token internal yang diharapkan; semua request dicatat.
    def __init__(self, extraction: str = "ok", analysis: str = "high", health: str = "ok", token: str = INTERNAL_TOKEN):
        self.modes = {EXTRACTION_PATH: extraction, ANALYSIS_PATH: analysis, HEALTH_PATH: health}
        for path, mode in self.modes.items():
            allowed = set(SUCCESS_EXAMPLES[path]) | ALLOWED_ERROR_MODES[path] | set(TRANSPORT_FAILURES)
            if mode not in allowed:
                raise ValueError(f"mode {mode!r} tidak mungkin terjadi pada {path}")
        self.token = token
        self.requests: list[httpx.Request] = []

    # Membuat httpx.MockTransport yang memakai handler fake ini.
    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)

    # Handler request: path tak dikenal 404, token salah 401, validasi body 400, lalu respons sesuai mode.
    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if path not in self.modes:
            return _envelope_response(request, 404, "NOT_FOUND", "Sumber daya tidak ditemukan.")
        mode = self.modes[path]
        if mode == "timeout":
            raise httpx.ReadTimeout("timeout (fake ai-service)", request=request)
        if mode == "unavailable":
            raise httpx.ConnectError("connection refused (fake ai-service)", request=request)
        if path != HEALTH_PATH and request.headers.get("X-Internal-Token") != self.token:
            return _example_response(request, *ERROR_EXAMPLES["unauthorized"])
        # Mode sukses endpoint didahulukan (mis. health "unconfigured" adalah respons 200, bukan error API-08).
        if mode in SUCCESS_EXAMPLES[path]:
            if not _body_valid(path, request):
                return _example_response(request, *ERROR_EXAMPLES["validation_error"])
            return _example_response(request, 200, SUCCESS_EXAMPLES[path][mode])
        return _example_response(request, *ERROR_EXAMPLES[mode])


# Memeriksa bentuk body seperti ai-service: I-01 multipart; API-08 JSON dengan documentContent non-kosong dan
# extractionMethod opsional (TEXT_LAYER/OCR/MIXED; tidak boleh null, D-20).
def _body_valid(path: str, request: httpx.Request) -> bool:
    if path == EXTRACTION_PATH:
        return request.headers.get("content-type", "").startswith("multipart/form-data")
    if path == ANALYSIS_PATH:
        try:
            body = json.loads(request.content or b"null")
        except ValueError:
            return False
        if not isinstance(body, dict) or set(body) - {"documentContent", "extractionMethod"}:
            return False
        method_valid = "extractionMethod" not in body or body["extractionMethod"] in EXTRACTION_METHODS
        return isinstance(body.get("documentContent"), str) and bool(body["documentContent"]) and method_valid
    return True


# Respons dari contoh JSON dengan X-Request-ID dipantulkan; requestId envelope disamakan dengan header.
def _example_response(request: httpx.Request, status: int, example: str) -> httpx.Response:
    body = load_example(example)
    request_id = request.headers.get("X-Request-ID") or "req_FAKEAISERVICE000"
    if isinstance(body, dict) and "requestId" in body:
        body = {**body, "requestId": request_id}
    return httpx.Response(status, json=body, headers={"X-Request-ID": request_id})


# Respons envelope SA §10.2 ad-hoc (untuk path tak dikenal).
def _envelope_response(request: httpx.Request, status: int, code: str, message: str) -> httpx.Response:
    request_id = request.headers.get("X-Request-ID") or "req_FAKEAISERVICE000"
    body = {"requestId": request_id, "error": {"code": code, "message": message, "details": []}}
    return httpx.Response(status, json=body, headers={"X-Request-ID": request_id})


# Assert helper: request internal membawa X-Internal-Token yang benar dan X-Request-ID yang aman (SA §8.1, §17.4).
def assert_internal_headers(request: httpx.Request, token: str = INTERNAL_TOKEN, request_id: str | None = None) -> None:
    assert request.headers.get("X-Internal-Token") == token, "X-Internal-Token tidak ada atau salah"
    received_id = request.headers.get("X-Request-ID")
    assert received_id and _SAFE_REQUEST_ID.fullmatch(received_id), "X-Request-ID tidak ada atau tidak valid"
    if request_id is not None:
        assert received_id == request_id
