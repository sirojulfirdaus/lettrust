# Owner: Sat (PIC 6) | Status: COMPLETE | Ref: PRD FR-03.03, FR-03.09, FR-04.02; SA §6.4, §6.5, §6.6, AD-22
"""Adapter registry nyata dengan transaksi terkonfirmasi, rekonsiliasi event, dan pemetaan error RPC."""

import json
import logging
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from enum import IntEnum
from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol

from web3 import Web3
from web3.contract.contract import Contract
from web3.exceptions import ContractLogicError, TimeExhausted, Web3Exception

from app.core.config import Settings, get_settings
from app.modules.registry.codec import bytes32_to_hex64, hex64_to_bytes32, proof_id_to_bytes32

logger = logging.getLogger(__name__)
ABI_PATH = Path(__file__).resolve().parent / "abi" / "OfferProofRegistry.json"

# Lock tingkat proses: membungkus build, sign, send, dan tunggu receipt agar nonce tidak bentrok (AD-22).
SIGNER_LOCK = threading.Lock()
_RPC_ERRORS = (OSError, ValueError, TypeError, KeyError, Web3Exception)


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


# Mengenali custom error dari data revert ABI tanpa bergantung pada teks pesan provider.
def _revert_name(error: Web3Exception) -> str | None:
    selectors = {
        Web3.keccak(text=f"{entry['name']}({','.join(item['type'] for item in entry['inputs'])})")[:4].hex(): entry[
            "name"
        ]
        for entry in load_abi()
        if entry["type"] == "error"
    }
    pending = [getattr(error, "data", None), getattr(error, "rpc_response", None), *error.args]
    while pending:
        value = pending.pop()
        if isinstance(value, Mapping):
            pending.extend(value.values())
        elif isinstance(value, bytes):
            name = selectors.get(value[:4].hex())
            if name is not None:
                return name
        elif isinstance(value, str) and value.startswith("0x"):
            name = selectors.get(value[2:10].lower())
            if name is not None:
                return name
    return None


# Memetakan revert transaksi sesuai Protocol; operasi issue tidak menghasilkan exception khusus revoke.
def _transaction_error(error: Web3Exception, operation: str) -> RegistryError | None:
    name = _revert_name(error)
    if operation == "revokeProof":
        if name == "ProofNotActive":
            return ProofNotActiveOnChain()
        if name == "IssuerMismatch":
            return IssuerMismatchOnChain()
    response = getattr(error, "rpc_response", None)
    rpc_error = response.get("error") if isinstance(response, Mapping) else None
    is_revert = isinstance(error, ContractLogicError) or (isinstance(rpc_error, Mapping) and rpc_error.get("code") == 3)
    return RegistryTransactionFailed(name) if name is not None or is_revert else None


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
        deployment = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(deployment, dict):
            raise ValueError("Metadata deployment registry harus berupa objek JSON.")
        address = deployment.get("contractAddress")
        return Web3.to_checksum_address(address) if address else None

    # Memuat contract hanya jika alamat tersedia dan memiliki kode; pengiriman ke alamat kosong dilarang.
    def _contract(self, web3: Web3) -> Contract:
        address = self.resolve_contract_address()
        if address is None or not web3.eth.get_code(address):
            raise RegistryUnavailable("Contract registry belum tersedia.")
        return web3.eth.contract(address=address, abi=load_abi())

    # Mengembalikan True bila RPC dapat dihubungi dan alamat deployment memiliki kode contract.
    def health(self) -> bool:
        try:
            address = self.resolve_contract_address()
            if address is None:
                return False
            return len(self._web3().eth.get_code(address)) > 0
        except _RPC_ERRORS as exc:
            logger.warning(
                "registry.health_failed", extra={"event": "registry.health_failed", "errorCode": type(exc).__name__}
            )
            return False

    # Menerbitkan bukti dengan input bytes32 tervalidasi dan menunggu receipt sukses.
    def issue_proof(self, proof_id: str, document_hash: str, issuer_ref: str) -> TxResult:
        args = (proof_id_to_bytes32(proof_id), hex64_to_bytes32(document_hash), hex64_to_bytes32(issuer_ref))
        return self._transact("issueProof", args)

    # Mencabut bukti milik issuerRef yang sama; revert lifecycle dipetakan ke exception domain.
    def revoke_proof(self, proof_id: str, issuer_ref: str) -> TxResult:
        return self._transact("revokeProof", (proof_id_to_bytes32(proof_id), hex64_to_bytes32(issuer_ref)))

    # Membaca data registry lewat eth_call; kegagalan RPC tidak pernah dianggap sebagai bukti tidak ada.
    def get_proof(self, proof_id: str) -> ProofRecord:
        encoded = proof_id_to_bytes32(proof_id)
        try:
            web3 = self._web3()
            exists, document_hash, issuer_ref, status, issued_at, revoked_at = (
                self._contract(web3).functions.getProof(encoded).call()
            )
            return ProofRecord(
                exists=exists,
                document_hash=bytes32_to_hex64(document_hash),
                issuer_ref=bytes32_to_hex64(issuer_ref),
                status=OnChainStatus(status),
                issued_at=int(issued_at),
                revoked_at=int(revoked_at),
            )
        except _RPC_ERRORS as exc:
            raise RegistryUnavailable("Pembacaan bukti dari registry gagal.") from exc

    # Mencari event penerbitan untuk menyelesaikan rekonsiliasi tanpa mengirim transaksi kedua.
    def find_issue_tx(self, proof_id: str) -> TxResult | None:
        return self._find_tx("ProofIssued", "issuedAt", proof_id_to_bytes32(proof_id))

    # Mencari event pencabutan untuk menyelesaikan rekonsiliasi idempotensi.
    def find_revoke_tx(self, proof_id: str) -> TxResult | None:
        return self._find_tx("ProofRevoked", "revokedAt", proof_id_to_bytes32(proof_id))

    # Mengunci seluruh alur nonce hingga receipt agar transaksi registrar tidak saling bertabrakan.
    def _transact(self, operation: str, args: tuple[bytes, ...]) -> TxResult:
        with SIGNER_LOCK:
            try:
                web3 = self._web3()
                contract = self._contract(web3)
                signer = web3.eth.account.from_key(self._settings.registry_signer_private_key.get_secret_value())
                transaction = getattr(contract.functions, operation)(*args).build_transaction(
                    {
                        "from": signer.address,
                        "nonce": web3.eth.get_transaction_count(signer.address, "pending"),
                        "chainId": web3.eth.chain_id,
                    }
                )
                signed = signer.sign_transaction(transaction)
                tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
                try:
                    receipt = web3.eth.wait_for_transaction_receipt(
                        tx_hash, timeout=self._settings.registry_tx_receipt_timeout_seconds, poll_latency=0.1
                    )
                except TimeExhausted as exc:
                    raise RegistryTransactionPending("Receipt registry belum terkonfirmasi.") from exc
                if receipt["status"] != 1:
                    raise RegistryTransactionFailed()
                block_number = int(receipt["blockNumber"])
                block = web3.eth.get_block(block_number)
                return TxResult(
                    tx_hash=Web3.to_hex(tx_hash),
                    block_number=block_number,
                    block_timestamp=int(block["timestamp"]),
                )
            except _RPC_ERRORS as exc:
                error = _transaction_error(exc, operation) if isinstance(exc, Web3Exception) else None
                if error is not None:
                    raise error from exc
                raise RegistryUnavailable("Transaksi registry tidak dapat diproses melalui RPC.") from exc

    # Membaca log event yang difilter proofId; None hanya diberikan setelah pencarian RPC berhasil.
    def _find_tx(self, event_name: str, timestamp_field: str, proof_id: bytes) -> TxResult | None:
        try:
            web3 = self._web3()
            event = getattr(self._contract(web3).events, event_name)()
            logs = event.get_logs(from_block=0, to_block="latest", argument_filters={"proofId": proof_id})
            log = next(iter(logs), None)
            if log is None:
                return None
            return TxResult(
                tx_hash=Web3.to_hex(log["transactionHash"]),
                block_number=int(log["blockNumber"]),
                block_timestamp=int(log["args"][timestamp_field]),
            )
        except _RPC_ERRORS as exc:
            raise RegistryUnavailable("Pencarian event registry gagal.") from exc


# Dependency: adapter registry tunggal per proses (hanya modul proofs dan health yang memakainya).
@lru_cache
def get_registry_adapter() -> Web3RegistryAdapter:
    return Web3RegistryAdapter(get_settings())
