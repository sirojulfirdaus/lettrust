# Owner: Sat (PIC 6) | Status: STUB | Ref: PRD FR-03.03, FR-03.09, FR-04.02; SA §6.4, §6.5, §6.6, AD-22
# TODO: Implementasikan issue_proof/revoke_proof (signer lock + receipt), get_proof (eth_call), find_*_tx,
# dan pemetaan revert.
"""Antarmuka dan adapter web3.py untuk OfferProofRegistry; health() sudah lengkap."""

import json
import logging
import threading
from dataclasses import dataclass
from enum import IntEnum
from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol

from web3 import Web3
from web3.exceptions import Web3Exception

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)
ABI_PATH = Path(__file__).resolve().parent / "abi" / "OfferProofRegistry.json"

# Lock tingkat proses: membungkus build, sign, send, dan tunggu receipt agar nonce tidak bentrok (AD-22).
SIGNER_LOCK = threading.Lock()


class OnChainStatus(IntEnum):
    """Enum Status pada contract (None, Active, Revoked)."""

    NONE = 0
    ACTIVE = 1
    REVOKED = 2


@dataclass(frozen=True)
class TxResult:
    """Hasil transaksi terkonfirmasi."""

    tx_hash: str
    block_number: int
    block_timestamp: int


@dataclass(frozen=True)
class ProofRecord:
    """Hasil getProof; document_hash dan issuer_ref dalam hex 64 karakter tanpa 0x."""

    exists: bool
    document_hash: str
    issuer_ref: str
    status: OnChainStatus
    issued_at: int
    revoked_at: int


class RegistryError(Exception):
    """Basis error adapter registry."""


class RegistryUnavailable(RegistryError):
    """RPC gagal/timeout → REGISTRY_UNAVAILABLE (503) atau lookup=UNAVAILABLE."""


class RegistryTransactionFailed(RegistryError):
    """Receipt status 0 atau revert yang tidak dipetakan → REGISTRY_TRANSACTION_FAILED (503)."""

    # Menyimpan nama custom error revert (bila diketahui) untuk pemetaan dan log.
    def __init__(self, revert_name: str | None = None):
        self.revert_name = revert_name
        super().__init__(revert_name or "transaction failed")


class ProofNotActiveOnChain(RegistryError):
    """Revert ProofNotActive → PROOF_ALREADY_REVOKED (409)."""


class IssuerMismatchOnChain(RegistryError):
    """Revert IssuerMismatch → PROOF_NOT_FOUND (404)."""


class RegistryTransactionPending(RegistryError):
    """Receipt timeout → REGISTRY_TRANSACTION_FAILED (503); direkonsiliasi pada pengulangan."""


class RegistryAdapter(Protocol):
    """Kontrak adapter registry yang dipakai modul proofs (SA §6.4)."""

    # Mengirim issueProof di bawah signer lock dan menunggu receipt.
    def issue_proof(self, proof_id: str, document_hash: str, issuer_ref: str) -> TxResult: ...

    # Mengirim revokeProof di bawah signer lock dan menunggu receipt.
    def revoke_proof(self, proof_id: str, issuer_ref: str) -> TxResult: ...

    # Membaca getProof melalui eth_call dengan timeout RPC.
    def get_proof(self, proof_id: str) -> ProofRecord: ...

    # Mencari event ProofIssued untuk rekonsiliasi idempotensi.
    def find_issue_tx(self, proof_id: str) -> TxResult | None: ...

    # Mencari event ProofRevoked untuk rekonsiliasi idempotensi.
    def find_revoke_tx(self, proof_id: str) -> TxResult | None: ...

    # Memeriksa koneksi RPC dan keberadaan kode contract.
    def health(self) -> bool: ...


# Memuat ABI OfferProofRegistry yang diekspor scripts/export_abi.py.
@lru_cache
def load_abi() -> list[dict[str, Any]]:
    return json.loads(ABI_PATH.read_text(encoding="utf-8"))


class Web3RegistryAdapter:
    """Implementasi RegistryAdapter berbasis web3.py; koneksi dibuat lazy agar backend tetap start tanpa chain."""

    # Menyimpan konfigurasi tanpa membuka koneksi RPC.
    def __init__(self, settings: Settings):
        self._settings = settings

    # Membuat client Web3 dengan timeout RPC dari konfigurasi.
    def _web3(self) -> Web3:
        timeout = self._settings.registry_rpc_timeout_seconds
        return Web3(Web3.HTTPProvider(self._settings.registry_rpc_url, request_kwargs={"timeout": timeout}))

    # Menentukan alamat contract dari override env atau berkas deployment; None bila belum tersedia.
    def resolve_contract_address(self) -> str | None:
        if self._settings.registry_contract_address:
            return Web3.to_checksum_address(self._settings.registry_contract_address)
        path = Path(self._settings.registry_deployment_file)
        if not path.is_file():
            return None
        address = json.loads(path.read_text(encoding="utf-8")).get("contractAddress")
        return Web3.to_checksum_address(address) if address else None

    # Mengembalikan True bila RPC dapat dihubungi dan alamat deployment memiliki kode contract.
    def health(self) -> bool:
        try:
            address = self.resolve_contract_address()
            if address is None:
                return False
            return len(self._web3().eth.get_code(address)) > 0
        except (OSError, ValueError, KeyError, Web3Exception) as exc:
            logger.warning(
                "registry.health_failed", extra={"event": "registry.health_failed", "errorCode": type(exc).__name__}
            )
            return False

    # Lihat RegistryAdapter.issue_proof.
    def issue_proof(self, proof_id: str, document_hash: str, issuer_ref: str) -> TxResult:
        raise NotImplementedError("registry.issue_proof belum diimplementasikan")

    # Lihat RegistryAdapter.revoke_proof.
    def revoke_proof(self, proof_id: str, issuer_ref: str) -> TxResult:
        raise NotImplementedError("registry.revoke_proof belum diimplementasikan")

    # Lihat RegistryAdapter.get_proof.
    def get_proof(self, proof_id: str) -> ProofRecord:
        raise NotImplementedError("registry.get_proof belum diimplementasikan")

    # Lihat RegistryAdapter.find_issue_tx.
    def find_issue_tx(self, proof_id: str) -> TxResult | None:
        raise NotImplementedError("registry.find_issue_tx belum diimplementasikan")

    # Lihat RegistryAdapter.find_revoke_tx.
    def find_revoke_tx(self, proof_id: str) -> TxResult | None:
        raise NotImplementedError("registry.find_revoke_tx belum diimplementasikan")


# Dependency: adapter registry tunggal per proses (hanya modul proofs dan health yang memakainya).
@lru_cache
def get_registry_adapter() -> Web3RegistryAdapter:
    return Web3RegistryAdapter(get_settings())
