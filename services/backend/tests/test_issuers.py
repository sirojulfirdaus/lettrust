# Owner: Zan (PIC 3) | Status: COMPLETE | Ref: PRD FR-01.03–FR-01.07; SA §8.2, §10.5
"""Menguji Issuers API dan otorisasi HR melalui FastAPI dengan SQLite test."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from functools import partial

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import event, select

from app.core.db import get_engine, get_session_factory
from app.core.ids import compute_issuer_ref, new_user_id
from app.core.security import create_access_token
from app.modules.auth.models import User
from app.modules.auth.schemas import Role
from app.modules.issuers.dependencies import authorized_hr
from app.modules.issuers.models import Issuer, IssuerMembership
from app.modules.issuers.schemas import RegisterIssuerRequest
from app.modules.issuers.service import register_issuer

ISSUERS_PATH = "/api/v1/issuers"


@pytest.fixture
def make_actor(client: TestClient) -> Callable[[Role], User]:
    """Menyimpan akun sintetis tanpa memakai kredensial seed untuk tes JWT."""

    def create_actor(role: Role) -> User:
        """Membuat identitas uji dengan role yang dibaca dari database."""
        user_id = new_user_id()
        user = User(
            id=user_id,
            email=f"{user_id.lower()}@lettrust.test",
            display_name="Akun Demo Issuers",
            password_hash="tidak-dipakai-oleh-tes-jwt",
            role=role,
            created_at=datetime.now(UTC),
        )
        with get_session_factory().begin() as db:
            db.add(user)
        return user

    return create_actor


def _headers(user: User) -> dict[str, str]:
    """Membuat header untuk token sintetis bertanda tangan sah."""
    token, _ = create_access_token(user.id, user.role)
    return {"Authorization": f"Bearer {token}"}


def _register(client: TestClient, user: User, registration_number: str) -> Response:
    """Mendaftarkan perusahaan sintetis melalui API-01."""
    return client.post(
        ISSUERS_PATH,
        headers=_headers(user),
        json={
            "companyName": "PT Penerbit Simulasi",
            "registrationNumber": registration_number,
            "contactEmail": "kontak@penerbit.test",
        },
    )


def _issuer_id(client: TestClient, user: User, registration_number: str) -> str:
    """Menyiapkan penerbit PENDING melalui endpoint yang sebenarnya."""
    response = _register(client, user, registration_number)
    assert response.status_code == 201
    return response.json()["issuerId"]


def _verify(client: TestClient, user: User, issuer_id: str, decision: str) -> Response:
    """Mengajukan keputusan verifikasi melalui API-02."""
    return client.patch(
        f"{ISSUERS_PATH}/{issuer_id}/verification",
        headers=_headers(user),
        json={"decision": decision, "evidenceRef": "EVD-DEMO-01", "reviewNote": "Catatan peninjauan sintetis."},
    )


def _authorize(client: TestClient, user: User, issuer_id: str, hr_id: str) -> Response:
    """Mengajukan otorisasi HR melalui API-03."""
    return client.post(
        f"{ISSUERS_PATH}/{issuer_id}/hr-authorizations",
        headers=_headers(user),
        json={"hrId": hr_id},
    )


def _assert_error(response: Response, status: int, error_code: str) -> None:
    """Memeriksa status HTTP dan kode error tanpa bergantung pada pesan tampilan."""
    assert response.status_code == status
    assert response.json()["error"]["code"] == error_code


def test_register_issuer_creates_pending_membership(client: TestClient, make_actor: Callable[[Role], User]) -> None:
    """Memastikan registrasi menyimpan penerbit dan membuat afiliasi tanpa hak penerbitan."""
    hr = make_actor(Role.HR)
    registration = _register(client, hr, "REG-ISS-TEST-01")
    assert registration.status_code == 201
    issuer_id = registration.json()["issuerId"]
    assert registration.json() == {"issuerId": issuer_id, "issuerStatus": "PENDING"}

    profile = client.get("/api/v1/auth/me", headers=_headers(hr))
    assert profile.status_code == 200
    assert profile.json()["membership"] == {
        "issuerId": issuer_id,
        "companyName": "PT Penerbit Simulasi",
        "issuerStatus": "PENDING",
        "authorizationStatus": "NOT_AUTHORIZED",
        "reviewNote": None,
    }
    with get_session_factory()() as db:
        issuer = db.get_one(Issuer, issuer_id)
        assert issuer.issuer_ref == compute_issuer_ref(issuer_id)
        assert issuer.registered_by == hr.id

    _assert_error(_register(client, hr, "REG-ISS-TEST-02"), 409, "ACCOUNT_ALREADY_AFFILIATED")
    _assert_error(_register(client, make_actor(Role.ADMIN), "REG-ISS-TEST-03"), 403, "FORBIDDEN_OPERATION")


def test_register_issuer_rejects_invalid_fields(client: TestClient, make_actor: Callable[[Role], User]) -> None:
    """Memastikan API-01 mengembalikan rincian validasi per field dalam envelope 400."""
    response = client.post(
        ISSUERS_PATH,
        headers=_headers(make_actor(Role.HR)),
        json={"companyName": "", "registrationNumber": "?", "contactEmail": "bukan-email"},
    )
    _assert_error(response, 400, "VALIDATION_ERROR")
    assert {detail["field"] for detail in response.json()["error"]["details"]} == {
        "companyName",
        "registrationNumber",
        "contactEmail",
    }


def test_register_issuer_rejects_blank_name_before_storing_company(
    client: TestClient, make_actor: Callable[[Role], User]
) -> None:
    """Memastikan nama yang hanya berisi spasi ditolak dan registrasi bisa diulang setelah diperbaiki."""
    hr = make_actor(Role.HR)
    payload = {
        "companyName": "   ",
        "registrationNumber": "REG-BLANK-COMPANY",
        "contactEmail": "kontak@penerbit.test",
    }
    response = client.post(ISSUERS_PATH, headers=_headers(hr), json=payload)
    _assert_error(response, 400, "VALIDATION_ERROR")
    assert response.json()["error"]["details"][0]["field"] == "companyName"
    assert client.get("/api/v1/auth/me", headers=_headers(hr)).json()["membership"] is None

    payload["companyName"] = "  PT Penerbit Demo  "
    retry = client.post(ISSUERS_PATH, headers=_headers(hr), json=payload)
    assert retry.status_code == 201
    assert client.get("/api/v1/auth/me", headers=_headers(hr)).json()["membership"]["companyName"] == "PT Penerbit Demo"


def test_verification_rejects_blank_evidence_before_committing_decision(
    client: TestClient, make_actor: Callable[[Role], User]
) -> None:
    """Memastikan rujukan kosong tidak mengunci keputusan final dan rujukan sah disimpan tanpa spasi tepi."""
    hr = make_actor(Role.HR)
    admin = make_actor(Role.ADMIN)
    issuer_id = _issuer_id(client, hr, "REG-BLANK-EVIDENCE")
    details_path = f"{ISSUERS_PATH}/{issuer_id}"
    headers = _headers(admin)
    payload = {"decision": "VERIFIED", "evidenceRef": "   "}

    response = client.patch(f"{details_path}/verification", headers=headers, json=payload)
    _assert_error(response, 400, "VALIDATION_ERROR")
    assert response.json()["error"]["details"][0]["field"] == "evidenceRef"
    pending = client.get(details_path, headers=headers).json()
    assert pending["issuerStatus"] == "PENDING"
    assert pending["evidenceRef"] is None
    assert pending["reviewedAt"] is None

    payload["evidenceRef"] = "  EVD-DEMO-VALID  "
    assert client.patch(f"{details_path}/verification", headers=headers, json=payload).status_code == 200
    assert client.get(details_path, headers=headers).json()["evidenceRef"] == "EVD-DEMO-VALID"


@pytest.mark.parametrize("same_hr", [True, False], ids=["satu-hr", "satu-nomor"])
def test_concurrent_registration_keeps_one_issuer(
    client: TestClient, make_actor: Callable[[Role], User], same_hr: bool
) -> None:
    """Memastikan konflik afiliasi atau nomor registrasi paralel tidak meninggalkan penerbit yatim."""
    first_hr = make_actor(Role.HR)
    second_hr = first_hr if same_hr else make_actor(Role.HR)
    suffix = "HR" if same_hr else "NUMBER"
    first_number = f"REG-PARALLEL-{suffix}-1"
    second_number = f"REG-PARALLEL-{suffix}-2" if same_hr else first_number

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(_register, client, first_hr, first_number)
        second = pool.submit(_register, client, second_hr, second_number)
        responses = [first.result(), second.result()]

    assert sorted(r.status_code for r in responses) == [201, 409]
    conflict = next(r for r in responses if r.status_code == 409)
    code = "ACCOUNT_ALREADY_AFFILIATED" if same_hr else "REGISTRATION_NUMBER_ALREADY_EXISTS"
    _assert_error(conflict, 409, code)
    with get_session_factory()() as db:
        issuers = db.scalars(select(Issuer.id).where(Issuer.registered_by.in_([first_hr.id, second_hr.id]))).all()
        memberships = db.scalars(
            select(IssuerMembership.issuer_id).where(IssuerMembership.user_id.in_([first_hr.id, second_hr.id]))
        ).all()
    assert len(issuers) == 1
    assert memberships == issuers


def test_admin_lists_issuers_by_status_and_page(client: TestClient, make_actor: Callable[[Role], User]) -> None:
    """Memastikan filter dan total diterapkan sebelum limit/offset dan hanya Admin dapat melihat daftar."""
    admin = make_actor(Role.ADMIN)
    first = make_actor(Role.HR)
    second = make_actor(Role.HR)
    first_id = _issuer_id(client, first, "REG-LIST-ISSUERS-01")
    second_id = _issuer_id(client, second, "REG-LIST-ISSUERS-02")
    assert _verify(client, admin, first_id, "REJECTED").status_code == 200
    assert _verify(client, admin, second_id, "REJECTED").status_code == 200

    headers = _headers(admin)
    listing = client.get(ISSUERS_PATH, params={"status": "REJECTED", "limit": 100}, headers=headers)
    assert listing.status_code == 200
    items = listing.json()["items"]
    items_by_id = {item["issuerId"]: item for item in items}
    assert {first_id, second_id} <= items_by_id.keys()
    assert all(item["issuerStatus"] == "REJECTED" for item in items)
    assert items_by_id[second_id]["memberCount"] == 1
    offset = next(i for i, item in enumerate(items) if item["issuerId"] == second_id)
    page = client.get(ISSUERS_PATH, params={"status": "REJECTED", "limit": 1, "offset": offset}, headers=headers)
    assert page.status_code == 200
    assert page.json() == {"items": [items_by_id[second_id]], "total": listing.json()["total"]}
    _assert_error(client.get(ISSUERS_PATH, headers=_headers(first)), 403, "FORBIDDEN_OPERATION")


@pytest.mark.parametrize("offset", [1000, 2**63], ids=["setelah-halaman-terakhir", "di-luar-rentang-sqlite"])
def test_issuer_list_preserves_total_for_empty_page(
    client: TestClient, make_actor: Callable[[Role], User], offset: int
) -> None:
    """Memastikan offset di luar daftar memberi halaman kosong dengan total sesuai filter."""
    admin = make_actor(Role.ADMIN)
    hr = make_actor(Role.HR)
    _issuer_id(client, hr, f"REG-PAGE-BOUNDS-{offset}")
    headers = _headers(admin)
    first = client.get(ISSUERS_PATH, params={"status": "PENDING"}, headers=headers)
    assert first.status_code == 200
    total = first.json()["total"]
    assert total >= 1

    empty = client.get(ISSUERS_PATH, params={"status": "PENDING", "offset": offset}, headers=headers)
    assert empty.status_code == 200
    assert empty.json() == {"items": [], "total": total}


def test_issuer_list_remains_consistent_when_registration_commits_during_read(
    client: TestClient, make_actor: Callable[[Role], User]
) -> None:
    """Memastikan total dan isi halaman berasal dari snapshot yang sama saat registrasi paralel."""
    admin = make_actor(Role.ADMIN)
    hr = make_actor(Role.HR)
    headers = _headers(admin)
    params = {"status": "PENDING", "limit": 100}
    first = client.get(ISSUERS_PATH, params=params, headers=headers)
    assert first.status_code == 200
    prior_total = first.json()["total"]
    engine = get_engine()
    registration_done = False

    def register_during_read(
        _conn: object,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: bool,
    ) -> None:
        """Menyisipkan commit registrasi dari sesi lain saat query penerbit pertama sudah berjalan."""
        nonlocal registration_done
        if registration_done or "FROM issuers" not in statement or not statement.lstrip().startswith("SELECT"):
            return
        registration_done = True
        with get_session_factory()() as writer:
            register_issuer(
                writer,
                writer.get_one(User, hr.id),
                RegisterIssuerRequest(
                    company_name="PT Penerbit Paralel",
                    registration_number="REG-LIST-SNAPSHOT",
                    contact_email="paralel@penerbit.test",
                ),
            )

    event.listen(engine, "after_cursor_execute", register_during_read)
    try:
        listing = client.get(ISSUERS_PATH, params=params, headers=headers)
    finally:
        event.remove(engine, "after_cursor_execute", register_during_read)

    assert registration_done
    assert listing.status_code == 200
    body = listing.json()
    assert len(body["items"]) == min(body["total"], 100)
    latest = client.get(ISSUERS_PATH, params=params, headers=headers)
    assert latest.json()["total"] == prior_total + 1


def test_issuer_detail_masks_other_member_email_and_returns_404_to_outsiders(
    client: TestClient, make_actor: Callable[[Role], User]
) -> None:
    """Memastikan S-05 menjaga privasi email dan tidak mengungkap penerbit ke HR luar."""
    admin = make_actor(Role.ADMIN)
    owner = make_actor(Role.HR)
    member = make_actor(Role.HR)
    outsider = make_actor(Role.HR)
    issuer_id = _issuer_id(client, owner, "REG-ISSUER-DETAIL")
    with get_session_factory().begin() as db:
        db.add(
            IssuerMembership(
                user_id=member.id,
                issuer_id=issuer_id,
                authorization_status="NOT_AUTHORIZED",
                created_at=datetime.now(UTC),
            )
        )

    path = f"{ISSUERS_PATH}/{issuer_id}"
    admin_view = client.get(path, headers=_headers(admin))
    assert admin_view.status_code == 200
    assert {m["hrId"]: m["email"] for m in admin_view.json()["members"]} == {
        owner.id: owner.email,
        member.id: member.email,
    }
    member_view = client.get(path, headers=_headers(member))
    assert member_view.status_code == 200
    assert {m["hrId"]: m["email"] for m in member_view.json()["members"]} == {owner.id: None, member.id: member.email}
    _assert_error(client.get(path, headers=_headers(outsider)), 404, "ISSUER_NOT_FOUND")
    _assert_error(client.get(f"{ISSUERS_PATH}/ISS-00000000", headers=_headers(admin)), 404, "ISSUER_NOT_FOUND")


def test_verification_accepts_one_final_decision_under_concurrent_requests(
    client: TestClient, make_actor: Callable[[Role], User]
) -> None:
    """Memastikan dua keputusan serentak tidak menimpa pemenang, dan hanya Admin boleh memutuskan."""
    hr = make_actor(Role.HR)
    admin = make_actor(Role.ADMIN)
    issuer_id = _issuer_id(client, hr, "REG-VERIFY-SINGLE")
    _assert_error(_verify(client, hr, issuer_id, "VERIFIED"), 403, "FORBIDDEN_OPERATION")
    _assert_error(_verify(client, admin, "ISS-00000000", "VERIFIED"), 404, "ISSUER_NOT_FOUND")

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(partial(_verify, client, admin, issuer_id), ["VERIFIED", "REJECTED"]))
    assert sorted(r.status_code for r in responses) == [200, 409]
    decision = next(r for r in responses if r.status_code == 200).json()
    assert decision["reviewedBy"] == admin.id
    assert decision["reviewedAt"].endswith("Z")
    _assert_error(next(r for r in responses if r.status_code == 409), 409, "ISSUER_DECISION_ALREADY_MADE")

    detail = client.get(f"{ISSUERS_PATH}/{issuer_id}", headers=_headers(admin)).json()
    assert detail["issuerStatus"] == decision["issuerStatus"]
    assert detail["reviewedBy"] == decision["reviewedBy"]
    assert detail["reviewedAt"] == decision["reviewedAt"]
    assert detail["evidenceRef"] == "EVD-DEMO-01"
    assert detail["reviewNote"] == "Catatan peninjauan sintetis."


def test_authorization_records_admin_and_allows_verified_hr(
    client: TestClient, make_actor: Callable[[Role], User]
) -> None:
    """Memastikan pemeriksaan status dan role mendahului otorisasi dan satu pemberian hak dicatat."""
    hr = make_actor(Role.HR)
    admin = make_actor(Role.ADMIN)
    issuer_id = _issuer_id(client, hr, "REG-AUTHORIZE-HR")
    _assert_error(_authorize(client, hr, issuer_id, hr.id), 403, "FORBIDDEN_OPERATION")
    _assert_error(_authorize(client, admin, "ISS-00000000", hr.id), 404, "ISSUER_NOT_FOUND")
    _assert_error(_authorize(client, admin, issuer_id, hr.id), 409, "ISSUER_NOT_VERIFIED")
    rejected_id = _issuer_id(client, make_actor(Role.HR), "REG-AUTHORIZE-REJECTED")
    assert _verify(client, admin, rejected_id, "REJECTED").status_code == 200
    _assert_error(_authorize(client, admin, rejected_id, hr.id), 409, "ISSUER_NOT_VERIFIED")
    assert _verify(client, admin, issuer_id, "VERIFIED").status_code == 200
    _assert_error(client.get("/api/v1/proofs", headers=_headers(hr)), 403, "FORBIDDEN_OPERATION")

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(partial(_authorize, client, admin, issuer_id), [hr.id, hr.id]))
    assert sorted(r.status_code for r in responses) == [201, 409]
    assert next(r for r in responses if r.status_code == 201).json() == {
        "issuerId": issuer_id,
        "hrId": hr.id,
        "authorizationStatus": "AUTHORIZED",
    }
    _assert_error(next(r for r in responses if r.status_code == 409), 409, "HR_ALREADY_AUTHORIZED")

    with get_session_factory()() as db:
        membership = db.get_one(IssuerMembership, hr.id)
        assert membership.authorized_by == admin.id
        assert membership.authorized_at is not None
        context = authorized_hr(hr, db)
        assert context.issuer_id == issuer_id
        assert context.issuer_ref == compute_issuer_ref(issuer_id)


def test_authorization_rejects_hr_from_another_issuer(client: TestClient, make_actor: Callable[[Role], User]) -> None:
    """Memastikan API-03 menolak HR lintas penerbit tanpa mengubah hak target."""
    admin = make_actor(Role.ADMIN)
    owner = make_actor(Role.HR)
    other_hr = make_actor(Role.HR)
    issuer_id = _issuer_id(client, owner, "REG-AUTHORIZE-SCOPE")
    other_issuer_id = _issuer_id(client, other_hr, "REG-AUTHORIZE-OTHER")
    assert _verify(client, admin, issuer_id, "VERIFIED").status_code == 200
    assert _verify(client, admin, other_issuer_id, "VERIFIED").status_code == 200

    _assert_error(_authorize(client, admin, issuer_id, other_hr.id), 422, "HR_NOT_AFFILIATED")
    with get_session_factory()() as db:
        member = db.get_one(IssuerMembership, other_hr.id)
        assert member.issuer_id == other_issuer_id
        assert member.authorization_status == "NOT_AUTHORIZED"
        assert member.authorized_by is None
        assert member.authorized_at is None


@pytest.mark.parametrize("issuer_status", ["PENDING", "REJECTED", "VERIFIED", "UNAFFILIATED", "ADMIN"])
def test_proof_operations_deny_hr_without_required_issuer_status(
    client: TestClient, make_actor: Callable[[Role], User], issuer_status: str
) -> None:
    """Memastikan guard bersama menolak penerbitan dan pencabutan tanpa otorisasi yang sah."""
    user = make_actor(Role.ADMIN if issuer_status == "ADMIN" else Role.HR)
    if issuer_status not in {"UNAFFILIATED", "ADMIN"}:
        issuer_id = _issuer_id(client, user, f"REG-PROOF-DENIED-{issuer_status}")
        if issuer_status != "PENDING":
            admin = make_actor(Role.ADMIN)
            assert _verify(client, admin, issuer_id, issuer_status).status_code == 200
        if issuer_status in {"PENDING", "REJECTED"}:
            # Buat data uji inkonsisten agar tes memastikan status penerbit tetap diperiksa.
            with get_session_factory().begin() as db:
                db.get_one(IssuerMembership, user.id).authorization_status = "AUTHORIZED"

    headers = _headers(user)
    issue = client.post(
        "/api/v1/proofs",
        headers=headers,
        files={"file": ("offer.pdf", b"%PDF-1.4\n", "application/pdf")},
    )
    _assert_error(issue, 403, "FORBIDDEN_OPERATION")
    proof_id = "0x" + "ab" * 32
    revoke = client.post(
        f"/api/v1/proofs/{proof_id}/revocations",
        headers=headers,
        json={"reasonCode": "OFFER_WITHDRAWN"},
    )
    _assert_error(revoke, 403, "FORBIDDEN_OPERATION")
