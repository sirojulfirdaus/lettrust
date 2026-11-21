# Owner: Zan (PIC 3) | Status: COMPLETE | Ref: SA §10.6 (API-04–API-06, S-06); PRD FR-03, FR-04
"""Skema kontrak endpoint SVC-02."""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import Field

from app.core.schemas import ApiModel

PROOF_ID_PATTERN = r"^0x[0-9a-f]{64}$"
DOCUMENT_HASH_PATTERN = r"^[0-9a-f]{64}$"
TX_HASH_PATTERN = r"^0x[0-9a-f]{64}$"
REFERENCE_CODE_PATTERN = r"^LTR-[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{4}$"
ISSUER_ID_PATTERN = r"^ISS-[0-9A-HJKMNP-TV-Z]{8}$"


class LifecycleStatus(StrEnum):
    """Status bukti pada registry."""

    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"


class RevocationReasonCode(StrEnum):
    """Alasan pencabutan yang diizinkan (disimpan off-chain)."""

    OFFER_WITHDRAWN = "OFFER_WITHDRAWN"
    ISSUED_IN_ERROR = "ISSUED_IN_ERROR"
    DOCUMENT_REPLACED = "DOCUMENT_REPLACED"
    OTHER = "OTHER"


class TransactionRef(ApiModel):
    """Referensi transaksi registry yang telah terkonfirmasi."""

    hash: str = Field(pattern=TX_HASH_PATTERN)
    block_number: int = Field(ge=0)


class IssueProofResponse(ApiModel):
    """API-04: bukti ACTIVE setelah receipt terkonfirmasi (issuedAt dan transaction aditif D3)."""

    proof_id: str = Field(pattern=PROOF_ID_PATTERN)
    reference_code: str = Field(pattern=REFERENCE_CODE_PATTERN)
    issuer_id: str = Field(pattern=ISSUER_ID_PATTERN)
    hash_algorithm: Literal["SHA-256"]
    document_hash: str = Field(pattern=DOCUMENT_HASH_PATTERN)
    lifecycle_status: LifecycleStatus
    issued_at: datetime
    transaction: TransactionRef


class ProofListItem(ApiModel):
    """Baris daftar bukti (S-06); status dari cermin off-chain."""

    proof_id: str = Field(pattern=PROOF_ID_PATTERN)
    reference_code: str = Field(pattern=REFERENCE_CODE_PATTERN)
    lifecycle_status: LifecycleStatus
    issued_at: datetime
    revoked_at: datetime | None


class ProofListResponse(ApiModel):
    """S-06: koleksi bukti milik penerbit HR."""

    items: list[ProofListItem]
    total: int = Field(ge=0)


class ProofStatusResponse(ApiModel):
    """API-05: hash, status, dan waktu dibaca dari registry; field lain dari off-chain."""

    proof_id: str = Field(pattern=PROOF_ID_PATTERN)
    issuer_id: str = Field(pattern=ISSUER_ID_PATTERN)
    document_hash: str = Field(pattern=DOCUMENT_HASH_PATTERN)
    lifecycle_status: LifecycleStatus
    reference_code: str = Field(pattern=REFERENCE_CODE_PATTERN)
    issued_at: datetime
    revoked_at: datetime | None
    revocation_reason_code: RevocationReasonCode | None
    issue_transaction: TransactionRef
    revoke_transaction: TransactionRef | None
    source: Literal["REGISTRY"]


class RevokeProofRequest(ApiModel):
    """API-06 revokeProof."""

    reason_code: RevocationReasonCode


class RevokeProofResponse(ApiModel):
    """API-06: bukti REVOKED setelah receipt pencabutan terkonfirmasi."""

    proof_id: str = Field(pattern=PROOF_ID_PATTERN)
    lifecycle_status: LifecycleStatus
    revoked_at: datetime
    transaction: TransactionRef
