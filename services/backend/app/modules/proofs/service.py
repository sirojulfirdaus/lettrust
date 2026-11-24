# Owner: Zan (PIC 3) | Status: STUB | Ref: PRD FR-03.01–FR-03.10, FR-04.01–FR-04.07; SA §6.5, §6.6, §10.6
# TODO: Implementasikan daftar, status dari registry, pencabutan, dan pembacaan untuk verifikasi.
"""Logika bisnis SVC-02; satu-satunya modul yang memanggil fungsi tulis registry."""

from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.ids import new_proof_id, new_reference_code
from app.core.schemas import ErrorCode, ErrorDetail
from app.modules.issuers.dependencies import AuthorizedHrContext
from app.modules.proofs.models import Proof
from app.modules.proofs.schemas import (
    IssueProofResponse,
    LifecycleStatus,
    ProofListResponse,
    ProofStatusResponse,
    RevokeProofRequest,
    RevokeProofResponse,
    TransactionRef,
)
from app.modules.registry import adapter as registry_adapter
from app.modules.verifications.schemas import ProofCheck

# Backend memakai satu worker (AD-22). Kunci ini menjaga satu percobaan per penerbit dan kunci idempotensi.
_ISSUE_LOCKS = tuple(Lock() for _ in range(64))


@dataclass(frozen=True)
class ProofVerificationRead:
    """Hasil baca bukti untuk API-07: komponen proofCheck dan documentHash registry (untuk integritas)."""

    proof_check: ProofCheck
    registry_document_hash: str | None


def issue_proof(
    db: Session, hr: AuthorizedHrContext, document_hash: str, idempotency_key: str | None
) -> IssueProofResponse:
    """Menerbitkan bukti idempoten dari hash PDF tervalidasi dengan kunci eksplisit yang tidak kosong."""
    if idempotency_key is not None and not idempotency_key.strip():
        raise AppError(
            ErrorCode.VALIDATION_ERROR,
            details=[ErrorDetail(field="Idempotency-Key", issue="string_too_short")],
        )
    key = uuid4().hex if idempotency_key is None else idempotency_key
    lock = _ISSUE_LOCKS[hash((hr.issuer_id, key)) % len(_ISSUE_LOCKS)]
    # Lepas koneksi dari pembacaan otorisasi sebelum menunggu kunci penerbitan.
    db.commit()
    with lock:
        proof = db.scalar(select(Proof).where(Proof.issuer_id == hr.issuer_id, Proof.idempotency_key == key))
        retry = proof is not None
        if proof is None:
            proof = _reserve_proof(db, hr, document_hash, key)
        elif proof.document_hash != document_hash:
            raise AppError(ErrorCode.IDEMPOTENCY_KEY_CONFLICT)
        elif proof.status in ("ACTIVE", "REVOKED"):
            return _issue_response(proof)

        # Lepas transaksi SQLite sebelum RPC; baris PENDING sudah tersimpan untuk pemulihan.
        db.commit()
        tx = _confirm_issue(db, proof, hr.issuer_ref, retry=retry)
        proof.status = "ACTIVE"
        proof.issue_tx_hash = tx.tx_hash
        proof.issue_block = tx.block_number
        proof.issued_at = datetime.fromtimestamp(tx.block_timestamp, UTC)
        proof.failure_code = None
        proof.updated_at = datetime.now(UTC)
        db.commit()
        return _issue_response(proof)


def _reserve_proof(db: Session, hr: AuthorizedHrContext, document_hash: str, key: str) -> Proof:
    """Membuat pemetaan PENDING dan mencoba ulang bila identifier acak bertabrakan."""
    now = datetime.now(UTC)
    for _ in range(3):
        proof = db.scalar(
            insert(Proof)
            .values(
                proof_id=new_proof_id(),
                reference_code=new_reference_code(),
                issuer_id=hr.issuer_id,
                document_hash=document_hash,
                status="PENDING",
                idempotency_key=key,
                issued_by=hr.user.id,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_nothing()
            .returning(Proof)
        )
        if proof is not None:
            return proof
    raise RuntimeError("Tidak dapat menyimpan identifier bukti yang unik")


def _confirm_issue(db: Session, proof: Proof, issuer_ref: str, *, retry: bool) -> registry_adapter.TxResult:
    """Memulihkan receipt yang sudah ada atau mengirim transaksi untuk proofId yang dicadangkan."""
    # Bergantung pada T6-02; diuji dengan MockRegistryAdapter.
    registry = registry_adapter.get_registry_adapter()
    if retry:
        tx = _find_confirmed_issue(registry, proof, issuer_ref)
        if tx is not None:
            return tx

    if proof.status == "FAILED":
        proof.status = "PENDING"
        proof.failure_code = None
        proof.updated_at = datetime.now(UTC)
        db.commit()

    try:
        return registry.issue_proof(proof.proof_id, proof.document_hash, issuer_ref)
    except registry_adapter.RegistryTransactionPending:
        raise AppError(ErrorCode.REGISTRY_TRANSACTION_FAILED) from None
    except (registry_adapter.RegistryUnavailable, registry_adapter.RegistryTransactionFailed) as exc:
        if isinstance(exc, registry_adapter.RegistryUnavailable):
            error_code = ErrorCode.REGISTRY_UNAVAILABLE
        else:
            error_code = ErrorCode.REGISTRY_TRANSACTION_FAILED
            if retry and exc.revert_name == "ProofAlreadyExists":
                # Transaksi sebelumnya dapat terkonfirmasi di sela lookup dan pengiriman ulang.
                tx = _find_confirmed_issue(registry, proof, issuer_ref)
                if tx is not None:
                    return tx
                raise AppError(error_code) from None
        proof.status = "FAILED"
        proof.failure_code = error_code
        proof.updated_at = datetime.now(UTC)
        db.commit()
        raise AppError(error_code) from None


def _find_confirmed_issue(
    registry: registry_adapter.RegistryAdapter, proof: Proof, issuer_ref: str
) -> registry_adapter.TxResult | None:
    """Mencari receipt bukti yang cocok; None hanya jika proofId belum ada di registry."""
    try:
        record = registry.get_proof(proof.proof_id)
        if not record.exists:
            return None
        if (
            record.status != registry_adapter.OnChainStatus.ACTIVE
            or record.document_hash != proof.document_hash
            or record.issuer_ref != issuer_ref
        ):
            raise AppError(ErrorCode.REGISTRY_TRANSACTION_FAILED)
        tx = registry.find_issue_tx(proof.proof_id)
        if tx is None:
            raise AppError(ErrorCode.REGISTRY_TRANSACTION_FAILED)
        return tx
    except registry_adapter.RegistryUnavailable:
        raise AppError(ErrorCode.REGISTRY_UNAVAILABLE) from None


def _issue_response(proof: Proof) -> IssueProofResponse:
    """Menyusun hasil penerbitan awal, termasuk saat bukti kemudian dicabut."""
    if proof.issued_at is None or proof.issue_tx_hash is None or proof.issue_block is None:
        raise RuntimeError("Metadata transaksi penerbitan tidak lengkap")
    return IssueProofResponse(
        proof_id=proof.proof_id,
        reference_code=proof.reference_code,
        issuer_id=proof.issuer_id,
        hash_algorithm="SHA-256",
        document_hash=proof.document_hash,
        lifecycle_status=LifecycleStatus.ACTIVE,
        issued_at=proof.issued_at.replace(tzinfo=UTC),
        transaction=TransactionRef(hash=proof.issue_tx_hash, block_number=proof.issue_block),
    )


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
