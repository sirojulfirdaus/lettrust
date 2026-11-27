# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: PRD NFR-09.05; SA §17.4
"""Event log NFR-09.05: app.error, proof.registry_unavailable, verification.completed, tanpa field terlarang."""

import hashlib
import io
import json
import logging
from collections.abc import Iterator

import pytest
from fakes.contracts import load_example
from fakes.proofs import found_active
from test_proofs_issue import issue, make_account
from test_proofs_issue import registry as registry
from test_proofs_read import owned_proof as owned_proof
from test_verifications import CODE, REQUEST_ID, post
from test_verifications import install as install

from app.core.config import get_settings
from app.core.logging import ALLOWED_FIELDS, JsonFormatter
from app.modules.registry.adapter import RegistryUnavailable
from app.modules.registry.mock import MockRegistryAdapter

BASE_FIELDS = {"ts", "level", "service", "requestId", "event", "exception"}


# Memasang handler dengan JsonFormatter produksi pada root logger; format terjadi saat emit sehingga requestId
# milik request ikut tercatat, sama seperti keluaran stderr aplikasi.
@pytest.fixture
def json_log() -> Iterator[io.StringIO]:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter(service="backend"))
    root = logging.getLogger()
    previous_level = root.level
    root.addHandler(handler)
    # Test memakai LOG_LEVEL=WARNING; event INFO (verification.completed, registry.tx_*) perlu level INFO.
    root.setLevel(logging.INFO)
    try:
        yield stream
    finally:
        root.removeHandler(handler)
        root.setLevel(previous_level)


# Membaca baris log JSON yang ditulis sejak pemanggilan sebelumnya lalu mengosongkan buffer.
def stderr_records(stream: io.StringIO) -> list[dict]:
    lines = stream.getvalue().splitlines()
    stream.seek(0)
    stream.truncate()
    return [json.loads(line) for line in lines]


# Mengambil tepat satu record dengan event tertentu.
def single(records: list[dict], event: str) -> dict:
    [record] = [record for record in records if record.get("event") == event]
    return record


# AppError dicatat `app.error` dengan kode, status, dan requestId respons; kategori registry dapat dibedakan.
def test_app_error_logged_with_code_and_status(client, registry: MockRegistryAdapter, json_log) -> None:
    _, headers = make_account()
    registry.set_unavailable(True)
    stderr_records(json_log)
    response = issue(client, headers)
    assert response.status_code == 503
    log = single(stderr_records(json_log), "app.error")
    assert (log["level"], log["errorCode"], log["status"]) == ("WARN", "REGISTRY_UNAVAILABLE", 503)
    assert log["requestId"] == response.headers["X-Request-ID"]


# Gangguan registry pada API-07 dicatat dengan penyebab (tipe exception asal), tanpa kode referensi atau proofId.
def test_api07_registry_unavailable_logged_with_cause(
    client, partner_headers, registry: MockRegistryAdapter, owned_proof, json_log
) -> None:
    _, _, proof = owned_proof
    error = RegistryUnavailable("Pembacaan bukti dari registry gagal.")
    error.__cause__ = TimeoutError("rpc timeout sintetis")
    registry.set_unavailable(True, error)
    stderr_records(json_log)
    response = post(client, partner_headers, code=proof["referenceCode"])
    assert response.status_code == 200
    assert response.json()["proofCheck"]["lookup"] == "UNAVAILABLE"
    records = stderr_records(json_log)
    log = single(records, "proof.registry_unavailable")
    assert (log["errorCode"], log["reason"], log["requestId"]) == ("REGISTRY_UNAVAILABLE", "TimeoutError", REQUEST_ID)
    completed = single(records, "verification.completed")
    assert completed["lookup"] == "UNAVAILABLE"
    assert completed["reason"]["proof"] == "REGISTRY_UNAVAILABLE"
    output = json.dumps(records)
    assert proof["referenceCode"] not in output
    assert proof["proofId"] not in output
    assert "rpc timeout sintetis" not in output


# verification.completed memuat status per komponen dan durasi; seluruh log tanpa field atau nilai terlarang.
def test_verification_completed_without_sensitive_values(client, partner_headers, install, json_log) -> None:
    install(proof=found_active())
    marked_file = b"%PDF-1.4\n%NILAI-RAHASIA-OBS\n"
    stderr_records(json_log)
    response = post(client, partner_headers, code=CODE, file=marked_file, include_risk=True)
    assert response.status_code == 200, response.text
    body = response.json()
    records = stderr_records(json_log)
    log = single(records, "verification.completed")
    assert log["requestId"] == REQUEST_ID
    assert (log["mode"], log["lookup"], log["integrity"], log["riskState"]) == (
        body["mode"],
        body["proofCheck"]["lookup"],
        body["integrityCheck"]["result"],
        body["riskAnalysis"]["state"],
    )
    assert isinstance(log["durationMs"], int)
    assert "category" not in json.dumps(log)

    assert all(set(record) <= BASE_FIELDS | set(ALLOWED_FIELDS) for record in records)
    extracted_text = load_example("internal/i-01.extraction-ok.json")["text"]
    sensitive = [
        "NILAI-RAHASIA",
        CODE,
        CODE.removeprefix("LTR-"),
        hashlib.sha256(marked_file).hexdigest(),
        get_settings().partner_token.get_secret_value(),
        *[line for line in extracted_text.splitlines() if len(line) > 8],
        *[quote for item in body["riskAnalysis"]["indicatorDetails"] for quote in item["evidence"]],
    ]
    output = json.dumps(records)
    assert [value for value in sensitive if value in output] == []
