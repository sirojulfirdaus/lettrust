# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: SA §10.7.2, §5.3; PRD §8.3, FR-06.01
"""Skema kontrak API-07 verifyOffer: tiga komponen terpisah tanpa vonis gabungan."""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import Field

from app.core.schemas import ApiModel


class VerificationMode(StrEnum):
    """Mode verifikasi: dengan kode atau AI saja."""

    REFERENCE_CHECK = "REFERENCE_CHECK"
    AI_ONLY = "AI_ONLY"


class ProofLookup(StrEnum):
    """Hasil pemeriksaan bukti."""

    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_REQUESTED = "NOT_REQUESTED"


class ProofReason(StrEnum):
    """Alasan status proofCheck."""

    NO_REFERENCE_CODE = "NO_REFERENCE_CODE"
    REGISTRY_UNAVAILABLE = "REGISTRY_UNAVAILABLE"


class ProofLifecycleStatus(StrEnum):
    """Status bukti yang dibaca dari registry."""

    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"


class IntegrityResult(StrEnum):
    """Hasil perbandingan hash berkas."""

    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    NOT_CHECKED = "NOT_CHECKED"


class IntegrityReason(StrEnum):
    """Alasan integritas tidak diperiksa."""

    NO_FILE = "NO_FILE"
    NO_REFERENCE_CODE = "NO_REFERENCE_CODE"
    PROOF_NOT_FOUND = "PROOF_NOT_FOUND"
    REGISTRY_UNAVAILABLE = "REGISTRY_UNAVAILABLE"


class RiskState(StrEnum):
    """Status analisis AI."""

    COMPLETED = "COMPLETED"
    NOT_REQUESTED = "NOT_REQUESTED"
    NOT_PERFORMED = "NOT_PERFORMED"
    UNAVAILABLE = "UNAVAILABLE"


class RiskReason(StrEnum):
    """Alasan analisis AI tidak selesai."""

    DOCUMENT_CONTENT_UNAVAILABLE = "DOCUMENT_CONTENT_UNAVAILABLE"
    AI_SERVICE_UNAVAILABLE = "AI_SERVICE_UNAVAILABLE"
    AI_TIMEOUT = "AI_TIMEOUT"
    AI_QUOTA_EXCEEDED = "AI_QUOTA_EXCEEDED"
    AI_OUTPUT_INVALID = "AI_OUTPUT_INVALID"


class RiskCategory(StrEnum):
    """Kategori risiko hasil skoring deterministik (PRD §8.5)."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class IndicatorCode(StrEnum):
    """Taksonomi tertutup indikator risiko (PRD §8.4)."""

    PAYMENT_REQUEST = "PAYMENT_REQUEST"
    SENSITIVE_DATA_REQUEST = "SENSITIVE_DATA_REQUEST"
    UNOFFICIAL_CONTACT = "UNOFFICIAL_CONTACT"
    URGENCY_PRESSURE = "URGENCY_PRESSURE"
    IDENTITY_INCONSISTENCY = "IDENTITY_INCONSISTENCY"
    UNREALISTIC_COMPENSATION = "UNREALISTIC_COMPENSATION"
    VAGUE_JOB_DETAILS = "VAGUE_JOB_DETAILS"


class Severity(StrEnum):
    """Tingkat indikator."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ExtractionMethod(StrEnum):
    """Metode pembacaan isi dokumen."""

    TEXT_LAYER = "TEXT_LAYER"
    OCR = "OCR"
    MIXED = "MIXED"


class VerifiedIssuer(ApiModel):
    """Identitas penerbit bukti (hanya id dan nama perusahaan, DLT-07)."""

    issuer_id: str = Field(pattern=r"^ISS-[0-9A-HJKMNP-TV-Z]{8}$")
    company_name: str


class ProofCheck(ApiModel):
    """Komponen pemeriksaan bukti (SA §5.3.1)."""

    lookup: ProofLookup
    reason: ProofReason | None
    issuer: VerifiedIssuer | None
    issuer_verified: bool | None
    lifecycle_status: ProofLifecycleStatus | None
    issued_at: datetime | None
    revoked_at: datetime | None


class IntegrityCheck(ApiModel):
    """Komponen pemeriksaan integritas berkas (SA §5.3.2)."""

    result: IntegrityResult
    reason: IntegrityReason | None
    hash_algorithm: Literal["SHA-256"] | None


class IndicatorDetail(ApiModel):
    """Indikator tervalidasi beserta kutipan bukti dari dokumen."""

    code: IndicatorCode
    label: str
    severity: Severity
    evidence: list[str] = Field(min_length=1, max_length=3)


class RiskAnalysis(ApiModel):
    """Komponen analisis risiko AI (SA §5.3.3); category null bila state bukan COMPLETED."""

    state: RiskState
    reason: RiskReason | None
    category: RiskCategory | None
    indicators: list[str]
    indicator_details: list[IndicatorDetail]
    explanation: str | None
    recommendation: str | None
    extraction_method: ExtractionMethod | None
    content_truncated: bool | None
    pages_analyzed: int | None = Field(ge=0)
    pages_total: int | None = Field(ge=0)


class VerificationResponse(ApiModel):
    """API-07: tiga komponen hasil terpisah; tidak ada field vonis gabungan."""

    verification_id: str = Field(pattern=r"^VER-[0-9A-HJKMNP-TV-Z]{10}$")
    mode: VerificationMode
    proof_check: ProofCheck
    integrity_check: IntegrityCheck
    risk_analysis: RiskAnalysis
