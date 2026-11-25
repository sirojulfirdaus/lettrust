# Owner: Zan (PIC 3) | Status: COMPLETE | Ref: PRD FR-01.01, FR-01.02, FR-01.04; SA §8 dan §10.5
"""Menguji registrasi, sesi JWT, dan otorisasi dengan SQLite test."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import get_session_factory
from app.core.ids import compute_issuer_ref, new_issuer_id, new_user_id
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.auth.models import User
from app.modules.auth.schemas import Role
from app.modules.issuers.models import Issuer, IssuerMembership

AUTH_PATH = "/api/v1/auth"
TEST_PASSWORD = "Auth#Demo2026"


# Menyiapkan akun sintetis tanpa perlu menjalankan CLI seed dari T3-01.
@pytest.fixture
def make_user(client: TestClient) -> Callable[[Role], User]:
    # Menyimpan akun dengan role dan hash password yang dapat dipakai login.
    def create_user(role: Role) -> User:
        user_id = new_user_id()
        user = User(
            id=user_id,
            email=f"{user_id.lower()}@lettrust.test",
            display_name="Akun Demo Auth",
            password_hash=hash_password(TEST_PASSWORD),
            role=role,
            created_at=datetime.now(UTC),
        )
        with get_session_factory().begin() as db:
            db.add(user)
        return user

    return create_user


# Memastikan registrasi menormalkan email, menyimpan hash, dan membuat HR tanpa afiliasi.
def test_register_creates_unaffiliated_hr(client: TestClient) -> None:
    response = client.post(
        f"{AUTH_PATH}/register",
        json={"displayName": "HR Baru Demo", "email": "NEW.HR@LETTRUST.TEST", "password": TEST_PASSWORD},
    )
    assert response.status_code == 201
    body = response.json()
    assert body == {
        "userId": body["userId"],
        "email": "new.hr@lettrust.test",
        "displayName": "HR Baru Demo",
        "role": "HR",
    }

    with get_session_factory()() as db:
        user = db.get_one(User, body["userId"])
        assert verify_password(TEST_PASSWORD, user.password_hash)
        assert db.get(IssuerMembership, user.id) is None


# Memastikan client tidak dapat menentukan role untuk akun baru.
def test_register_rejects_client_role(client: TestClient) -> None:
    response = client.post(
        f"{AUTH_PATH}/register",
        json={
            "displayName": "HR Demo",
            "email": "client-role@lettrust.test",
            "password": TEST_PASSWORD,
            "role": "ADMIN",
        },
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


# Memastikan request bersamaan dengan email yang sama hanya mencatat satu akun.
def test_register_rejects_duplicate_email(client: TestClient) -> None:
    # Mengirim registrasi dengan variasi kapitalisasi untuk alamat yang sama.
    def register_with_email(email: str) -> tuple[int, dict]:
        response = client.post(
            f"{AUTH_PATH}/register",
            json={"displayName": "HR Demo", "email": email, "password": TEST_PASSWORD},
        )
        return response.status_code, response.json()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(register_with_email, ("Duplicate@lettrust.test", "duplicate@LETTRUST.TEST")))
    assert sorted(status for status, _ in results) == [201, 409]
    duplicate = next(body for status, body in results if status == 409)
    assert duplicate["error"]["code"] == "EMAIL_ALREADY_REGISTERED"
    with get_session_factory()() as db:
        assert db.scalars(select(User.id).where(User.email == "duplicate@lettrust.test")).one()


# Memastikan HR dan admin mendapat JWT HS256 sesuai masa berlaku konfigurasi dan profil tanpa afiliasi.
@pytest.mark.parametrize("role", [Role.HR, Role.ADMIN])
def test_login_and_session(client: TestClient, make_user: Callable[[Role], User], role: Role) -> None:
    account = make_user(role)
    response = client.post(f"{AUTH_PATH}/login", json={"email": account.email.upper(), "password": TEST_PASSWORD})
    assert response.status_code == 200
    result = response.json()
    assert set(result) == {"accessToken", "tokenType", "expiresIn", "user"}
    assert result["tokenType"] == "Bearer"
    settings = get_settings()
    expires_in = settings.jwt_expires_minutes * 60
    assert result["expiresIn"] == expires_in
    summary = {"userId": account.id, "email": account.email, "displayName": account.display_name, "role": role}
    assert result["user"] == summary

    claims = jwt.decode(result["accessToken"], settings.jwt_secret.get_secret_value(), algorithms=["HS256"])
    assert claims["sub"] == account.id
    assert claims["role"] == role
    assert claims["exp"] - claims["iat"] == expires_in

    profile = client.get(f"{AUTH_PATH}/me", headers={"Authorization": f"Bearer {result['accessToken']}"})
    assert profile.status_code == 200
    assert profile.json() == {**summary, "membership": None}


# Memastikan akun yang tidak ada dan password yang salah menghasilkan respons gagal yang sama.
def test_login_rejects_invalid_credentials(client: TestClient, make_user: Callable[[Role], User]) -> None:
    known_user = make_user(Role.HR)
    wrong_password = client.post(f"{AUTH_PATH}/login", json={"email": known_user.email, "password": "PasswordSalah"})
    unknown_email = client.post(
        f"{AUTH_PATH}/login", json={"email": "unknown-login@lettrust.test", "password": "PasswordSalah"}
    )
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json()["error"] == unknown_email.json()["error"]
    assert wrong_password.json()["error"]["code"] == "INVALID_CREDENTIALS"


# Memastikan endpoint sesi menolak Bearer yang hilang, salah, kedaluwarsa, atau kehilangan akun.
@pytest.mark.parametrize("case", ["missing", "scheme", "malformed", "partner", "wrong_signature", "expired", "no_user"])
def test_session_rejects_invalid_token(client: TestClient, make_user: Callable[[Role], User], case: str) -> None:
    if case == "missing":
        headers = {}
    elif case == "scheme":
        headers = {"Authorization": "Basic ZGVtbzpkZW1v"}
    elif case == "malformed":
        headers = {"Authorization": "Bearer bukan-jwt"}
    elif case == "partner":
        partner_token = get_settings().partner_token.get_secret_value()
        headers = {"Authorization": f"Bearer {partner_token}"}
    else:
        issued_at = datetime.now(UTC) - timedelta(hours=1)
        subject = new_user_id() if case == "no_user" else make_user(Role.HR).id
        expiry = issued_at + (timedelta(minutes=1) if case == "expired" else timedelta(hours=8))
        secret = get_settings().jwt_secret.get_secret_value()
        key = "kunci-sintetis-lain-untuk-uji-tanda-tangan" if case == "wrong_signature" else secret
        token = jwt.encode({"sub": subject, "role": "HR", "iat": issued_at, "exp": expiry}, key, algorithm="HS256")
        headers = {"Authorization": f"Bearer {token}"}

    response = client.get(f"{AUTH_PATH}/me", headers=headers)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


# Memastikan perubahan penerbit dan otorisasi muncul pada profil dengan JWT yang sama.
def test_session_reads_current_membership(client: TestClient, make_user: Callable[[Role], User]) -> None:
    hr = make_user(Role.HR)
    admin = make_user(Role.ADMIN)
    now = datetime.now(UTC)
    issuer_id = new_issuer_id()
    with get_session_factory().begin() as db:
        db.add(
            Issuer(
                id=issuer_id,
                company_name="PT Sesi Demo",
                registration_number="REG-SESI-DEMO",
                contact_email=hr.email,
                status="PENDING",
                issuer_ref=compute_issuer_ref(issuer_id),
                registered_by=hr.id,
                created_at=now,
            )
        )
        db.flush()
        db.add(
            IssuerMembership(user_id=hr.id, issuer_id=issuer_id, authorization_status="NOT_AUTHORIZED", created_at=now)
        )

    token, _ = create_access_token(hr.id, hr.role)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get(f"{AUTH_PATH}/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["membership"] == {
        "issuerId": issuer_id,
        "companyName": "PT Sesi Demo",
        "issuerStatus": "PENDING",
        "authorizationStatus": "NOT_AUTHORIZED",
        "reviewNote": None,
    }

    with get_session_factory().begin() as db:
        issuer = db.get_one(Issuer, issuer_id)
        issuer.status = "VERIFIED"
        issuer.review_note = "Dokumen demo sudah ditinjau."
        issuer.evidence_ref = "EVD-SESI-DEMO"
        issuer.reviewed_by = admin.id
        issuer.reviewed_at = now
        membership = db.get_one(IssuerMembership, hr.id)
        membership.authorization_status = "AUTHORIZED"
        membership.authorized_by = admin.id
        membership.authorized_at = now

    response = client.get(f"{AUTH_PATH}/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["membership"] == {
        "issuerId": issuer_id,
        "companyName": "PT Sesi Demo",
        "issuerStatus": "VERIFIED",
        "authorizationStatus": "AUTHORIZED",
        "reviewNote": "Dokumen demo sudah ditinjau.",
    }


# Memastikan role yang dibaca dari DB menentukan akses pada rute admin dan HR.
@pytest.mark.parametrize(
    ("actual_role", "token_role", "method", "path"),
    [
        (Role.HR, Role.ADMIN, "GET", "/api/v1/issuers"),
        (Role.ADMIN, Role.HR, "POST", "/api/v1/proofs"),
    ],
)
def test_role_guards_use_database_role(
    client: TestClient,
    make_user: Callable[[Role], User],
    actual_role: Role,
    token_role: Role,
    method: str,
    path: str,
) -> None:
    user = make_user(actual_role)
    token, _ = create_access_token(user.id, token_role)
    files = {"file": ("demo.pdf", b"%PDF-1.4\n", "application/pdf")} if method == "POST" else None
    response = client.request(method, path, headers={"Authorization": f"Bearer {token}"}, files=files)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN_OPERATION"
