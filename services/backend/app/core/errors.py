# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: SA §10.2, §10.3; PRD §9.8
"""Error aplikasi dengan pemetaan kode ke HTTP status dan pesan aman berbahasa Indonesia."""

from typing import Any

from app.core.schemas import ErrorCode, ErrorDetail, ErrorEnvelope

ERROR_HTTP_STATUS: dict[ErrorCode, int] = {
    ErrorCode.VALIDATION_ERROR: 400,
    ErrorCode.INVALID_INPUT_COMBINATION: 400,
    ErrorCode.AI_ONLY_REQUIRES_INCLUDE_RISK: 400,
    ErrorCode.INVALID_REFERENCE_CODE_FORMAT: 400,
    ErrorCode.EMPTY_FILE: 400,
    ErrorCode.MULTIPLE_FILES: 400,
    ErrorCode.UNAUTHENTICATED: 401,
    ErrorCode.INVALID_CREDENTIALS: 401,
    ErrorCode.FORBIDDEN_OPERATION: 403,
    ErrorCode.ISSUER_NOT_FOUND: 404,
    ErrorCode.PROOF_NOT_FOUND: 404,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.METHOD_NOT_ALLOWED: 405,
    ErrorCode.EMAIL_ALREADY_REGISTERED: 409,
    ErrorCode.ACCOUNT_ALREADY_AFFILIATED: 409,
    ErrorCode.REGISTRATION_NUMBER_ALREADY_EXISTS: 409,
    ErrorCode.ISSUER_DECISION_ALREADY_MADE: 409,
    ErrorCode.ISSUER_NOT_VERIFIED: 409,
    ErrorCode.HR_ALREADY_AUTHORIZED: 409,
    ErrorCode.PROOF_ALREADY_REVOKED: 409,
    ErrorCode.IDEMPOTENCY_KEY_CONFLICT: 409,
    ErrorCode.DUPLICATE_ACTIVE_DOCUMENT: 409,
    ErrorCode.FILE_TOO_LARGE: 413,
    ErrorCode.UNSUPPORTED_MEDIA_TYPE: 415,
    ErrorCode.HR_NOT_AFFILIATED: 422,
    ErrorCode.RATE_LIMITED: 429,
    ErrorCode.INTERNAL_ERROR: 500,
    ErrorCode.AI_OUTPUT_INVALID: 502,
    ErrorCode.REGISTRY_UNAVAILABLE: 503,
    ErrorCode.REGISTRY_TRANSACTION_FAILED: 503,
    ErrorCode.SERVICE_UNAVAILABLE: 503,
    ErrorCode.AI_PROVIDER_UNCONFIGURED: 503,
    ErrorCode.AI_QUOTA_EXCEEDED: 503,
    ErrorCode.AI_PROVIDER_ERROR: 503,
    ErrorCode.AI_TIMEOUT: 504,
}

DEFAULT_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.VALIDATION_ERROR: "Data yang dikirim tidak valid.",
    ErrorCode.INVALID_INPUT_COMBINATION: "Masukkan kode referensi atau unggah berkas PDF untuk dianalisis.",
    ErrorCode.AI_ONLY_REQUIRES_INCLUDE_RISK: (
        "Tanpa kode referensi, pemeriksaan hanya dapat dilakukan dengan analisis AI. "
        "Setujui pemrosesan AI untuk melanjutkan."
    ),
    ErrorCode.INVALID_REFERENCE_CODE_FORMAT: "Format kode referensi tidak valid. Periksa kembali kode pada surat Anda.",
    ErrorCode.EMPTY_FILE: "Berkas kosong tidak dapat diproses.",
    ErrorCode.MULTIPLE_FILES: "Hanya satu berkas yang dapat diproses per permintaan.",
    ErrorCode.UNAUTHENTICATED: "Sesi Anda telah berakhir. Silakan masuk kembali.",
    ErrorCode.INVALID_CREDENTIALS: "Email atau password tidak sesuai.",
    ErrorCode.FORBIDDEN_OPERATION: "Anda tidak memiliki izin untuk tindakan ini.",
    ErrorCode.ISSUER_NOT_FOUND: "Penerbit tidak ditemukan.",
    ErrorCode.PROOF_NOT_FOUND: "Bukti tidak ditemukan.",
    ErrorCode.NOT_FOUND: "Sumber daya tidak ditemukan.",
    ErrorCode.METHOD_NOT_ALLOWED: "Metode tidak diizinkan untuk endpoint ini.",
    ErrorCode.EMAIL_ALREADY_REGISTERED: "Email sudah terdaftar. Silakan masuk.",
    ErrorCode.ACCOUNT_ALREADY_AFFILIATED: "Akun Anda sudah terhubung dengan perusahaan.",
    ErrorCode.REGISTRATION_NUMBER_ALREADY_EXISTS: "Nomor registrasi perusahaan sudah terdaftar.",
    ErrorCode.ISSUER_DECISION_ALREADY_MADE: "Penerbit ini sudah memiliki keputusan verifikasi.",
    ErrorCode.ISSUER_NOT_VERIFIED: "Penerbit belum terverifikasi sehingga HR belum dapat diotorisasi.",
    ErrorCode.HR_ALREADY_AUTHORIZED: "Akun HR ini sudah diotorisasi.",
    ErrorCode.PROOF_ALREADY_REVOKED: "Bukti ini sudah dicabut sebelumnya.",
    ErrorCode.IDEMPOTENCY_KEY_CONFLICT: (
        "Permintaan bertentangan dengan permintaan sebelumnya. Mulai ulang proses penerbitan."
    ),
    ErrorCode.DUPLICATE_ACTIVE_DOCUMENT: "Berkas yang sama sudah memiliki bukti aktif.",
    ErrorCode.HR_NOT_AFFILIATED: "Akun HR tidak terhubung dengan penerbit ini.",
    ErrorCode.FILE_TOO_LARGE: "Ukuran berkas melebihi batas yang diizinkan.",
    ErrorCode.UNSUPPORTED_MEDIA_TYPE: "Berkas harus berformat PDF.",
    ErrorCode.RATE_LIMITED: "Terlalu banyak permintaan. Coba lagi beberapa saat lagi.",
    ErrorCode.INTERNAL_ERROR: "Terjadi kesalahan internal. Coba lagi beberapa saat lagi.",
    ErrorCode.REGISTRY_UNAVAILABLE: "Pencatatan ke registry gagal. Tidak ada perubahan yang tersimpan. Coba lagi.",
    ErrorCode.REGISTRY_TRANSACTION_FAILED: (
        "Pencatatan ke registry gagal. Tidak ada perubahan yang tersimpan. Coba lagi."
    ),
    ErrorCode.SERVICE_UNAVAILABLE: "Layanan pemeriksaan sedang tidak tersedia. Coba lagi beberapa saat lagi.",
    ErrorCode.AI_PROVIDER_UNCONFIGURED: "Layanan analisis AI belum dikonfigurasi.",
    ErrorCode.AI_QUOTA_EXCEEDED: "Kapasitas layanan analisis sedang habis.",
    ErrorCode.AI_PROVIDER_ERROR: "Layanan analisis AI sedang tidak tersedia.",
    ErrorCode.AI_OUTPUT_INVALID: "Output analisis AI tidak valid.",
    ErrorCode.AI_TIMEOUT: "Analisis AI melebihi batas waktu.",
}


class AppError(Exception):
    """Exception terkontrol yang diubah menjadi envelope error SA §10.2 oleh handler global."""

    # Menyimpan kode, pesan aman, dan rincian validasi opsional.
    def __init__(self, code: ErrorCode, message: str | None = None, details: list[ErrorDetail] | None = None):
        self.code = code
        self.message = message or DEFAULT_MESSAGES[code]
        self.details = details or []
        super().__init__(code.value)

    # Mengembalikan HTTP status untuk kode error ini.
    @property
    def status_code(self) -> int:
        return ERROR_HTTP_STATUS[self.code]


# Menyusun dokumentasi respons error OpenAPI (model ErrorEnvelope) untuk kode-kode yang mungkin muncul.
def error_responses(*codes: ErrorCode) -> dict[int | str, dict[str, Any]]:
    grouped: dict[int, list[str]] = {}
    for code in (*codes, ErrorCode.VALIDATION_ERROR, ErrorCode.INTERNAL_ERROR):
        grouped.setdefault(ERROR_HTTP_STATUS[code], [])
        if code.value not in grouped[ERROR_HTTP_STATUS[code]]:
            grouped[ERROR_HTTP_STATUS[code]].append(code.value)
    return {
        status: {"model": ErrorEnvelope, "description": "Kode error: " + ", ".join(names)}
        for status, names in sorted(grouped.items())
    }
