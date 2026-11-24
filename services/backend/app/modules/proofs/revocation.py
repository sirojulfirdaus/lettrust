# Owner: Sat (PIC 6) | Status: COMPLETE | Ref: SA §6.6, §10.6; FR-04.01–FR-04.05; T6-03
"""Pencabutan bukti dengan metadata tertunda dan rekonsiliasi receipt registry."""

import re
from datetime import UTC, datetime
from threading import Lock
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.schemas import ErrorCode, ErrorDetail
from app.modules.issuers.dependencies import AuthorizedHrContext
from app.modules.proofs.models import Proof
from app.modules.proofs.schemas import (
    PROOF_ID_PATTERN,
    LifecycleStatus,
    RevokeProofRequest,
    RevokeProofResponse,
    TransactionRef,
)
from app.modules.registry import adapter as registry_adapter

_REVOKE_LOCKS = tuple(Lock() for _ in range(64))


# Mencabut hanya bukti penerbit HR; percobaan tidak pasti dipertahankan untuk rekonsiliasi berikutnya.
def revoke_proof(
    db: Session, hr: AuthorizedHrContext, proof_id: str, payload: RevokeProofRequest, idempotency_key: str | None
) -> RevokeProofResponse:
    if idempotency_key is not None and not idempotency_key.strip():
        raise AppError(
            ErrorCode.VALIDATION_ERROR, details=[ErrorDetail(field="Idempotency-Key", issue="string_too_short")]
        )
    if re.fullmatch(PROOF_ID_PATTERN, proof_id) is None:
        raise AppError(ErrorCode.PROOF_NOT_FOUND)
    key = uuid4().hex if idempotency_key is None else idempotency_key
    db.commit()
    with _REVOKE_LOCKS[hash(proof_id) % len(_REVOKE_LOCKS)]:
        proof = db.scalar(select(Proof).where(Proof.proof_id == proof_id, Proof.issuer_id == hr.issuer_id))
        if proof is None or proof.status not in ("ACTIVE", "REVOKED"):
            raise AppError(ErrorCode.PROOF_NOT_FOUND)
        db.commit()
        registry = registry_adapter.get_registry_adapter()
        record = _read_record(registry, proof, hr.issuer_ref)
        if record.status == registry_adapter.OnChainStatus.REVOKED:
            return _recover(db, registry, proof, record, payload, idempotency_key)
        if record.status != registry_adapter.OnChainStatus.ACTIVE or proof.status == "REVOKED":
            raise AppError(ErrorCode.REGISTRY_TRANSACTION_FAILED)
        retry_pending = proof.revoke_idempotency_key is not None
        if retry_pending:
            if proof.revoke_idempotency_key != key:
                # Percobaan yang belum pasti tidak boleh ditimpa oleh kunci atau pelaku baru.
                raise AppError(ErrorCode.REGISTRY_TRANSACTION_FAILED)
            if proof.revoke_reason_code != payload.reason_code:
                raise AppError(ErrorCode.IDEMPOTENCY_KEY_CONFLICT)
        else:
            proof.revoke_idempotency_key = key
            proof.revoke_reason_code = payload.reason_code
            proof.revoked_by = hr.user.id
            proof.updated_at = datetime.now(UTC)
            db.commit()
        try:
            tx = registry.revoke_proof(proof_id, hr.issuer_ref)
        except registry_adapter.RegistryTransactionPending:
            raise AppError(ErrorCode.REGISTRY_TRANSACTION_FAILED) from None
        except registry_adapter.ProofNotActiveOnChain:
            # Receipt sebelumnya dapat terkonfirmasi di antara pembacaan dan pengiriman ulang.
            record = _read_record(registry, proof, hr.issuer_ref)
            if record.status == registry_adapter.OnChainStatus.REVOKED:
                return _recover(db, registry, proof, record, payload, idempotency_key)
            raise AppError(ErrorCode.REGISTRY_TRANSACTION_FAILED) from None
        except registry_adapter.IssuerMismatchOnChain:
            if not retry_pending:
                _clear_pending(db, proof)
            raise AppError(ErrorCode.PROOF_NOT_FOUND) from None
        except (registry_adapter.RegistryUnavailable, registry_adapter.RegistryTransactionFailed) as exc:
            # Gagal pasti pada retry tidak membuktikan transaksi percobaan sebelumnya juga gagal.
            if not retry_pending:
                _clear_pending(db, proof)
            code = (
                ErrorCode.REGISTRY_UNAVAILABLE
                if isinstance(exc, registry_adapter.RegistryUnavailable)
                else ErrorCode.REGISTRY_TRANSACTION_FAILED
            )
            raise AppError(code) from None
        return _finalize(db, proof, tx)


# Membaca registry sebagai sumber status dan menolak pemetaan penerbit atau hash yang tidak konsisten.
def _read_record(
    registry: registry_adapter.RegistryAdapter, proof: Proof, issuer_ref: str
) -> registry_adapter.ProofRecord:
    try:
        record = registry.get_proof(proof.proof_id)
    except registry_adapter.RegistryUnavailable:
        raise AppError(ErrorCode.REGISTRY_UNAVAILABLE) from None
    if not record.exists or record.issuer_ref != issuer_ref:
        raise AppError(ErrorCode.PROOF_NOT_FOUND)
    if record.document_hash != proof.document_hash:
        raise AppError(ErrorCode.REGISTRY_TRANSACTION_FAILED)
    return record


# Mengembalikan receipt pencabutan semula hanya untuk kunci dan alasan yang sama serta event terkonfirmasi.
def _recover(
    db: Session,
    registry: registry_adapter.RegistryAdapter,
    proof: Proof,
    record: registry_adapter.ProofRecord,
    payload: RevokeProofRequest,
    key: str | None,
) -> RevokeProofResponse:
    if key is None or key != proof.revoke_idempotency_key:
        raise AppError(ErrorCode.PROOF_ALREADY_REVOKED)
    if payload.reason_code != proof.revoke_reason_code:
        raise AppError(ErrorCode.IDEMPOTENCY_KEY_CONFLICT)
    try:
        tx = registry.find_revoke_tx(proof.proof_id)
    except registry_adapter.RegistryUnavailable:
        raise AppError(ErrorCode.REGISTRY_UNAVAILABLE) from None
    if tx is None or tx.block_timestamp != record.revoked_at:
        raise AppError(ErrorCode.REGISTRY_TRANSACTION_FAILED)
    return _finalize(db, proof, tx)


# Memfinalisasi mirror hanya setelah receipt sukses, dengan waktu dari registry dan audit percobaan semula.
def _finalize(db: Session, proof: Proof, tx: registry_adapter.TxResult) -> RevokeProofResponse:
    proof.status = "REVOKED"
    proof.revoked_at = datetime.fromtimestamp(tx.block_timestamp, UTC)
    proof.revoke_tx_hash = tx.tx_hash
    proof.revoke_block = tx.block_number
    proof.updated_at = datetime.now(UTC)
    db.commit()
    return RevokeProofResponse(
        proof_id=proof.proof_id,
        lifecycle_status=LifecycleStatus.REVOKED,
        revoked_at=proof.revoked_at.replace(tzinfo=UTC),
        transaction=TransactionRef(hash=tx.tx_hash, block_number=tx.block_number),
    )


# Mengosongkan metadata tertunda hanya pada kegagalan pasti; status ACTIVE dan data penerbitan tetap utuh.
def _clear_pending(db: Session, proof: Proof) -> None:
    proof.revoke_idempotency_key = None
    proof.revoke_reason_code = None
    proof.revoked_by = None
    proof.updated_at = datetime.now(UTC)
    db.commit()
