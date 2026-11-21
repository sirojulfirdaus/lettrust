# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: SA §17.3; PRD NFR-04.07
"""Pemeriksaan health komponen; tidak pernah gagal keras, kegagalan dilaporkan sebagai status."""

import asyncio
import logging

import httpx
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core.db import get_engine
from app.modules.health.schemas import ComponentStatus, HealthComponents, HealthResponse
from app.modules.registry.adapter import get_registry_adapter

logger = logging.getLogger(__name__)
AI_HEALTH_TIMEOUT_SECONDS = 5.0


# Menjalankan `SELECT 1` pada basis data.
def _ping_database() -> None:
    with get_engine().connect() as connection:
        connection.execute(text("SELECT 1"))


# Memeriksa basis data dapat diakses.
async def check_database() -> ComponentStatus:
    try:
        await asyncio.to_thread(_ping_database)
        return ComponentStatus.OK
    except SQLAlchemyError as exc:
        logger.warning(
            "health.database_failed", extra={"event": "health.database_failed", "errorCode": type(exc).__name__}
        )
        return ComponentStatus.UNAVAILABLE


# Memeriksa RPC chain dapat dihubungi dan contract ter-deploy di alamat deployment.
async def check_registry() -> ComponentStatus:
    healthy = await asyncio.to_thread(get_registry_adapter().health)
    return ComponentStatus.OK if healthy else ComponentStatus.UNAVAILABLE


# Memeriksa ai-service; `unconfigured` bila LLM belum dikonfigurasi tetapi OCR siap.
async def check_ai_service() -> ComponentStatus:
    url = get_settings().ai_service_url.rstrip("/") + "/internal/v1/health"
    try:
        async with httpx.AsyncClient(timeout=AI_HEALTH_TIMEOUT_SECONDS) as client:
            response = await client.get(url)
        body = response.json() if response.status_code == 200 else {}
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "health.ai_service_failed", extra={"event": "health.ai_service_failed", "errorCode": type(exc).__name__}
        )
        return ComponentStatus.UNAVAILABLE
    ocr_ready = bool(body.get("tesseract", {}).get("available")) and not body.get("tesseract", {}).get(
        "missingLanguages"
    )
    if body.get("status") == "ok":
        return ComponentStatus.OK
    if ocr_ready and body.get("llm") == "unconfigured":
        return ComponentStatus.UNCONFIGURED
    return ComponentStatus.UNAVAILABLE


# Menyusun respons health; `degraded` bila ada komponen yang tidak `ok`.
async def get_health() -> HealthResponse:
    database, registry, ai_service = await asyncio.gather(check_database(), check_registry(), check_ai_service())
    components = HealthComponents(database=database, registry=registry, ai_service=ai_service)
    healthy = all(value is ComponentStatus.OK for value in (database, registry, ai_service))
    return HealthResponse(status="ok" if healthy else "degraded", components=components)
