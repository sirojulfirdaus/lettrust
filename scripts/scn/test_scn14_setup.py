# Owner: Zan (PIC 3) | Status: COMPLETE | Ref: T3-06, PRD SCN-14, FR-03.05, FR-03.06
"""Setup SCN-14 dapat diulang: pakai ulang bukti ACTIVE, dan kunci setup stabil memulihkan receipt yang timeout."""

import hashlib
import json

import httpx
import pytest

from common import ScenarioError
from scn14_authz_negative import PROOFS, find_or_issue_active, setup_idempotency_key

PDF = b"%PDF-1.4\n%fixture-sintetis\n"
DIGEST = hashlib.sha256(PDF).hexdigest()
ISSUER = "ISS-SINTETIS01"
TRANSACTION = {"hash": "0x" + "ab" * 32, "blockNumber": 7}


class FakeApi:
    """API-04/API-05/S-06 palsu: daftar ACTIVE berhalaman, detail, dan penerbitan berbasis Idempotency-Key."""

    # Menyimpan daftar bukti per halaman dan antrean respons POST yang sudah ditentukan tes.
    def __init__(self, pages: list[list[dict]], posts: list[tuple[int, dict]] | None = None) -> None:
        self.pages = pages
        self.posts = list(posts or [])
        self.post_keys: list[str] = []

    # Melayani satu request sesuai path dan method.
    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == PROOFS:
            offset = int(request.url.params["offset"])
            index = 0 if offset == 0 else 1
            items = self.pages[index] if index < len(self.pages) else []
            total = sum(len(page) for page in self.pages)
            return httpx.Response(200, json={"items": [{"proofId": p["proofId"]} for p in items], "total": total})
        if request.method == "GET":
            proof_id = request.url.path.rsplit("/", 1)[-1]
            detail = next(p for page in self.pages for p in page if p["proofId"] == proof_id)
            return httpx.Response(200, json=detail)
        self.post_keys.append(request.headers["Idempotency-Key"])
        status, body = self.posts.pop(0)
        return httpx.Response(status, json=body)


# Membuat client httpx yang diarahkan ke FakeApi.
def client_for(api: FakeApi) -> httpx.Client:
    return httpx.Client(base_url="http://127.0.0.1:8000", transport=httpx.MockTransport(api.handler))


# Membuat detail bukti sintetis seperti respons API-05.
def detail(proof_id: str, document_hash: str, status: str = "ACTIVE") -> dict:
    return {
        "proofId": proof_id,
        "issuerId": ISSUER,
        "documentHash": document_hash,
        "lifecycleStatus": status,
        "issueTransaction": TRANSACTION,
    }


# Bukti ACTIVE yang cocok di halaman kedua dipakai ulang tanpa penerbitan baru.
def test_reuses_active_proof_on_second_page() -> None:
    first_page = [detail(f"0x{i:064x}", "cd" * 32) for i in range(100)]
    api = FakeApi([first_page, [detail("0x" + "ef" * 32, DIGEST)]])
    with client_for(api) as client:
        issued = find_or_issue_active(client, "token-sintetis", PDF, ISSUER)
    assert issued["proofId"] == "0x" + "ef" * 32
    assert issued["transaction"] == TRANSACTION
    assert api.post_keys == []


# Receipt setup timeout (503) lalu run berikutnya memakai kunci yang sama sehingga backend memulihkan bukti sama.
def test_timed_out_setup_retries_with_same_key() -> None:
    api = FakeApi(
        [[]],
        posts=[
            (503, {"error": {"code": "REGISTRY_TRANSACTION_FAILED"}}),
            (201, {**detail("0x" + "11" * 32, DIGEST), "transaction": TRANSACTION}),
        ],
    )
    with client_for(api) as client:
        with pytest.raises(ScenarioError):
            find_or_issue_active(client, "token-sintetis", PDF, ISSUER)
        issued = find_or_issue_active(client, "token-sintetis", PDF, ISSUER)
    assert issued["lifecycleStatus"] == "ACTIVE"
    assert api.post_keys == [setup_idempotency_key(ISSUER, DIGEST)] * 2


# Kunci stabil milik bukti yang sudah dicabut → satu penerbitan baru dengan kunci lain.
def test_revoked_replay_issues_once_with_new_key() -> None:
    api = FakeApi(
        [[]],
        posts=[
            (201, {**detail("0x" + "22" * 32, DIGEST, "REVOKED"), "transaction": TRANSACTION}),
            (201, {**detail("0x" + "33" * 32, DIGEST), "transaction": TRANSACTION}),
        ],
    )
    with client_for(api) as client:
        issued = find_or_issue_active(client, "token-sintetis", PDF, ISSUER)
    assert issued["proofId"] == "0x" + "33" * 32
    assert api.post_keys[0] == setup_idempotency_key(ISSUER, DIGEST)
    assert api.post_keys[1] != api.post_keys[0]
    assert json.dumps(issued).count("REVOKED") == 0
