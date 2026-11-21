# Owner: Dws (PIC 1) | Status: STUB | Ref: PRD FR-05.01, FR-05.04, FR-05.09; SA §5.3.3, §7.1, §10.8
# TODO: Panggil I-01 lalu API-08 dengan X-Internal-Token dan X-Request-ID (httpx, timeout terpisah);
# petakan kegagalan ke RiskAnalysis UNAVAILABLE.
"""Client internal ke ai-service dan pipeline risiko yang tidak pernah raise ke orkestrator."""

from app.modules.verifications.schemas import RiskAnalysis


class AiServiceClient:
    """Client HTTP ke ai-service; satu-satunya pemegang INTERNAL_API_TOKEN di backend selain health."""

    # Memanggil POST /internal/v1/document-extractions dengan byte berkas yang sama dengan yang di-hash.
    async def extract(self, file_bytes: bytes, request_id: str) -> dict:
        raise NotImplementedError("AiServiceClient.extract belum diimplementasikan")

    # Memanggil POST /internal/v1/risk-analyses (API-08) dengan teks hasil ekstraksi.
    async def analyze(self, document_content: str, request_id: str) -> dict:
        raise NotImplementedError("AiServiceClient.analyze belum diimplementasikan")


# Menjalankan ekstraksi + analisis; NO_CONTENT → NOT_PERFORMED, kegagalan → UNAVAILABLE dengan reason (tanpa fallback).
async def run_risk_pipeline(file_bytes: bytes, request_id: str) -> RiskAnalysis:
    raise NotImplementedError("ai_client.run_risk_pipeline belum diimplementasikan")
