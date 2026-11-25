# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: PRD FR-05.01, FR-05.04, FR-05.09; SA §5.3.3, §7.2, §10.8, §17.1, §17.4
"""Client internal ke ai-service (I-01 lalu API-08) dan pipeline risiko yang tidak pernah raise ke orkestrator.

Model respons I-01/API-08 di bawah harus sama bentuknya dengan `services/ai-service/app/schemas.py`
(divalidasi terhadap `contracts/examples/internal/`, SCAFFOLD_REPORT §10 butir 5).
"""

import logging
from enum import StrEnum

import httpx
from pydantic import Field, ValidationError, ValidationInfo, field_validator

from app.core.config import get_settings
from app.core.schemas import ApiModel, ErrorCode, ErrorEnvelope
from app.modules.verifications.schemas import (
    ExtractionMethod,
    IndicatorDetail,
    RiskAnalysis,
    RiskCategory,
    RiskReason,
    RiskState,
    Severity,
)

logger = logging.getLogger("app.verifications.ai_client")
EXTRACTION_PATH = "/internal/v1/document-extractions"
ANALYSIS_PATH = "/internal/v1/risk-analyses"
# Kode error ai-service yang memiliki reason khusus (SA §5.3.3); kode atau status lain → AI_SERVICE_UNAVAILABLE.
AI_ERROR_REASONS = {
    ErrorCode.AI_TIMEOUT: RiskReason.AI_TIMEOUT,
    ErrorCode.AI_QUOTA_EXCEEDED: RiskReason.AI_QUOTA_EXCEEDED,
    ErrorCode.AI_OUTPUT_INVALID: RiskReason.AI_OUTPUT_INVALID,
}
# Pengganti nama key tak dikenal di log; nama key berasal dari respons ai-service sehingga tidak disalin.
UNKNOWN_FIELD = "<unknown_field>"


class ExtractionStatus(StrEnum):
    """Status ekstraksi I-01."""

    OK = "OK"
    NO_CONTENT = "NO_CONTENT"


class NoContentReason(StrEnum):
    """Alasan NO_CONTENT I-01 (SA §7.2)."""

    PDF_UNREADABLE = "PDF_UNREADABLE"
    NO_EXTRACTABLE_TEXT = "NO_EXTRACTABLE_TEXT"


class ExtractionResponse(ApiModel):
    """Respons I-01 (sama dengan ai-service `ExtractionResponse`)."""

    status: ExtractionStatus
    text: str | None
    method: ExtractionMethod | None
    pages_total: int | None = Field(ge=0)
    pages_processed: int | None = Field(ge=0)
    truncated: bool
    language: str | None
    reason_detail: NoContentReason | None = None

    # Status OK wajib membawa teks tidak kosong; selain itu respons melanggar kontrak I-01 (bentuk field tetap).
    @field_validator("text")
    @classmethod
    def _ok_requires_text(cls, value: str | None, info: ValidationInfo) -> str | None:
        if info.data.get("status") is ExtractionStatus.OK and not value:
            raise ValueError("status OK wajib memiliki teks tidak kosong")
        return value


class RiskAnalysisRequest(ApiModel):
    """Body API-08 (sama dengan ai-service `RiskAnalysisRequest`); `extractionMethod` opsional (D-20)."""

    document_content: str = Field(min_length=1)
    extraction_method: ExtractionMethod | None = None


class AnalysisIndicatorDetail(ApiModel):
    """Indikator API-08 (sama dengan ai-service `IndicatorDetail`; kode divalidasi taksonomi saat komposisi)."""

    code: str
    label: str
    severity: Severity
    evidence: list[str] = Field(min_length=1, max_length=3)


class AnalysisMeta(ApiModel):
    """Metadata API-08; tidak diteruskan ke API-07."""

    model: str
    prompt_version: str
    latency_ms: int = Field(ge=0)
    dropped_indicators: int = Field(ge=0)


class RiskAnalysisResponse(ApiModel):
    """Respons API-08 (sama dengan ai-service `RiskAnalysisResponse`)."""

    category: RiskCategory
    indicators: list[str]
    indicator_details: list[AnalysisIndicatorDetail]
    explanation: str
    recommendation: str
    meta: AnalysisMeta


class AiServiceError(Exception):
    """Kegagalan pemanggilan ai-service yang sudah dipetakan ke reason SA §5.3.3 (tanpa isi dokumen)."""

    # Menyimpan reason, path, status HTTP (None untuk kegagalan transport), dan lokasi field yang melanggar
    # skema backend (None bila bukan pelanggaran skema; kosong bila tanpa lokasi, mis. body bukan JSON) untuk log.
    def __init__(
        self, reason: RiskReason, path: str, status: int | None = None, invalid_fields: list[str] | None = None
    ):
        self.reason = reason
        self.path = path
        self.status = status
        self.invalid_fields = invalid_fields
        super().__init__(reason.value)


# Lokasi field yang gagal divalidasi (mis. `indicatorDetails.0.code`); nilai input tidak pernah diambil.
# Key tak dikenal (`extra_forbidden`) ditulis sebagai UNKNOWN_FIELD; error tanpa lokasi (body bukan JSON
# atau bukan objek) tidak menghasilkan entri.
def _field_paths(exc: ValidationError, prefix: tuple[str | int, ...] = ()) -> list[str]:
    paths = set()
    for error in exc.errors(include_input=False):
        loc = error["loc"]
        if error["type"] == "extra_forbidden":
            loc = (*loc[:-1], UNKNOWN_FIELD)
        if parts := (*prefix, *loc):
            paths.add(".".join(str(part) for part in parts))
    return sorted(paths)


class AiServiceClient:
    """Client HTTP ke ai-service; satu-satunya pemegang INTERNAL_API_TOKEN di backend selain health."""

    # Memakai AsyncClient yang sudah diarahkan ke AI_SERVICE_URL (transport dapat diganti di test).
    def __init__(self, http: httpx.AsyncClient):
        self.http = http

    # Memanggil POST /internal/v1/document-extractions dengan byte berkas yang sama dengan yang di-hash.
    async def extract(self, file_bytes: bytes, request_id: str) -> ExtractionResponse:
        response = await self._post(
            EXTRACTION_PATH,
            request_id,
            get_settings().ai_extraction_timeout_seconds,
            files={"file": ("document.pdf", file_bytes, "application/pdf")},
        )
        return _parse(response, ExtractionResponse, EXTRACTION_PATH)

    # Memanggil POST /internal/v1/risk-analyses (API-08) dengan teks dan metode hasil ekstraksi; metode None tidak
    # dikirim sehingga ai-service memakai default TEXT_LAYER (tanpa fuzzy).
    async def analyze(
        self, document_content: str, extraction_method: ExtractionMethod | None, request_id: str
    ) -> RiskAnalysisResponse:
        request = RiskAnalysisRequest(document_content=document_content, extraction_method=extraction_method)
        payload = request.model_dump(by_alias=True, mode="json", exclude_none=True)
        response = await self._post(ANALYSIS_PATH, request_id, get_settings().ai_analysis_timeout_seconds, json=payload)
        return _parse(response, RiskAnalysisResponse, ANALYSIS_PATH)

    # POST dengan X-Internal-Token, X-Request-ID, dan timeout per panggilan; kegagalan transport atau decoding
    # body (mis. gzip rusak) → AiServiceError.
    async def _post(self, path: str, request_id: str, timeout: float, **kwargs) -> httpx.Response:
        headers = {
            "X-Internal-Token": get_settings().internal_api_token.get_secret_value(),
            "X-Request-ID": request_id,
        }
        try:
            return await self.http.post(path, headers=headers, timeout=timeout, **kwargs)
        except httpx.TimeoutException as exc:
            raise AiServiceError(RiskReason.AI_TIMEOUT, path) from exc
        except httpx.RequestError as exc:
            raise AiServiceError(RiskReason.AI_SERVICE_UNAVAILABLE, path) from exc


# Memvalidasi respons 200 ke model (body bukan JSON juga pelanggaran skema); selain 200 dipetakan dari kode
# envelope error (SA §5.3.3).
def _parse[T: ApiModel](response: httpx.Response, model: type[T], path: str) -> T:
    if response.status_code == 200:
        try:
            return model.model_validate_json(response.content)
        except ValidationError as exc:
            raise AiServiceError(RiskReason.AI_SERVICE_UNAVAILABLE, path, 200, _field_paths(exc)) from exc
    try:
        code = ErrorEnvelope.model_validate_json(response.content).error.code
    except ValidationError:
        code = None
    reason = AI_ERROR_REASONS.get(code, RiskReason.AI_SERVICE_UNAVAILABLE)
    raise AiServiceError(reason, path, response.status_code)


# RiskAnalysis tanpa hasil (NOT_PERFORMED/UNAVAILABLE): category dan metadata null, sama dengan contoh API-07.
def _without_result(state: RiskState, reason: RiskReason) -> RiskAnalysis:
    return RiskAnalysis(
        state=state,
        reason=reason,
        category=None,
        indicators=[],
        indicator_details=[],
        explanation=None,
        recommendation=None,
        extraction_method=None,
        content_truncated=None,
        pages_analyzed=None,
        pages_total=None,
    )


# Menjalankan ekstraksi + analisis; NO_CONTENT → NOT_PERFORMED, kegagalan → UNAVAILABLE dengan reason (tanpa fallback).
# Hanya reason, path, status, dan lokasi field pelanggaran skema yang dicatat; teks dokumen dan nilai respons
# ai-service tidak pernah di-log.
async def run_risk_pipeline(
    file_bytes: bytes, request_id: str, transport: httpx.AsyncBaseTransport | None = None
) -> RiskAnalysis:
    try:
        async with httpx.AsyncClient(base_url=get_settings().ai_service_url, transport=transport) as http:
            client = AiServiceClient(http)
            extraction = await client.extract(file_bytes, request_id)
            # OK tanpa teks sudah ditolak validator ExtractionResponse sebagai pelanggaran kontrak.
            if extraction.status is ExtractionStatus.NO_CONTENT or extraction.text is None:
                return _without_result(RiskState.NOT_PERFORMED, RiskReason.DOCUMENT_CONTENT_UNAVAILABLE)
            analysis = await client.analyze(extraction.text, extraction.method, request_id)
        # Kode indikator di luar taksonomi backend berarti respons ai-service melanggar kontrak.
        details = []
        for index, item in enumerate(analysis.indicator_details):
            try:
                details.append(IndicatorDetail.model_validate(item.model_dump()))
            except ValidationError as exc:
                fields = _field_paths(exc, ("indicatorDetails", index))
                raise AiServiceError(RiskReason.AI_SERVICE_UNAVAILABLE, ANALYSIS_PATH, 200, fields) from exc
    except AiServiceError as exc:
        logger.warning(
            "ai.pipeline_failed",
            extra={
                "event": "ai.pipeline_failed",
                "errorCode": exc.reason.value,
                "path": exc.path,
                "status": exc.status,
                "riskState": RiskState.UNAVAILABLE.value,
                "reason": "schema_violation" if exc.invalid_fields is not None else None,
                "fields": exc.invalid_fields or None,
            },
        )
        return _without_result(RiskState.UNAVAILABLE, exc.reason)
    return RiskAnalysis(
        state=RiskState.COMPLETED,
        reason=None,
        category=analysis.category,
        indicators=analysis.indicators,
        indicator_details=details,
        explanation=analysis.explanation,
        recommendation=analysis.recommendation,
        extraction_method=extraction.method,
        content_truncated=extraction.truncated,
        pages_analyzed=extraction.pages_processed,
        pages_total=extraction.pages_total,
    )
