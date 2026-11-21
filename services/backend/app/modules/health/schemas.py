# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: SA §17.3
"""Skema health check komponen backend."""

from enum import StrEnum
from typing import Literal

from app.core.schemas import ApiModel


class ComponentStatus(StrEnum):
    """Status satu komponen yang dipantau."""

    OK = "ok"
    UNAVAILABLE = "unavailable"
    UNCONFIGURED = "unconfigured"


class HealthComponents(ApiModel):
    """Status basis data, registry, dan layanan AI."""

    database: ComponentStatus
    registry: ComponentStatus
    ai_service: ComponentStatus


class HealthResponse(ApiModel):
    """S-07: `degraded` bila ada komponen unavailable/unconfigured; HTTP tetap 200."""

    status: Literal["ok", "degraded"]
    components: HealthComponents
