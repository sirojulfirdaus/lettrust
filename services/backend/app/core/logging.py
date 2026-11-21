# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: SA §17.4; PRD NFR-02.05
"""Logging JSON satu baris per event ke stderr; tanpa body, berkas, teks, token, atau secret."""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

# Hanya field ini yang boleh ditambahkan lewat `extra`; mencegah konten sensitif ikut tercatat.
ALLOWED_FIELDS = (
    "event",
    "method",
    "path",
    "status",
    "durationMs",
    "errorCode",
    "proofId",
    "txHash",
    "mode",
    "lookup",
    "riskState",
    "model",
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


# Mengonfigurasi root logger dengan formatter JSON ke stderr (stdout dipakai export-openapi).
def configure_logging(level: str = "INFO", service: str = "backend") -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter(service))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    for name in ("uvicorn", "uvicorn.error"):
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True
