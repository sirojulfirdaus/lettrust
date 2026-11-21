# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: SA §10.1, §10.2
"""Basis skema Pydantic bersama (camelCase) dan envelope error kontrak API."""

from enum import StrEnum

import email_validator
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

# Seed dan data uji memakai domain fiktif `.test` (SA §9.5); email-validator menolaknya secara default.
if "test" in email_validator.SPECIAL_USE_DOMAIN_NAMES:
    email_validator.SPECIAL_USE_DOMAIN_NAMES.remove("test")


class ApiModel(BaseModel):
    """Basis seluruh skema API: field camelCase, field tak dikenal ditolak."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class ErrorCode(StrEnum):
    """Katalog kode error SA §10.3 (ditambah NOT_IMPLEMENTED sementara selama scaffolding)."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT_COMBINATION = "INVALID_INPUT_COMBINATION"
    AI_ONLY_REQUIRES_INCLUDE_RISK = "AI_ONLY_REQUIRES_INCLUDE_RISK"
    INVALID_REFERENCE_CODE_FORMAT = "INVALID_REFERENCE_CODE_FORMAT"
    EMPTY_FILE = "EMPTY_FILE"
    MULTIPLE_FILES = "MULTIPLE_FILES"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    FORBIDDEN_OPERATION = "FORBIDDEN_OPERATION"
    ISSUER_NOT_FOUND = "ISSUER_NOT_FOUND"
    PROOF_NOT_FOUND = "PROOF_NOT_FOUND"
    EMAIL_ALREADY_REGISTERED = "EMAIL_ALREADY_REGISTERED"
    ACCOUNT_ALREADY_AFFILIATED = "ACCOUNT_ALREADY_AFFILIATED"
    REGISTRATION_NUMBER_ALREADY_EXISTS = "REGISTRATION_NUMBER_ALREADY_EXISTS"
    ISSUER_DECISION_ALREADY_MADE = "ISSUER_DECISION_ALREADY_MADE"
    ISSUER_NOT_VERIFIED = "ISSUER_NOT_VERIFIED"
    HR_ALREADY_AUTHORIZED = "HR_ALREADY_AUTHORIZED"
    PROOF_ALREADY_REVOKED = "PROOF_ALREADY_REVOKED"
    IDEMPOTENCY_KEY_CONFLICT = "IDEMPOTENCY_KEY_CONFLICT"
    DUPLICATE_ACTIVE_DOCUMENT = "DUPLICATE_ACTIVE_DOCUMENT"
    HR_NOT_AFFILIATED = "HR_NOT_AFFILIATED"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    UNSUPPORTED_MEDIA_TYPE = "UNSUPPORTED_MEDIA_TYPE"
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    REGISTRY_UNAVAILABLE = "REGISTRY_UNAVAILABLE"
    REGISTRY_TRANSACTION_FAILED = "REGISTRY_TRANSACTION_FAILED"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    AI_PROVIDER_UNCONFIGURED = "AI_PROVIDER_UNCONFIGURED"
    AI_QUOTA_EXCEEDED = "AI_QUOTA_EXCEEDED"
    AI_PROVIDER_ERROR = "AI_PROVIDER_ERROR"
    AI_OUTPUT_INVALID = "AI_OUTPUT_INVALID"
    AI_TIMEOUT = "AI_TIMEOUT"
    NOT_FOUND = "NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"


class ErrorDetail(ApiModel):
    """Rincian error validasi per field (hanya untuk VALIDATION_ERROR)."""

    field: str
    issue: str


class ErrorBody(ApiModel):
    """Isi error: kode stabil, pesan aman untuk pengguna, dan rincian opsional."""

    code: ErrorCode
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)


class ErrorEnvelope(ApiModel):
    """Envelope error SA §10.2 yang dikembalikan seluruh endpoint saat gagal."""

    request_id: str
    error: ErrorBody
