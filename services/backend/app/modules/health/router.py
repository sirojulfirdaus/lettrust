# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: SA §17.3, §10.4 (S-07)
"""Router S-07 health (publik)."""

from fastapi import APIRouter

from app.modules.health.schemas import HealthResponse
from app.modules.health.service import get_health

router = APIRouter(tags=["health"])


# S-07: status komponen database, registry, dan aiService; selalu HTTP 200.
@router.get("/health", response_model=HealthResponse, operation_id="getHealth")
async def health() -> HealthResponse:
    return await get_health()
