# Owner: Zan (PIC 3) | Status: COMPLETE | Ref: T3-06, PRD SCN-14, FR-03.05, FR-03.06
"""Setup SCN-14 dapat diulang: pakai ulang bukti ACTIVE, kunci setup stabil memulihkan receipt yang timeout, dan bukti
setup yang sudah dicabut diganti dengan generasi kunci stabil berikutnya."""

import hashlib

import httpx
import pytest

from common import ScenarioError
from scn14_authz_negative import PROOFS, find_or_issue_active, setup_idempotency_key

PDF = b"%PDF-1.4\n%fixture-sintetis\n"
DIGEST = hashlib.sha256(PDF).hexdigest()
ISSUER = "ISS-SINTETIS01"
TRANSACTION = {"hash": "0x" + "ab" * 32, "blockNumber": 7}


class FakeApi:
    """Backend palsu yang mengikuti API-04/API-05/S-06: replay kunci mengembalikan hasil penerbitan historis (ACTIVE)
    walau bukti sudah dicabut; status terkini hanya terlihat dari detail API-05 dan daftar ACTIVE."""

    # `status` = status terkini per proofId; `keys` = proofId milik tiap Idempotency-Key; `timeouts` = kunci yang
    # sekali mendapat 503 (receipt timeout) sebelum tercatat.
    def __init__(self, status: dict[str, str] | None = None, keys: dict[str, str] | None = None) -> None:
        self.status = dict(status or {})
        self.keys = dict(keys or {})
        self.timeouts: set[str] = set()
        self.post_keys: list[str] = []
        self.counter = 0

    # Daftar ACTIVE berhalaman (100 per halaman) diurutkan seperti S-06.
    def _list(self, offset: int) -> httpx.Response:
        active = [proof_id for proof_id, status in self.status.items() if status == "ACTIVE"]
        page = active[offset : offset + 100]
        return httpx.Response(200, json={"items": [{"proofId": p} for p in page], "total": len(active)})

    # Detail API-05: status terkini dari registry; baris PENDING tidak terlihat (404) seperti mirror nyata.
    def _detail(self, proof_id: str) -> httpx.Response:
        if self.status[proof_id] == "PENDING":
            return httpx.Response(404, json={"error": {"code": "PROOF_NOT_FOUND"}})
        document_hash = "cd" * 32 if proof_id.startswith("0xother") else DIGEST
        return httpx.Response(
            200,
            json={
                "proofId": proof_id,
                "issuerId": ISSUER,
                "documentHash": document_hash,
                "lifecycleStatus": self.status[proof_id],
                "issueTransaction": TRANSACTION,
            },
        )

    # API-04: kunci baru menerbitkan ACTIVE; kunci lama me-replay hasil historis ACTIVE apa pun status terkininya;
    # kunci yang receipt-nya timeout meninggalkan baris PENDING yang dipulihkan menjadi ACTIVE saat kunci diulang.
    def _issue(self, key: str) -> httpx.Response:
        self.post_keys.append(key)
        if key in self.timeouts:
            self.timeouts.discard(key)
            self.counter += 1
            self.keys[key] = f"0x{self.counter:064x}"
            self.status[self.keys[key]] = "PENDING"
            return httpx.Response(503, json={"error": {"code": "REGISTRY_TRANSACTION_FAILED"}})
        if key in self.keys and self.status[self.keys[key]] == "PENDING":
            self.status[self.keys[key]] = "ACTIVE"
        if key not in self.keys:
            self.counter += 1
            self.keys[key] = f"0x{self.counter:064x}"
            self.status[self.keys[key]] = "ACTIVE"
        proof_id = self.keys[key]
        return httpx.Response(201, json={"proofId": proof_id, "lifecycleStatus": "ACTIVE", "transaction": TRANSACTION})

    # Melayani satu request sesuai path dan method.
    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return self._issue(request.headers["Idempotency-Key"])
        if request.url.path == PROOFS:
            return self._list(int(request.url.params["offset"]))
        return self._detail(request.url.path.rsplit("/", 1)[-1])


# Membuat client httpx yang diarahkan ke FakeApi.
def client_for(api: FakeApi) -> httpx.Client:
    return httpx.Client(base_url="http://127.0.0.1:8000", transport=httpx.MockTransport(api.handler))


# Bukti ACTIVE yang cocok di halaman kedua dipakai ulang tanpa penerbitan baru.
def test_reuses_active_proof_on_second_page() -> None:
    status = {f"0xother{i:058x}": "ACTIVE" for i in range(100)}
    status["0x" + "ef" * 32] = "ACTIVE"
    api = FakeApi(status)
    with client_for(api) as client:
        issued = find_or_issue_active(client, "token-sintetis", PDF, ISSUER)
    assert issued["proofId"] == "0x" + "ef" * 32
    assert issued["transaction"] == TRANSACTION
    assert api.post_keys == []


# Receipt setup timeout (503) lalu run berikutnya memakai kunci yang sama sehingga backend memulihkan bukti sama.
def test_timed_out_setup_retries_with_same_key() -> None:
    api = FakeApi()
    first_key = setup_idempotency_key(ISSUER, DIGEST)
    api.timeouts.add(first_key)
    with client_for(api) as client:
        with pytest.raises(ScenarioError):
            find_or_issue_active(client, "token-sintetis", PDF, ISSUER)
        # Mirror masih PENDING: bukti belum muncul di daftar ACTIVE, jadi run berikutnya me-replay kunci yang sama.
        pending_id = api.keys[first_key]
        assert api.status[pending_id] == "PENDING"
        issued = find_or_issue_active(client, "token-sintetis", PDF, ISSUER)
    assert issued["proofId"] == pending_id
    assert issued["lifecycleStatus"] == "ACTIVE"
    assert api.post_keys == [first_key, first_key]


# Bukti setup historis sudah dicabut: replay API-04 tetap 201 ACTIVE (historis), tetapi API-05 menunjukkan REVOKED,
# sehingga setup memakai generasi kunci stabil berikutnya dan tidak memakai bukti yang dicabut.
def test_revoked_setup_proof_is_replaced_with_next_stable_key() -> None:
    first_key = setup_idempotency_key(ISSUER, DIGEST)
    api = FakeApi(status={"0x" + "22" * 32: "REVOKED"}, keys={first_key: "0x" + "22" * 32})
    with client_for(api) as client:
        issued = find_or_issue_active(client, "token-sintetis", PDF, ISSUER)
        again = find_or_issue_active(client, "token-sintetis", PDF, ISSUER)
    second_key = setup_idempotency_key(ISSUER, DIGEST, 1)
    assert issued["lifecycleStatus"] == "ACTIVE"
    assert issued["proofId"] != "0x" + "22" * 32
    assert api.post_keys == [first_key, second_key]
    assert second_key != first_key
    # Run berikutnya memakai ulang bukti pengganti dari daftar ACTIVE tanpa penerbitan baru.
    assert again["proofId"] == issued["proofId"]


# Penerbitan pengganti yang timeout dipulihkan oleh run berikutnya dengan generasi kunci yang sama.
def test_timed_out_replacement_is_recovered_with_same_generation_key() -> None:
    first_key = setup_idempotency_key(ISSUER, DIGEST)
    second_key = setup_idempotency_key(ISSUER, DIGEST, 1)
    api = FakeApi(status={"0x" + "22" * 32: "REVOKED"}, keys={first_key: "0x" + "22" * 32})
    api.timeouts.add(second_key)
    with client_for(api) as client:
        with pytest.raises(ScenarioError):
            find_or_issue_active(client, "token-sintetis", PDF, ISSUER)
        replacement = api.keys[second_key]
        assert api.status[replacement] == "PENDING"
        recovered = find_or_issue_active(client, "token-sintetis", PDF, ISSUER)
    assert recovered["proofId"] == replacement
    assert api.post_keys == [first_key, second_key, first_key, second_key]
    assert len(set(api.keys.values())) == 2


# Semua generasi dipakai bukti yang dicabut → setup berhenti dengan pesan jelas, tanpa loop tak terbatas.
def test_exhausted_generations_stop_setup() -> None:
    keys = {setup_idempotency_key(ISSUER, DIGEST, g): f"0x{g + 100:064x}" for g in range(20)}
    api = FakeApi(status={proof_id: "REVOKED" for proof_id in keys.values()}, keys=keys)
    with client_for(api) as client:
        with pytest.raises(ScenarioError, match="generasi"):
            find_or_issue_active(client, "token-sintetis", PDF, ISSUER)
    assert len(api.post_keys) == 20
