# Owner: Dws (PIC 1) [init-db, export-openapi]; Zan (PIC 3) [seed]
# Status: COMPLETE (seed: STUB) | Ref: SA §9.1, §9.5, §10.1
# TODO (Zan): Seed idempotent SA §9.5 (admin, 4 penerbit, HR, partner dari PARTNER_TOKEN);
# --with-sample-proofs (P1).
"""CLI backend: `python -m app.cli init-db | seed [--if-empty] | export-openapi`."""

import argparse
import json
import logging
import sys

from app.core.config import get_settings
from app.core.db import init_db
from app.core.logging import configure_logging

logger = logging.getLogger("app.cli")


# Membuat seluruh tabel bila belum ada (tanpa migrasi, AD-03).
def cmd_init_db(_: argparse.Namespace) -> int:
    init_db()
    logger.info("db.initialized", extra={"event": "db.initialized"})
    return 0


# STUB: seed data sintetis; sementara hanya memberi tahu belum diimplementasikan dan keluar 0 agar startup tetap jalan.
def cmd_seed(args: argparse.Namespace) -> int:
    mode = "--if-empty" if args.if_empty else "penuh"
    print(f"[seed] Seed belum diimplementasikan (STUB, mode {mode}); tidak ada data yang dibuat.", file=sys.stderr)
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
    seed.add_argument("--with-sample-proofs", action="store_true", help="(P1) Terbitkan FX-01 melalui service layer")
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
