# Owner: Zan (PIC 3) | Status: COMPLETE | Ref: PRD FR-03.01–FR-03.10, FR-04.01–FR-04.07; SA §6.5, §6.6, §10.6
"""Logika penerbitan dan pembacaan bukti untuk SVC-02."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock
from uuid import uuid4

from sqlalchemy import func, select, true, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.db import get_session_factory
from app.core.errors import AppError
from app.core.ids import new_proof_id, new_reference_code
from app.core.schemas import ErrorCode, ErrorDetail
from app.modules.auth.schemas import IssuerStatus
from app.modules.issuers.dependencies import AuthorizedHrContext
from app.modules.issuers.models import Issuer
from app.modules.proofs.models import Proof
from app.modules.proofs.schemas import (
    IssueProofResponse,
    LifecycleStatus,
    ProofListItem,
    ProofListResponse,
    ProofStatusResponse,
    RevocationReasonCode,
    TransactionRef,
)
from app.modules.registry import adapter as registry_adapter
from app.modules.verifications.schemas import ProofCheck, ProofLifecycleStatus, ProofLookup, ProofReason, VerifiedIssuer

logger = logging.getLogger(__name__)
_VISIBLE_STATUSES = (LifecycleStatus.ACTIVE, LifecycleStatus.REVOKED)
_SQLITE_MAX_OFFSET = 2**63 - 1

# Pesan netral untuk kegagalan registry pada operasi baca (API-05, PRD §9.8); pesan katalog bermakna penulisan gagal.
REGISTRY_READ_UNAVAILABLE_MESSAGE = "Data bukti dari registry belum dapat dimuat. Coba lagi beberapa saat lagi."

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
            _reject_active_duplicate(db, hr, document_hash)
            proof = _reserve_proof(db, hr, document_hash, key)
        elif proof.document_hash != document_hash:
            raise AppError(ErrorCode.IDEMPOTENCY_KEY_CONFLICT)
        elif proof.status in ("ACTIVE", "REVOKED"):
            return _issue_response(proof)

        # Lepas transaksi SQLite sebelum RPC; baris PENDING sudah tersimpan untuk pemulihan.
        db.commit()
        tx = _confirm_issue(db, hr, proof, retry=retry)
        proof.status = "ACTIVE"
        proof.issue_tx_hash = tx.tx_hash
        proof.issue_block = tx.block_number
        proof.issued_at = datetime.fromtimestamp(tx.block_timestamp, UTC)
        proof.failure_code = None
        proof.updated_at = datetime.now(UTC)
        db.commit()
        return _issue_response(proof)


def _reject_active_duplicate(
    db: Session, hr: AuthorizedHrContext, document_hash: str, exclude_proof_id: str | None = None
) -> None:
    """FR-03.06 / SA §6.5 butir 5: tolak hash yang sama dengan bukti ACTIVE penerbit yang sama sebelum transaksi.

    Berlaku untuk kunci idempotensi baru (sebelum INSERT) dan retry kunci lama yang akan mengirim transaksi baru
    (baris retry itu dikecualikan lewat `exclude_proof_id`). Bukti REVOKED dan penerbit lain tidak menghalangi
    (AC-03). Cermin ACTIVE tanpa pencabutan tertunda sudah final sehingga ditolak tanpa RPC. Baris yang belum final
    (penerbitan PENDING setelah receipt timeout, ACTIVE dengan pencabutan tertunda, atau FAILED) dibaca dari registry
    tanpa transaksi. Penerbitan PENDING yang belum ada di registry ditandai FAILED hanya bila transaksinya pasti gagal
    atau hilang dari antrean node (D-24); bila status belum dapat dipastikan, penerbitan dihentikan sebelum transaksi
    baru dikirim.
    """
    rows = db.execute(
        select(Proof.proof_id, Proof.status, Proof.revoke_idempotency_key, Proof.issue_tx_hash).where(
            Proof.issuer_id == hr.issuer_id,
            Proof.document_hash == document_hash,
            Proof.status.in_(("ACTIVE", "PENDING", "FAILED")),
            Proof.proof_id != exclude_proof_id if exclude_proof_id else true(),
        )
    ).all()
    if any(row.status == "ACTIVE" and row.revoke_idempotency_key is None for row in rows):
        raise AppError(ErrorCode.DUPLICATE_ACTIVE_DOCUMENT)
    for row in rows:
        try:
            record = _read_registry_proof(row.proof_id, hr.issuer_ref)
        except registry_adapter.RegistryUnavailable:
            raise AppError(ErrorCode.REGISTRY_UNAVAILABLE) from None
        if record.exists and record.status == registry_adapter.OnChainStatus.ACTIVE:
            raise AppError(ErrorCode.DUPLICATE_ACTIVE_DOCUMENT)
        if not record.exists and row.status == "PENDING":
            _fail_dropped_issue(db, row.proof_id, row.issue_tx_hash, hr.issuer_ref)


def _fail_dropped_issue(db: Session, proof_id: str, tx_hash: str | None, issuer_ref: str) -> None:
    """Menandai penerbitan PENDING FAILED bila transaksinya pasti gagal/hilang; selain itu 503 tanpa transaksi.

    Registry dibaca ulang setelah pemeriksaan antrean: retry kunci lama dapat menambang bukti yang sama selagi
    pemeriksaan menunggu SIGNER_LOCK, sehingga hasil `get_proof` sebelumnya sudah basi (FR-03.06).
    """
    try:
        dropped = registry_adapter.get_registry_adapter().is_issue_failed_or_dropped(tx_hash, proof_id)
    except registry_adapter.RegistryUnavailable:
        raise AppError(ErrorCode.REGISTRY_UNAVAILABLE) from None
    if not dropped:
        # Transaksi penerbitan sebelumnya masih dapat terkonfirmasi; ulangi dengan Idempotency-Key semula.
        raise AppError(ErrorCode.REGISTRY_TRANSACTION_FAILED)
    try:
        record = _read_registry_proof(proof_id, issuer_ref)
    except registry_adapter.RegistryUnavailable:
        raise AppError(ErrorCode.REGISTRY_UNAVAILABLE) from None
    if record.exists:
        if record.status == registry_adapter.OnChainStatus.ACTIVE:
            raise AppError(ErrorCode.DUPLICATE_ACTIVE_DOCUMENT)
        # Sudah tercatat lalu dicabut: bukan duplikat aktif dan bukan kegagalan; mirror diselesaikan retry kunci lama.
        return
    db.execute(
        update(Proof)
        .where(Proof.proof_id == proof_id, Proof.status == "PENDING")
        .values(status="FAILED", failure_code=ErrorCode.REGISTRY_TRANSACTION_FAILED, updated_at=datetime.now(UTC))
    )
    db.commit()


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


def _confirm_issue(db: Session, hr: AuthorizedHrContext, proof: Proof, *, retry: bool) -> registry_adapter.TxResult:
    """Memulihkan receipt yang sudah ada atau mengirim transaksi untuk proofId yang dicadangkan."""
    # Bergantung pada T6-02; diuji dengan MockRegistryAdapter.
    issuer_ref = hr.issuer_ref
    registry = registry_adapter.get_registry_adapter()
    if retry:
        tx = _find_confirmed_issue(registry, proof, issuer_ref)
        if tx is not None:
            return tx
        # Kunci lama akan mengirim transaksi baru; bukti lain dengan hash sama bisa sudah ACTIVE (FR-03.06).
        _reject_active_duplicate(db, hr, proof.document_hash, exclude_proof_id=proof.proof_id)

    # Percobaan PENDING sebelumnya belum pasti gagal: transaksinya bisa masih di antrean node.
    prior_pending = retry and proof.status == "PENDING"
    if proof.status == "FAILED":
        proof.status = "PENDING"
        proof.failure_code = None
        proof.updated_at = datetime.now(UTC)
        db.commit()

    try:
        return registry.issue_proof(proof.proof_id, proof.document_hash, issuer_ref)
    except registry_adapter.RegistryTransactionPending as exc:
        if exc.tx_hash is not None:
            # Hash percobaan yang belum terkonfirmasi (baris tetap PENDING dan tidak terlihat) untuk deteksi D-24;
            # ditimpa hash receipt saat penerbitan terkonfirmasi.
            proof.issue_tx_hash = exc.tx_hash
            proof.updated_at = datetime.now(UTC)
            db.commit()
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
        if prior_pending:
            # Gagal sebelum broadcast pada retry tidak membuktikan transaksi percobaan sebelumnya gagal (pola
            # retry_pending pada pencabutan); baris tetap PENDING agar kunci baru tidak menerbitkan duplikat.
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


def list_proofs(
    db: Session, hr: AuthorizedHrContext, status: LifecycleStatus | None, limit: int, offset: int
) -> ProofListResponse:
    """Membaca halaman dan total bukti milik penerbit HR dari satu snapshot mirror."""
    visible_statuses = (status,) if status is not None else _VISIBLE_STATUSES
    filters = (Proof.issuer_id == hr.issuer_id, Proof.status.in_(visible_statuses))
    total = select(func.count().label("total")).select_from(Proof).where(*filters).subquery()
    page = (
        select(Proof.proof_id, Proof.reference_code, Proof.status, Proof.issued_at, Proof.revoked_at)
        .where(*filters)
        .order_by(Proof.issued_at.desc(), Proof.proof_id)
        .limit(limit)
        .offset(min(offset, _SQLITE_MAX_OFFSET))
        .subquery()
    )
    rows = db.execute(
        select(page, total.c.total)
        .select_from(total.outerjoin(page, true()))
        .order_by(page.c.issued_at.desc(), page.c.proof_id)
    ).all()
    items = [
        ProofListItem(
            proof_id=row.proof_id,
            reference_code=row.reference_code,
            lifecycle_status=LifecycleStatus(row.status),
            issued_at=row.issued_at.replace(tzinfo=UTC),
            revoked_at=row.revoked_at.replace(tzinfo=UTC) if row.revoked_at is not None else None,
        )
        for row in rows
        if row.proof_id is not None
    ]
    return ProofListResponse(items=items, total=rows[0].total)


def get_proof_status(db: Session, hr: AuthorizedHrContext, proof_id: str) -> ProofStatusResponse:
    """Memeriksa kepemilikan sebelum membaca lifecycle dan hash dari registry."""
    proof = db.scalar(
        select(Proof).where(
            Proof.proof_id == proof_id, Proof.issuer_id == hr.issuer_id, Proof.status.in_(_VISIBLE_STATUSES)
        )
    )
    if proof is None:
        raise AppError(ErrorCode.PROOF_NOT_FOUND)

    # Menyimpan snapshot metadata dan melepaskan koneksi SQLite sebelum RPC.
    db.expunge(proof)
    db.rollback()
    try:
        record = _read_registry_proof(proof_id, hr.issuer_ref)
    except registry_adapter.RegistryUnavailable:
        raise AppError(ErrorCode.REGISTRY_UNAVAILABLE, REGISTRY_READ_UNAVAILABLE_MESSAGE) from None
    if not record.exists:
        raise AppError(ErrorCode.PROOF_NOT_FOUND)
    if proof.issue_tx_hash is None or proof.issue_block is None:
        raise RuntimeError("Metadata transaksi penerbitan tidak lengkap")

    revoked = record.status == registry_adapter.OnChainStatus.REVOKED
    revoke_hash, revoke_block, revoke_reason = proof.revoke_tx_hash, proof.revoke_block, proof.revoke_reason_code
    if revoked and (revoke_hash is None or revoke_block is None or revoke_reason is None):
        # Pencabutan dapat dikomit ke mirror saat RPC berjalan.
        receipt = db.execute(
            select(Proof.revoke_tx_hash, Proof.revoke_block, Proof.revoke_reason_code).where(
                Proof.proof_id == proof_id, Proof.issuer_id == hr.issuer_id
            )
        ).one_or_none()
        if receipt is None:
            raise AppError(ErrorCode.PROOF_NOT_FOUND)
        revoke_hash, revoke_block, revoke_reason = receipt

    revoke_transaction = None
    if revoked and revoke_hash is not None and revoke_block is not None:
        revoke_transaction = TransactionRef(hash=revoke_hash, block_number=revoke_block)
    return ProofStatusResponse(
        proof_id=proof.proof_id,
        issuer_id=proof.issuer_id,
        document_hash=record.document_hash,
        lifecycle_status=LifecycleStatus(record.status.name),
        reference_code=proof.reference_code,
        issued_at=datetime.fromtimestamp(record.issued_at, UTC),
        revoked_at=datetime.fromtimestamp(record.revoked_at, UTC) if revoked else None,
        revocation_reason_code=RevocationReasonCode(revoke_reason) if revoked and revoke_reason is not None else None,
        issue_transaction=TransactionRef(hash=proof.issue_tx_hash, block_number=proof.issue_block),
        revoke_transaction=revoke_transaction,
        source="REGISTRY",
    )


async def read_proof_for_verification(reference_code: str) -> ProofVerificationRead:
    """Membaca kode kanonis API-07 di thread agar akses SQLite dan Web3 tidak memblokir event loop."""
    return await run_in_threadpool(_read_proof_for_verification, reference_code)


def _read_proof_for_verification(reference_code: str) -> ProofVerificationRead:
    """Memetakan kode yang terkonfirmasi dan membaca status registry untuk komponen proofCheck."""
    try:
        with get_session_factory()() as db:
            proof = db.execute(
                select(
                    Proof.proof_id, Issuer.id.label("issuer_id"), Issuer.issuer_ref, Issuer.company_name, Issuer.status
                )
                .join(Issuer, Issuer.id == Proof.issuer_id)
                .where(Proof.reference_code == reference_code, Proof.status.in_(_VISIBLE_STATUSES))
            ).one_or_none()
    except SQLAlchemyError as exc:
        logger.error(
            "proof.lookup_db_failed",
            exc_info=(type(exc), None, None),
            extra={"event": "proof.lookup_db_failed", "errorCode": ErrorCode.REGISTRY_UNAVAILABLE},
        )
        return _lookup_without_proof(ProofLookup.UNAVAILABLE, ProofReason.REGISTRY_UNAVAILABLE)

    if proof is None:
        return _lookup_without_proof(ProofLookup.NOT_FOUND)
    try:
        record = _read_registry_proof(proof.proof_id, proof.issuer_ref)
    except registry_adapter.RegistryUnavailable as exc:
        # NFR-09.05: penyebab (mis. ReadTimeout vs ConnectionError) dicatat tanpa kode referensi atau proofId.
        logger.warning(
            "proof.registry_unavailable",
            extra={
                "event": "proof.registry_unavailable",
                "errorCode": ErrorCode.REGISTRY_UNAVAILABLE.value,
                "reason": registry_adapter.failure_reason(exc),
            },
        )
        return _lookup_without_proof(ProofLookup.UNAVAILABLE, ProofReason.REGISTRY_UNAVAILABLE)
    if not record.exists:
        return _lookup_without_proof(ProofLookup.NOT_FOUND)

    return ProofVerificationRead(
        proof_check=ProofCheck(
            lookup=ProofLookup.FOUND,
            reason=None,
            issuer=VerifiedIssuer(issuer_id=proof.issuer_id, company_name=proof.company_name),
            issuer_verified=proof.status == IssuerStatus.VERIFIED,
            lifecycle_status=ProofLifecycleStatus(record.status.name),
            issued_at=datetime.fromtimestamp(record.issued_at, UTC),
            revoked_at=(
                datetime.fromtimestamp(record.revoked_at, UTC)
                if record.status == registry_adapter.OnChainStatus.REVOKED
                else None
            ),
        ),
        registry_document_hash=record.document_hash,
    )


def _lookup_without_proof(lookup: ProofLookup, reason: ProofReason | None = None) -> ProofVerificationRead:
    """Menyusun hasil lookup tanpa metadata atau hash bukti."""
    return ProofVerificationRead(
        proof_check=ProofCheck(
            lookup=lookup,
            reason=reason,
            issuer=None,
            issuer_verified=None,
            lifecycle_status=None,
            issued_at=None,
            revoked_at=None,
        ),
        registry_document_hash=None,
    )


def _read_registry_proof(proof_id: str, issuer_ref: str) -> registry_adapter.ProofRecord:
    """Memeriksa issuerRef sebelum memakai record registry, tanpa mencatat identitas bukti."""
    record = registry_adapter.get_registry_adapter().get_proof(proof_id)
    if record.exists and record.issuer_ref != issuer_ref:
        logger.warning("proof.registry_issuer_mismatch", extra={"event": "proof.registry_issuer_mismatch"})
        raise registry_adapter.RegistryUnavailable("Identitas penerbit tidak cocok dengan registry.")
    return record
