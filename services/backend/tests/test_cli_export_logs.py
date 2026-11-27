# Owner: Zan (PIC 3) | Status: COMPLETE | Ref: PRD FR-06.08 AC-02, AC-03; SA §9.2
"""Menguji perintah `export-verification-logs` pada basis data SQLite terpisah."""

import csv
import io
import json
import os
import subprocess
import sys
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.cli import VERIFICATION_LOG_EXPORT_FIELDS
from app.modules.partners.models import Partner
from app.modules.verifications.models import VerificationLog

BASE_TIME = datetime(2026, 5, 1, 8, 0, tzinfo=UTC)


# Menjalankan entry point CLI dengan DATABASE_URL uji dan menangkap output.
def run_cli(env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "app.cli", *args],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


# Membuat DB baru berisi satu partner dan dua log yang disisipkan terbalik dari urutan created_at.
@pytest.fixture
def logs_env(tmp_path: Path) -> Iterator[dict[str, str]]:
    database_url = f"sqlite:///{(tmp_path / 'logs.db').as_posix()}"
    env = dict(os.environ, DATABASE_URL=database_url)
    result = run_cli(env, "init-db")
    assert result.returncode == 0, result.stderr

    engine = create_engine(database_url)
    try:
        with Session(engine) as db, db.begin():
            db.add(Partner(id="ptn_export", name="Partner Uji", token_hash="h" * 64, active=True, created_at=BASE_TIME))
            db.flush()
            db.add_all(
                [
                    VerificationLog(
                        id="ver_second",
                        partner_id="ptn_export",
                        mode="AI_ONLY",
                        lookup="NOT_REQUESTED",
                        lifecycle_status=None,
                        integrity_result="NOT_CHECKED",
                        risk_state="ANALYZED",
                        risk_category="HIGH",
                        proof_reason="NO_REFERENCE_CODE",
                        integrity_reason="NO_REFERENCE_CODE",
                        risk_reason=None,
                        duration_ms=1500,
                        created_at=BASE_TIME + timedelta(minutes=5),
                    ),
                    VerificationLog(
                        id="ver_first",
                        partner_id="ptn_export",
                        mode="FULL",
                        lookup="FOUND",
                        lifecycle_status="ACTIVE",
                        integrity_result="MATCH",
                        risk_state="UNAVAILABLE",
                        risk_category=None,
                        proof_reason=None,
                        integrity_reason=None,
                        risk_reason="AI_SERVICE_UNAVAILABLE",
                        duration_ms=320,
                        created_at=BASE_TIME,
                    ),
                ]
            )
        yield env
    finally:
        engine.dispose()


# Default JSONL ke stdout: urut created_at, kolom persis allowlist, waktu ISO-8601 UTC.
def test_export_jsonl_to_stdout(logs_env: dict[str, str]) -> None:
    result = run_cli(logs_env, "export-verification-logs")
    assert result.returncode == 0, result.stderr

    records = [json.loads(line) for line in result.stdout.splitlines()]
    assert [record["id"] for record in records] == ["ver_first", "ver_second"]
    assert all(tuple(record) == VERIFICATION_LOG_EXPORT_FIELDS for record in records)
    assert records[0]["created_at"] == "2026-05-01T08:00:00+00:00"
    assert records[0]["lifecycle_status"] == "ACTIVE"
    assert records[1]["lifecycle_status"] is None
    assert records[1]["duration_ms"] == 1500


# CSV memuat header persis allowlist dan baris berurutan created_at.
def test_export_csv(logs_env: dict[str, str]) -> None:
    result = run_cli(logs_env, "export-verification-logs", "--format", "csv")
    assert result.returncode == 0, result.stderr

    reader = csv.DictReader(io.StringIO(result.stdout))
    assert tuple(reader.fieldnames or ()) == VERIFICATION_LOG_EXPORT_FIELDS
    rows = list(reader)
    assert [row["id"] for row in rows] == ["ver_first", "ver_second"]
    assert rows[0]["risk_reason"] == "AI_SERVICE_UNAVAILABLE"


# --out menulis ke berkas dan tidak mengirim data ke stdout.
def test_export_out_file(logs_env: dict[str, str], tmp_path: Path) -> None:
    out_path = tmp_path / "export" / "logs.jsonl"
    out_path.parent.mkdir()
    result = run_cli(logs_env, "export-verification-logs", "--out", str(out_path))
    assert result.returncode == 0, result.stderr

    assert result.stdout == ""
    lines = out_path.read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["id"] for line in lines] == ["ver_first", "ver_second"]


# Allowlist sama dengan kolom aman SA §9.2; gagal bila skema tabel berubah agar allowlist ditinjau ulang.
def test_export_fields_match_safe_columns() -> None:
    assert set(VERIFICATION_LOG_EXPORT_FIELDS) == set(VerificationLog.__table__.columns.keys())
    forbidden = ("reference", "code", "hash", "text", "file", "token", "email", "name")
    assert not [field for field in VERIFICATION_LOG_EXPORT_FIELDS if any(word in field for word in forbidden)]
