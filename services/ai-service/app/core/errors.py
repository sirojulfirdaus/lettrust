# Owner: B (PIC 5) | Status: COMPLETE | Ref: SA §10.2, §10.3, §7.4.1
"""Kode error ai-service, envelope SA §10.2, dan AppError."""

from enum import StrEnum

from pydantic import Field

from app.schemas import ApiModel


class ErrorCode(StrEnum):
    """Kode error yang dapat dikembalikan ai-service (subset SA §10.3 + NOT_FOUND/METHOD_NOT_ALLOWED routing)."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    EMPTY_FILE = "EMPTY_FILE"
    MULTIPLE_FILES = "MULTIPLE_FILES"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    UNSUPPORTED_MEDIA_TYPE = "UNSUPPORTED_MEDIA_TYPE"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    AI_PROVIDER_UNCONFIGURED = "AI_PROVIDER_UNCONFIGURED"
    AI_QUOTA_EXCEEDED = "AI_QUOTA_EXCEEDED"
    AI_PROVIDER_ERROR = "AI_PROVIDER_ERROR"
    AI_OUTPUT_INVALID = "AI_OUTPUT_INVALID"
    AI_TIMEOUT = "AI_TIMEOUT"
    NOT_FOUND = "NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"


ERROR_HTTP_STATUS: dict[ErrorCode, int] = {
    ErrorCode.VALIDATION_ERROR: 400,
    ErrorCode.EMPTY_FILE: 400,
    ErrorCode.MULTIPLE_FILES: 400,
    ErrorCode.UNAUTHENTICATED: 401,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.METHOD_NOT_ALLOWED: 405,
    ErrorCode.FILE_TOO_LARGE: 413,
    ErrorCode.UNSUPPORTED_MEDIA_TYPE: 415,
    ErrorCode.INTERNAL_ERROR: 500,
    ErrorCode.AI_OUTPUT_INVALID: 502,
    ErrorCode.AI_PROVIDER_UNCONFIGURED: 503,
    ErrorCode.AI_QUOTA_EXCEEDED: 503,
    ErrorCode.AI_PROVIDER_ERROR: 503,
    ErrorCode.AI_TIMEOUT: 504,
}

DEFAULT_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.VALIDATION_ERROR: "Data yang dikirim tidak valid.",
    ErrorCode.EMPTY_FILE: "Berkas kosong tidak dapat diproses.",
    ErrorCode.MULTIPLE_FILES: "Hanya satu berkas yang dapat diproses per permintaan.",
    ErrorCode.UNAUTHENTICATED: "Token internal tidak valid.",
    ErrorCode.FILE_TOO_LARGE: "Ukuran berkas melebihi batas yang diizinkan.",
    ErrorCode.UNSUPPORTED_MEDIA_TYPE: "Berkas harus berformat PDF.",
    ErrorCode.INTERNAL_ERROR: "Terjadi kesalahan internal.",
    ErrorCode.AI_PROVIDER_UNCONFIGURED: "Penyedia model AI belum dikonfigurasi.",
    ErrorCode.AI_QUOTA_EXCEEDED: "Kuota atau rate limit penyedia model terlampaui.",
    ErrorCode.AI_PROVIDER_ERROR: "Penyedia model AI mengembalikan kesalahan.",
    ErrorCode.AI_OUTPUT_INVALID: "Output model tidak valid setelah satu kali pengulangan.",
    ErrorCode.AI_TIMEOUT: "Penyedia model AI melebihi batas waktu.",
    ErrorCode.NOT_FOUND: "Sumber daya tidak ditemukan.",
    ErrorCode.METHOD_NOT_ALLOWED: "Metode tidak diizinkan untuk endpoint ini.",
}


class ErrorDetail(ApiModel):
    """Rincian error validasi per field."""

    field: str
    issue: str


class ErrorBody(ApiModel):
    """Isi error: kode stabil, pesan aman, rincian opsional."""

    code: ErrorCode
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)


class ErrorEnvelope(ApiModel):
    """Envelope error SA §10.2."""

    request_id: str
    error: ErrorBody


class AppError(Exception):
    """Exception terkontrol yang diubah menjadi envelope error oleh handler global."""

    # Menyimpan kode, pesan aman, dan rincian opsional.
    def __init__(self, code: ErrorCode, message: str | None = None, details: list[ErrorDetail] | None = None):
        self.code = code
        self.message = message or DEFAULT_MESSAGES[code]
        self.details = details or []
        super().__init__(code.value)
