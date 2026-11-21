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
class _InjectedFailure:
    """Kegagalan terjadwal: exception yang dilempar dan apakah state tetap diterapkan (mis. receipt timeout)."""

    error: RegistryError
    commit: bool


class MockRegistryAdapter:
    """Registry palsu in-memory: satu transaksi per blok (auto-mine Anvil), revert dipetakan seperti adapter nyata.

    Injeksi kegagalan: `fail_next(operation, error, commit=False)` menjadwalkan exception untuk panggilan berikut
    operasi tersebut; `set_unavailable(True)` membuat semua panggilan RPC melempar RegistryUnavailable.
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

    # Mengosongkan state, jadwal kegagalan, dan log panggilan.
    def reset(self) -> None:
        self._proofs.clear()
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
            raise failure.error
        if int(key, 16) == 0 or int(doc, 16) == 0 or int(ref, 16) == 0:
            raise RegistryTransactionFailed("InvalidInput")
        if key in self._proofs:
            raise RegistryTransactionFailed("ProofAlreadyExists")
        tx = self._mine("issue", key)
        self._proofs[key] = MockProof(key, doc, ref, OnChainStatus.ACTIVE, tx.block_timestamp, 0, tx)
        if failure is not None:
            raise failure.error
        return tx

    # Lihat RegistryAdapter.revoke_proof; urutan revert mengikuti contract: NotFound → NotActive → IssuerMismatch.
    def revoke_proof(self, proof_id: str, issuer_ref: str) -> TxResult:
        failure = self._enter("revoke_proof", proof_id, issuer_ref)
        key, ref = _proof_key(proof_id), _hex64(issuer_ref)
        if failure is not None and not failure.commit:
            raise failure.error
        proof = self._proofs.get(key)
        if proof is None:
            raise RegistryTransactionFailed("ProofNotFound")
        if proof.status is not OnChainStatus.ACTIVE:
            raise ProofNotActiveOnChain()
        if proof.issuer_ref != ref:
            raise IssuerMismatchOnChain()
        tx = self._mine("revoke", key)
        self._proofs[key] = replace(proof, status=OnChainStatus.REVOKED, revoked_at=tx.block_timestamp, revoke_tx=tx)
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
