# Owner: B (PIC 5) | Status: COMPLETE | Ref: SA §7.1, §10.4 (I-02), TOI-09
"""Router I-02 health: ketersediaan Tesseract (ind, eng) dan konfigurasi LLM."""

import logging
from functools import lru_cache

import pytesseract
from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas import AiHealthResponse, TesseractStatus

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)
REQUIRED_LANGUAGES = ("ind", "eng")


# Memeriksa biner Tesseract dan paket bahasa sekali per proses (instalasi tidak berubah saat runtime).
@lru_cache
def tesseract_status() -> TesseractStatus:
    try:
        version = str(pytesseract.get_tesseract_version())
        languages = sorted(lang for lang in pytesseract.get_languages(config="") if lang != "osd")
    except (pytesseract.TesseractNotFoundError, pytesseract.TesseractError, OSError) as exc:
        logger.warning(
            "ocr.tesseract_unavailable", extra={"event": "ocr.tesseract_unavailable", "errorCode": type(exc).__name__}
        )
        return TesseractStatus(available=False, version=None, languages=[], missing_languages=list(REQUIRED_LANGUAGES))
    missing = [lang for lang in REQUIRED_LANGUAGES if lang not in languages]
    return TesseractStatus(available=True, version=version, languages=languages, missing_languages=missing)


# I-02: status OCR, LLM configured/unconfigured, dan nama model; selalu HTTP 200.
@router.get("/health", response_model=AiHealthResponse, operation_id="getAiHealth")
async def health() -> AiHealthResponse:
    settings = get_settings()
    tesseract = tesseract_status()
    llm = "configured" if settings.llm_configured else "unconfigured"
    ok = tesseract.available and not tesseract.missing_languages and llm == "configured"
    return AiHealthResponse(status="ok" if ok else "degraded", tesseract=tesseract, llm=llm, model=settings.llm_model)
