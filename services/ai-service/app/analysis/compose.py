# Owner: B (PIC 5) | Status: STUB | Ref: PRD FR-05.07; SA §7.7
# TODO: Susun indicators/indicatorDetails, explanation (model ≤600 karakter atau template), dan recommendation template.
"""Komposisi respons API-08 dari indikator tervalidasi dan kategori."""

from app.analysis.validator import ValidatedIndicator
from app.schemas import AnalysisMeta, RiskAnalysisResponse, RiskCategory


# Menyusun rekomendasi deterministik: selalu kanal resmi; + larangan bayar/beri data sesuai indikator; + catatan LOW.
def build_recommendation(category: RiskCategory, codes: set[str]) -> str:
    raise NotImplementedError("compose.build_recommendation belum diimplementasikan")


# Menyusun RiskAnalysisResponse lengkap; label indikator diambil dari taksonomi.
def compose_result(
    indicators: list[ValidatedIndicator], category: RiskCategory, model_explanation: str | None, meta: AnalysisMeta
) -> RiskAnalysisResponse:
    raise NotImplementedError("compose.compose_result belum diimplementasikan")
