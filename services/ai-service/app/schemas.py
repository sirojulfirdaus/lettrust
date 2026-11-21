# Owner: B (PIC 5) | Status: COMPLETE | Ref: SA §7.2, §7.7, §10.8 (I-01, API-08, I-02)
"""Skema kontrak endpoint internal ai-service (camelCase)."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    """Basis skema: field camelCase, field tak dikenal ditolak."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class ExtractionStatus(StrEnum):
    """Status ekstraksi: OK atau tidak ada konten yang dapat dianalisis."""

    OK = "OK"
    NO_CONTENT = "NO_CONTENT"


class ExtractionMethod(StrEnum):
    """Metode pembacaan isi dokumen."""

    TEXT_LAYER = "TEXT_LAYER"
    OCR = "OCR"
    MIXED = "MIXED"


class NoContentReason(StrEnum):
    """Alasan NO_CONTENT (SA §7.2)."""

    PDF_UNREADABLE = "PDF_UNREADABLE"
    NO_EXTRACTABLE_TEXT = "NO_EXTRACTABLE_TEXT"


class ExtractionResponse(ApiModel):
    """I-01: hasil ekstraksi/OCR; NO_CONTENT disertai reasonDetail dan text null."""

    status: ExtractionStatus
    text: str | None
    method: ExtractionMethod | None
    pages_total: int | None = Field(ge=0)
    pages_processed: int | None = Field(ge=0)
    truncated: bool
    language: str | None
    reason_detail: NoContentReason | None = None


class RiskAnalysisRequest(ApiModel):
    """API-08 (sesuai D2): teks dokumen 1–AI_MAX_CHARS karakter; batas atas diperiksa handler dari konfigurasi."""

    document_content: str = Field(min_length=1)


class Severity(StrEnum):
    """Tingkat indikator."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RiskCategory(StrEnum):
    """Kategori risiko hasil skoring deterministik."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class IndicatorDetail(ApiModel):
    """Indikator tervalidasi; label dari taksonomi, kutipan bukti ditemukan di dokumen."""

    code: str
    label: str
    severity: Severity
    evidence: list[str] = Field(min_length=1, max_length=3)


class AnalysisMeta(ApiModel):
    """Metadata untuk log backend dan evaluasi; tidak diteruskan ke API-07."""

    model: str
    prompt_version: str
    latency_ms: int = Field(ge=0)
    dropped_indicators: int = Field(ge=0)


class RiskAnalysisResponse(ApiModel):
    """API-08: field D2 (category, indicators, explanation, recommendation) + indicatorDetails dan meta aditif."""

    category: RiskCategory
    indicators: list[str]
    indicator_details: list[IndicatorDetail]
    explanation: str
    recommendation: str
    meta: AnalysisMeta


class TesseractStatus(ApiModel):
    """Ketersediaan Tesseract dan paket bahasa yang wajib (ind, eng)."""

    available: bool
    version: str | None
    languages: list[str]
    missing_languages: list[str]


class AiHealthResponse(ApiModel):
    """I-02: status OCR dan konfigurasi LLM; `degraded` bila OCR tidak siap atau LLM unconfigured."""

    status: Literal["ok", "degraded"]
    tesseract: TesseractStatus
    llm: Literal["configured", "unconfigured"]
    model: str
