"""Menguji otorisasi HR, daftar bukti, dan detail registry lewat HTTP."""

from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update
from test_proofs_issue import BLOCK_TIME, PDF, URL, issue, make_account
from test_proofs_issue import registry as registry

from app.core.db import get_session_factory
from app.core.ids import compute_issuer_ref
from app.modules.auth.schemas import AuthorizationStatus
from app.modules.proofs.models import Proof
from app.modules.proofs.service import REGISTRY_READ_UNAVAILABLE_MESSAGE
from app.modules.registry.adapter import ProofRecord
from app.modules.registry.mock import MockRegistryAdapter


@pytest.fixture
def owned_proof(client: TestClient, registry: MockRegistryAdapter) -> tuple[str, dict[str, str], dict[str, Any]]:
    """Menerbitkan bukti untuk HR sintetis agar mirror dan registry sama-sama terisi."""
    issuer_id, headers = make_account()
    response = issue(client, headers)
    assert response.status_code == 201
    return issuer_id, headers, response.json()


def change_mirror(proof_id: str, **values: Any) -> None:
    """Mengatur mirror secara independen dari registry untuk membedakan sumber data."""
    with get_session_factory().begin() as db:
        db.execute(update(Proof).where(Proof.proof_id == proof_id).values(**values))


def test_list_scopes_filters_and_pages_mirror(client: TestClient, registry: MockRegistryAdapter) -> None:
    """Daftar hanya memuat bukti terkonfirmasi dari satu issuer, dengan total dan urutan stabil."""
    _, headers = make_account()
    _, other = make_account()
    proof_ids = []
    for key, owner in [(str(i), headers) for i in range(6)] + [("other", other)]:
        response = issue(client, owner, key, pdf=PDF + key.encode())
        assert response.status_code == 201
        proof_ids.append(response.json()["proofId"])
    active_a, active_b, newest, revoked, pending, failed, _ = proof_ids
    change_mirror(newest, issued_at=datetime.fromtimestamp(BLOCK_TIME + 1, UTC))
    change_mirror(revoked, status="REVOKED", revoked_at=datetime.fromtimestamp(BLOCK_TIME + 2, UTC))
    change_mirror(pending, status="PENDING")
    change_mirror(failed, status="FAILED")
    registry.calls.clear()
    registry.set_unavailable(True)

    response = client.get(URL, headers=headers, params={"limit": 2, "offset": 0})
    assert response.status_code == 200
    assert response.json()["total"] == 4
    assert [item["proofId"] for item in response.json()["items"]] == [newest, min(active_a, active_b, revoked)]

    response = client.get(URL, headers=headers, params={"status": "ACTIVE", "limit": 2, "offset": 1})
    assert response.status_code == 200
    assert response.json()["total"] == 3
    assert [item["proofId"] for item in response.json()["items"]] == sorted([active_a, active_b])
    assert all(item["lifecycleStatus"] == "ACTIVE" and item["revokedAt"] is None for item in response.json()["items"])

    response = client.get(URL, headers=headers, params={"status": "REVOKED"})
    assert response.status_code == 200
    assert response.json()["total"] == 1
    [item] = response.json()["items"]
    assert (item["proofId"], item["lifecycleStatus"]) == (revoked, "REVOKED")
    assert datetime.fromisoformat(item["revokedAt"]) == datetime.fromtimestamp(BLOCK_TIME + 2, UTC)

    response = client.get(URL, headers=headers, params={"status": "ACTIVE", "offset": 10**30})
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 3}
    assert registry.calls == []


def test_list_without_proofs(client: TestClient) -> None:
    """HR berwenang mendapat koleksi kosong ketika penerbit belum punya bukti."""
    _, headers = make_account()
    response = client.get(URL, headers=headers)
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


@pytest.mark.parametrize("detail", [False, True])
def test_proof_reads_require_authorized_hr(
    client: TestClient, registry: MockRegistryAdapter, partner_headers: dict[str, str], detail: bool
) -> None:
    """Tanpa JWT, partner, dan HR belum berwenang tidak bisa membaca bukti."""
    _, unauthorized = make_account(authorization=AuthorizationStatus.NOT_AUTHORIZED)
    path = f"{URL}/0x{'0' * 64}" if detail else URL
    assert client.get(path).status_code == 401
    assert client.get(path, headers=partner_headers).status_code == 401
    assert client.get(path, headers=unauthorized).status_code == 403
    assert registry.calls == []


@pytest.mark.parametrize("revoked", [False, True])
def test_detail_uses_chain_hash_status_and_times(
    client: TestClient, registry: MockRegistryAdapter, owned_proof: tuple, revoked: bool
) -> None:
    """Detail memakai nilai registry dan mempertahankan referensi transaksi off-chain."""
    issuer_id, headers, proof = owned_proof
    proof_id = proof["proofId"]
    change_mirror(proof_id, document_hash="f" * 64, issued_at=datetime.fromtimestamp(BLOCK_TIME - 10, UTC))
    if revoked:
        tx = registry.revoke_proof(proof_id, compute_issuer_ref(issuer_id))
        change_mirror(
            proof_id,
            revoked_at=datetime.fromtimestamp(BLOCK_TIME - 1, UTC),
            revoke_reason_code="OFFER_WITHDRAWN",
            revoke_tx_hash=tx.tx_hash,
            revoke_block=tx.block_number,
        )

    registry.calls.clear()
    response = client.get(f"{URL}/{proof_id}", headers=headers)
    assert response.status_code == 200
    result = response.json()
    assert result["proofId"] == proof_id and result["issuerId"] == issuer_id
    assert result["referenceCode"] == proof["referenceCode"]
    assert result["source"] == "REGISTRY"
    assert result["documentHash"] == proof["documentHash"]
    assert result["lifecycleStatus"] == ("REVOKED" if revoked else "ACTIVE")
    assert datetime.fromisoformat(result["issuedAt"]) == datetime.fromtimestamp(BLOCK_TIME, UTC)
    assert result["issueTransaction"] == proof["transaction"]
    if revoked:
        assert datetime.fromisoformat(result["revokedAt"]) == datetime.fromtimestamp(tx.block_timestamp, UTC)
        assert result["revocationReasonCode"] == "OFFER_WITHDRAWN"
        assert result["revokeTransaction"] == {"hash": tx.tx_hash, "blockNumber": tx.block_number}
    else:
        assert result["revokedAt"] is None
        assert result["revocationReasonCode"] is None
        assert result["revokeTransaction"] is None
    assert registry.calls == [("get_proof", (proof_id,))]


@pytest.mark.parametrize("case", ["unknown", "other_issuer", "pending", "failed", "missing_on_chain"])
def test_detail_non_visible_proof_is_not_found(
    client: TestClient, registry: MockRegistryAdapter, owned_proof: tuple, case: str
) -> None:
    """ID asing atau bukti belum terkonfirmasi mendapat 404 tanpa membocorkan data."""
    _, headers, proof = owned_proof
    proof_id = proof["proofId"]
    if case == "unknown":
        proof_id = f"0x{'0' * 64}"
    elif case == "other_issuer":
        _, headers = make_account()
    elif case in ("pending", "failed"):
        change_mirror(proof_id, status=case.upper())
    else:
        registry.reset()

    registry.calls.clear()
    response = client.get(f"{URL}/{proof_id}", headers=headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROOF_NOT_FOUND"
    assert registry.calls == ([("get_proof", (proof_id,))] if case == "missing_on_chain" else [])


@pytest.mark.parametrize("case", ["rpc_failed", "issuer_mismatch"])
def test_detail_unavailable_instead_of_using_mirror(
    client: TestClient, registry: MockRegistryAdapter, owned_proof: tuple, case: str
) -> None:
    """Registry gagal atau identitasnya tidak cocok, sehingga detail tidak memakai mirror."""
    _, headers, proof = owned_proof
    proof_id = proof["proofId"]
    if case == "rpc_failed":
        registry.set_unavailable(True)
    else:
        registry.reset()
        registry.issue_proof(proof_id, proof["documentHash"], "e" * 64)

    response = client.get(f"{URL}/{proof_id}", headers=headers)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "REGISTRY_UNAVAILABLE"
    # Operasi baca memakai pesan netral PRD §9.8, bukan pesan "Pencatatan ke registry gagal" milik operasi tulis.
    assert response.json()["error"]["message"] == REGISTRY_READ_UNAVAILABLE_MESSAGE
    assert "Pencatatan" not in response.json()["error"]["message"]


def test_detail_reads_revocation_metadata_committed_during_rpc(
    client: TestClient,
    registry: MockRegistryAdapter,
    owned_proof: tuple,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Detail memakai riwayat off-chain yang dikomit ketika pembacaan registry masih berlangsung."""
    issuer_id, headers, proof = owned_proof
    proof_id = proof["proofId"]
    tx = registry.revoke_proof(proof_id, compute_issuer_ref(issuer_id))
    get_proof = registry.get_proof

    def read_after_mirror_commit(proof_id: str) -> ProofRecord:
        """Menyelesaikan penulisan metadata pencabutan sebelum RPC mengembalikan hasil."""
        change_mirror(
            proof_id,
            status="REVOKED",
            revoke_reason_code="OFFER_WITHDRAWN",
            revoke_tx_hash=tx.tx_hash,
            revoke_block=tx.block_number,
            revoked_at=datetime.fromtimestamp(tx.block_timestamp, UTC),
        )
        return get_proof(proof_id)

    monkeypatch.setattr(registry, "get_proof", read_after_mirror_commit)
    response = client.get(f"{URL}/{proof_id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["lifecycleStatus"] == "REVOKED"
    assert response.json()["revocationReasonCode"] == "OFFER_WITHDRAWN"
    assert response.json()["revokeTransaction"] == {"hash": tx.tx_hash, "blockNumber": tx.block_number}
