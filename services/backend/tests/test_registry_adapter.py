# Owner: Sat (PIC 6) | Status: COMPLETE | Ref: SA §6.3, §6.4, AD-22; T6-02
"""Menguji batas RPC, konfirmasi transaksi, dan lock; conformance nyata tetap dijalankan terhadap Anvil."""

from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest
from web3 import Web3
from web3.exceptions import (
    ContractCustomError,
    ContractLogicError,
    TimeExhausted,
    TransactionIndexingInProgress,
    TransactionNotFound,
    Web3Exception,
    Web3RPCError,
)

from app.core.config import get_settings
from app.modules.registry import adapter as registry_adapter
from app.modules.registry.adapter import (
    SIGNER_LOCK,
    IssuerMismatchOnChain,
    ProofNotActiveOnChain,
    RegistryError,
    RegistryTransactionFailed,
    RegistryTransactionPending,
    RegistryUnavailable,
    TxResult,
    Web3RegistryAdapter,
)

PROOF_ID = "0x" + "11" * 32
DOCUMENT_HASH = "22" * 32
ISSUER_REF = "33" * 32
CONTRACT_ADDRESS = "0x" + "44" * 20
TX_HASH = bytes.fromhex("55" * 32)
READ_OPERATIONS = ["get_proof", "find_issue_tx", "find_revoke_tx"]


# Menyiapkan adapter berkonfigurasi test tanpa membuka koneksi ke node sungguhan.
@pytest.fixture
def adapter() -> Web3RegistryAdapter:
    settings = get_settings().model_copy(
        update={
            "registry_contract_address": CONTRACT_ADDRESS,
            "registry_rpc_timeout_seconds": 0.15,
            "registry_tx_receipt_timeout_seconds": 0.25,
        }
    )
    return Web3RegistryAdapter(settings)


# Menginjeksi batas web3 lokal untuk menguji kegagalan transport dan receipt secara deterministik.
@pytest.fixture
def rpc(adapter: Web3RegistryAdapter, monkeypatch: pytest.MonkeyPatch) -> Mock:
    web3 = Mock()
    web3.eth.get_code.return_value = b"\x60\x00"
    web3.eth.chain_id = 31337
    web3.eth.get_transaction_count.return_value = 7
    web3.eth.account.from_key.return_value.address = "0x" + "66" * 20
    web3.eth.account.from_key.return_value.sign_transaction.return_value.raw_transaction = b"signed-transaction-test"
    web3.eth.send_raw_transaction.return_value = TX_HASH
    web3.eth.get_transaction_receipt.return_value = {"status": 1, "blockNumber": 42}
    contract = web3.eth.contract.return_value
    contract.address = CONTRACT_ADDRESS
    fields = {
        "proofId": bytes.fromhex("11" * 32),
        "issuerRef": bytes.fromhex(ISSUER_REF),
        "documentHash": bytes.fromhex(DOCUMENT_HASH),
        "issuedAt": 1_790_000_000,
        "revokedAt": 1_790_000_000,
    }
    for event_name in ("ProofIssued", "ProofRevoked"):
        getattr(contract.events, event_name).return_value.process_receipt.return_value = [
            {"address": CONTRACT_ADDRESS, "args": fields}
        ]
    monkeypatch.setattr(adapter, "_web3", Mock(return_value=web3))
    return web3


# Mengarahkan operasi tulis publik ke argumen valid yang sesuai signature Protocol.
def write_proof(adapter: Web3RegistryAdapter, method: str) -> TxResult:
    if method == "issue_proof":
        return adapter.issue_proof(PROOF_ID, DOCUMENT_HASH, ISSUER_REF)
    return adapter.revoke_proof(PROOF_ID, ISSUER_REF)


# Memastikan setiap input tidak valid ditolak sebelum menghubungi RPC atau menandatangani transaksi.
@pytest.mark.parametrize(
    ("method", "args"),
    [
        ("issue_proof", ("0x123", DOCUMENT_HASH, ISSUER_REF)),
        ("issue_proof", (PROOF_ID, "0x" + DOCUMENT_HASH, ISSUER_REF)),
        ("issue_proof", (PROOF_ID, DOCUMENT_HASH, "not-hex")),
        ("revoke_proof", ("0x123", ISSUER_REF)),
        ("revoke_proof", (PROOF_ID, "not-hex")),
        ("get_proof", ("0x123",)),
        ("find_issue_tx", ("0x123",)),
        ("find_revoke_tx", ("0x123",)),
    ],
)
def test_invalid_input_never_contacts_rpc(
    adapter: Web3RegistryAdapter, rpc: Mock, method: str, args: tuple[str, ...]
) -> None:
    with pytest.raises(ValueError):
        getattr(adapter, method)(*args)
    rpc.eth.get_code.assert_not_called()


# Memastikan kegagalan transport pada pembacaan tidak disamakan dengan bukti atau event yang tidak ada.
@pytest.mark.parametrize("method", READ_OPERATIONS)
def test_read_transport_failure_is_unavailable(
    adapter: Web3RegistryAdapter, monkeypatch: pytest.MonkeyPatch, method: str
) -> None:
    monkeypatch.setattr(adapter, "_web3", Mock(side_effect=OSError("upstream-sensitive-detail")))
    with pytest.raises(RegistryUnavailable) as error:
        getattr(adapter, method)(PROOF_ID)
    assert "upstream-sensitive-detail" not in str(error.value)


# Memastikan gangguan transport saat transaksi tidak menghasilkan hasil transaksi sukses.
@pytest.mark.parametrize("method", ["issue_proof", "revoke_proof"])
def test_write_transport_failure_is_unavailable(
    adapter: Web3RegistryAdapter, monkeypatch: pytest.MonkeyPatch, method: str
) -> None:
    monkeypatch.setattr(adapter, "_web3", Mock(side_effect=OSError("upstream-sensitive-detail")))
    with pytest.raises(RegistryUnavailable) as error:
        write_proof(adapter, method)
    assert "upstream-sensitive-detail" not in str(error.value)
    assert not SIGNER_LOCK.locked()


# Memastikan custom error ABI memiliki pemetaan yang sama dengan mock bersama.
@pytest.mark.parametrize(
    ("method", "error_name", "expected"),
    [
        ("issue_proof", "InvalidInput", RegistryTransactionFailed),
        ("issue_proof", "ProofAlreadyExists", RegistryTransactionFailed),
        ("issue_proof", "NotRegistrar", RegistryTransactionFailed),
        ("revoke_proof", "ProofNotFound", RegistryTransactionFailed),
        ("revoke_proof", "ProofNotActive", ProofNotActiveOnChain),
        ("revoke_proof", "IssuerMismatch", IssuerMismatchOnChain),
    ],
)
def test_custom_revert_matches_registry_protocol(
    adapter: Web3RegistryAdapter, rpc: Mock, method: str, error_name: str, expected: type[RegistryError]
) -> None:
    selector = Web3.to_hex(Web3.keccak(text=error_name + "()")[:4])
    function_name = "issueProof" if method == "issue_proof" else "revokeProof"
    function = getattr(rpc.eth.contract.return_value.functions, function_name).return_value
    function.build_transaction.side_effect = ContractCustomError("execution reverted", data=selector)

    with pytest.raises(expected) as error:
        write_proof(adapter, method)
    if expected is RegistryTransactionFailed:
        assert error.value.revert_name == error_name
    rpc.eth.send_raw_transaction.assert_not_called()
    assert not SIGNER_LOCK.locked()


# Memastikan receipt yang belum terkonfirmasi menghasilkan Pending dan tidak diperlakukan sebagai kegagalan pasti.
def test_receipt_timeout_is_pending(adapter: Web3RegistryAdapter, rpc: Mock) -> None:
    rpc.eth.get_transaction_receipt.side_effect = TimeExhausted("receipt timeout")
    with pytest.raises(RegistryTransactionPending):
        adapter.issue_proof(PROOF_ID, DOCUMENT_HASH, ISSUER_REF)
    rpc.eth.get_block.assert_not_called()
    assert not SIGNER_LOCK.locked()


# Memastikan receipt status nol tidak menghasilkan TxResult atau pembacaan blok sukses.
def test_failed_receipt_is_transaction_failed(adapter: Web3RegistryAdapter, rpc: Mock) -> None:
    rpc.eth.get_transaction_receipt.return_value = {"status": 0, "blockNumber": 42}
    with pytest.raises(RegistryTransactionFailed):
        adapter.issue_proof(PROOF_ID, DOCUMENT_HASH, ISSUER_REF)
    rpc.eth.get_block.assert_not_called()


# Memastikan nonce, penandatanganan, broadcast, dan receipt berada di bawah lock yang sama.
@pytest.mark.parametrize("method", ["issue_proof", "revoke_proof"])
def test_write_lock_and_confirmation_cover_the_whole_transaction(
    adapter: Web3RegistryAdapter, rpc: Mock, method: str
) -> None:
    stages = []

    # Merekam setiap tahap RPC dan memastikan lock masih dipegang selama transaksi berlangsung.
    def locked_result(stage: str, value: Any) -> Any:
        assert SIGNER_LOCK.locked()
        stages.append(stage)
        return value

    rpc.eth.get_transaction_count.side_effect = lambda *_: locked_result("nonce", 7)
    signer = rpc.eth.account.from_key.return_value
    signed = signer.sign_transaction.return_value
    signer.sign_transaction.side_effect = lambda _: locked_result("sign", signed)
    rpc.eth.send_raw_transaction.side_effect = lambda _: locked_result("broadcast", TX_HASH)
    rpc.eth.get_transaction_receipt.side_effect = lambda _: locked_result("receipt", {"status": 1, "blockNumber": 42})

    result = write_proof(adapter, method)

    assert result == TxResult("0x" + "55" * 32, 42, 1_790_000_000)
    assert stages == ["nonce", "sign", "broadcast", "receipt"]
    rpc.eth.get_transaction_count.assert_called_once_with(signer.address, "pending")
    rpc.eth.get_transaction_receipt.assert_called_once_with(TX_HASH)
    rpc.eth.get_block.assert_not_called()
    assert not SIGNER_LOCK.locked()


# Memastikan gangguan polling setelah broadcast tetap Pending agar backend dapat merekonsiliasi bukti.
@pytest.mark.parametrize("method", ["issue_proof", "revoke_proof"])
def test_confirmation_rpc_failure_remains_pending(adapter: Web3RegistryAdapter, rpc: Mock, method: str) -> None:
    rpc.eth.get_transaction_receipt.side_effect = OSError("confirmation transport timeout")
    with pytest.raises(RegistryTransactionPending):
        write_proof(adapter, method)
    rpc.eth.send_raw_transaction.assert_called_once()
    assert not SIGNER_LOCK.locked()


# Memastikan balasan broadcast yang hilang tidak dianggap sebagai kegagalan pasti transaksi.
@pytest.mark.parametrize("method", ["issue_proof", "revoke_proof"])
def test_broadcast_acknowledgement_failure_is_pending(adapter: Web3RegistryAdapter, rpc: Mock, method: str) -> None:
    rpc.eth.send_raw_transaction.side_effect = OSError("broadcast acknowledgement lost")
    with pytest.raises(RegistryTransactionPending):
        write_proof(adapter, method)
    rpc.eth.get_transaction_receipt.assert_not_called()
    assert not SIGNER_LOCK.locked()


# Memastikan receipt sukses cukup untuk mengembalikan timestamp tanpa RPC blok yang mungkin sedang gagal.
@pytest.mark.parametrize("method", ["issue_proof", "revoke_proof"])
def test_confirmed_receipt_uses_its_event_timestamp(adapter: Web3RegistryAdapter, rpc: Mock, method: str) -> None:
    rpc.eth.get_block.side_effect = OSError("block endpoint unavailable")
    assert write_proof(adapter, method) == TxResult("0x" + "55" * 32, 42, 1_790_000_000)
    rpc.eth.get_block.assert_not_called()


# Memastikan receipt sukses tanpa event lengkap tetap dapat direkonsiliasi dan tidak menjadi kegagalan pasti.
def test_missing_receipt_event_is_pending(adapter: Web3RegistryAdapter, rpc: Mock) -> None:
    rpc.eth.contract.return_value.events.ProofIssued.return_value.process_receipt.return_value = []
    with pytest.raises(RegistryTransactionPending):
        adapter.issue_proof(PROOF_ID, DOCUMENT_HASH, ISSUER_REF)
    rpc.eth.get_block.assert_not_called()


# Memastikan polling kedua memakai sisa anggaran dan lock dilepas tepat setelah anggaran habis.
def test_receipt_polling_uses_remaining_budget(
    adapter: Web3RegistryAdapter, rpc: Mock, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = [0.0]
    timeouts: list[float] = []

    # Memajukan jam virtual untuk mengukur anggaran tanpa bergantung pada kecepatan mesin tes.
    def advance(seconds: float) -> None:
        clock[0] += seconds

    # Merekam batas per request yang diberikan adapter kepada transport konfirmasi.
    def client(timeout: float | None = None) -> Mock:
        if timeout is not None:
            timeouts.append(timeout)
        return rpc

    # Menyimulasikan transaksi belum ditemukan lalu timeout pada sisa anggaran berikutnya.
    def receipt(_tx_hash: bytes) -> None:
        if len(timeouts) == 1:
            advance(0.12)
            raise TransactionNotFound("not indexed yet")
        advance(timeouts[-1])
        raise OSError("receipt transport timeout")

    monkeypatch.setattr(registry_adapter, "monotonic", lambda: clock[0])
    monkeypatch.setattr(registry_adapter, "sleep", advance)
    monkeypatch.setattr(adapter, "_web3", client)
    rpc.eth.get_transaction_receipt.side_effect = receipt
    with pytest.raises(RegistryTransactionPending):
        adapter.issue_proof(PROOF_ID, DOCUMENT_HASH, ISSUER_REF)
    assert timeouts == pytest.approx([0.15, 0.03])
    assert clock[0] == pytest.approx(0.25)
    assert not SIGNER_LOCK.locked()


# Memastikan transaksi belum terindeks menghabiskan anggaran lewat jeda terbatas, tanpa polling sesudah deadline.
@pytest.mark.parametrize("pending_error", [TransactionNotFound, TransactionIndexingInProgress])
def test_unindexed_receipt_stops_at_deadline(
    adapter: Web3RegistryAdapter, rpc: Mock, monkeypatch: pytest.MonkeyPatch, pending_error: type[Web3Exception]
) -> None:
    clock = [0.0]
    delays: list[float] = []

    # Merekam jeda dan memajukan jam virtual sampai batas receipt tercapai.
    def advance(seconds: float) -> None:
        delays.append(seconds)
        clock[0] += seconds

    monkeypatch.setattr(registry_adapter, "monotonic", lambda: clock[0])
    monkeypatch.setattr(registry_adapter, "sleep", advance)
    rpc.eth.get_transaction_receipt.side_effect = pending_error("receipt not indexed")
    with pytest.raises(RegistryTransactionPending):
        adapter.issue_proof(PROOF_ID, DOCUMENT_HASH, ISSUER_REF)
    assert clock[0] == pytest.approx(0.25)
    assert delays == pytest.approx([0.1, 0.1, 0.05])
    assert rpc.eth.get_transaction_receipt.call_count == 3
    assert not SIGNER_LOCK.locked()


# Menolak alamat tanpa bytecode sebelum transaksi ditandatangani atau disiarkan.
def test_missing_contract_code_cannot_return_success(adapter: Web3RegistryAdapter, rpc: Mock) -> None:
    rpc.eth.get_code.return_value = b""
    with pytest.raises(RegistryUnavailable):
        adapter.issue_proof(PROOF_ID, DOCUMENT_HASH, ISSUER_REF)
    rpc.eth.account.from_key.assert_not_called()
    rpc.eth.send_raw_transaction.assert_not_called()


# Memastikan error RPC tanpa revert tetap Unavailable dan pesan provider tidak terekspos.
def test_non_revert_rpc_error_is_unavailable(adapter: Web3RegistryAdapter, rpc: Mock) -> None:
    rpc.eth.get_code.side_effect = Web3RPCError(
        "upstream-sensitive-detail", rpc_response={"error": {"code": -32005, "message": "upstream-sensitive-detail"}}
    )
    with pytest.raises(RegistryUnavailable) as error:
        adapter.issue_proof(PROOF_ID, DOCUMENT_HASH, ISSUER_REF)
    assert "upstream-sensitive-detail" not in str(error.value)


# Memastikan revert pada pembacaan tidak diperlakukan sebagai hasil NOT_FOUND.
def test_read_revert_is_unavailable(adapter: Web3RegistryAdapter, rpc: Mock) -> None:
    rpc.eth.contract.return_value.functions.getProof.return_value.call.side_effect = ContractLogicError("read failed")
    with pytest.raises(RegistryUnavailable):
        adapter.get_proof(PROOF_ID)


# Memastikan health gagal secara eksplisit tanpa mencatat pesan RPC mentah.
def test_health_failure_does_not_log_raw_rpc_error(
    adapter: Web3RegistryAdapter, rpc: Mock, caplog: pytest.LogCaptureFixture
) -> None:
    rpc.eth.get_code.side_effect = OSError("upstream-sensitive-detail")
    assert adapter.health() is False
    assert "upstream-sensitive-detail" not in caplog.text


# Memastikan metadata deployment yang rusak menghasilkan Unavailable pada operasi dan False pada health.
@pytest.mark.parametrize("content", ["[]", "{invalid-json", '{"contractAddress": "invalid-address"}'])
def test_invalid_deployment_is_unavailable(
    adapter: Web3RegistryAdapter, rpc: Mock, tmp_path: Path, content: str
) -> None:
    deployment = tmp_path / "deployment.json"
    deployment.write_text(content, encoding="utf-8")
    adapter._settings = adapter._settings.model_copy(
        update={"registry_contract_address": "", "registry_deployment_file": str(deployment)}
    )
    assert adapter.health() is False
    with pytest.raises(RegistryUnavailable):
        adapter.issue_proof(PROOF_ID, DOCUMENT_HASH, ISSUER_REF)
