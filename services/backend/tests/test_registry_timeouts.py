# Owner: Sat (PIC 6) | Status: COMPLETE | Ref: SA §6.4, AD-22; PR #27
"""Regresi timeout memakai HTTP lokal nyata agar retry tersembunyi web3 ikut teruji."""

from collections.abc import Iterator
from dataclasses import dataclass
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from time import perf_counter, sleep
from typing import Any

import pytest
from conftest import REAL_REGISTRY_ENV
from pydantic import SecretStr
from web3 import Web3

from app.core.config import get_settings
from app.core.ids import new_proof_id
from app.modules.registry.adapter import (
    OnChainStatus,
    RegistryTransactionPending,
    RegistryUnavailable,
    Web3RegistryAdapter,
)


@dataclass
class RpcEndpoint:
    """Konfigurasi dan penghitung request pada node HTTP lokal yang sengaja gagal."""

    url: str = ""
    delay: float = 0.0
    requests: int = 0


# Menjalankan endpoint HTTP lokal tanpa log payload untuk mengukur retry dan read timeout sebenarnya.
@pytest.fixture
def endpoint() -> Iterator[RpcEndpoint]:
    state = RpcEndpoint()

    class Handler(BaseHTTPRequestHandler):
        """Menunda balasan RPC atau mengembalikan 503 tanpa mencatat body permintaan."""

        # Menghitung request dan menoleransi klien yang sudah menutup koneksi akibat timeout.
        def do_POST(self) -> None:
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            state.requests += 1
            sleep(state.delay)
            try:
                self.send_response(503)
                self.end_headers()
                self.wfile.write(b"{}")
            except (BrokenPipeError, ConnectionResetError):
                pass

        # Menjaga pengujian transport bebas dari log request atau payload RPC.
        def log_message(self, message: str, *args: Any) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    state.url = f"http://127.0.0.1:{server.server_port}"
    worker = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    worker.start()
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=1)


# Menyiapkan adapter dengan timeout pendek sesuai kasus reviewer tanpa memakai signer di jaringan nyata.
@pytest.fixture
def adapter(endpoint: RpcEndpoint) -> Web3RegistryAdapter:
    settings = get_settings().model_copy(
        update={
            "registry_rpc_url": endpoint.url,
            "registry_contract_address": "0x" + "44" * 20,
            "registry_rpc_timeout_seconds": 0.15,
            "registry_tx_receipt_timeout_seconds": 0.25,
        }
    )
    return Web3RegistryAdapter(settings)


# Memastikan HTTP 503 hanya menghasilkan satu request, tanpa retry dan backoff bawaan provider.
def test_rpc_http_failure_is_not_retried(adapter: Web3RegistryAdapter, endpoint: RpcEndpoint) -> None:
    with pytest.raises(RegistryUnavailable):
        adapter.get_proof("0x" + "11" * 32)
    assert endpoint.requests == 1


# Memastikan timeout RPC 0,15 detik tidak diperbesar retry; toleransi tambahan menampung penjadwalan CI.
def test_rpc_timeout_is_not_multiplied(adapter: Web3RegistryAdapter, endpoint: RpcEndpoint) -> None:
    endpoint.delay = 0.8
    started = perf_counter()
    with pytest.raises(RegistryUnavailable):
        adapter.get_proof("0x" + "11" * 32)
    elapsed = perf_counter() - started
    assert endpoint.requests == 1
    assert elapsed < 0.6


# Memastikan receipt beranggaran pendek membatasi HTTP meskipun timeout RPC dikonfigurasi lebih panjang.
def test_receipt_budget_caps_the_http_request(adapter: Web3RegistryAdapter, endpoint: RpcEndpoint) -> None:
    endpoint.delay = 0.8
    adapter._settings = adapter._settings.model_copy(
        update={"registry_rpc_timeout_seconds": 0.6, "registry_tx_receipt_timeout_seconds": 0.08}
    )
    started = perf_counter()
    with pytest.raises(RegistryTransactionPending):
        adapter._wait_for_receipt(bytes.fromhex("55" * 32))
    elapsed = perf_counter() - started
    assert endpoint.requests == 1
    assert elapsed < 0.35


# Membuat adapter terhadap Anvil container dengan konfigurasi asli yang disimpan sebelum env unit test ditimpa.
@pytest.fixture
def real_registry() -> Web3RegistryAdapter:
    if not REAL_REGISTRY_ENV["REGISTRY_RPC_URL"] or not REAL_REGISTRY_ENV["REGISTRY_SIGNER_PRIVATE_KEY"]:
        pytest.fail("Tes real_registry memerlukan konfigurasi registry asli dari container backend yang berjalan.")
    settings = get_settings().model_copy(
        update={
            **{key.lower(): value for key, value in REAL_REGISTRY_ENV.items() if key != "REGISTRY_SIGNER_PRIVATE_KEY"},
            "registry_signer_private_key": SecretStr(REAL_REGISTRY_ENV["REGISTRY_SIGNER_PRIVATE_KEY"]),
        }
    )
    return Web3RegistryAdapter(settings)


# Membuat input sintetis unik agar pengujian ulang tidak bertabrakan dengan state Anvil persisten.
def proof_input() -> tuple[str, str, str]:
    proof_id = new_proof_id()
    return proof_id, sha256(proof_id.encode()).hexdigest(), sha256(b"issuer-konfirmasi-sintetis").hexdigest()


# Membuktikan transaksi nyata tetap tercatat ketika jalur pembacaan receipt mengalami gangguan transport.
@pytest.mark.real_registry
@pytest.mark.parametrize("method", ["issue_proof", "revoke_proof"])
def test_real_proof_survives_receipt_transport_failure(
    real_registry: Web3RegistryAdapter, monkeypatch: pytest.MonkeyPatch, method: str
) -> None:
    proof_id, document_hash, issuer_ref = proof_input()
    if method == "revoke_proof":
        real_registry.issue_proof(proof_id, document_hash, issuer_ref)
    original_client = real_registry._web3

    # Mengganggu receipt saja; pengiriman dan pembacaan bukti tetap memakai RPC Anvil sungguhan.
    def client(timeout: float | None = None) -> Web3:
        web3 = original_client(timeout)
        if timeout is not None:
            # Mensimulasikan koneksi yang putus setelah transaksi telah diterima node.
            def unavailable_receipt(*_args: Any, **_kwargs: Any) -> None:
                raise OSError("receipt transport interrupted after broadcast")

            monkeypatch.setattr(web3.eth, "get_transaction_receipt", unavailable_receipt)
        return web3

    monkeypatch.setattr(real_registry, "_web3", client)
    with pytest.raises(RegistryTransactionPending):
        if method == "issue_proof":
            real_registry.issue_proof(proof_id, document_hash, issuer_ref)
        else:
            real_registry.revoke_proof(proof_id, issuer_ref)
    record = real_registry.get_proof(proof_id)
    assert record.exists is True
    assert record.document_hash == document_hash
    assert record.status == (OnChainStatus.ACTIVE if method == "issue_proof" else OnChainStatus.REVOKED)
    found = real_registry.find_issue_tx(proof_id) if method == "issue_proof" else real_registry.find_revoke_tx(proof_id)
    assert found is not None
    assert found.block_timestamp == (record.issued_at if method == "issue_proof" else record.revoked_at)


# Membuktikan timestamp receipt nyata tetap berhasil ketika pembacaan blok terkonfirmasi sengaja diganggu.
@pytest.mark.real_registry
@pytest.mark.parametrize("method", ["issue_proof", "revoke_proof"])
def test_real_success_uses_event_without_block_lookup(
    real_registry: Web3RegistryAdapter, monkeypatch: pytest.MonkeyPatch, method: str
) -> None:
    proof_id, document_hash, issuer_ref = proof_input()
    if method == "revoke_proof":
        real_registry.issue_proof(proof_id, document_hash, issuer_ref)
    original_client = real_registry._web3
    blocked_queries: list[int] = []

    # Mengizinkan blok latest untuk estimasi fee, tetapi menolak RPC blok bernomor setelah receipt.
    def client(timeout: float | None = None) -> Web3:
        web3 = original_client(timeout)
        original_block = web3.eth.get_block

        # Menyimulasikan kegagalan endpoint blok yang dahulu dapat mengaburkan transaksi sukses.
        def get_block(identifier: Any, *args: Any, **kwargs: Any) -> Any:
            if isinstance(identifier, int):
                blocked_queries.append(identifier)
                raise OSError("confirmed block endpoint unavailable")
            return original_block(identifier, *args, **kwargs)

        monkeypatch.setattr(web3.eth, "get_block", get_block)
        return web3

    monkeypatch.setattr(real_registry, "_web3", client)
    result = (
        real_registry.issue_proof(proof_id, document_hash, issuer_ref)
        if method == "issue_proof"
        else real_registry.revoke_proof(proof_id, issuer_ref)
    )
    record = real_registry.get_proof(proof_id)
    assert result.block_timestamp == (record.issued_at if method == "issue_proof" else record.revoked_at)
    assert blocked_queries == []
