# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: SA §6.2, §6.3, §6.4, §18.1, §18.2, AD-16
"""MockRegistryAdapter in-memory khusus unit test; perilaku mengikuti OfferProofRegistry dan adapter web3 (SA §6)."""

import hashlib
import re
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, replace

from app.core.config import get_settings
from app.modules.registry.adapter import (
    IssuerMismatchOnChain,
    OnChainStatus,
    ProofNotActiveOnChain,
    ProofRecord,
    RegistryError,
    RegistryTransactionFailed,
    RegistryTransactionPending,
    RegistryUnavailable,
    TxResult,
)

_PROOF_ID = re.compile(r"^0x[0-9a-fA-F]{64}$")
_HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
_ZERO_HEX64 = "0" * 64
# Exception yang dapat dihasilkan adapter nyata per operasi (SA §6.4); injeksi di luar daftar ini ditolak.
_TX_FAILURES = (RegistryUnavailable, RegistryTransactionFailed, RegistryTransactionPending)
ALLOWED_FAILURES: dict[str, tuple[type[RegistryError], ...]] = {
    "issue_proof": _TX_FAILURES,
    "revoke_proof": (*_TX_FAILURES, ProofNotActiveOnChain, IssuerMismatchOnChain),
    "get_proof": (RegistryUnavailable,),
    "find_issue_tx": (RegistryUnavailable,),
    "find_revoke_tx": (RegistryUnavailable,),
    "health": (RegistryUnavailable,),
    "is_transaction_failed_or_dropped": (RegistryUnavailable,),
    "is_issue_failed_or_dropped": (RegistryUnavailable,),
}
OPERATIONS = tuple(ALLOWED_FAILURES)


@dataclass(frozen=True)
class MockProof:
    """State satu bukti di registry palsu beserta transaksi penerbitan/pencabutan."""

    proof_id: str
    document_hash: str
    issuer_ref: str
    status: OnChainStatus
    issued_at: int
    revoked_at: int
    issue_tx: TxResult
    revoke_tx: TxResult | None = None


@dataclass(frozen=True)
class _PoolEntry:
    """Transaksi yang dikirim tetapi belum ditambang (Pending tanpa commit); tx_hash None = data lama tanpa hash."""

    operation: str
    proof_id: str
    tx_hash: str | None


@dataclass(frozen=True)
class _InjectedFailure:
    """Kegagalan terjadwal: exception yang dilempar dan apakah state tetap diterapkan (mis. receipt timeout)."""

    error: RegistryError
    commit: bool


class MockRegistryAdapter:
    """Registry palsu in-memory: satu transaksi per blok (auto-mine Anvil), revert dipetakan seperti adapter nyata.

    Injeksi kegagalan: `fail_next(operation, error, commit=False)` menjadwalkan exception untuk panggilan berikut
    operasi tersebut; `set_unavailable(True)` membuat semua panggilan RPC melempar RegistryUnavailable.

    Antrean node: RegistryTransactionPending tanpa commit berarti transaksi masih menunggu di antrean (belum pasti
    gagal), sama seperti Anvil yang belum menambangnya; `drop_pending()` mensimulasikan transaksi hilang dari node
    (mis. chain dimulai ulang). Transaksi yang berhasil ditambang untuk proofId dan operasi yang sama mengosongkan
    entri antreannya.
    """

    # Menolak instansiasi di luar test; clock dan blok awal dapat diinjeksi agar deterministik.
    def __init__(self, clock: Callable[[], int] | None = None, start_block: int = 1) -> None:
        if get_settings().app_env != "test":
            raise RuntimeError("MockRegistryAdapter hanya boleh dipakai saat APP_ENV=test")
        self._clock = clock or (lambda: int(time.time()))
        self._next_block = start_block
        self._proofs: dict[str, MockProof] = {}
        self._failures: dict[str, deque[_InjectedFailure]] = {op: deque() for op in OPERATIONS}
        self._unavailable: RegistryError | None = None
        self._pool: list[_PoolEntry] = []
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    # Menjadwalkan exception untuk panggilan berikut `operation`; commit=True menerapkan perubahan state dulu.
    def fail_next(self, operation: str, error: RegistryError, commit: bool = False) -> None:
        if operation not in OPERATIONS:
            raise ValueError(f"Operasi tidak dikenal: {operation}")
        if not isinstance(error, ALLOWED_FAILURES[operation]):
            raise ValueError(f"{type(error).__name__} tidak pernah dihasilkan adapter nyata untuk {operation}")
        if commit and operation not in ("issue_proof", "revoke_proof"):
            raise ValueError("commit=True hanya bermakna untuk issue_proof/revoke_proof")
        self._failures[operation].append(_InjectedFailure(error, commit))

    # Mengaktifkan/mematikan mode registry tidak tersedia untuk semua operasi (health menjadi False).
    def set_unavailable(self, unavailable: bool, error: RegistryUnavailable | None = None) -> None:
        self._unavailable = (error or RegistryUnavailable("registry tidak tersedia (mock)")) if unavailable else None

    # Mengembalikan salinan seluruh bukti yang tercatat (helper inspeksi test, bukan bagian Protocol).
    @property
    def proofs(self) -> dict[str, MockProof]:
        return dict(self._proofs)

    # Mensimulasikan transaksi yang hilang dari antrean node (semua, atau hanya milik proofId tertentu).
    def drop_pending(self, proof_id: str | None = None) -> None:
        key = None if proof_id is None else _proof_key(proof_id)
        self._pool = [entry for entry in self._pool if key is not None and entry.proof_id != key]

    # Mengosongkan state, jadwal kegagalan, dan log panggilan.
    def reset(self) -> None:
        self._proofs.clear()
        self._pool.clear()
        for queue in self._failures.values():
            queue.clear()
        self._unavailable = None
        self.calls.clear()

    # Mencatat panggilan dan mengambil kegagalan terjadwal (mode unavailable didahulukan).
    def _enter(self, operation: str, *args: str) -> _InjectedFailure | None:
        self.calls.append((operation, args))
        if self._unavailable is not None:
            return _InjectedFailure(self._unavailable, commit=False)
        queue = self._failures[operation]
        return queue.popleft() if queue else None

    # Melempar kegagalan terjadwal tanpa commit; Pending dicatat sebagai transaksi yang masih di antrean node.
    def _raise_uncommitted(self, operation: str, key: str, failure: _InjectedFailure) -> None:
        if isinstance(failure.error, RegistryTransactionPending):
            self._pool.append(_PoolEntry(operation, key, failure.error.tx_hash))
        raise failure.error

    # Menghapus entri antrean operasi yang baru saja ditambang untuk proofId tersebut.
    def _settle(self, operation: str, key: str) -> None:
        self._pool = [entry for entry in self._pool if (entry.operation, entry.proof_id) != (operation, key)]

    # Hash transaksi yang sudah ditambang (receipt status 1).
    def _mined_hashes(self) -> set[str]:
        hashes = {proof.issue_tx.tx_hash for proof in self._proofs.values()}
        return hashes | {proof.revoke_tx.tx_hash for proof in self._proofs.values() if proof.revoke_tx is not None}

    # Hash masih di antrean atau sudah ditambang berarti belum/tidak gagal.
    def _hash_alive(self, tx_hash: str) -> bool:
        return any(entry.tx_hash == tx_hash for entry in self._pool) or tx_hash in self._mined_hashes()

    # Menambang "blok" baru dan mengembalikan TxResult dengan hash transaksi deterministik (format 0x + 64 hex).
    def _mine(self, operation: str, proof_id: str) -> TxResult:
        block = self._next_block
        self._next_block += 1
        tx_hash = "0x" + hashlib.sha256(f"{operation}:{proof_id}:{block}".encode()).hexdigest()
        return TxResult(tx_hash=tx_hash, block_number=block, block_timestamp=self._clock())

    # Lihat RegistryAdapter.issue_proof; revert contract → RegistryTransactionFailed(nama revert).
    def issue_proof(self, proof_id: str, document_hash: str, issuer_ref: str) -> TxResult:
        failure = self._enter("issue_proof", proof_id, document_hash, issuer_ref)
        key, doc, ref = _proof_key(proof_id), _hex64(document_hash), _hex64(issuer_ref)
        if failure is not None and not failure.commit:
            self._raise_uncommitted("issue_proof", key, failure)
        if int(key, 16) == 0 or int(doc, 16) == 0 or int(ref, 16) == 0:
            raise RegistryTransactionFailed("InvalidInput")
        if key in self._proofs:
            raise RegistryTransactionFailed("ProofAlreadyExists")
        tx = self._mine("issue", key)
        self._proofs[key] = MockProof(key, doc, ref, OnChainStatus.ACTIVE, tx.block_timestamp, 0, tx)
        self._settle("issue_proof", key)
        if failure is not None:
            raise failure.error
        return tx

    # Lihat RegistryAdapter.revoke_proof; urutan revert mengikuti contract: NotFound → NotActive → IssuerMismatch.
    def revoke_proof(self, proof_id: str, issuer_ref: str) -> TxResult:
        failure = self._enter("revoke_proof", proof_id, issuer_ref)
        key, ref = _proof_key(proof_id), _hex64(issuer_ref)
        if failure is not None and not failure.commit:
            self._raise_uncommitted("revoke_proof", key, failure)
        proof = self._proofs.get(key)
        if proof is None:
            raise RegistryTransactionFailed("ProofNotFound")
        if proof.status is not OnChainStatus.ACTIVE:
            raise ProofNotActiveOnChain()
        if proof.issuer_ref != ref:
            raise IssuerMismatchOnChain()
        tx = self._mine("revoke", key)
        self._proofs[key] = replace(proof, status=OnChainStatus.REVOKED, revoked_at=tx.block_timestamp, revoke_tx=tx)
        self._settle("revoke_proof", key)
        if failure is not None:
            raise failure.error
        return tx

    # Lihat RegistryAdapter.get_proof; bukti tidak ada → exists=False dan nilai nol (getProof tidak pernah revert).
    def get_proof(self, proof_id: str) -> ProofRecord:
        failure = self._enter("get_proof", proof_id)
        key = _proof_key(proof_id)
        if failure is not None:
            raise failure.error
        proof = self._proofs.get(key)
        if proof is None:
            return ProofRecord(False, _ZERO_HEX64, _ZERO_HEX64, OnChainStatus.NONE, 0, 0)
        return ProofRecord(True, proof.document_hash, proof.issuer_ref, proof.status, proof.issued_at, proof.revoked_at)

    # Lihat RegistryAdapter.find_issue_tx; None bila event ProofIssued tidak ada.
    def find_issue_tx(self, proof_id: str) -> TxResult | None:
        failure = self._enter("find_issue_tx", proof_id)
        key = _proof_key(proof_id)
        if failure is not None:
            raise failure.error
        proof = self._proofs.get(key)
        return proof.issue_tx if proof else None

    # Lihat RegistryAdapter.find_revoke_tx; None bila event ProofRevoked tidak ada.
    def find_revoke_tx(self, proof_id: str) -> TxResult | None:
        failure = self._enter("find_revoke_tx", proof_id)
        key = _proof_key(proof_id)
        if failure is not None:
            raise failure.error
        proof = self._proofs.get(key)
        return proof.revoke_tx if proof else None

    # Lihat RegistryAdapter.health; seperti adapter nyata tidak pernah raise: kegagalan → False.
    def health(self) -> bool:
        return self._enter("health") is None

    # Lihat RegistryAdapter.is_transaction_failed_or_dropped; tanpa hash, antrean revokeProof proofId yang diperiksa.
    def is_transaction_failed_or_dropped(self, tx_hash: str | None, proof_id: str | None = None) -> bool:
        failure = self._enter("is_transaction_failed_or_dropped", *(value for value in (tx_hash, proof_id) if value))
        if failure is not None:
            raise failure.error
        if tx_hash is not None:
            return not self._hash_alive(tx_hash)
        if proof_id is None:
            return False
        key = _proof_key(proof_id)
        return not any((entry.operation, entry.proof_id) == ("revoke_proof", key) for entry in self._pool)

    # Lihat RegistryAdapter.is_issue_failed_or_dropped; hash dan antrean issueProof proofId harus sama-sama mati.
    def is_issue_failed_or_dropped(self, tx_hash: str | None, proof_id: str) -> bool:
        failure = self._enter("is_issue_failed_or_dropped", *(value for value in (tx_hash, proof_id) if value))
        key = _proof_key(proof_id)
        if failure is not None:
            raise failure.error
        if tx_hash is not None and self._hash_alive(tx_hash):
            return False
        return not any((entry.operation, entry.proof_id) == ("issue_proof", key) for entry in self._pool)


# Memvalidasi dan menormalisasi proofId (0x + 64 hex, lowercase); format salah → ValueError (seperti codec).
def _proof_key(proof_id: str) -> str:
    if not _PROOF_ID.fullmatch(proof_id):
        raise ValueError("proofId harus 0x + 64 hex")
    return proof_id.lower()


# Memvalidasi dan menormalisasi hex 64 karakter tanpa 0x (documentHash/issuerRef).
def _hex64(value: str) -> str:
    if not _HEX64.fullmatch(value):
        raise ValueError("nilai harus 64 hex tanpa 0x")
    return value.lower()
