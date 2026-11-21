# Owner: B (PIC 5) | Status: STUB | Ref: PRD FR-05.05–FR-05.09; SA §7.3–§7.7, §10.8 (API-08)
# TODO: Tolak >AI_MAX_CHARS, 503 AI_PROVIDER_UNCONFIGURED tanpa API key,
# lalu prompt → provider → validator → scoring → compose.
"""Router API-08 analyzeOfferRisk (hanya backend dan skrip evaluasi, X-Internal-Token)."""

from fastapi import APIRouter, Depends

from app.core.auth import internal_caller
from app.core.errors import not_implemented
from app.schemas import RiskAnalysisRequest, RiskAnalysisResponse

router = APIRouter(tags=["risk-analysis"], dependencies=[Depends(internal_caller)])


# API-08: analisis risiko dari teks dokumen; kategori dari skoring deterministik, bukan dari model.
@router.post("/risk-analyses", response_model=RiskAnalysisResponse, operation_id="analyzeOfferRisk")
async def analyze_offer_risk(payload: RiskAnalysisRequest) -> RiskAnalysisResponse:
    raise not_implemented()
