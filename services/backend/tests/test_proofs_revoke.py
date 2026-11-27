# Owner: Sat (PIC 6) | Status: COMPLETE | Ref: FR-04.01–FR-04.05; SA §6.6; T6-03
"""Menguji API-06 melalui autentikasi dan SQLite nyata; mock hanya untuk tes unit."""

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event

import pytest
from conftest import REAL_REGISTRY_ENV
from fakes.contracts import examples_dir
from fastapi.testclient import TestClient
from httpx import Response
from pydantic import SecretStr
from test_proofs_issue import BLOCK_TIME, assert_error, issue, issuer_proofs, make_account
from web3.exceptions import TransactionNotFound

from app.core.config import get_settings
from app.core.db import get_session_factory
from app.main import create_app
from app.modules.auth.schemas import AuthorizationStatus, IssuerStatus, Role
from app.modules.proofs.models import Proof
from app.modules.registry import adapter as registry_adapter
from app.modules.registry.mock import MockRegistryAdapter


# Menginjeksi adapter bersama tanpa mengganti pemeriksaan otorisasi atau database.
@pytest.fixture
def registry(monkeypatch: pytest.MonkeyPatch) -> MockRegistryAdapter:
    instance = MockRegistryAdapter(clock=lambda: BLOCK_TIME)
    monkeypatch.setattr(registry_adapter, "get_registry_adapter", lambda: instance)
    return instance


# Membuka registry Anvil asli hanya saat marker real_registry dipilih secara eksplisit.
@pytest.fixture
def anvil_registry() -> registry_adapter.Web3RegistryAdapter:
    if not REAL_REGISTRY_ENV["REGISTRY_RPC_URL"] or not REAL_REGISTRY_ENV["REGISTRY_SIGNER_PRIVATE_KEY"]:
        pytest.fail("Tes nyata memerlukan konfigurasi registry dari container backend.")
    return registry_adapter.Web3RegistryAdapter(
        get_settings().model_copy(
            update={
                **{
                    key.lower(): value
                    for key, value in REAL_REGISTRY_ENV.items()
                    if key != "REGISTRY_SIGNER_PRIVATE_KEY"
                },
                "registry_signer_private_key": SecretStr(REAL_REGISTRY_ENV["REGISTRY_SIGNER_PRIVATE_KEY"]),
            }
        )
    )


# Mengirim pencabutan beralasan terstruktur dengan kunci opsional.
def revoke(
    client: TestClient,
    headers: dict[str, str],
    proof_id: str,
    key: str | None = "revoke-1",
    reason: str = "OFFER_WITHDRAWN",
) -> Response:
    return client.post(
        f"/api/v1/proofs/{proof_id}/revocations",
        headers=headers if key is None else {**headers, "Idempotency-Key": key},
        json={"reasonCode": reason},
    )


# Memastikan pencabutan dan replay mempertahankan receipt serta metadata penerbitan tanpa transaksi kedua.
def test_revoke_and_replay(client: TestClient, registry: MockRegistryAdapter) -> None:
    issuer_id, headers = make_account()
    issued = issue(client, headers).json()
    result = revoke(client, headers, issued["proofId"])
    assert result.status_code == 201
    body = result.json()
    assert body["lifecycleStatus"] == "REVOKED"
    assert body["transaction"]["blockNumber"] == 2
    assert revoke(client, headers, issued["proofId"]).json() == body
    (proof,) = issuer_proofs(issuer_id)
    assert proof.status == "REVOKED"
    assert proof.revoke_reason_code == "OFFER_WITHDRAWN"
    assert proof.revoke_idempotency_key == "revoke-1"
    assert proof.revoked_by == proof.issued_by
    assert proof.issue_tx_hash == issued["transaction"]["hash"]
    assert registry.get_proof(proof.proof_id).document_hash == issued["documentHash"]
    assert [name for name, _ in registry.calls].count("revoke_proof") == 1


# Unavailable pada lookup event tidak mengganggu replay yang receipt lengkapnya sudah tersimpan.
def test_successful_replay_uses_saved_receipt(client: TestClient, registry: MockRegistryAdapter) -> None:
    _, headers = make_account()
    proof_id = issue(client, headers).json()["proofId"]
    original = revoke(client, headers, proof_id)
    assert original.status_code == 201
    registry.fail_next("find_revoke_tx", registry_adapter.RegistryUnavailable())
    before = len(registry.calls)
    replay = revoke(client, headers, proof_id)
    assert replay.status_code == 201
    assert replay.json() == original.json()
    assert registry.calls[before:] == [("get_proof", (proof_id,))]


# Receipt tersimpan tetap memerlukan pembacaan status registry sebelum boleh dikembalikan.
def test_successful_replay_requires_registry_read(client: TestClient, registry: MockRegistryAdapter) -> None:
    _, headers = make_account()
    proof_id = issue(client, headers).json()["proofId"]
    assert revoke(client, headers, proof_id).status_code == 201
    registry.set_unavailable(True)
    assert_error(revoke(client, headers, proof_id), 503, "REGISTRY_UNAVAILABLE")


# Receipt parsial harus dilengkapi dari event, tanpa menyatakan sukses ketika lookup gagal.
@pytest.mark.parametrize("field", ["revoked_at", "revoke_tx_hash", "revoke_block"])
def test_incomplete_receipt_is_reconciled(client: TestClient, registry: MockRegistryAdapter, field: str) -> None:
    _, headers = make_account()
    proof_id = issue(client, headers).json()["proofId"]
    original = revoke(client, headers, proof_id)
    assert original.status_code == 201
    with get_session_factory().begin() as db:
        proof = db.get(Proof, proof_id)
        assert proof is not None
        setattr(proof, field, None)
    registry.fail_next("find_revoke_tx", registry_adapter.RegistryUnavailable())
    assert_error(revoke(client, headers, proof_id), 503, "REGISTRY_UNAVAILABLE")
    recovered = revoke(client, headers, proof_id)
    assert recovered.status_code == 201
    assert recovered.json() == original.json()
    assert [name for name, _ in registry.calls].count("revoke_proof") == 1


# Mencegah komentar handler mengubah ekspor kontrak beku secara tidak sengaja.
def test_revocation_keeps_frozen_openapi() -> None:
    frozen = json.loads((examples_dir().parent / "openapi.json").read_text(encoding="utf-8"))
    assert create_app().openapi() == frozen


# Menolak pencabutan ulang tanpa kunci atau dengan kunci baru setelah registry menyatakan REVOKED.
@pytest.mark.parametrize("key", [None, "different"])
def test_revoked_rejects_new_attempt(client: TestClient, registry: MockRegistryAdapter, key: str | None) -> None:
    _, headers = make_account()
    proof_id = issue(client, headers).json()["proofId"]
    assert revoke(client, headers, proof_id).status_code == 201
    assert_error(revoke(client, headers, proof_id, key), 409, "PROOF_ALREADY_REVOKED")
    assert [name for name, _ in registry.calls].count("revoke_proof") == 1


# Menolak payload lain untuk kunci pencabutan yang sudah berhasil.
def test_replay_reason_conflict(client: TestClient, registry: MockRegistryAdapter) -> None:
    _, headers = make_account()
    proof_id = issue(client, headers).json()["proofId"]
    assert revoke(client, headers, proof_id).status_code == 201
    assert_error(revoke(client, headers, proof_id, reason="OTHER"), 409, "IDEMPOTENCY_KEY_CONFLICT")


# Menerima seluruh alasan kontrak tanpa header opsional dan tetap menolak pencabutan kedua.
@pytest.mark.parametrize("reason", ["OFFER_WITHDRAWN", "ISSUED_IN_ERROR", "DOCUMENT_REPLACED", "OTHER"])
def test_revoke_without_key(client: TestClient, registry: MockRegistryAdapter, reason: str) -> None:
    issuer_id, headers = make_account()
    proof_id = issue(client, headers).json()["proofId"]
    assert revoke(client, headers, proof_id, key=None, reason=reason).status_code == 201
    assert issuer_proofs(issuer_id)[0].revoke_reason_code == reason
    assert_error(revoke(client, headers, proof_id, key=None, reason=reason), 409, "PROOF_ALREADY_REVOKED")


# Menolak perubahan identitas percobaan yang belum pasti tanpa menimpa audit atau mengirim transaksi. Kunci sama dengan
# alasan berbeda selalu 409 (SA §10.3); kunci lain menunggu selama transaksi awal masih di antrean node.
@pytest.mark.parametrize(
    ("key", "reason", "code"),
    [
        ("different", "OTHER", "REGISTRY_TRANSACTION_FAILED"),
        ("revoke-1", "OTHER", "IDEMPOTENCY_KEY_CONFLICT"),
    ],
)
def test_pending_attempt_cannot_be_overwritten(
    client: TestClient, registry: MockRegistryAdapter, key: str, reason: str, code: str
) -> None:
    issuer_id, headers = make_account()
    proof_id = issue(client, headers).json()["proofId"]
    registry.fail_next("revoke_proof", registry_adapter.RegistryTransactionPending())
    assert revoke(client, headers, proof_id).status_code == 503
    assert_error(
        revoke(client, headers, proof_id, key=key, reason=reason),
        409 if code == "IDEMPOTENCY_KEY_CONFLICT" else 503,
        code,
    )
    (proof,) = issuer_proofs(issuer_id)
    assert proof.revoke_idempotency_key == "revoke-1"
    assert proof.revoke_reason_code == "OFFER_WITHDRAWN"
    assert proof.status == "ACTIVE"
    assert [name for name, _ in registry.calls].count("revoke_proof") == 1


# Tidak mempercayai mirror ACTIVE ketika pembacaan registry gagal.
def test_registry_read_outage(client: TestClient, registry: MockRegistryAdapter) -> None:
    issuer_id, headers = make_account()
    proof_id = issue(client, headers).json()["proofId"]
    registry.set_unavailable(True)
    assert_error(revoke(client, headers, proof_id), 503, "REGISTRY_UNAVAILABLE")
    (proof,) = issuer_proofs(issuer_id)
    assert proof.status == "ACTIVE"
    assert proof.revoke_idempotency_key is None
    assert not any(name == "revoke_proof" for name, _ in registry.calls)


# Status registry tetap disinkronkan tanpa mengarang receipt atau mengembalikan sukses.
def test_missing_event_does_not_finalize(
    client: TestClient, registry: MockRegistryAdapter, monkeypatch: pytest.MonkeyPatch
) -> None:
    issuer_id, headers = make_account()
    proof_id = issue(client, headers).json()["proofId"]
    registry.fail_next("revoke_proof", registry_adapter.RegistryTransactionPending(), commit=True)
    assert revoke(client, headers, proof_id).status_code == 503
    monkeypatch.setattr(registry, "find_revoke_tx", lambda _: None)
    assert_error(revoke(client, headers, proof_id), 503, "REGISTRY_TRANSACTION_FAILED")
    (proof,) = issuer_proofs(issuer_id)
    assert proof.status == "REVOKED"
    assert proof.revoked_at is not None
    assert proof.revoke_tx_hash is proof.revoke_block is None


# Memastikan bukti asing dan identifier tidak ada tidak mengungkap detail atau memanggil RPC.
def test_foreign_and_unknown_proof_are_404(client: TestClient, registry: MockRegistryAdapter) -> None:
    _, headers = make_account()
    _, other = make_account()
    proof_id = issue(client, headers).json()["proofId"]
    before = len(registry.calls)
    for value, caller in ((proof_id, other), ("0x" + "ff" * 32, headers), ("invalid", headers)):
        assert_error(revoke(client, caller, value), 404, "PROOF_NOT_FOUND")
    assert len(registry.calls) == before


# Menolak peran dan afiliasi yang tidak memenuhi syarat pencabutan.
@pytest.mark.parametrize(
    ("role", "status", "authorization"),
    [
        (Role.ADMIN, None, AuthorizationStatus.AUTHORIZED),
        (Role.HR, None, AuthorizationStatus.AUTHORIZED),
        (Role.HR, IssuerStatus.PENDING, AuthorizationStatus.AUTHORIZED),
        (Role.HR, IssuerStatus.REJECTED, AuthorizationStatus.AUTHORIZED),
        (Role.HR, IssuerStatus.VERIFIED, AuthorizationStatus.NOT_AUTHORIZED),
    ],
)
def test_revoke_requires_authorized_hr(
    client: TestClient,
    registry: MockRegistryAdapter,
    role: Role,
    status: IssuerStatus | None,
    authorization: AuthorizationStatus,
) -> None:
    _, headers = make_account(role=role, status=status, authorization=authorization)
    assert_error(revoke(client, headers, "0x" + "ff" * 32), 403, "FORBIDDEN_OPERATION")
    assert registry.calls == []


# Menolak token hilang atau salah sebelum pemeriksaan bukti.
@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid"}])
def test_revoke_requires_authentication(
    client: TestClient, registry: MockRegistryAdapter, headers: dict[str, str]
) -> None:
    assert_error(revoke(client, headers, "0x" + "ff" * 32), 401, "UNAUTHENTICATED")
    assert registry.calls == []


# Memvalidasi alasan tertutup dan kunci kosong sebelum registry dipanggil.
@pytest.mark.parametrize(("key", "reason"), [("", "OTHER"), ("   ", "OTHER"), ("valid", "INVALID")])
def test_invalid_request_is_rejected(client: TestClient, registry: MockRegistryAdapter, key: str, reason: str) -> None:
    _, headers = make_account()
    assert_error(revoke(client, headers, "0x" + "ff" * 32, key, reason), 400, "VALIDATION_ERROR")
    assert registry.calls == []


# Memastikan kegagalan pasti membersihkan metadata tertunda dan memungkinkan retry yang benar.
@pytest.mark.parametrize(
    ("error", "code"),
    [
        (registry_adapter.RegistryUnavailable, "REGISTRY_UNAVAILABLE"),
        (registry_adapter.RegistryTransactionFailed, "REGISTRY_TRANSACTION_FAILED"),
    ],
)
def test_definite_failure_clears_pending(
    client: TestClient, registry: MockRegistryAdapter, error: type[registry_adapter.RegistryError], code: str
) -> None:
    issuer_id, headers = make_account()
    proof_id = issue(client, headers).json()["proofId"]
    registry.fail_next("revoke_proof", error())
    assert_error(revoke(client, headers, proof_id), 503, code)
    (proof,) = issuer_proofs(issuer_id)
    assert proof.status == "ACTIVE"
    assert proof.revoke_idempotency_key is proof.revoke_reason_code is proof.revoked_by is None
    assert registry.get_proof(proof_id).status == registry_adapter.OnChainStatus.ACTIVE
    assert revoke(client, headers, proof_id).status_code == 201


# Memastikan timeout mempertahankan audit dan replay merekonsiliasi state chain sebelum menulis ulang.
@pytest.mark.parametrize("mined", [False, True])
def test_pending_confirmation_is_reconciled(client: TestClient, registry: MockRegistryAdapter, mined: bool) -> None:
    issuer_id, headers = make_account()
    proof_id = issue(client, headers).json()["proofId"]
    registry.fail_next("revoke_proof", registry_adapter.RegistryTransactionPending(), commit=mined)
    assert_error(revoke(client, headers, proof_id), 503, "REGISTRY_TRANSACTION_FAILED")
    (proof,) = issuer_proofs(issuer_id)
    assert proof.status == "ACTIVE"
    assert proof.revoke_idempotency_key == "revoke-1"
    assert proof.revoked_at is proof.revoke_tx_hash is None
    if not mined:
        # Transaksi masih di antrean: retry menunggu tanpa transaksi kedua, lalu boleh dikirim ulang setelah hilang.
        assert_error(revoke(client, headers, proof_id), 503, "REGISTRY_TRANSACTION_FAILED")
        assert [name for name, _ in registry.calls].count("revoke_proof") == 1
        registry.drop_pending(proof_id)
    assert revoke(client, headers, proof_id).status_code == 201
    assert [name for name, _ in registry.calls].count("revoke_proof") == (1 if mined else 2)


# Retry tanpa header menunggu konfirmasi tanpa transaksi baru lalu memperbaiki mirror sebelum respons 409.
def test_unkeyed_pending_reconciles_before_conflict(client: TestClient, registry: MockRegistryAdapter) -> None:
    issuer_id, headers = make_account()
    issued = issue(client, headers).json()
    proof_id = issued["proofId"]
    registry.fail_next("revoke_proof", registry_adapter.RegistryTransactionPending())
    assert_error(revoke(client, headers, proof_id, key=None), 503, "REGISTRY_TRANSACTION_FAILED")
    pending = issuer_proofs(issuer_id)[0]
    assert_error(revoke(client, headers, proof_id, key=None), 503, "REGISTRY_TRANSACTION_FAILED")
    assert [name for name, _ in registry.calls].count("revoke_proof") == 1
    tx = registry.revoke_proof(proof_id, registry.get_proof(proof_id).issuer_ref)
    before = len(registry.calls)
    assert_error(revoke(client, headers, proof_id, key=None), 409, "PROOF_ALREADY_REVOKED")
    (proof,) = issuer_proofs(issuer_id)
    assert proof.status == "REVOKED"
    assert proof.revoke_tx_hash == tx.tx_hash
    assert proof.revoke_block == tx.block_number
    assert proof.revoked_at is not None
    assert proof.revoke_idempotency_key == pending.revoke_idempotency_key
    assert proof.revoke_reason_code == pending.revoke_reason_code
    assert proof.revoked_by == pending.revoked_by
    assert proof.issue_tx_hash == issued["transaction"]["hash"]
    assert not any(name == "revoke_proof" for name, _ in registry.calls[before:])


# Bukti transaksi gugur membuka percobaan baru, termasuk ketika klien tidak mengetahui kunci awal.
@pytest.mark.parametrize("key", [None, "new-key"])
def test_dropped_attempt_allows_new_request(
    client: TestClient, registry: MockRegistryAdapter, monkeypatch: pytest.MonkeyPatch, key: str | None
) -> None:
    issuer_id, headers = make_account()
    proof_id = issue(client, headers).json()["proofId"]
    tx_hash = "0x" + "ab" * 32
    registry.fail_next("revoke_proof", registry_adapter.RegistryTransactionPending(tx_hash=tx_hash))
    assert revoke(client, headers, proof_id, key=None).status_code == 503
    pending = issuer_proofs(issuer_id)[0]
    assert pending.revoke_tx_hash == tx_hash
    checked: list[str] = []

    # Menyediakan kapabilitas pelacakan lokal tes tanpa mengubah mock bersama milik Dws.
    def dropped(value: str) -> bool:
        checked.append(value)
        return True

    monkeypatch.setattr(registry, "is_transaction_failed_or_dropped", dropped, raising=False)
    result = revoke(client, headers, proof_id, key=key, reason="OTHER")
    assert result.status_code == 201
    (proof,) = issuer_proofs(issuer_id)
    assert checked == [tx_hash]
    assert proof.status == "REVOKED"
    assert proof.revoke_reason_code == "OTHER"
    assert proof.revoke_idempotency_key != pending.revoke_idempotency_key
    assert proof.revoke_tx_hash == result.json()["transaction"]["hash"]


# Transaksi yang masih hidup atau pemeriksaan RPC gagal tidak boleh membuka percobaan pengganti.
@pytest.mark.parametrize("key", [None, "new-key", "revoke-1"])
@pytest.mark.parametrize("rpc_unavailable", [False, True])
def test_tracked_pending_cannot_be_overwritten(
    client: TestClient,
    registry: MockRegistryAdapter,
    monkeypatch: pytest.MonkeyPatch,
    key: str | None,
    rpc_unavailable: bool,
) -> None:
    issuer_id, headers = make_account()
    proof_id = issue(client, headers).json()["proofId"]
    tx_hash = "0x" + "ab" * 32
    registry.fail_next("revoke_proof", registry_adapter.RegistryTransactionPending(tx_hash=tx_hash))
    assert revoke(client, headers, proof_id).status_code == 503
    pending = issuer_proofs(issuer_id)[0]

    # Memisahkan transaksi pending dari kegagalan mengetahui status transaksi.
    def check(_value: str) -> bool:
        if rpc_unavailable:
            raise registry_adapter.RegistryUnavailable()
        return False

    monkeypatch.setattr(registry, "is_transaction_failed_or_dropped", check, raising=False)
    assert_error(
        revoke(client, headers, proof_id, key=key),
        503,
        "REGISTRY_UNAVAILABLE" if rpc_unavailable else "REGISTRY_TRANSACTION_FAILED",
    )
    (proof,) = issuer_proofs(issuer_id)
    assert proof.status == "ACTIVE"
    assert proof.revoke_tx_hash == tx_hash
    assert proof.revoke_idempotency_key == pending.revoke_idempotency_key
    assert proof.revoke_reason_code == pending.revoke_reason_code
    assert [name for name, _ in registry.calls].count("revoke_proof") == 1


# Respons konflik tidak boleh menghalangi sinkronisasi receipt atau mengganti audit percobaan awal.
@pytest.mark.parametrize(
    ("key", "code"),
    [
        (None, "PROOF_ALREADY_REVOKED"),
        ("different", "PROOF_ALREADY_REVOKED"),
        ("revoke-1", "IDEMPOTENCY_KEY_CONFLICT"),
    ],
)
def test_conflicting_retry_reconciles_mirror(
    client: TestClient, registry: MockRegistryAdapter, key: str | None, code: str
) -> None:
    issuer_id, headers = make_account()
    proof_id = issue(client, headers).json()["proofId"]
    registry.fail_next("revoke_proof", registry_adapter.RegistryTransactionPending(), commit=True)
    assert revoke(client, headers, proof_id).status_code == 503
    pending = issuer_proofs(issuer_id)[0]
    assert_error(revoke(client, headers, proof_id, key=key, reason="OTHER"), 409, code)
    (proof,) = issuer_proofs(issuer_id)
    assert proof.status == "REVOKED"
    tx = registry.find_revoke_tx(proof_id)
    assert tx is not None
    assert proof.revoke_tx_hash == tx.tx_hash
    assert proof.revoke_block == tx.block_number
    assert proof.revoked_at is not None
    assert proof.revoke_idempotency_key == pending.revoke_idempotency_key
    assert proof.revoke_reason_code == "OFFER_WITHDRAWN"
    assert proof.revoked_by == pending.revoked_by
    assert revoke(client, headers, proof_id).status_code == 201
    assert [name for name, _ in registry.calls].count("revoke_proof") == 1


# Konflik dari status chain tidak berubah menjadi 503 saat receipt belum dapat disinkronkan.
@pytest.mark.parametrize(
    ("key", "code"),
    [
        (None, "PROOF_ALREADY_REVOKED"),
        ("different", "PROOF_ALREADY_REVOKED"),
        ("revoke-1", "IDEMPOTENCY_KEY_CONFLICT"),
    ],
)
@pytest.mark.parametrize("event_missing", [False, True])
def test_conflict_survives_event_outage(
    client: TestClient,
    registry: MockRegistryAdapter,
    monkeypatch: pytest.MonkeyPatch,
    key: str | None,
    code: str,
    event_missing: bool,
) -> None:
    issuer_id, headers = make_account()
    proof_id = issue(client, headers).json()["proofId"]
    registry.fail_next("revoke_proof", registry_adapter.RegistryTransactionPending(), commit=True)
    assert revoke(client, headers, proof_id).status_code == 503
    pending = issuer_proofs(issuer_id)[0]
    with monkeypatch.context() as outage:
        if event_missing:
            outage.setattr(registry, "find_revoke_tx", lambda _: None)
        else:
            registry.fail_next("find_revoke_tx", registry_adapter.RegistryUnavailable())
        assert_error(revoke(client, headers, proof_id, key=key, reason="OTHER"), 409, code)
    (proof,) = issuer_proofs(issuer_id)
    assert proof.status == "REVOKED"
    assert proof.revoked_at is not None
    assert proof.revoke_tx_hash is proof.revoke_block is None
    assert proof.revoke_idempotency_key == pending.revoke_idempotency_key
    assert proof.revoke_reason_code == pending.revoke_reason_code
    assert proof.revoked_by == pending.revoked_by
    assert revoke(client, headers, proof_id).status_code == 201
    assert [name for name, _ in registry.calls].count("revoke_proof") == 1


# Retry selama transaksi terdahulu belum pasti tidak mengirim transaksi baru dan tidak menghapus auditnya.
def test_failed_retry_preserves_original_pending(client: TestClient, registry: MockRegistryAdapter) -> None:
    issuer_id, headers = make_account()
    proof_id = issue(client, headers).json()["proofId"]
    registry.fail_next("revoke_proof", registry_adapter.RegistryTransactionPending())
    assert revoke(client, headers, proof_id).status_code == 503
    assert_error(revoke(client, headers, proof_id), 503, "REGISTRY_TRANSACTION_FAILED")
    assert [name for name, _ in registry.calls].count("revoke_proof") == 1
    (proof,) = issuer_proofs(issuer_id)
    assert proof.status == "ACTIVE"
    assert proof.revoke_idempotency_key == "revoke-1"
    assert proof.revoke_reason_code == "OFFER_WITHDRAWN"
    assert proof.revoked_by == proof.issued_by
    # Mensimulasikan konfirmasi transaksi terdahulu yang terlambat terlihat oleh backend.
    registry.revoke_proof(proof_id, registry.get_proof(proof_id).issuer_ref)
    before = len(registry.calls)
    assert revoke(client, headers, proof_id).status_code == 201
    assert not any(name == "revoke_proof" for name, _ in registry.calls[before:])


# Menahan receipt sukses sambil menyinkronkan status registry ketika lookup event sedang gagal.
def test_event_outage_preserves_pending(client: TestClient, registry: MockRegistryAdapter) -> None:
    issuer_id, headers = make_account()
    proof_id = issue(client, headers).json()["proofId"]
    registry.fail_next("revoke_proof", registry_adapter.RegistryTransactionPending(), commit=True)
    assert revoke(client, headers, proof_id).status_code == 503
    registry.fail_next("find_revoke_tx", registry_adapter.RegistryUnavailable())
    assert_error(revoke(client, headers, proof_id), 503, "REGISTRY_UNAVAILABLE")
    (proof,) = issuer_proofs(issuer_id)
    assert proof.status == "REVOKED"
    assert proof.revoked_at is not None
    assert proof.revoke_tx_hash is proof.revoke_block is None
    assert proof.revoke_idempotency_key == "revoke-1"
    assert revoke(client, headers, proof_id).status_code == 201


# Memulihkan receipt yang muncul di antara pembacaan status dan pengiriman ulang.
def test_late_receipt_is_reconciled(client: TestClient, registry: MockRegistryAdapter) -> None:
    _, headers = make_account()
    proof_id = issue(client, headers).json()["proofId"]
    registry.fail_next("revoke_proof", registry_adapter.RegistryTransactionPending())
    assert revoke(client, headers, proof_id).status_code == 503
    # Antrean tampak kosong saat diperiksa, tetapi receipt terdahulu terkonfirmasi sebelum pengiriman ulang.
    registry.drop_pending(proof_id)
    registry.fail_next("revoke_proof", registry_adapter.ProofNotActiveOnChain(), commit=True)
    assert revoke(client, headers, proof_id).status_code == 201


# Memastikan catatan chain yang tidak konsisten tidak menghasilkan pencabutan sukses.
@pytest.mark.parametrize("field", ["issuer_ref", "document_hash"])
def test_chain_mismatch_is_rejected(
    client: TestClient, registry: MockRegistryAdapter, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    _, headers = make_account()
    proof_id = issue(client, headers).json()["proofId"]
    record = registry.get_proof(proof_id)
    monkeypatch.setattr(registry, "get_proof", lambda _: replace(record, **{field: "ff" * 32}))
    assert_error(
        revoke(client, headers, proof_id),
        404 if field == "issuer_ref" else 503,
        "PROOF_NOT_FOUND" if field == "issuer_ref" else "REGISTRY_TRANSACTION_FAILED",
    )


# Menjaga satu transaksi saat dua request berebut bukti dan kunci yang sama.
def test_parallel_revoke_sends_once(
    client: TestClient, registry: MockRegistryAdapter, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, headers = make_account()
    proof_id = issue(client, headers).json()["proofId"]
    entered, release = Event(), Event()
    original = registry.revoke_proof

    # Menahan receipt pertama agar permintaan kedua menunggu lock per bukti.
    def delayed(proof_id: str, issuer_ref: str) -> registry_adapter.TxResult:
        entered.set()
        assert release.wait(5)
        return original(proof_id, issuer_ref)

    monkeypatch.setattr(registry, "revoke_proof", delayed)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(revoke, client, headers, proof_id)
        try:
            assert entered.wait(5)
            second = pool.submit(revoke, client, headers, proof_id)
        finally:
            release.set()
        a, b = first.result(timeout=5), second.result(timeout=5)
    assert a.status_code == b.status_code == 201
    assert a.json() == b.json()
    assert [name for name, _ in registry.calls].count("revoke_proof") == 1


# Memverifikasi API-04 → API-06 dan replay melalui HTTP lokal terhadap registry Anvil sungguhan.
@pytest.mark.real_registry
def test_real_issue_revoke_and_replay(
    client: TestClient, anvil_registry: registry_adapter.Web3RegistryAdapter, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_registry = anvil_registry
    monkeypatch.setattr(registry_adapter, "get_registry_adapter", lambda: real_registry)
    issuer_id, headers = make_account()
    issued = issue(client, headers).json()
    proof_id = issued["proofId"]
    result = revoke(client, headers, proof_id)
    assert result.status_code == 201
    assert revoke(client, headers, proof_id).json() == result.json()
    record = real_registry.get_proof(proof_id)
    assert record.status == registry_adapter.OnChainStatus.REVOKED
    assert record.document_hash == issued["documentHash"]
    tx = real_registry.find_revoke_tx(proof_id)
    assert tx is not None
    assert tx.tx_hash == result.json()["transaction"]["hash"]
    assert tx.block_timestamp == record.revoked_at
    assert issuer_proofs(issuer_id)[0].status == "REVOKED"


# Menambang transaksi tertunda secara manual untuk membuktikan retry tanpa header menyinkronkan SQLite.
@pytest.mark.real_registry
def test_real_unkeyed_timeout_recovers_mirror(
    client: TestClient, anvil_registry: registry_adapter.Web3RegistryAdapter, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(registry_adapter, "get_registry_adapter", lambda: anvil_registry)
    issuer_id, headers = make_account()
    issued = issue(client, headers).json()
    proof_id = issued["proofId"]
    web3 = anvil_registry._web3()
    signer = web3.eth.account.from_key(anvil_registry._settings.registry_signer_private_key.get_secret_value())
    original_nonce = web3.eth.get_transaction_count(signer.address, "latest")
    anvil_registry._settings = anvil_registry._settings.model_copy(update={"registry_tx_receipt_timeout_seconds": 0.2})
    try:
        assert "error" not in web3.provider.make_request("evm_setAutomine", [False])
        assert_error(revoke(client, headers, proof_id, key=None), 503, "REGISTRY_TRANSACTION_FAILED")
        pending = issuer_proofs(issuer_id)[0]
        assert pending.status == "ACTIVE"
        assert anvil_registry.get_proof(proof_id).status == registry_adapter.OnChainStatus.ACTIVE
        assert_error(revoke(client, headers, proof_id, key=None), 503, "REGISTRY_TRANSACTION_FAILED")
        assert web3.eth.get_transaction_count(signer.address, "pending") == original_nonce + 1
        assert "error" not in web3.provider.make_request("evm_mine", [])
        assert_error(revoke(client, headers, proof_id, key=None), 409, "PROOF_ALREADY_REVOKED")
        (proof,) = issuer_proofs(issuer_id)
        record = anvil_registry.get_proof(proof_id)
        tx = anvil_registry.find_revoke_tx(proof_id)
        assert record.status == registry_adapter.OnChainStatus.REVOKED
        assert record.document_hash == issued["documentHash"]
        assert proof.status == "REVOKED"
        assert tx is not None
        assert proof.revoke_tx_hash == tx.tx_hash
        assert proof.revoke_block == tx.block_number
        assert proof.revoked_at is not None
        assert proof.revoke_idempotency_key == pending.revoke_idempotency_key
        assert proof.revoke_reason_code == pending.revoke_reason_code
        assert proof.revoked_by == pending.revoked_by
        assert web3.eth.get_transaction_count(signer.address, "latest") == original_nonce + 1
        events = (
            anvil_registry._contract(web3)
            .events.ProofRevoked()
            .get_logs(from_block=0, argument_filters={"proofId": bytes.fromhex(proof_id[2:])})
        )
        assert len(events) == 1
    finally:
        assert "error" not in web3.provider.make_request("evm_setAutomine", [True])


# Menghapus transaksi dari mempool Anvil nyata lalu membuktikan retry tanpa key atau key baru dapat selesai.
@pytest.mark.real_registry
@pytest.mark.parametrize("key", [None, "new-key"])
@pytest.mark.parametrize("legacy", [False, True])
def test_real_dropped_unkeyed_transaction_recovers(
    client: TestClient,
    anvil_registry: registry_adapter.Web3RegistryAdapter,
    monkeypatch: pytest.MonkeyPatch,
    key: str | None,
    legacy: bool,
) -> None:
    monkeypatch.setattr(registry_adapter, "get_registry_adapter", lambda: anvil_registry)
    issuer_id, headers = make_account()
    proof_id = issue(client, headers).json()["proofId"]
    web3 = anvil_registry._web3()
    anvil_registry._settings = anvil_registry._settings.model_copy(update={"registry_tx_receipt_timeout_seconds": 0.2})
    try:
        assert "error" not in web3.provider.make_request("evm_setAutomine", [False])
        assert revoke(client, headers, proof_id, key=None).status_code == 503
        pending = issuer_proofs(issuer_id)[0]
        assert pending.revoke_tx_hash is not None
        pending_transaction = web3.eth.get_transaction(pending.revoke_tx_hash)
        assert pending_transaction["blockNumber"] is None
        pending_nonce = web3.eth.get_transaction_count(pending_transaction["from"], "pending")
        if legacy:
            with get_session_factory().begin() as db:
                proof = db.get(Proof, proof_id)
                assert proof is not None
                proof.revoke_tx_hash = None
        assert_error(revoke(client, headers, proof_id, key=key), 503, "REGISTRY_TRANSACTION_FAILED")
        assert web3.eth.get_transaction_count(pending_transaction["from"], "pending") == pending_nonce
        assert "error" not in web3.provider.make_request("anvil_dropTransaction", [pending.revoke_tx_hash])
        with pytest.raises(TransactionNotFound):
            web3.eth.get_transaction(pending.revoke_tx_hash)
        assert "error" not in web3.provider.make_request("evm_setAutomine", [True])
        result = revoke(client, headers, proof_id, key=key, reason="OTHER")
        assert result.status_code == 201
        (proof,) = issuer_proofs(issuer_id)
        record = anvil_registry.get_proof(proof_id)
        tx = anvil_registry.find_revoke_tx(proof_id)
        assert record.status == registry_adapter.OnChainStatus.REVOKED
        assert proof.status == "REVOKED"
        assert tx is not None
        assert proof.revoke_tx_hash == tx.tx_hash == result.json()["transaction"]["hash"]
        assert proof.revoke_reason_code == "OTHER"
        assert proof.revoke_idempotency_key != pending.revoke_idempotency_key
        events = (
            anvil_registry._contract(web3)
            .events.ProofRevoked()
            .get_logs(from_block=0, argument_filters={"proofId": bytes.fromhex(proof_id[2:])})
        )
        assert len(events) == 1
    finally:
        assert "error" not in web3.provider.make_request("evm_setAutomine", [True])


# Konflik kunci diputuskan sebelum pelacakan transaksi: tetap 409 walau status antrean tidak dapat dibaca.
def test_key_conflict_precedes_transaction_tracking(client: TestClient, registry: MockRegistryAdapter) -> None:
    issuer_id, headers = make_account()
    proof_id = issue(client, headers).json()["proofId"]
    registry.fail_next("revoke_proof", registry_adapter.RegistryTransactionPending(tx_hash="0x" + "ab" * 32))
    assert revoke(client, headers, proof_id).status_code == 503
    registry.fail_next("is_transaction_failed_or_dropped", registry_adapter.RegistryUnavailable())
    registry.calls.clear()
    assert_error(revoke(client, headers, proof_id, reason="OTHER"), 409, "IDEMPOTENCY_KEY_CONFLICT")
    assert [name for name, _ in registry.calls] == ["get_proof"]
    (proof,) = issuer_proofs(issuer_id)
    assert (proof.revoke_reason_code, proof.revoke_tx_hash) == ("OFFER_WITHDRAWN", "0x" + "ab" * 32)


# Node tanpa txpool_content (atau RPC gagal) membuat status percobaan lama tanpa hash tidak pasti → 503
# REGISTRY_UNAVAILABLE tanpa transaksi baru dan tanpa melepas audit.
def test_untracked_pending_without_pool_access_stays_pending(client: TestClient, registry: MockRegistryAdapter) -> None:
    issuer_id, headers = make_account()
    proof_id = issue(client, headers).json()["proofId"]
    registry.fail_next("revoke_proof", registry_adapter.RegistryTransactionPending())
    assert revoke(client, headers, proof_id).status_code == 503
    registry.fail_next("is_transaction_failed_or_dropped", registry_adapter.RegistryUnavailable())
    registry.calls.clear()
    assert_error(revoke(client, headers, proof_id, key="new-key"), 503, "REGISTRY_UNAVAILABLE")
    assert "revoke_proof" not in [name for name, _ in registry.calls]
    (proof,) = issuer_proofs(issuer_id)
    assert (proof.status, proof.revoke_idempotency_key) == ("ACTIVE", "revoke-1")


# Setelah transaksi lama pasti hilang, kunci yang sama mengirim ulang dan berhasil (pengiriman ulang tetap ada).
def test_same_key_resends_after_drop(client: TestClient, registry: MockRegistryAdapter) -> None:
    _, headers = make_account()
    proof_id = issue(client, headers).json()["proofId"]
    registry.fail_next("revoke_proof", registry_adapter.RegistryTransactionPending(tx_hash="0x" + "cd" * 32))
    assert revoke(client, headers, proof_id).status_code == 503
    registry.drop_pending(proof_id)
    registry.calls.clear()
    response = revoke(client, headers, proof_id)
    assert response.status_code == 201
    assert [name for name, _ in registry.calls].count("revoke_proof") == 1
    assert revoke(client, headers, proof_id).json() == response.json()


# Setelah transaksi lama hilang, kirim ulang yang gagal pasti membersihkan pencabutan tertunda; retry berikutnya 201.
@pytest.mark.parametrize("error", [registry_adapter.RegistryUnavailable, registry_adapter.RegistryTransactionFailed])
def test_definite_failure_after_drop_clears_pending(
    client: TestClient, registry: MockRegistryAdapter, error: type[registry_adapter.RegistryError]
) -> None:
    issuer_id, headers = make_account()
    proof_id = issue(client, headers).json()["proofId"]
    registry.fail_next("revoke_proof", registry_adapter.RegistryTransactionPending(tx_hash="0x" + "ee" * 32))
    assert revoke(client, headers, proof_id).status_code == 503
    registry.drop_pending(proof_id)
    registry.fail_next("revoke_proof", error())
    assert revoke(client, headers, proof_id).status_code == 503
    (proof,) = issuer_proofs(issuer_id)
    assert proof.status == "ACTIVE"
    assert proof.revoke_idempotency_key is proof.revoke_reason_code is proof.revoked_by is None
    assert proof.revoke_tx_hash is None
    assert revoke(client, headers, proof_id).status_code == 201
