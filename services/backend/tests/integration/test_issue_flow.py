# Owner: Sat (PIC 6) | Status: COMPLETE | Ref: SA §6.5, §18.1; FR-03; T6-04
"""Penerbitan, pembacaan, receipt, dan idempotensi API terhadap chain Compose nyata."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from hashlib import sha256

import pytest

from app.modules.registry.adapter import OnChainStatus

from .conftest import RegistryFlow

pytestmark = pytest.mark.real_registry


# API-04, API-05, mirror, receipt, dan event harus menunjuk hash byte asli dan penerbit yang sama.
def test_issue_and_read_confirmed_proof(flow: RegistryFlow) -> None:
    result = flow.issue()
    assert result.status_code == 201
    issued = result.json()
    proof_id = issued["proofId"]
    expected_hash = sha256(flow.pdf).hexdigest()
    record = flow.registry.get_proof(proof_id)
    assert record.exists and record.status == OnChainStatus.ACTIVE
    assert record.document_hash == expected_hash == issued["documentHash"]
    assert record.issuer_ref == flow.issuer_ref
    assert issued["issuerId"] == flow.issuer_id
    assert datetime.fromisoformat(issued["issuedAt"]).timestamp() == record.issued_at
    receipt = flow.confirmed_receipt(proof_id, issued["transaction"], "ProofIssued")
    assert receipt["blockNumber"] > 0
    read = flow.read(proof_id)
    assert read.status_code == 200
    body = read.json()
    assert body["source"] == "REGISTRY"
    assert body["lifecycleStatus"] == "ACTIVE"
    assert body["documentHash"] == expected_hash
    assert body["issuedAt"] == issued["issuedAt"]
    assert body["issueTransaction"] == issued["transaction"]
    assert body["revokeTransaction"] is None
    stored = flow.stored_proof(proof_id)
    assert stored.status == "ACTIVE"
    assert stored.document_hash == expected_hash
    assert stored.issue_tx_hash == issued["transaction"]["hash"]
    assert stored.issue_block == issued["transaction"]["blockNumber"]


# Replay issuance harus mengembalikan hasil awal tanpa menambah nonce atau event registry.
def test_issue_replay_sends_one_transaction(flow: RegistryFlow) -> None:
    first = flow.issue()
    assert first.status_code == 201
    body = first.json()
    receipt = flow.confirmed_receipt(body["proofId"], body["transaction"], "ProofIssued")
    nonce = flow.nonce(receipt["from"])
    replay = flow.issue()
    assert replay.status_code == 201
    assert replay.json() == body
    assert flow.nonce(receipt["from"]) == nonce
    assert len(flow.events(body["proofId"], "ProofIssued")) == 1


# Payload berbeda untuk kunci issuance yang sama ditolak sebelum transaksi kedua dikirim.
def test_issue_key_conflict_keeps_original_proof(flow: RegistryFlow) -> None:
    first = flow.issue()
    assert first.status_code == 201
    body = first.json()
    receipt = flow.confirmed_receipt(body["proofId"], body["transaction"], "ProofIssued")
    nonce = flow.nonce(receipt["from"])
    conflict = flow.issue(pdf=flow.pdf + b"\n%konten berbeda\n")
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "IDEMPOTENCY_KEY_CONFLICT"
    assert flow.nonce(receipt["from"]) == nonce
    assert flow.registry.get_proof(body["proofId"]).document_hash == sha256(flow.pdf).hexdigest()


# Receipt issuance tetap idempoten sesudah revoke; pembacaan terkini harus tetap REVOKED.
def test_issue_replay_after_revocation_keeps_lifecycle(flow: RegistryFlow) -> None:
    first = flow.issue()
    assert first.status_code == 201
    issued = first.json()
    revoked = flow.revoke(issued["proofId"])
    assert revoked.status_code == 201
    receipt = flow.confirmed_receipt(issued["proofId"], revoked.json()["transaction"], "ProofRevoked")
    nonce = flow.nonce(receipt["from"])
    replay = flow.issue()
    assert replay.status_code == 201
    assert replay.json() == issued
    assert flow.nonce(receipt["from"]) == nonce
    current = flow.read(issued["proofId"])
    assert current.status_code == 200
    assert current.json()["lifecycleStatus"] == "REVOKED"
    assert flow.stored_proof(issued["proofId"]).status == "REVOKED"


# Registry dan API-05 menyatakan bukti acak yang tidak pernah diterbitkan sebagai tidak ada.
def test_read_unknown_proof(flow: RegistryFlow) -> None:
    from app.core.ids import new_proof_id

    proof_id = new_proof_id()
    assert flow.registry.get_proof(proof_id).exists is False
    result = flow.read(proof_id)
    assert result.status_code == 404
    assert result.json()["error"]["code"] == "PROOF_NOT_FOUND"


# Dua issuance bersamaan harus memperoleh nonce dan receipt berbeda lewat signer yang sama.
def test_parallel_issuance_uses_distinct_nonces(flow: RegistryFlow) -> None:
    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(flow.issue)
        b = pool.submit(flow.issue, key=flow.key + "-other", pdf=flow.pdf + b"\n%offer kedua\n")
        results = [a.result(timeout=30), b.result(timeout=30)]
    assert all(result.status_code == 201 for result in results)
    bodies = [result.json() for result in results]
    assert bodies[0]["proofId"] != bodies[1]["proofId"]
    receipts = [flow.confirmed_receipt(body["proofId"], body["transaction"], "ProofIssued") for body in bodies]
    web3 = flow.registry._web3()
    nonces = [web3.eth.get_transaction(receipt["transactionHash"])["nonce"] for receipt in receipts]
    assert abs(nonces[0] - nonces[1]) == 1
    for body in bodies:
        assert flow.registry.get_proof(body["proofId"]).document_hash == body["documentHash"]
