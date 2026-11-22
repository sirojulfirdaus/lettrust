# Owner: Zan (PIC 3) | Status: COMPLETE | Ref: PRD FR-01.08; SA §9.5
"""Menguji perintah seed dengan basis data SQLite terpisah."""

import hashlib
import os
import subprocess
import sys
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.modules.auth.models import User
from app.modules.issuers.models import Issuer, IssuerMembership
from app.modules.partners.models import Partner
from app.modules.proofs.models import Proof


# Menjalankan entry point CLI dengan konfigurasi sintetis dan menangkap output untuk diperiksa.
def run_cli(env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "app.cli", *args],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


# Membuat skema seperti saat startup backend, pada berkas SQLite baru untuk setiap tes.
@pytest.fixture
def seed_database(tmp_path: Path) -> Iterator[tuple[dict[str, str], Session]]:
    database_url = f"sqlite:///{(tmp_path / 'seed.db').as_posix()}"
    env = dict(
        os.environ,
        DATABASE_URL=database_url,
        SEED_ADMIN_PASSWORD="Admin!SeedTest2026",
        SEED_HR_PASSWORD="HR!SeedTest2026",
        PARTNER_TOKEN="synthetic-partner-token-for-seed-test",
    )
    result = run_cli(env, "init-db")
    assert result.returncode == 0, result.stderr

    engine = create_engine(database_url)
    try:
        with Session(engine) as db:
            yield env, db
    finally:
        engine.dispose()


# Memastikan startup mengisi semua entitas demo dengan status dan kredensial sesuai konfigurasi.
def test_seed_creates_demo_data(seed_database: tuple[dict[str, str], Session]) -> None:
    env, db = seed_database
    result = run_cli(env, "seed", "--if-empty")
    assert result.returncode == 0, result.stderr

    users = {user.email: user for user in db.scalars(select(User))}
    admin = users.pop("admin@lettrust.test")
    assert admin.role == "ADMIN"
    assert verify_password(env["SEED_ADMIN_PASSWORD"], admin.password_hash)
    assert set(users) == {
        "hr.sinar@lettrust.test",
        "hr.nusantara@lettrust.test",
        "hr.pending@lettrust.test",
        "hr.rejected@lettrust.test",
        "hr2.sinar@lettrust.test",
    }
    for user in users.values():
        assert user.role == "HR"
        assert verify_password(env["SEED_HR_PASSWORD"], user.password_hash)

    issuers = {issuer.id: issuer for issuer in db.scalars(select(Issuer))}
    assert {issuer.company_name: issuer.status for issuer in issuers.values()} == {
        "PT Sinar Demo Sejahtera": "VERIFIED",
        "PT Nusantara Contoh Digital": "VERIFIED",
        "PT Menunggu Verifikasi Demo": "PENDING",
        "PT Ditolak Demo": "REJECTED",
    }
    assert {
        (membership.user_id, issuers[membership.issuer_id].company_name, membership.authorization_status)
        for membership in db.scalars(select(IssuerMembership))
    } == {
        (users["hr.sinar@lettrust.test"].id, "PT Sinar Demo Sejahtera", "AUTHORIZED"),
        (users["hr.nusantara@lettrust.test"].id, "PT Nusantara Contoh Digital", "AUTHORIZED"),
        (users["hr.pending@lettrust.test"].id, "PT Menunggu Verifikasi Demo", "NOT_AUTHORIZED"),
        (users["hr.rejected@lettrust.test"].id, "PT Ditolak Demo", "NOT_AUTHORIZED"),
        (users["hr2.sinar@lettrust.test"].id, "PT Sinar Demo Sejahtera", "NOT_AUTHORIZED"),
    }

    partner = db.scalars(select(Partner)).one()
    assert partner.name == "Portal Karier Mitra (Simulasi)"
    assert partner.active
    assert partner.token_hash == hashlib.sha256(env["PARTNER_TOKEN"].encode()).hexdigest()
    assert db.scalars(select(Proof)).first() is None
    for key in ("SEED_ADMIN_PASSWORD", "SEED_HR_PASSWORD", "PARTNER_TOKEN"):
        assert env[key] not in result.stdout + result.stderr


# Memastikan pengulangan seed tidak menggandakan entitas atau menimpa otorisasi yang sudah berubah.
def test_seed_retries_preserve_existing_data(seed_database: tuple[dict[str, str], Session]) -> None:
    env, db = seed_database
    with ThreadPoolExecutor(max_workers=2) as executor:
        manual = executor.submit(run_cli, env, "seed")
        startup = executor.submit(run_cli, env, "seed", "--if-empty")
        for pending in (manual, startup):
            result = pending.result()
            assert result.returncode == 0, result.stderr
    hr_id = db.scalars(select(User.id).where(User.email == "hr2.sinar@lettrust.test")).one()
    membership = db.get_one(IssuerMembership, hr_id)
    membership.authorization_status = "AUTHORIZED"
    membership.authorized_by = db.scalars(select(User.id).where(User.role == "ADMIN")).one()
    membership.authorized_at = datetime.now(UTC)
    db.commit()

    for args in (("seed", "--if-empty"), ("seed",)):
        result = run_cli(env, *args)
        assert result.returncode == 0, result.stderr

    assert len(db.scalars(select(User)).all()) == 6
    assert len(db.scalars(select(Issuer)).all()) == 4
    assert len(db.scalars(select(IssuerMembership)).all()) == 5
    assert len(db.scalars(select(Partner)).all()) == 1
    assert db.get_one(IssuerMembership, hr_id).authorization_status == "AUTHORIZED"


# Memastikan mode startup melewati DB terisi dan seed manual gagal utuh bila email demo berbenturan.
def test_seed_does_not_take_over_existing_account(seed_database: tuple[dict[str, str], Session]) -> None:
    env, db = seed_database
    db.add(
        User(
            id="USR-EX1ST1NG",
            email="hr.nusantara@lettrust.test",
            display_name="HR Contoh yang Sudah Terdaftar",
            password_hash="hash-sintetis-untuk-tes",
            role="HR",
            created_at=datetime.now(UTC),
        )
    )
    db.commit()

    startup_seed = run_cli(env, "seed", "--if-empty")
    assert startup_seed.returncode == 0, startup_seed.stderr
    assert db.scalars(select(User.id)).all() == ["USR-EX1ST1NG"]

    manual_seed = run_cli(env, "seed")
    assert manual_seed.returncode != 0
    assert db.scalars(select(User.id)).all() == ["USR-EX1ST1NG"]
    assert db.scalars(select(Issuer)).first() is None
    assert db.scalars(select(IssuerMembership)).first() is None
    assert db.scalars(select(Partner)).first() is None
    assert "INSERT INTO" not in manual_seed.stdout + manual_seed.stderr


# Memastikan kegagalan SQLite saat insert terakhir me-rollback seed tanpa membocorkan parameter SQL.
def test_seed_rolls_back_on_database_error_without_logging_parameters(
    seed_database: tuple[dict[str, str], Session],
) -> None:
    env, db = seed_database
    db.execute(
        text(
            "CREATE TRIGGER fail_partner_seed BEFORE INSERT ON partners "
            "BEGIN INSERT INTO missing_seed_table (id) VALUES (NEW.id); END"
        )
    )
    db.commit()

    result = run_cli(env, "seed")
    assert result.returncode == 1
    output = result.stdout + result.stderr
    if "INSERT INTO" in output or "Traceback" in output:
        pytest.fail("Error basis data seed menampilkan SQL atau traceback")
    assert "seed.database_error" in output
    assert db.scalars(select(User.id)).first() is None
    assert db.scalars(select(Issuer.id)).first() is None
    assert db.scalars(select(IssuerMembership.user_id)).first() is None
    assert db.scalars(select(Partner.id)).first() is None
