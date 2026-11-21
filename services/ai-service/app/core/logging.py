# Owner: B (PIC 5) | Status: COMPLETE | Ref: SA §17.4; PRD NFR-02.05, FR-05.11
"""Logging JSON satu baris ke stderr; tanpa teks dokumen, kutipan, output model mentah, token, atau kunci."""

import json
import logging
import secrets
import sys
from contextvars import ContextVar
from datetime import UTC, datetime

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


# Membuat requestId `req_` + 16 karakter Crockford bila backend tidak mengirim X-Request-ID.
def new_request_id() -> str:
    return "req_" + "".join(secrets.choice(_CROCKFORD) for _ in range(16))


# Hanya field ini yang boleh ditambahkan lewat `extra`; mencegah konten sensitif ikut tercatat.
ALLOWED_FIELDS = (
    "event",
    "method",
    "path",
    "status",
    "durationMs",
    "errorCode",
    "model",
    "promptVersion",
    "latencyMs",
    "droppedIndicators",
    "extractionMethod",
    "component",
)
_LEVEL_NAMES = {"WARNING": "WARN", "CRITICAL": "ERROR"}


class JsonFormatter(logging.Formatter):
    """Memformat LogRecord menjadi JSON SA §17.4."""

    # Menyimpan nama layanan untuk field `service`.
    def __init__(self, service: str):
        super().__init__()
        self.service = service

    # Menyusun objek log dari record dan field yang diizinkan.
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "level": _LEVEL_NAMES.get(record.levelname, record.levelname),
            "service": self.service,
            "requestId": request_id_var.get(),
            "event": getattr(record, "event", None) or record.getMessage(),
        }
        for field in ALLOWED_FIELDS[1:]:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info and record.exc_info[0] is not None:
            payload["exception"] = record.exc_info[0].__name__
        return json.dumps(payload, ensure_ascii=False)


# Mengonfigurasi root logger dengan formatter JSON ke stderr (stdout bersih untuk skrip evaluasi).
def configure_logging(level: str = "INFO", service: str = "ai-service") -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter(service))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    for name in ("uvicorn", "uvicorn.error"):
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True
