# Owner: Zan (PIC 3) | Status: STUB | Ref: PRD FR-03.01–FR-03.10, FR-04.01–FR-04.07; SA §6.5, §6.6, §10.6
# TODO: Implementasikan penerbitan idempoten, daftar, status dari registry, pencabutan, dan pembacaan untuk verifikasi.
"""Logika bisnis SVC-02; satu-satunya modul yang memanggil fungsi tulis registry."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.modules.issuers.dependencies import AuthorizedHrContext
from app.modules.proofs.schemas import (
    IssueProofResponse,
    LifecycleStatus,
    ProofListResponse,
    ProofStatusResponse,
    RevokeProofRequest,
    RevokeProofResponse,
)
from app.modules.verifications.schemas import ProofCheck


@dataclass(frozen=True)
class ProofVerificationRead:
    """Hasil baca bukti untuk API-07: komponen proofCheck dan documentHash registry (untuk integritas)."""

    proof_check: ProofCheck
    registry_document_hash: str | None


# API-04: validasi berkas, SHA-256 byte asli, idempotensi, transaksi issueProof, lalu ACTIVE setelah receipt.
def issue_proof(
    db: Session, hr: AuthorizedHrContext, file_bytes: bytes, issuer_id: str | None, idempotency_key: str | None
) -> IssueProofResponse:
    raise NotImplementedError("proofs.issue_proof belum diimplementasikan")


# S-06: daftar bukti ACTIVE/REVOKED milik penerbit HR (status dari cermin off-chain).
def list_proofs(
    db: Session, hr: AuthorizedHrContext, status: LifecycleStatus | None, limit: int, offset: int
) -> ProofListResponse:
    raise NotImplementedError("proofs.list_proofs belum diimplementasikan")


# API-05: status dan hash dibaca dari registry; bukti milik penerbit lain menghasilkan 404.
def get_proof_status(db: Session, hr: AuthorizedHrContext, proof_id: str) -> ProofStatusResponse:
    raise NotImplementedError("proofs.get_proof_status belum diimplementasikan")


# API-06: pencabutan dengan idempotensi SA §6.6; REVOKED hanya setelah receipt sukses.
def revoke_proof(
    db: Session, hr: AuthorizedHrContext, proof_id: str, payload: RevokeProofRequest, idempotency_key: str | None
) -> RevokeProofResponse:
    raise NotImplementedError("proofs.revoke_proof belum diimplementasikan")


# Operasi baca internal API-07 (SA §5.3.1); tidak pernah raise: kegagalan registry menjadi lookup=UNAVAILABLE.
async def read_proof_for_verification(reference_code: str) -> ProofVerificationRead:
    raise NotImplementedError("proofs.read_proof_for_verification belum diimplementasikan")
