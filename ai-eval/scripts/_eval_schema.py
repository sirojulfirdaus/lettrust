# Owner: Sat (PIC 6), B/Pash (konsumen) | Status: COMPLETE | Ref: T6-05, T5-07, T4-07; SA §7.9
"""Kontrak raw.jsonl v1 untuk pipeline dan baseline; terpisah dari kontrak API publik."""

from typing import Literal

from pydantic import Field, model_validator

from app.analysis.scoring import score
from app.schemas import (
    ApiModel,
    ExtractionMethod,
    ExtractionResponse,
    ExtractionStatus,
    NoContentReason,
    RiskAnalysisResponse,
)


class ExtractionMetadata(ApiModel):
    """Metadata I-01 tanpa field text agar hasil evaluasi tidak menggandakan isi dokumen."""

    status: ExtractionStatus
    method: ExtractionMethod | None
    pages_total: int | None = Field(ge=0)
    pages_processed: int | None = Field(ge=0)
    truncated: bool
    language: str | None
    reason_detail: NoContentReason | None = None

    # Mengambil metadata persis dari hasil ekstraksi, tanpa menyertakan teks surat.
    @classmethod
    def from_response(cls, response: ExtractionResponse) -> "ExtractionMetadata":
        return cls.model_validate(response.model_dump(mode="json", by_alias=True, exclude={"text"}))


class EvaluationError(ApiModel):
    """Kegagalan terstruktur memakai kode aman, bukan exception, payload, atau pesan provider mentah."""

    stage: Literal["INPUT", "EXTRACTION", "ANALYSIS"]
    code: str = Field(pattern=r"^[A-Z][A-Z0-9_]*$")
    reason_detail: NoContentReason | None = None


class EvaluationRecord(ApiModel):
    """Satu hasil per pasangan (variant, id); result sukses berbentuk API-08 yang sama untuk kedua sistem."""

    schema_version: Literal[1] = 1
    id: str = Field(min_length=1)
    variant: Literal["pipeline", "baseline"]
    status: Literal["OK", "UNAVAILABLE"]
    result: RiskAnalysisResponse | None
    extraction: ExtractionMetadata | None
    error: EvaluationError | None
    latency_ms: int = Field(ge=0)

    # Menolak kategori palsu ketika gagal dan memastikan kategori sukses mengikuti skoring runtime.
    @model_validator(mode="after")
    def _check_result(self) -> "EvaluationRecord":
        if self.status == "OK":
            if self.result is None or self.error is not None or self.extraction is None:
                raise ValueError("Hasil OK memerlukan result, metadata ekstraksi, dan error null.")
            if self.extraction.status is not ExtractionStatus.OK:
                raise ValueError("Hasil OK memerlukan ekstraksi OK.")
            if self.result.category != score({item.code for item in self.result.indicator_details}):
                raise ValueError("Kategori evaluasi tidak cocok dengan indikator dan skoring runtime.")
        elif self.result is not None or self.error is None:
            raise ValueError("Hasil UNAVAILABLE memerlukan result null dan error terstruktur.")
        return self
