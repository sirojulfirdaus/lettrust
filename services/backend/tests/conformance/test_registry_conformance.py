# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: SA §6.2.2, §6.3, §6.4
"""Conformance RegistryAdapter: test hanya memakai Protocol; mock lulus sekarang, Web3RegistryAdapter wajib lulus nanti.

Provider (Sat) menjalankan dengan stack hidup:
`docker compose exec backend python -m pytest -m real_registry tests/conformance`.
"""

import re

import pytest

from app.modules.registry.adapter import (
    IssuerMismatchOnChain,
    OnChainStatus,
    ProofNotActiveOnChain,
    RegistryTransactionFailed,
    RegistryTransactionPending,
    RegistryUnavailable,
    TxResult,
)
from app.modules.registry.mock import MockRegistryAdapter

TX_HASH = re.compile(r"^0x[0-9a-f]{64}$")
ZERO = "0" * 64


# Memastikan TxResult berformat seperti receipt nyata (hash 0x+64 hex, blok dan timestamp positif).
def assert_tx(tx: TxResult) -> None:
    assert isinstance(tx, TxResult)
    assert TX_HASH.fullmatch(tx.tx_hash)
    assert tx.block_number > 0
    assert tx.block_timestamp > 0


# Issue lalu get mengembalikan data yang sama, status ACTIVE, issuedAt = timestamp blok.
def test_issue_then_get_returns_same_data(registry, new_proof):
    proof = new_proof()
    tx = registry.issue_proof(proof.proof_id, proof.document_hash, proof.issuer_ref)
    assert_tx(tx)
    record = registry.get_proof(proof.proof_id)
    assert record.exists is True
    assert record.document_hash == proof.document_hash
    assert record.issuer_ref == proof.issuer_ref
    assert record.status == OnChainStatus.ACTIVE
    assert record.issued_at == tx.block_timestamp
    assert record.revoked_at == 0


# Issue duplikat → revert ProofAlreadyExists; data awal tidak berubah.
def test_duplicate_issue_rejected(registry, new_proof):
    proof = new_proof()
    registry.issue_proof(proof.proof_id, proof.document_hash, proof.issuer_ref)
    with pytest.raises(RegistryTransactionFailed) as excinfo:
        registry.issue_proof(proof.proof_id, "ab" * 32, proof.issuer_ref)
    assert excinfo.value.revert_name == "ProofAlreadyExists"
    assert registry.get_proof(proof.proof_id).document_hash == proof.document_hash


# Issue dengan input nol → revert InvalidInput.
def test_issue_zero_input_rejected(registry, new_proof):
    proof = new_proof()
    with pytest.raises(RegistryTransactionFailed) as excinfo:
        registry.issue_proof(proof.proof_id, ZERO, proof.issuer_ref)
    assert excinfo.value.revert_name == "InvalidInput"
    assert registry.get_proof(proof.proof_id).exists is False


# getProof bukti tidak ada → exists=False dan nilai nol, tanpa exception.
def test_get_unknown_returns_not_exists(registry, new_proof):
    record = registry.get_proof(new_proof().proof_id)
    assert record.exists is False
    assert record.document_hash == ZERO
    assert record.issuer_ref == ZERO
    assert record.status == OnChainStatus.NONE
    assert (record.issued_at, record.revoked_at) == (0, 0)


# Revoke bukti aktif → REVOKED, revokedAt = timestamp blok, hash dan issuedAt tetap.
def test_revoke_active(registry, new_proof):
    proof = new_proof()
    issue_tx = registry.issue_proof(proof.proof_id, proof.document_hash, proof.issuer_ref)
    revoke_tx = registry.revoke_proof(proof.proof_id, proof.issuer_ref)
    assert_tx(revoke_tx)
    assert revoke_tx.block_number > issue_tx.block_number
    record = registry.get_proof(proof.proof_id)
    assert record.status == OnChainStatus.REVOKED
    assert record.revoked_at == revoke_tx.block_timestamp > 0
    assert record.document_hash == proof.document_hash
    assert record.issued_at == issue_tx.block_timestamp


# Revoke bukti tidak ada → revert ProofNotFound (tidak dipetakan khusus → RegistryTransactionFailed).
def test_revoke_unknown(registry, new_proof):
    proof = new_proof()
    with pytest.raises(RegistryTransactionFailed) as excinfo:
        registry.revoke_proof(proof.proof_id, proof.issuer_ref)
    assert excinfo.value.revert_name == "ProofNotFound"


# Revoke dua kali → ProofNotActiveOnChain (PROOF_ALREADY_REVOKED).
def test_revoke_twice(registry, new_proof):
    proof = new_proof()
    registry.issue_proof(proof.proof_id, proof.document_hash, proof.issuer_ref)
    registry.revoke_proof(proof.proof_id, proof.issuer_ref)
    with pytest.raises(ProofNotActiveOnChain):
        registry.revoke_proof(proof.proof_id, proof.issuer_ref)


# Revoke dengan issuerRef lain → IssuerMismatchOnChain; status tetap ACTIVE.
def test_revoke_issuer_mismatch(registry, new_proof):
    proof, other = new_proof(), new_proof()
    registry.issue_proof(proof.proof_id, proof.document_hash, proof.issuer_ref)
    with pytest.raises(IssuerMismatchOnChain):
        registry.revoke_proof(proof.proof_id, other.issuer_ref)
    assert registry.get_proof(proof.proof_id).status == OnChainStatus.ACTIVE


# find_issue_tx/find_revoke_tx mengembalikan transaksi yang sama dengan hasil issue/revoke; None bila belum ada.
def test_find_transactions(registry, new_proof):
    proof = new_proof()
    assert registry.find_issue_tx(proof.proof_id) is None
    issue_tx = registry.issue_proof(proof.proof_id, proof.document_hash, proof.issuer_ref)
    found_issue = registry.find_issue_tx(proof.proof_id)
    assert (found_issue.tx_hash, found_issue.block_number) == (issue_tx.tx_hash, issue_tx.block_number)
    assert registry.find_revoke_tx(proof.proof_id) is None
    revoke_tx = registry.revoke_proof(proof.proof_id, proof.issuer_ref)
    found_revoke = registry.find_revoke_tx(proof.proof_id)
    assert (found_revoke.tx_hash, found_revoke.block_number) == (revoke_tx.tx_hash, revoke_tx.block_number)


# Health True saat registry dapat dihubungi dan contract ter-deploy.
def test_health(registry):
    assert registry.health() is True


# Mock saja: mode unavailable → RegistryUnavailable di semua operasi RPC dan health False (tidak raise).
def test_mock_unavailable_mode(new_proof):
    mock = MockRegistryAdapter()
    proof = new_proof()
    mock.set_unavailable(True)
    for call in (
        lambda: mock.issue_proof(proof.proof_id, proof.document_hash, proof.issuer_ref),
        lambda: mock.revoke_proof(proof.proof_id, proof.issuer_ref),
        lambda: mock.get_proof(proof.proof_id),
        lambda: mock.find_issue_tx(proof.proof_id),
        lambda: mock.find_revoke_tx(proof.proof_id),
    ):
        with pytest.raises(RegistryUnavailable):
            call()
    assert mock.health() is False
    mock.set_unavailable(False)
    assert mock.health() is True
    assert mock.proofs == {}


# Mock saja: fail_next berlaku untuk satu panggilan; timeout RPC dipetakan ke RegistryUnavailable seperti adapter nyata.
def test_mock_fail_next_once(new_proof):
    mock = MockRegistryAdapter()
    proof = new_proof()
    mock.fail_next("get_proof", RegistryUnavailable("timeout"))
    with pytest.raises(RegistryUnavailable):
        mock.get_proof(proof.proof_id)
    assert mock.get_proof(proof.proof_id).exists is False
    mock.fail_next("health", RegistryUnavailable("timeout"))
    assert mock.health() is False
    assert mock.health() is True


# Mock saja: receipt timeout dengan commit=True → transaksi tetap tercatat; rekonsiliasi via find_issue_tx (SA §6.5).
def test_mock_receipt_timeout_commits_state(new_proof):
    mock = MockRegistryAdapter(clock=lambda: 1_790_000_000)
    proof = new_proof()
    mock.fail_next("issue_proof", RegistryTransactionPending(), commit=True)
    with pytest.raises(RegistryTransactionPending):
        mock.issue_proof(proof.proof_id, proof.document_hash, proof.issuer_ref)
    assert mock.get_proof(proof.proof_id).status == OnChainStatus.ACTIVE
    assert mock.find_issue_tx(proof.proof_id).block_timestamp == 1_790_000_000


# Mock saja: kegagalan transaksi tanpa commit tidak mengubah state; log panggilan tercatat.
def test_mock_transaction_failure_no_state_change(new_proof):
    mock = MockRegistryAdapter(start_block=10)
    proof = new_proof()
    mock.fail_next("issue_proof", RegistryTransactionFailed())
    with pytest.raises(RegistryTransactionFailed):
        mock.issue_proof(proof.proof_id, proof.document_hash, proof.issuer_ref)
    assert mock.proofs == {}
    assert mock.issue_proof(proof.proof_id, proof.document_hash, proof.issuer_ref).block_number == 10
    assert [name for name, _ in mock.calls] == ["issue_proof", "issue_proof"]


# Mock saja: format input salah → ValueError; mock menolak dibuat di luar APP_ENV=test.
def test_mock_input_validation_and_guard(monkeypatch):
    mock = MockRegistryAdapter()
    with pytest.raises(ValueError):
        mock.get_proof("0x123")
    with pytest.raises(ValueError):
        mock.issue_proof("0x" + "1" * 64, "0x" + "2" * 64, "3" * 64)
    with pytest.raises(ValueError):
        mock.fail_next("get_proof", RegistryUnavailable(), commit=True)
    with pytest.raises(ValueError):
        mock.fail_next("get_proof", ProofNotActiveOnChain())
    monkeypatch.setattr("app.modules.registry.mock.get_settings", lambda: type("S", (), {"app_env": "local"})())
    with pytest.raises(RuntimeError, match="APP_ENV=test"):
        MockRegistryAdapter()
