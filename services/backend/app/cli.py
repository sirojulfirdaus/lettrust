# Owner: Dws (PIC 1) [init-db, export-openapi]; Zan (PIC 3) [seed]
# Status: COMPLETE | Ref: SA §9.1, §9.5, §10.1
"""CLI backend: `python -m app.cli init-db | seed [--if-empty] | export-openapi`."""

import argparse
import json
import logging
import sys
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_session_factory, init_db
from app.core.ids import compute_issuer_ref, new_issuer_id, new_partner_id, new_user_id
from app.core.logging import configure_logging
from app.core.security import hash_password, hash_token
from app.modules.auth.models import User
from app.modules.issuers.models import Issuer, IssuerMembership
from app.modules.partners.models import Partner

logger = logging.getLogger("app.cli")

SEED_ADMIN_EMAIL = "admin@lettrust.test"
SEED_REGISTRATION_PREFIX = "REG-SEED-DEMO-"
SEED_ISSUERS = (
    ("PT Sinar Demo Sejahtera", "VERIFIED", ("hr.sinar", "hr2.sinar")),
    ("PT Nusantara Contoh Digital", "VERIFIED", ("hr.nusantara",)),
    ("PT Menunggu Verifikasi Demo", "PENDING", ("hr.pending",)),
    ("PT Ditolak Demo", "REJECTED", ("hr.rejected",)),
)


# Membuat seluruh tabel bila belum ada (tanpa migrasi, AD-03).
def cmd_init_db(_: argparse.Namespace) -> int:
    init_db()
    logger.info("db.initialized", extra={"event": "db.initialized"})
    return 0


# Menambah semua entitas demo pada satu transaksi, dengan urutan insert sesuai foreign key.
def add_demo_seed(db: Session) -> None:
    settings = get_settings()
    now = datetime.now(UTC)
    admin = User(
        id=new_user_id(),
        email=SEED_ADMIN_EMAIL,
        display_name="Administrator Demo Lettrust",
        password_hash=hash_password(settings.seed_admin_password.get_secret_value()),
        role="ADMIN",
        created_at=now,
    )
    db.add(admin)
    db.flush()

    hr_password = settings.seed_hr_password.get_secret_value()
    for number, (company_name, status, usernames) in enumerate(SEED_ISSUERS, start=1):
        users = [
            User(
                id=new_user_id(),
                email=f"{username}@lettrust.test",
                display_name=f"HR Demo ({username})",
                password_hash=hash_password(hr_password),
                role="HR",
                created_at=now,
            )
            for username in usernames
        ]
        db.add_all(users)
        db.flush()

        issuer_id = new_issuer_id()
        reviewed = status != "PENDING"
        db.add(
            Issuer(
                id=issuer_id,
                issuer_ref=compute_issuer_ref(issuer_id),
                company_name=company_name,
                registration_number=f"{SEED_REGISTRATION_PREFIX}{number:02d}",
                contact_email=users[0].email,
                status=status,
                registered_by=users[0].id,
                evidence_ref=f"EVD-SEED-DEMO-{number:02d}" if reviewed else None,
                reviewed_by=admin.id if reviewed else None,
                reviewed_at=now if reviewed else None,
                created_at=now,
            )
        )
        db.flush()

        for user in users:
            authorized = status == "VERIFIED" and user is users[0]
            db.add(
                IssuerMembership(
                    user_id=user.id,
                    issuer_id=issuer_id,
                    authorization_status="AUTHORIZED" if authorized else "NOT_AUTHORIZED",
                    authorized_by=admin.id if authorized else None,
                    authorized_at=now if authorized else None,
                    created_at=now,
                )
            )

    db.add(
        Partner(
            id=new_partner_id(),
            name="Portal Karier Mitra (Simulasi)",
            token_hash=hash_token(settings.partner_token.get_secret_value()),
            active=True,
            created_at=now,
        )
    )


# Mengisi seed secara idempoten dan membatalkan seluruh perubahan bila identitas demo berbenturan.
def cmd_seed(args: argparse.Namespace) -> int:
    try:
        with get_session_factory().begin() as db:
            # Kunci tulis SQLite sebelum memeriksa state agar dua proses seed tidak berjalan bersamaan.
            connection = db.connection()
            connection.exec_driver_sql("PRAGMA busy_timeout = 30000")
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            if args.if_empty and (db.scalar(select(User.id).limit(1)) or db.scalar(select(Partner.id).limit(1))):
                logger.info("seed.skipped_nonempty")
                return 0

            # Jejak keputusan admin demo menandai seed yang sudah dikomit sebagai satu transaksi.
            seeded = db.scalar(
                select(User.id)
                .join(Issuer, Issuer.reviewed_by == User.id)
                .where(
                    User.email == SEED_ADMIN_EMAIL,
                    User.role == "ADMIN",
                    Issuer.registration_number == f"{SEED_REGISTRATION_PREFIX}01",
                )
            )
            if seeded is not None:
                logger.info("seed.skipped_existing")
                return 0

            add_demo_seed(db)
    except IntegrityError:
        logger.error("seed.data_conflict")
        return 1
    except DBAPIError:
        logger.error("seed.database_error")
        return 1

    logger.info("seed.completed")
    return 0


# Mencetak OpenAPI JSON aplikasi ke stdout (dipakai `dev.py openapi`).
def cmd_export_openapi(_: argparse.Namespace) -> int:
    from app.main import create_app

    sys.stdout.write(json.dumps(create_app().openapi(), indent=2, ensure_ascii=False) + "\n")
    return 0


# Menyusun parser subperintah CLI.
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init-db", help="Buat tabel basis data").set_defaults(func=cmd_init_db)
    seed = sub.add_parser("seed", help="Isi data sintetis (idempotent)")
    seed.add_argument("--if-empty", action="store_true", help="Hanya seed bila basis data kosong")
    seed.set_defaults(func=cmd_seed)
    sub.add_parser("export-openapi", help="Cetak OpenAPI JSON ke stdout").set_defaults(func=cmd_export_openapi)
    return parser


# Titik masuk CLI; konfigurasi divalidasi sebelum perintah dijalankan.
def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(get_settings().log_level, service="backend")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
