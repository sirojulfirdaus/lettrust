"""Menguji API-04 dengan SQLite dan adapter registry palsu bersama."""

import hashlib
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime
from threading import Event, Lock

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.db import get_db, get_engine, get_session_factory
from app.core.ids import compute_issuer_ref, new_issuer_id, new_user_id
from app.core.security import create_access_token
from app.modules.auth.models import User
from app.modules.auth.schemas import AuthorizationStatus, IssuerStatus, Role
from app.modules.issuers.dependencies import AuthorizedHrContext
from app.modules.issuers.models import Issuer, IssuerMembership
from app.modules.proofs import service
from app.modules.proofs.models import Proof
from app.modules.proofs.schemas import IssueProofResponse
from app.modules.registry import adapter as registry_adapter
from app.modules.registry.mock import MockRegistryAdapter

URL = "/api/v1/proofs"
PDF = b"%PDF-1.4\n%offer sintetis\n"
BLOCK_TIME = 1795490000


@pytest.fixture
def registry(monkeypatch: pytest.MonkeyPatch) -> MockRegistryAdapter:
    """Mengganti koneksi registry saja agar autentikasi dan database tetap diperiksa."""
    registry = MockRegistryAdapter(clock=lambda: BLOCK_TIME)
    monkeypatch.setattr(registry_adapter, "get_registry_adapter", lambda: registry)
    return registry


def make_account(
    *,
    role: Role = Role.HR,
    status: IssuerStatus | None = IssuerStatus.VERIFIED,
    authorization: AuthorizationStatus = AuthorizationStatus.AUTHORIZED,
) -> tuple[str, dict[str, str]]:
    """Membuat akun dan afiliasi sintetis tersendiri untuk setiap kasus."""
    user_id, issuer_id = new_user_id(), new_issuer_id()
    now = datetime.now(UTC)
    with get_session_factory().begin() as db:
        db.add(
            User(
                id=user_id,
                email=f"{user_id.lower()}@lettrust.test",
                display_name="HR Uji",
                role=role,
                password_hash="tidak-dipakai",
                created_at=now,
            )
        )
        if status is not None:
            db.flush()
            db.add(
                Issuer(
                    id=issuer_id,
                    company_name="PT Uji API-04",
                    registration_number=issuer_id,
                    contact_email="kontak@lettrust.test",
                    issuer_ref=compute_issuer_ref(issuer_id),
                    status=status,
                    registered_by=user_id,
                    created_at=now,
                )
            )
            db.flush()
            db.add(
                IssuerMembership(
                    user_id=user_id, issuer_id=issuer_id, authorization_status=authorization, created_at=now
                )
            )
    token, _ = create_access_token(user_id, role)
    return issuer_id, {"Authorization": f"Bearer {token}"}


def issue(
    client: TestClient,
    headers: dict[str, str],
    key: str | None = "offer-1",
    *,
    pdf: bytes = PDF,
    issuer_id: str | None = None,
) -> Response:
    """Mengirim permintaan multipart dengan payload uji yang dapat diulang."""
    return client.post(
        URL,
        headers=headers if key is None else {**headers, "Idempotency-Key": key},
        files={"file": ("offer.pdf", pdf, "application/pdf")},
        data={} if issuer_id is None else {"issuerId": issuer_id},
    )


def issuer_proofs(issuer_id: str) -> list[Proof]:
    """Membaca status yang sudah di-commit melalui sesi database terpisah."""
    with get_session_factory()() as db:
        return list(db.scalars(select(Proof).where(Proof.issuer_id == issuer_id)))


def assert_error(response: Response, status: int, code: str) -> None:
    """Memastikan kegagalan API memakai envelope dan tidak menerbitkan kode referensi."""
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert "referenceCode" not in response.json()


def test_issue_and_replay_return_confirmed_receipt(client: TestClient, registry: MockRegistryAdapter) -> None:
    """Memastikan hash, identitas penerbit, dan metadata receipt tersimpan dan dapat diulang."""
    issuer_id, headers = make_account()
    response = issue(client, headers, issuer_id=issuer_id)
    assert response.status_code == 201
    body = response.json()
    proof_id = body["proofId"]
    document_hash = hashlib.sha256(PDF).hexdigest()
    recorded = registry.proofs[proof_id]
    assert body == {
        "proofId": proof_id,
        "referenceCode": body["referenceCode"],
        "issuerId": issuer_id,
        "hashAlgorithm": "SHA-256",
        "documentHash": document_hash,
        "lifecycleStatus": "ACTIVE",
        "issuedAt": datetime.fromtimestamp(BLOCK_TIME, UTC).isoformat().replace("+00:00", "Z"),
        "transaction": {"hash": recorded.issue_tx.tx_hash, "blockNumber": 1},
    }
    (proof,) = issuer_proofs(issuer_id)
    assert (proof.proof_id, proof.reference_code, proof.status) == (proof_id, body["referenceCode"], "ACTIVE")
    assert registry.calls == [("issue_proof", (proof_id, document_hash, compute_issuer_ref(issuer_id)))]

    registry.set_unavailable(True)
    replay = issue(client, headers)
    assert replay.status_code == 201
    assert replay.json() == body
    assert len(registry.calls) == 1


def test_issue_key_conflicts_only_within_issuer(client: TestClient, registry: MockRegistryAdapter) -> None:
    """Menolak hash lain untuk kunci yang sama sambil mengizinkan penerbit berbeda memakai kunci tersebut."""
    issuer_id, headers = make_account()
    other_issuer_id, other_headers = make_account()
    assert issue(client, headers).status_code == 201
    assert_error(issue(client, headers, pdf=PDF + b"!"), 409, "IDEMPOTENCY_KEY_CONFLICT")
    assert issue(client, other_headers, pdf=PDF + b"!").status_code == 201
    assert len(issuer_proofs(issuer_id)) == len(issuer_proofs(other_issuer_id)) == 1
    assert len(registry.calls) == 2


def test_missing_key_creates_independent_attempts(client: TestClient, registry: MockRegistryAdapter) -> None:
    """Memastikan permintaan tanpa header memakai kunci internal yang berbeda."""
    issuer_id, headers = make_account()
    first = issue(client, headers, None)
    second = issue(client, headers, None, pdf=PDF + b"!")
    assert first.status_code == second.status_code == 201
    assert first.json()["proofId"] != second.json()["proofId"]
    assert len({proof.idempotency_key for proof in issuer_proofs(issuer_id)}) == len(registry.proofs) == 2


@pytest.mark.parametrize("key", ["", "   "], ids=["empty", "whitespace"])
def test_blank_key_rejected_before_reserving_proof(client: TestClient, registry: MockRegistryAdapter, key: str) -> None:
    """Menolak kunci kosong atau spasi tanpa membuat percobaan penerbitan."""
    issuer_id, headers = make_account()
    response = issue(client, headers, key)
    assert_error(response, 400, "VALIDATION_ERROR")
    assert response.json()["error"]["details"] == [{"field": "Idempotency-Key", "issue": "string_too_short"}]
    assert issuer_proofs(issuer_id) == []
    assert registry.calls == []


def test_replay_after_revocation_preserves_issuance_result(client: TestClient, registry: MockRegistryAdapter) -> None:
    """Mengembalikan receipt penerbitan semula tanpa menerbitkan ulang atau mengubah status terkini."""
    issuer_id, headers = make_account()
    original = issue(client, headers)
    assert original.status_code == 201
    proof_id = original.json()["proofId"]
    registry.revoke_proof(proof_id, compute_issuer_ref(issuer_id))
    with get_session_factory().begin() as db:
        proof = db.get(Proof, proof_id)
        assert proof is not None
        proof.status = "REVOKED"

    replay = issue(client, headers)
    assert replay.status_code == 201
    assert replay.json() == original.json()
    (proof,) = issuer_proofs(issuer_id)
    assert proof.status == "REVOKED"
    assert [operation for operation, _ in registry.calls] == ["issue_proof", "revoke_proof"]


@pytest.mark.parametrize(
    ("files", "status", "code"),
    [
        (None, 400, "VALIDATION_ERROR"),
        ([("file", ("offer.pdf", b""))], 400, "EMPTY_FILE"),
        ([("file", ("offer.pdf", PDF)), ("extra", ("other.pdf", PDF))], 400, "MULTIPLE_FILES"),
        ([("file", ("offer.pdf", b"teks"))], 415, "UNSUPPORTED_MEDIA_TYPE"),
    ],
    ids=["missing", "empty", "multiple", "signature"],
)
def test_invalid_upload_never_reaches_registry(
    client: TestClient,
    registry: MockRegistryAdapter,
    files: list[tuple[str, tuple[str, bytes]]] | None,
    status: int,
    code: str,
) -> None:
    """Menolak berkas tidak valid sebelum membuat percobaan penerbitan."""
    issuer_id, headers = make_account()
    assert_error(client.post(URL, headers=headers, files=files), status, code)
    assert issuer_proofs(issuer_id) == []
    assert registry.calls == []


def test_pdf_over_file_limit_rejected(client: TestClient, registry: MockRegistryAdapter) -> None:
    """Memastikan batas berkas juga berlaku ketika multipart masih lolos batas transport."""
    issuer_id, headers = make_account()
    oversized_pdf = PDF.ljust(get_settings().max_upload_bytes + 1, b"x")
    assert_error(issue(client, headers, pdf=oversized_pdf), 413, "FILE_TOO_LARGE")
    assert issuer_proofs(issuer_id) == []
    assert registry.calls == []


@pytest.mark.parametrize("token", [None, "sintetis-bukan-jwt"], ids=["missing", "invalid"])
def test_issue_rejects_missing_or_invalid_token(
    client: TestClient, registry: MockRegistryAdapter, token: str | None
) -> None:
    """Memastikan API-04 menolak token hilang atau tidak valid sebelum memanggil registry."""
    headers = {} if token is None else {"Authorization": f"Bearer {token}"}
    assert_error(issue(client, headers), 401, "UNAUTHENTICATED")
    assert registry.calls == []


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
def test_issue_requires_authorized_hr_of_verified_issuer(
    client: TestClient,
    registry: MockRegistryAdapter,
    role: Role,
    status: IssuerStatus | None,
    authorization: AuthorizationStatus,
) -> None:
    """Menolak peran atau afiliasi yang tidak memenuhi syarat tanpa memanggil registry."""
    issuer_id, headers = make_account(role=role, status=status, authorization=authorization)
    assert_error(issue(client, headers), 403, "FORBIDDEN_OPERATION")
    assert issuer_proofs(issuer_id) == []
    assert registry.calls == []


def test_body_issuer_must_match_membership(client: TestClient, registry: MockRegistryAdapter) -> None:
    """Menolak klaim penerbit berbeda meski pemanggil berwenang pada penerbitnya sendiri."""
    issuer_id, headers = make_account()
    other_issuer_id, _ = make_account()
    assert_error(issue(client, headers, issuer_id=other_issuer_id), 403, "FORBIDDEN_OPERATION")
    assert issuer_proofs(issuer_id) == issuer_proofs(other_issuer_id) == []
    assert registry.calls == []


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (registry_adapter.RegistryUnavailable, "REGISTRY_UNAVAILABLE"),
        (registry_adapter.RegistryTransactionFailed, "REGISTRY_TRANSACTION_FAILED"),
    ],
)
def test_retry_reuses_failed_attempt(
    client: TestClient,
    registry: MockRegistryAdapter,
    error: type[registry_adapter.RegistryError],
    code: str,
) -> None:
    """Memastikan kegagalan menyisakan baris yang bisa dicoba lagi dengan proofId yang sama."""
    issuer_id, headers = make_account()
    registry.fail_next("issue_proof", error())
    assert_error(issue(client, headers), 503, code)
    (pending,) = issuer_proofs(issuer_id)
    assert (pending.status, pending.failure_code) == ("FAILED", code)
    assert pending.issue_tx_hash is None
    response = issue(client, headers)
    assert response.status_code == 201
    assert response.json()["proofId"] == pending.proof_id
    assert response.json()["referenceCode"] == pending.reference_code
    assert [operation for operation, _ in registry.calls] == ["issue_proof", "get_proof", "issue_proof"]


@pytest.mark.parametrize("mined", [False, True])
def test_retry_after_receipt_timeout(client: TestClient, registry: MockRegistryAdapter, mined: bool) -> None:
    """Merekonsiliasi timeout dengan membaca registry sebelum memutuskan perlu mengirim ulang."""
    issuer_id, headers = make_account()
    registry.fail_next("issue_proof", registry_adapter.RegistryTransactionPending(), commit=mined)
    assert_error(issue(client, headers), 503, "REGISTRY_TRANSACTION_FAILED")
    (pending,) = issuer_proofs(issuer_id)
    assert pending.status == "PENDING"
    assert pending.issued_at is None
    response = issue(client, headers)
    assert response.status_code == 201
    assert response.json()["proofId"] == pending.proof_id
    assert response.json()["referenceCode"] == pending.reference_code
    assert response.json()["transaction"]["blockNumber"] == 1
    assert [operation for operation, _ in registry.calls] == [
        "issue_proof",
        "get_proof",
        "find_issue_tx" if mined else "issue_proof",
    ]


def test_retry_recovers_late_receipt_when_resubmission_reverts(
    client: TestClient,
    registry: MockRegistryAdapter,
) -> None:
    """Memulihkan hasil saat transaksi pertama tercatat di antara lookup dan pengiriman ulang."""
    issuer_id, headers = make_account()
    registry.fail_next("issue_proof", registry_adapter.RegistryTransactionPending())
    assert_error(issue(client, headers), 503, "REGISTRY_TRANSACTION_FAILED")
    (pending,) = issuer_proofs(issuer_id)
    registry.fail_next("issue_proof", registry_adapter.RegistryTransactionFailed("ProofAlreadyExists"), commit=True)

    response = issue(client, headers)
    assert response.status_code == 201
    assert response.json()["proofId"] == pending.proof_id
    assert response.json()["transaction"]["blockNumber"] == 1
    assert [operation for operation, _ in registry.calls] == [
        "issue_proof",
        "get_proof",
        "issue_proof",
        "get_proof",
        "find_issue_tx",
    ]


def test_retry_requires_chain_confirmation(client: TestClient, registry: MockRegistryAdapter) -> None:
    """Tidak menambah transaksi atau mengeluarkan kode bila lookup transaksi terganggu."""
    issuer_id, headers = make_account()
    registry.fail_next("issue_proof", registry_adapter.RegistryTransactionPending(), commit=True)
    assert_error(issue(client, headers), 503, "REGISTRY_TRANSACTION_FAILED")
    registry.fail_next("find_issue_tx", registry_adapter.RegistryUnavailable())
    assert_error(issue(client, headers), 503, "REGISTRY_UNAVAILABLE")
    (pending,) = issuer_proofs(issuer_id)
    assert pending.status == "PENDING"
    assert pending.issue_tx_hash is None
    assert [operation for operation, _ in registry.calls] == ["issue_proof", "get_proof", "find_issue_tx"]


@pytest.mark.parametrize("mismatch", ["document_hash", "issuer_ref", "status", "missing_event"])
def test_retry_rejects_incomplete_or_inconsistent_chain_record(
    client: TestClient,
    registry: MockRegistryAdapter,
    monkeypatch: pytest.MonkeyPatch,
    mismatch: str,
) -> None:
    """Menahan finalisasi bila record atau receipt tidak membuktikan penerbitan yang dimaksud."""
    issuer_id, headers = make_account()
    registry.fail_next("issue_proof", registry_adapter.RegistryTransactionPending(), commit=True)
    assert_error(issue(client, headers), 503, "REGISTRY_TRANSACTION_FAILED")
    (pending,) = issuer_proofs(issuer_id)
    record = registry.get_proof(pending.proof_id)
    if mismatch == "missing_event":
        monkeypatch.setattr(registry, "find_issue_tx", lambda _: None)
    else:
        bad_value = registry_adapter.OnChainStatus.REVOKED if mismatch == "status" else "f" * 64
        monkeypatch.setattr(registry, "get_proof", lambda _: replace(record, **{mismatch: bad_value}))

    assert_error(issue(client, headers), 503, "REGISTRY_TRANSACTION_FAILED")
    (proof,) = issuer_proofs(issuer_id)
    assert proof.status == "PENDING"
    assert proof.issue_tx_hash is None
    assert [operation for operation, _ in registry.calls].count("issue_proof") == 1


def test_parallel_requests_share_pending_row_and_receipt(
    client: TestClient,
    registry: MockRegistryAdapter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Memastikan permintaan tumpang tindih dengan kunci sama memanggil registry sekali."""
    issuer_id, headers = make_account()
    entered, release, second_started = Event(), Event(), Event()
    original = registry.issue_proof
    original_service = service.issue_proof
    engine = create_engine(get_engine().url, pool_size=1, max_overflow=0, pool_timeout=1)
    sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def get_test_db() -> Iterator[Session]:
        """Membatasi pool agar tes mendeteksi koneksi tertahan selama menunggu lock penerbitan."""
        with sessions() as db:
            yield db

    def track_service_entry(
        db: Session,
        hr: AuthorizedHrContext,
        document_hash: str,
        key: str | None,
    ) -> IssueProofResponse:
        """Memberi tanda saat permintaan kedua selesai menjalankan dependency database."""
        if entered.is_set():
            second_started.set()
        return original_service(db, hr, document_hash, key)

    def wait_for_receipt(proof_id: str, document_hash: str, issuer_ref: str) -> registry_adapter.TxResult:
        """Menahan receipt agar kedua permintaan berebut percobaan PENDING yang sama."""
        entered.set()
        assert release.wait(5)
        return original(proof_id, document_hash, issuer_ref)

    monkeypatch.setattr(registry, "issue_proof", wait_for_receipt)
    monkeypatch.setattr(service, "issue_proof", track_service_entry)
    monkeypatch.setitem(client.app.dependency_overrides, get_db, get_test_db)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(issue, client, headers)
            try:
                assert entered.wait(5)
                (pending,) = issuer_proofs(issuer_id)
                assert pending.status == "PENDING"
                assert pending.issue_tx_hash is None
                second = pool.submit(issue, client, headers)
                assert second_started.wait(5)
            finally:
                release.set()
            first_response, second_response = first.result(timeout=5), second.result(timeout=5)
    finally:
        engine.dispose()
    assert first_response.status_code == second_response.status_code == 201
    assert first_response.json() == second_response.json()
    assert [operation for operation, _ in registry.calls] == ["issue_proof"]


def test_duplicate_active_document_rejected_before_registry(client: TestClient, registry: MockRegistryAdapter) -> None:
    """FR-03.06 AC-01: hash ACTIVE yang sama dari penerbit sama dengan kunci baru → 409 tanpa baris atau transaksi."""
    issuer_id, headers = make_account()
    assert issue(client, headers, "offer-1").status_code == 201
    registry.calls.clear()
    assert_error(issue(client, headers, "offer-2"), 409, "DUPLICATE_ACTIVE_DOCUMENT")
    assert registry.calls == []
    assert len(issuer_proofs(issuer_id)) == 1


def test_parallel_duplicate_document_issues_once(
    client: TestClient,
    registry: MockRegistryAdapter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Memastikan dua permintaan untuk PDF yang sama hanya mencatat satu bukti."""
    issuer_id, headers = make_account()
    first_key = "offer-1"
    stripe_count = len(service._ISSUE_LOCKS)
    first_stripe = hash((issuer_id, first_key)) % stripe_count
    second_key = next(
        f"offer-{index}"
        for index in range(2, 2 * stripe_count)
        if hash((issuer_id, f"offer-{index}")) % stripe_count != first_stripe
    )
    first_checked, second_ready, release_first = Event(), Event(), Event()
    original_reserve = service._reserve_proof

    class ObservedLock:
        """Memberi tanda saat permintaan kedua menunggu kunci yang sama."""

        def __init__(self) -> None:
            self.lock = Lock()

        def __enter__(self) -> None:
            if not self.lock.acquire(blocking=False):
                second_ready.set()
                self.lock.acquire()

        def __exit__(self, *_: object) -> None:
            self.lock.release()

    def reserve(db: Session, hr: AuthorizedHrContext, document_hash: str, key: str) -> Proof:
        """Menahan permintaan pertama setelah cek duplikat dan sebelum reservasi."""
        if key == first_key:
            first_checked.set()
            assert release_first.wait(5)
        else:
            second_ready.set()
        return original_reserve(db, hr, document_hash, key)

    monkeypatch.setattr(service, "_ISSUE_LOCKS", tuple(ObservedLock() for _ in range(stripe_count)))
    monkeypatch.setattr(service, "_reserve_proof", reserve)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(issue, client, headers, first_key)
        try:
            assert first_checked.wait(5)
            second = pool.submit(issue, client, headers, second_key)
            assert second_ready.wait(5)
        finally:
            release_first.set()
        assert first.result(timeout=5).status_code == 201
        assert_error(second.result(timeout=5), 409, "DUPLICATE_ACTIVE_DOCUMENT")

    assert len(issuer_proofs(issuer_id)) == 1
    assert [operation for operation, _ in registry.calls] == ["issue_proof"]


def test_same_hash_from_other_issuer_is_issued(client: TestClient, registry: MockRegistryAdapter) -> None:
    """SA §6.5 butir 5 membatasi duplikat pada penerbit yang sama; penerbit lain boleh mencatat hash yang sama."""
    _, first = make_account()
    _, second = make_account()
    assert issue(client, first).status_code == 201
    response = issue(client, second)
    assert response.status_code == 201
    assert [operation for operation, _ in registry.calls].count("issue_proof") == 2


def test_same_hash_after_revocation_is_new_proof(client: TestClient, registry: MockRegistryAdapter) -> None:
    """FR-03.06 AC-03: berkas identik dengan bukti REVOKED dicatat sebagai bukti baru."""
    _, headers = make_account()
    revoked_id = issue(client, headers, "offer-1").json()["proofId"]
    revoked = client.post(f"{URL}/{revoked_id}/revocations", headers=headers, json={"reasonCode": "OFFER_WITHDRAWN"})
    assert revoked.status_code == 201
    response = issue(client, headers, "offer-2")
    assert response.status_code == 201
    assert response.json()["proofId"] != revoked_id
    assert response.json()["lifecycleStatus"] == "ACTIVE"


def test_idempotent_replay_is_not_duplicate(client: TestClient, registry: MockRegistryAdapter) -> None:
    """SCN-15: kunci dan berkas sama mengembalikan hasil awal (bukan 409) karena idempotensi diperiksa lebih dulu."""
    issuer_id, headers = make_account()
    first = issue(client, headers, "offer-1")
    replay = issue(client, headers, "offer-1")
    assert first.status_code == replay.status_code == 201
    assert replay.json() == first.json()
    assert [operation for operation, _ in registry.calls] == ["issue_proof"]
    assert len(issuer_proofs(issuer_id)) == 1


def issue_operations(registry: MockRegistryAdapter) -> int:
    """Jumlah pengiriman transaksi issueProof yang dicatat mock."""
    return [operation for operation, _ in registry.calls].count("issue_proof")


def revoke(client: TestClient, headers: dict[str, str], proof_id: str) -> Response:
    """Mencabut bukti melalui API-06 dengan alasan enum tetap."""
    return client.post(f"{URL}/{proof_id}/revocations", headers=headers, json={"reasonCode": "OFFER_WITHDRAWN"})


def test_issue_receipt_timeout_on_chain_blocks_new_key(client: TestClient, registry: MockRegistryAdapter) -> None:
    """Receipt penerbitan terlambat tetapi bukti sudah ACTIVE di registry → kunci baru 409 tanpa transaksi kedua."""
    issuer_id, headers = make_account()
    registry.fail_next("issue_proof", registry_adapter.RegistryTransactionPending(), commit=True)
    assert_error(issue(client, headers, "offer-1"), 503, "REGISTRY_TRANSACTION_FAILED")
    assert [proof.status for proof in issuer_proofs(issuer_id)] == ["PENDING"]
    registry.calls.clear()
    assert_error(issue(client, headers, "offer-2"), 409, "DUPLICATE_ACTIVE_DOCUMENT")
    assert issue_operations(registry) == 0
    assert len(issuer_proofs(issuer_id)) == 1


def test_issue_receipt_unknown_stops_without_transaction(client: TestClient, registry: MockRegistryAdapter) -> None:
    """Penerbitan PENDING yang belum terlihat di registry belum pasti → 503 tanpa transaksi; kunci semula memulihkan."""
    issuer_id, headers = make_account()
    registry.fail_next("issue_proof", registry_adapter.RegistryTransactionPending())
    assert_error(issue(client, headers, "offer-1"), 503, "REGISTRY_TRANSACTION_FAILED")
    registry.calls.clear()
    assert_error(issue(client, headers, "offer-2"), 503, "REGISTRY_TRANSACTION_FAILED")
    assert issue_operations(registry) == 0
    assert issue(client, headers, "offer-1").status_code == 201
    assert len(issuer_proofs(issuer_id)) == 1


def test_revoke_receipt_timeout_allows_reissue(client: TestClient, registry: MockRegistryAdapter) -> None:
    """Receipt pencabutan terlambat tetapi registry sudah REVOKED → berkas sama boleh diterbitkan ulang (AC-03)."""
    _, headers = make_account()
    proof_id = issue(client, headers, "offer-1").json()["proofId"]
    registry.fail_next("revoke_proof", registry_adapter.RegistryTransactionPending(), commit=True)
    assert_error(revoke(client, headers, proof_id), 503, "REGISTRY_TRANSACTION_FAILED")
    response = issue(client, headers, "offer-2")
    assert response.status_code == 201
    assert response.json()["proofId"] != proof_id


def test_revoke_receipt_unknown_still_duplicate(client: TestClient, registry: MockRegistryAdapter) -> None:
    """Pencabutan tertunda yang belum terlihat di registry → bukti masih ACTIVE, penerbitan ulang tetap 409."""
    _, headers = make_account()
    proof_id = issue(client, headers, "offer-1").json()["proofId"]
    registry.fail_next("revoke_proof", registry_adapter.RegistryTransactionPending())
    assert_error(revoke(client, headers, proof_id), 503, "REGISTRY_TRANSACTION_FAILED")
    registry.calls.clear()
    assert_error(issue(client, headers, "offer-2"), 409, "DUPLICATE_ACTIVE_DOCUMENT")
    assert issue_operations(registry) == 0


def test_unfinished_duplicate_with_registry_down_stops(client: TestClient, registry: MockRegistryAdapter) -> None:
    """Status baris belum final tidak dapat dibaca karena registry mati → 503 REGISTRY_UNAVAILABLE tanpa baris baru."""
    issuer_id, headers = make_account()
    registry.fail_next("issue_proof", registry_adapter.RegistryTransactionPending(), commit=True)
    issue(client, headers, "offer-1")
    registry.set_unavailable(True)
    assert_error(issue(client, headers, "offer-2"), 503, "REGISTRY_UNAVAILABLE")
    assert len(issuer_proofs(issuer_id)) == 1


def test_definitive_failure_does_not_block_new_key(client: TestClient, registry: MockRegistryAdapter) -> None:
    """Penerbitan FAILED yang tidak ada di registry bukan duplikat; kunci baru menerbitkan bukti."""
    _, headers = make_account()
    registry.fail_next("issue_proof", registry_adapter.RegistryTransactionFailed())
    assert_error(issue(client, headers, "offer-1"), 503, "REGISTRY_TRANSACTION_FAILED")
    assert issue(client, headers, "offer-2").status_code == 201


def test_retry_old_key_rejected_when_other_key_active(client: TestClient, registry: MockRegistryAdapter) -> None:
    """Urutan A → B → A: retry kunci lama yang akan mengirim transaksi baru ditolak bila hash sama sudah ACTIVE."""
    issuer_id, headers = make_account()
    registry.fail_next("issue_proof", registry_adapter.RegistryUnavailable())
    assert_error(issue(client, headers, "offer-a"), 503, "REGISTRY_UNAVAILABLE")
    failed_id = issuer_proofs(issuer_id)[0].proof_id
    active_id = issue(client, headers, "offer-b").json()["proofId"]
    registry.calls.clear()
    assert_error(issue(client, headers, "offer-a"), 409, "DUPLICATE_ACTIVE_DOCUMENT")
    assert issue_operations(registry) == 0
    assert {proof.proof_id: proof.status for proof in issuer_proofs(issuer_id)} == {
        failed_id: "FAILED",
        active_id: "ACTIVE",
    }
    # Setelah bukti B dicabut, kunci A boleh melanjutkan proofId semula (AC-03).
    assert revoke(client, headers, active_id).status_code == 201
    response = issue(client, headers, "offer-a")
    assert response.status_code == 201
    assert response.json()["proofId"] == failed_id


def test_retry_failure_before_broadcast_keeps_pending(client: TestClient, registry: MockRegistryAdapter) -> None:
    """Retry yang gagal sebelum broadcast tidak menandai FAILED selama transaksi awal masih di antrean node."""
    issuer_id, headers = make_account()
    registry.fail_next("issue_proof", registry_adapter.RegistryTransactionPending())
    assert_error(issue(client, headers, "offer-1"), 503, "REGISTRY_TRANSACTION_FAILED")
    registry.fail_next("issue_proof", registry_adapter.RegistryUnavailable())
    assert_error(issue(client, headers, "offer-1"), 503, "REGISTRY_UNAVAILABLE")
    assert [proof.status for proof in issuer_proofs(issuer_id)] == ["PENDING"]
    registry.calls.clear()
    assert_error(issue(client, headers, "offer-2"), 503, "REGISTRY_TRANSACTION_FAILED")
    assert issue_operations(registry) == 0
    assert len(issuer_proofs(issuer_id)) == 1


def test_pending_issue_stores_broadcast_hash(client: TestClient, registry: MockRegistryAdapter) -> None:
    """Hash broadcast yang belum terkonfirmasi disimpan untuk deteksi transaksi hilang; bukti tetap tidak terlihat."""
    issuer_id, headers = make_account()
    tx_hash = "0x" + "cd" * 32
    registry.fail_next("issue_proof", registry_adapter.RegistryTransactionPending(tx_hash=tx_hash))
    assert_error(issue(client, headers, "offer-1"), 503, "REGISTRY_TRANSACTION_FAILED")
    (pending,) = issuer_proofs(issuer_id)
    assert (pending.status, pending.issue_tx_hash) == ("PENDING", tx_hash)
    assert client.get(URL, headers=headers).json()["items"] == []


@pytest.mark.parametrize("tracked_hash", [False, True])
def test_dropped_pending_issue_allows_new_key(
    client: TestClient, registry: MockRegistryAdapter, tracked_hash: bool
) -> None:
    """D-24: penerbitan PENDING yang pasti hilang dari node ditandai FAILED sehingga kunci baru dapat menerbitkan."""
    issuer_id, headers = make_account()
    pending_error = registry_adapter.RegistryTransactionPending(tx_hash="0x" + "ef" * 32 if tracked_hash else None)
    registry.fail_next("issue_proof", pending_error)
    assert_error(issue(client, headers, "offer-1"), 503, "REGISTRY_TRANSACTION_FAILED")
    old_id = issuer_proofs(issuer_id)[0].proof_id
    registry.drop_pending()
    registry.calls.clear()
    response = issue(client, headers, "offer-2")
    assert response.status_code == 201
    assert ("is_issue_failed_or_dropped", (old_id,) if not tracked_hash else ("0x" + "ef" * 32, old_id)) in [
        (name, args) for name, args in registry.calls
    ]
    statuses = {proof.proof_id: proof.status for proof in issuer_proofs(issuer_id)}
    assert statuses == {old_id: "FAILED", response.json()["proofId"]: "ACTIVE"}
    # Kunci lama tidak dapat menghidupkan duplikat setelah dokumen yang sama ACTIVE dengan kunci baru.
    assert_error(issue(client, headers, "offer-1"), 409, "DUPLICATE_ACTIVE_DOCUMENT")


def test_drop_check_outage_stops_without_transaction(client: TestClient, registry: MockRegistryAdapter) -> None:
    """Status antrean yang tidak dapat dibaca menghentikan penerbitan dengan 503 tanpa transaksi baru."""
    issuer_id, headers = make_account()
    registry.fail_next("issue_proof", registry_adapter.RegistryTransactionPending())
    issue(client, headers, "offer-1")
    registry.fail_next("is_issue_failed_or_dropped", registry_adapter.RegistryUnavailable())
    registry.calls.clear()
    assert_error(issue(client, headers, "offer-2"), 503, "REGISTRY_UNAVAILABLE")
    assert issue_operations(registry) == 0
    assert [proof.status for proof in issuer_proofs(issuer_id)] == ["PENDING"]


def test_drop_check_rereads_registry_before_failing(
    client: TestClient, registry: MockRegistryAdapter, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Race: retry kunci lama menambang bukti selagi pemeriksaan antrean berjalan → kunci baru 409, bukan FAILED."""
    issuer_id, headers = make_account()
    registry.fail_next("issue_proof", registry_adapter.RegistryTransactionPending())
    assert_error(issue(client, headers, "offer-1"), 503, "REGISTRY_TRANSACTION_FAILED")
    (pending,) = issuer_proofs(issuer_id)
    original_check = registry.is_issue_failed_or_dropped

    # Saat pemeriksaan antrean, transaksi retry kunci lama ditambang lalu antrean kosong (hasil pemeriksaan True).
    def mined_during_check(tx_hash: str | None, proof_id: str) -> bool:
        registry.drop_pending(proof_id)
        registry.issue_proof(proof_id, pending.document_hash, compute_issuer_ref(issuer_id))
        return original_check(tx_hash, proof_id)

    monkeypatch.setattr(registry, "is_issue_failed_or_dropped", mined_during_check)
    assert_error(issue(client, headers, "offer-2"), 409, "DUPLICATE_ACTIVE_DOCUMENT")
    assert [proof.status for proof in issuer_proofs(issuer_id)] == ["PENDING"]
    monkeypatch.setattr(registry, "is_issue_failed_or_dropped", original_check)
    recovered = issue(client, headers, "offer-1")
    assert recovered.status_code == 201
    assert recovered.json()["proofId"] == pending.proof_id


def test_active_mirror_missing_on_registry_blocks_new_key(client: TestClient, registry: MockRegistryAdapter) -> None:
    """Mirror ACTIVE dengan pencabutan tertunda tetapi registry tidak mengenalnya → 503 tanpa penerbitan baru."""
    issuer_id, headers = make_account()
    proof_id = issue(client, headers, "offer-1").json()["proofId"]
    registry.fail_next("revoke_proof", registry_adapter.RegistryTransactionPending())
    revoked = client.post(f"{URL}/{proof_id}/revocations", headers=headers, json={"reasonCode": "OFFER_WITHDRAWN"})
    assert revoked.status_code == 503
    registry.reset()
    assert_error(issue(client, headers, "offer-2"), 503, "REGISTRY_TRANSACTION_FAILED")
    assert issue_operations(registry) == 0
    assert [(proof.proof_id, proof.status) for proof in issuer_proofs(issuer_id)] == [(proof_id, "ACTIVE")]


def test_retry_recovers_when_revert_name_is_lost(client: TestClient, registry: MockRegistryAdapter) -> None:
    """Retry yang revert tanpa nama (replay receipt kehilangan ProofAlreadyExists) memulihkan receipt pertama."""
    issuer_id, headers = make_account()
    registry.fail_next("issue_proof", registry_adapter.RegistryTransactionPending())
    assert_error(issue(client, headers, "offer-1"), 503, "REGISTRY_TRANSACTION_FAILED")
    (pending,) = issuer_proofs(issuer_id)
    # Transaksi pertama ternyata ditambang di blok yang sama; kirim ulang revert tetapi namanya tidak terbaca.
    registry.fail_next("issue_proof", registry_adapter.RegistryTransactionFailed(), commit=True)
    response = issue(client, headers, "offer-1")
    assert response.status_code == 201
    assert response.json()["proofId"] == pending.proof_id
    assert [proof.status for proof in issuer_proofs(issuer_id)] == ["ACTIVE"]
