# Owner: Sat (PIC 6) | Status: COMPLETE | Ref: SA §6.6, §18.1; FR-04; T6-04
"""Pencabutan dan pengulangan API dengan pembuktian status serta event Anvil asli."""

from datetime import datetime

import pytest
from test_proofs_issue import make_account

from app.modules.registry.adapter import OnChainStatus

from .conftest import RegistryFlow

pytestmark = pytest.mark.real_registry


# Pencabutan harus terkonfirmasi, terbaca lewat API-05/S-06, dan mempertahankan data penerbitan.
def test_revoke_updates_registry_api_and_mirror(flow: RegistryFlow) -> None:
    first = flow.issue()
    assert first.status_code == 201
    issued = first.json()
    proof_id = issued["proofId"]
    revoked = flow.revoke(proof_id, reason="DOCUMENT_REPLACED")
    assert revoked.status_code == 201
    body = revoked.json()
    flow.confirmed_receipt(proof_id, body["transaction"], "ProofRevoked")
    record = flow.registry.get_proof(proof_id)
    assert record.status == OnChainStatus.REVOKED
    assert record.document_hash == issued["documentHash"]
    assert record.issuer_ref == flow.issuer_ref
    assert datetime.fromisoformat(body["revokedAt"]).timestamp() == record.revoked_at
    assert datetime.fromisoformat(issued["issuedAt"]).timestamp() == record.issued_at
    result = flow.read(proof_id)
    assert result.status_code == 200
    read = result.json()
    assert read["source"] == "REGISTRY"
    assert read["lifecycleStatus"] == "REVOKED"
    assert read["revokedAt"] == body["revokedAt"]
    assert read["issueTransaction"] == issued["transaction"]
    assert read["revokeTransaction"] == body["transaction"]
    assert read["revocationReasonCode"] == "DOCUMENT_REPLACED"
    stored = flow.stored_proof(proof_id)
    assert stored.status == "REVOKED"
    assert stored.revoke_reason_code == "DOCUMENT_REPLACED"
    assert stored.revoke_tx_hash == body["transaction"]["hash"]
    assert stored.revoke_block == body["transaction"]["blockNumber"]
    assert stored.issue_tx_hash == issued["transaction"]["hash"]
    listed = flow.client.get("/api/v1/proofs", headers=flow.headers, params={"status": "REVOKED"})
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["proofId"] == proof_id
    assert listed.json()["items"][0]["lifecycleStatus"] == "REVOKED"


# Replay revoke dengan kunci yang sama harus memakai receipt awal dan tidak mengirim transaksi revert sekalipun.
def test_revoke_replay_sends_one_transaction(flow: RegistryFlow) -> None:
    issued = flow.issue()
    assert issued.status_code == 201
    proof_id = issued.json()["proofId"]
    first = flow.revoke(proof_id)
    assert first.status_code == 201
    receipt = flow.confirmed_receipt(proof_id, first.json()["transaction"], "ProofRevoked")
    nonce = flow.nonce(receipt["from"])
    replay = flow.revoke(proof_id)
    assert replay.status_code == 201
    assert replay.json() == first.json()
    assert flow.nonce(receipt["from"]) == nonce
    assert len(flow.events(proof_id, "ProofRevoked")) == 1


# Bukti REVOKED menolak kunci baru atau tanpa kunci dengan 409 dan tanpa transaksi tambahan.
@pytest.mark.parametrize("key", [None, "another-key"])
def test_revoked_rejects_new_attempt(flow: RegistryFlow, key: str | None) -> None:
    issued = flow.issue()
    assert issued.status_code == 201
    proof_id = issued.json()["proofId"]
    first = flow.revoke(proof_id)
    assert first.status_code == 201
    receipt = flow.confirmed_receipt(proof_id, first.json()["transaction"], "ProofRevoked")
    nonce = flow.nonce(receipt["from"])
    result = flow.revoke(proof_id, key=key)
    assert result.status_code == 409
    assert result.json()["error"]["code"] == "PROOF_ALREADY_REVOKED"
    assert flow.nonce(receipt["from"]) == nonce
    assert len(flow.events(proof_id, "ProofRevoked")) == 1


# Mengubah alasan pada replay berkunci sama ditolak tanpa mengganti audit alasan semula.
def test_revoke_payload_conflict_preserves_reason(flow: RegistryFlow) -> None:
    issued = flow.issue()
    assert issued.status_code == 201
    proof_id = issued.json()["proofId"]
    first = flow.revoke(proof_id)
    assert first.status_code == 201
    receipt = flow.confirmed_receipt(proof_id, first.json()["transaction"], "ProofRevoked")
    nonce = flow.nonce(receipt["from"])
    result = flow.revoke(proof_id, reason="OTHER")
    assert result.status_code == 409
    assert result.json()["error"]["code"] == "IDEMPOTENCY_KEY_CONFLICT"
    assert flow.stored_proof(proof_id).revoke_reason_code == "OFFER_WITHDRAWN"
    assert flow.nonce(receipt["from"]) == nonce


# HR penerbit lain tidak dapat membaca atau mencabut bukti; registry harus tetap ACTIVE.
def test_foreign_issuer_cannot_read_or_revoke(flow: RegistryFlow) -> None:
    issued = flow.issue()
    assert issued.status_code == 201
    body = issued.json()
    proof_id = body["proofId"]
    _, other_headers = make_account()
    receipt = flow.confirmed_receipt(proof_id, body["transaction"], "ProofIssued")
    nonce = flow.nonce(receipt["from"])
    read = flow.client.get(f"/api/v1/proofs/{proof_id}", headers=other_headers)
    revoke = flow.client.post(
        f"/api/v1/proofs/{proof_id}/revocations", headers=other_headers, json={"reasonCode": "OFFER_WITHDRAWN"}
    )
    for result in (read, revoke):
        assert result.status_code == 404
        assert result.json()["error"]["code"] == "PROOF_NOT_FOUND"
    assert flow.registry.get_proof(proof_id).status == OnChainStatus.ACTIVE
    assert flow.events(proof_id, "ProofRevoked") == []
    assert flow.nonce(receipt["from"]) == nonce
