# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: PRD FR-02.03, FR-02.04, FR-03.10, FR-05.10, FR-06.01–FR-06.05;
# SA §5.2–§5.6, §10.7
"""Test API-07 verifyOffer end-to-end lewat HTTP dengan FakeProofReader dan FakeAiService (tanpa registry/LLM nyata)."""

import asyncio
import functools
import hashlib
import json
import logging
import re

import pytest
from fakes.ai_service import EXTRACTION_PATH, FakeAiService, assert_internal_headers
from fakes.contracts import load_example
from fakes.proofs import (
    MATCHING_FILE_BYTES,
    MISMATCHING_FILE_BYTES,
    FakeProofReader,
    found_active,
    found_issuer_not_verified,
    found_revoked,
    install_fake_proof_reader,
    registry_unavailable,
)
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError

from app.core.config import get_settings
from app.core.db import get_session_factory
from app.core.logging import JsonFormatter
from app.core.security import hash_token
from app.modules.partners.models import Partner
from app.modules.proofs.service import ProofVerificationRead
from app.modules.verifications import ai_client, orchestrator
from app.modules.verifications.models import VerificationLog

URL = "/api/v1/verifications"
CODE = "LTR-7K3M-9QX2-H4TD"
# Kode berformat valid yang tidak didaftarkan di FakeProofReader (default NOT_FOUND).
UNKNOWN_CODE = "LTR-9Z9Z-9Z9Z-9Z9Z"
REQUEST_ID = "req_T105VERIFYTEST01"
VERIFICATION_ID = re.compile(r"^VER-[0-9A-HJKMNP-TV-Z]{10}$")


# Memasang FakeAiService pada pipeline ai_client yang dipanggil orkestrator.
def install_fake_ai(monkeypatch, extraction="ok", analysis="high") -> FakeAiService:
    fake = FakeAiService(extraction=extraction, analysis=analysis)
    pipeline = functools.partial(ai_client.run_risk_pipeline, transport=fake.transport())
    monkeypatch.setattr(ai_client, "run_risk_pipeline", pipeline)
    return fake


# Memasang FakeProofReader dan FakeAiService pada atribut modul yang dipanggil orkestrator; dipanggil sekali per test.
@pytest.fixture
def install(monkeypatch):
    # proof=None → reader tanpa entri (setiap kode NOT_FOUND); mode AI sesuai FakeAiService.
    def _install(proof=None, extraction="ok", analysis="high"):
        reader = install_fake_proof_reader(monkeypatch, FakeProofReader({CODE: proof} if proof else {}))
        return reader, install_fake_ai(monkeypatch, extraction, analysis)

    return _install


# Mengirim API-07 multipart dengan X-Request-ID tetap; field yang None tidak dikirim.
def post(client, headers, *, code=None, file=None, include_risk=None, files=None):
    data = {}
    if code is not None:
        data["referenceCode"] = code
    if include_risk is not None:
        data["includeRisk"] = "true" if include_risk else "false"
    if file is not None:
        files = {"file": ("offer.pdf", file, "application/pdf")}
    return client.post(URL, headers={**headers, "X-Request-ID": REQUEST_ID}, data=data, files=files)


# Respons harus sama bentuknya dengan contoh API-07: mode, proofCheck, integrityCheck identik; riskAnalysis
# identik bila tanpa hasil. Untuk COMPLETED isi analisis berasal dari contoh internal FakeAiService, sehingga
# yang dibandingkan adalah himpunan field, state, reason, dan kategori.
def assert_matches_example(body: dict, example_file: str) -> None:
    example = load_example(example_file)
    assert VERIFICATION_ID.fullmatch(body["verificationId"])
    assert set(body) == set(example)
    for key in ("mode", "proofCheck", "integrityCheck"):
        assert body[key] == example[key], key
    risk, expected = body["riskAnalysis"], example["riskAnalysis"]
    assert set(risk) == set(expected)
    if expected["state"] == "COMPLETED":
        assert (risk["state"], risk["reason"], risk["category"]) == ("COMPLETED", None, expected["category"])
        assert risk["extractionMethod"] is not None and risk["pagesAnalyzed"] is not None
    else:
        assert risk == expected


# Mengambil satu log event tertentu dan memformatnya dengan JsonFormatter produksi.
def formatted_log(caplog, event: str) -> dict:
    [record] = [r for r in caplog.records if getattr(r, "event", None) == event]
    return json.loads(JsonFormatter(service="backend").format(record))


EXAMPLE_CASES = [
    pytest.param(
        "api-07.reference-match-ai.json",
        {"code": CODE, "file": MATCHING_FILE_BYTES, "include_risk": True},
        {"proof": found_active(), "analysis": "low"},
        id="SCN-01-reference-match-ai",
    ),
    pytest.param(
        "api-07.not-found-code-only.json",
        {"code": UNKNOWN_CODE},
        {},
        id="SCN-04a-not-found-code-only",
    ),
    pytest.param(
        "api-07.not-found-with-ai.json",
        {"code": UNKNOWN_CODE, "file": MISMATCHING_FILE_BYTES, "include_risk": True},
        {"analysis": "high"},
        id="SCN-04b-not-found-with-ai",
    ),
    pytest.param(
        "api-07.code-only.json",
        {"code": CODE, "include_risk": False},
        {"proof": found_active()},
        id="SCN-05a-code-only",
    ),
    pytest.param(
        "api-07.ai-not-performed.json",
        {"code": CODE, "include_risk": True},
        {"proof": found_active()},
        id="SCN-05b-code-only-include-risk",
    ),
    pytest.param(
        "api-07.ai-unavailable.json",
        {"code": CODE, "file": MATCHING_FILE_BYTES, "include_risk": True},
        {"proof": found_active(), "extraction": "unavailable"},
        id="SCN-07a-ai-unavailable",
    ),
    pytest.param(
        "api-07.registry-unavailable.json",
        {"code": CODE, "file": MATCHING_FILE_BYTES, "include_risk": True},
        {"proof": registry_unavailable(), "analysis": "low"},
        id="SCN-07b-registry-unavailable",
    ),
    pytest.param(
        "api-07.ai-only.json",
        {"file": MISMATCHING_FILE_BYTES, "include_risk": True},
        {"analysis": "high"},
        id="SCN-08-ai-only",
    ),
    pytest.param(
        "api-07.double-outage.json",
        {"code": CODE, "file": MATCHING_FILE_BYTES, "include_risk": True},
        {"proof": registry_unavailable(), "extraction": "timeout"},
        id="SCN-17-double-outage",
    ),
    pytest.param(
        "api-07.revoked-mismatch.json",
        {"code": CODE, "file": MISMATCHING_FILE_BYTES},
        {"proof": found_revoked()},
        id="revoked-mismatch",
    ),
    pytest.param(
        "api-07.issuer-not-verified.json",
        {"code": CODE, "file": MATCHING_FILE_BYTES},
        {"proof": found_issuer_not_verified()},
        id="issuer-not-verified",
    ),
    pytest.param(
        "api-07.ai-quota-exceeded.json",
        {"file": MATCHING_FILE_BYTES, "include_risk": True},
        {"analysis": "quota_exceeded"},
        id="ai-only-quota-exceeded",
    ),
    pytest.param(
        "api-07.ai-only-medium-partial.json",
        {"file": MATCHING_FILE_BYTES, "include_risk": True},
        {"extraction": "ok_truncated", "analysis": "medium"},
        id="ai-only-medium-partial",
    ),
]


# Setiap kombinasi valid menghasilkan HTTP 200 berbentuk contoh API-07 yang sesuai. Pembacaan bukti hanya pada
# REFERENCE_CHECK (kode ternormalisasi); AI hanya bila includeRisk dan berkas ada, dengan X-Request-ID yang sama.
@pytest.mark.parametrize(("example", "request_kwargs", "setup"), EXAMPLE_CASES)
def test_api07_matches_example(client, partner_headers, install, example, request_kwargs, setup):
    reader, fake = install(**setup)
    response = post(client, partner_headers, **request_kwargs)
    assert response.status_code == 200, response.text
    assert_matches_example(response.json(), example)
    code = request_kwargs.get("code")
    assert reader.calls == ([code] if code else [])
    if request_kwargs.get("include_risk") and "file" in request_kwargs:
        assert fake.requests and fake.requests[0].url.path == EXTRACTION_PATH
        for request in fake.requests:
            assert_internal_headers(request, request_id=REQUEST_ID)
        assert request_kwargs["file"] in fake.requests[0].content
    else:
        assert fake.requests == []


# referenceCode dinormalisasi (SA §6.3.1) sebelum dibaca; kode spasi-saja berarti tidak ada kode.
def test_reference_code_normalized(client, partner_headers, install):
    reader, _ = install(proof=found_active())
    response = post(client, partner_headers, code="  ltr 7k3m-9qx2 h4td ", include_risk=False)
    assert response.status_code == 200
    assert reader.calls == [CODE]
    assert response.json()["proofCheck"]["lookup"] == "FOUND"


# Pembacaan bukti dan analisis AI berjalan paralel: masing-masing menunggu tugas lain sudah mulai.
def test_proof_and_ai_run_in_parallel(client, partner_headers, monkeypatch):
    proof_started, ai_started = asyncio.Event(), asyncio.Event()
    fake = FakeAiService(extraction="ok", analysis="low")
    pipeline = functools.partial(ai_client.run_risk_pipeline, transport=fake.transport())

    # Reader yang baru selesai setelah tugas AI berjalan (timeout bila orkestrator berurutan).
    async def reader(reference_code: str):
        proof_started.set()
        await asyncio.wait_for(ai_started.wait(), timeout=2)
        return found_active()

    # Pipeline yang baru berjalan setelah pembacaan bukti dimulai.
    async def risk_pipeline(file_bytes: bytes, request_id: str):
        ai_started.set()
        await asyncio.wait_for(proof_started.wait(), timeout=2)
        return await pipeline(file_bytes, request_id)

    monkeypatch.setattr("app.modules.proofs.service.read_proof_for_verification", reader)
    monkeypatch.setattr(ai_client, "run_risk_pipeline", risk_pipeline)
    response = post(client, partner_headers, code=CODE, file=MATCHING_FILE_BYTES, include_risk=True)
    assert response.status_code == 200, response.text
    assert_matches_example(response.json(), "api-07.reference-match-ai.json")


# SCN-10 dan validasi berkas (SA §5.2 langkah 3–6): 400/413/415 sebelum registry atau AI dipanggil.
@pytest.mark.parametrize(
    ("request_kwargs", "status", "code"),
    [
        pytest.param({"include_risk": True}, 400, "INVALID_INPUT_COMBINATION", id="SCN-10a-no-code-no-file"),
        pytest.param({}, 400, "INVALID_INPUT_COMBINATION", id="SCN-10a-empty-form"),
        pytest.param({"code": "   ", "include_risk": True}, 400, "INVALID_INPUT_COMBINATION", id="blank-code"),
        pytest.param(
            {"file": MATCHING_FILE_BYTES, "include_risk": False},
            400,
            "AI_ONLY_REQUIRES_INCLUDE_RISK",
            id="SCN-10b-ai-only-without-include-risk",
        ),
        pytest.param({"file": MATCHING_FILE_BYTES}, 400, "AI_ONLY_REQUIRES_INCLUDE_RISK", id="SCN-10b-absent"),
        pytest.param(
            {"code": "LTR-123", "file": MATCHING_FILE_BYTES, "include_risk": True},
            400,
            "INVALID_REFERENCE_CODE_FORMAT",
            id="SCN-10c-invalid-format",
        ),
        # Kombinasi (langkah 5) diperiksa sebelum isi berkas (langkah 6).
        pytest.param({"file": b"", "include_risk": False}, 400, "AI_ONLY_REQUIRES_INCLUDE_RISK", id="order-5-before-6"),
        pytest.param({"code": CODE, "file": b"", "include_risk": True}, 400, "EMPTY_FILE", id="empty-file"),
        pytest.param(
            {"code": CODE, "file": b"bukan pdf", "include_risk": True}, 415, "UNSUPPORTED_MEDIA_TYPE", id="not-pdf"
        ),
        pytest.param(
            {"file": b"%PDF-" + b"0" * get_settings().max_upload_bytes, "include_risk": True},
            413,
            "FILE_TOO_LARGE",
            id="file-too-large",
        ),
        pytest.param(
            {
                "code": CODE,
                "files": [
                    ("file", ("a.pdf", MATCHING_FILE_BYTES, "application/pdf")),
                    ("file", ("b.pdf", MATCHING_FILE_BYTES, "application/pdf")),
                ],
            },
            400,
            "MULTIPLE_FILES",
            id="multiple-files",
        ),
    ],
)
def test_invalid_requests_stop_before_registry_and_ai(client, partner_headers, install, request_kwargs, status, code):
    reader, fake = install(proof=found_active())
    response = post(client, partner_headers, **request_kwargs)
    assert response.status_code == status, response.text
    assert response.json()["error"]["code"] == code
    assert response.headers["X-Request-ID"] == REQUEST_ID
    assert reader.calls == [] and fake.requests == []


# Tanpa token partner valid → 401 sebelum parsing/registry/AI.
@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer token-salah"}])
def test_unauthenticated(client, install, headers):
    reader, fake = install(proof=found_active())
    response = post(client, headers, code=CODE, file=MATCHING_FILE_BYTES, include_risk=True)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"
    assert reader.calls == [] and fake.requests == []


# Exception tak terduga di jalur AI → UNAVAILABLE / AI_SERVICE_UNAVAILABLE; proofCheck dan integrityCheck tetap
# lengkap. Log hanya reason=unexpected_error dan nama tipe exception, tanpa pesan.
def test_unexpected_ai_exception_is_isolated(client, partner_headers, install, monkeypatch, caplog):
    install(proof=found_active())

    # Pipeline rusak yang melempar exception berisi penanda sintetis.
    async def broken_pipeline(file_bytes: bytes, request_id: str):
        raise RuntimeError("NILAI-RAHASIA isi dokumen")

    monkeypatch.setattr(ai_client, "run_risk_pipeline", broken_pipeline)
    with caplog.at_level(logging.WARNING):
        response = post(client, partner_headers, code=CODE, file=MATCHING_FILE_BYTES, include_risk=True)
    assert response.status_code == 200, response.text
    assert_matches_example(response.json(), "api-07.ai-unavailable.json")
    logged = formatted_log(caplog, "ai.pipeline_failed")
    assert logged["reason"] == "unexpected_error"
    assert logged["exception"] == "RuntimeError"
    assert (logged["errorCode"], logged["riskState"]) == ("AI_SERVICE_UNAVAILABLE", "UNAVAILABLE")
    assert "NILAI-RAHASIA" not in json.dumps(logged) and "NILAI-RAHASIA" not in caplog.text


class Web3RPCError(Exception):
    """Exception web3 sintetis yang (seharusnya tidak) lolos dari read_proof_for_verification."""


# Exception tak terduga dari pembaca bukti → proofCheck UNAVAILABLE / REGISTRY_UNAVAILABLE dan integritas
# NOT_CHECKED; tugas AI tidak dibatalkan dan hasilnya (COMPLETED atau UNAVAILABLE) tetap dikembalikan.
@pytest.mark.parametrize(
    ("ai_setup", "example"),
    [
        ({"analysis": "low"}, "api-07.registry-unavailable.json"),
        ({"extraction": "timeout"}, "api-07.double-outage.json"),
    ],
    ids=["ai-completed", "ai-unavailable"],
)
def test_unexpected_proof_exception_is_isolated(
    client, partner_headers, install, monkeypatch, caplog, ai_setup, example
):
    _, fake = install(**ai_setup)

    # Pembaca bukti yang melanggar kontrak "tidak raise" dengan pesan berisi penanda sintetis.
    async def broken_reader(reference_code: str):
        raise Web3RPCError("NILAI-RAHASIA rpc gagal")

    monkeypatch.setattr("app.modules.proofs.service.read_proof_for_verification", broken_reader)
    with caplog.at_level(logging.WARNING):
        response = post(client, partner_headers, code=CODE, file=MATCHING_FILE_BYTES, include_risk=True)
    assert response.status_code == 200, response.text
    assert_matches_example(response.json(), example)
    assert fake.requests and fake.requests[0].url.path == EXTRACTION_PATH
    logged = formatted_log(caplog, "proof.read_failed")
    assert (logged["reason"], logged["exception"]) == ("unexpected_error", "Web3RPCError")
    assert (logged["errorCode"], logged["lookup"]) == ("REGISTRY_UNAVAILABLE", "UNAVAILABLE")
    assert "NILAI-RAHASIA" not in json.dumps(logged) and "NILAI-RAHASIA" not in caplog.text


# FOUND tanpa documentHash (kombinasi mustahil di integrity_from) → 200 dengan integrityCheck NOT_CHECKED /
# REGISTRY_UNAVAILABLE dan log unexpected_error; proofCheck tetap seperti yang dibaca.
def test_found_without_hash_not_checked(client, partner_headers, install, caplog):
    found = found_active()
    install(proof=ProofVerificationRead(proof_check=found.proof_check, registry_document_hash=None))
    with caplog.at_level(logging.WARNING):
        response = post(client, partner_headers, code=CODE, file=MATCHING_FILE_BYTES, include_risk=False)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["proofCheck"] == load_example("api-07.code-only.json")["proofCheck"]
    assert body["integrityCheck"] == {"result": "NOT_CHECKED", "reason": "REGISTRY_UNAVAILABLE", "hashAlgorithm": None}
    logged = formatted_log(caplog, "integrity.check_failed")
    assert (logged["reason"], logged["exception"], logged["lookup"]) == ("unexpected_error", "ValueError", "FOUND")


# DLT-14: stub T3-05 (NotImplementedError) → 200 dengan proofCheck UNAVAILABLE / REGISTRY_UNAVAILABLE dan
# integritas NOT_CHECKED; tugas AI tidak dibatalkan (COMPLETED). Log memakai reason=not_implemented tanpa pesan.
def test_proof_reader_stub_unavailable(client, partner_headers, install, monkeypatch, caplog):
    _, fake = install(analysis="low")

    # Meniru stub proofs.service yang belum diimplementasikan, dengan pesan berisi penanda sintetis.
    async def stub_reader(reference_code: str):
        raise NotImplementedError("NILAI-RAHASIA belum diimplementasikan")

    monkeypatch.setattr("app.modules.proofs.service.read_proof_for_verification", stub_reader)
    with caplog.at_level(logging.WARNING):
        response = post(client, partner_headers, code=CODE, file=MATCHING_FILE_BYTES, include_risk=True)
    assert response.status_code == 200, response.text
    assert_matches_example(response.json(), "api-07.registry-unavailable.json")
    assert fake.requests and fake.requests[0].url.path == EXTRACTION_PATH
    logged = formatted_log(caplog, "proof.read_failed")
    assert (logged["reason"], logged["exception"]) == ("not_implemented", "NotImplementedError")
    assert (logged["errorCode"], logged["lookup"]) == ("REGISTRY_UNAVAILABLE", "UNAVAILABLE")
    assert "NILAI-RAHASIA" not in json.dumps(logged) and "NILAI-RAHASIA" not in caplog.text


# Membaca baris verification_logs untuk satu verificationId sebagai dict kolom → nilai (None bila tidak ada).
def logged_row(verification_id: str) -> dict | None:
    with get_session_factory()() as db:
        row = db.get(VerificationLog, verification_id)
        return None if row is None else {c.name: getattr(row, c.name) for c in VerificationLog.__table__.columns}


# Jumlah seluruh baris verification_logs.
def log_count() -> int:
    with get_session_factory()() as db:
        return db.scalar(select(func.count()).select_from(VerificationLog))


# Kolom enum yang diharapkan dari body API-07 (SA §9.2).
def expected_log(body: dict) -> dict:
    proof, integrity, risk = body["proofCheck"], body["integrityCheck"], body["riskAnalysis"]
    return {
        "id": body["verificationId"],
        "mode": body["mode"],
        "lookup": proof["lookup"],
        "lifecycle_status": proof["lifecycleStatus"],
        "proof_reason": proof["reason"],
        "integrity_result": integrity["result"],
        "integrity_reason": integrity["reason"],
        "risk_state": risk["state"],
        "risk_category": risk["category"],
        "risk_reason": risk["reason"],
    }


# id partner pemilik PARTNER_TOKEN uji.
def current_partner_id() -> str:
    token = get_settings().partner_token.get_secret_value()
    with get_session_factory()() as db:
        return db.scalar(select(Partner.id).where(Partner.token_hash == hash_token(token)))


# T1-06: setiap API-07 200 (Mode Dengan Kode, Mode Tanpa Kode, dan hasil parsial) mencatat tepat satu baris berisi
# enum hasil yang sama dengan respons, partner pemanggil, durasi, dan waktu.
@pytest.mark.parametrize(
    ("setup", "request_kwargs", "expected"),
    [
        pytest.param(
            {"proof": found_active()},
            {"code": CODE, "file": MATCHING_FILE_BYTES, "include_risk": True},
            ("REFERENCE_CHECK", "FOUND", "ACTIVE", "MATCH", "COMPLETED", "HIGH"),
            id="reference-check",
        ),
        pytest.param(
            {"analysis": "low"},
            {"file": MATCHING_FILE_BYTES, "include_risk": True},
            ("AI_ONLY", "NOT_REQUESTED", None, "NOT_CHECKED", "COMPLETED", "LOW"),
            id="ai-only",
        ),
        pytest.param(
            {"proof": registry_unavailable(), "extraction": "timeout"},
            {"code": CODE, "file": MATCHING_FILE_BYTES, "include_risk": True},
            ("REFERENCE_CHECK", "UNAVAILABLE", None, "NOT_CHECKED", "UNAVAILABLE", None),
            id="partial-double-outage",
        ),
    ],
)
def test_verification_logged(client, partner_headers, install, setup, request_kwargs, expected):
    install(**setup)
    before = log_count()
    response = post(client, partner_headers, **request_kwargs)
    assert response.status_code == 200, response.text
    body = response.json()
    row = logged_row(body["verificationId"])
    assert log_count() == before + 1
    assert row is not None
    columns = ("mode", "lookup", "lifecycle_status", "integrity_result", "risk_state", "risk_category")
    assert tuple(row[c] for c in columns) == expected
    assert {k: row[k] for k in expected_log(body)} == expected_log(body)
    assert row["partner_id"] == current_partner_id()
    assert isinstance(row["duration_ms"], int) and row["duration_ms"] >= 0
    assert row["created_at"] is not None


# Respons error (400 validasi, 401 token) tidak mencatat log verifikasi.
@pytest.mark.parametrize(
    ("headers", "request_kwargs", "status"),
    [
        (None, {}, 400),
        (None, {"file": MATCHING_FILE_BYTES}, 400),
        ({"Authorization": "Bearer token-salah"}, {"file": MATCHING_FILE_BYTES, "include_risk": True}, 401),
    ],
    ids=["no-input", "ai-only-without-risk", "bad-token"],
)
def test_error_responses_not_logged(client, partner_headers, install, headers, request_kwargs, status):
    install()
    before = log_count()
    response = post(client, headers or partner_headers, **request_kwargs)
    assert response.status_code == status, response.text
    assert log_count() == before


# Factory session sintetis yang gagal saat transaksi dibuka; pesannya memuat penanda yang tidak boleh tercatat.
class BrokenSessionFactory:
    """Meniru DB yang terkunci saat log verifikasi ditulis."""

    # Membuka transaksi selalu gagal dengan OperationalError.
    def begin(self):
        raise OperationalError("INSERT INTO verification_logs NILAI-RAHASIA", {}, Exception("database is locked"))


# Kegagalan tulis log tidak mengubah respons API-07 (tetap 200, hasil sama dengan contoh); hanya log ERROR
# verification.log_failed dengan nama tipe exception, tanpa pesan.
def test_log_write_failure_keeps_response(client, partner_headers, install, monkeypatch, caplog):
    install(proof=found_active(), analysis="low")
    monkeypatch.setattr(orchestrator, "get_session_factory", BrokenSessionFactory)
    with caplog.at_level(logging.WARNING):
        response = post(client, partner_headers, code=CODE, file=MATCHING_FILE_BYTES, include_risk=True)
    assert response.status_code == 200, response.text
    assert_matches_example(response.json(), "api-07.reference-match-ai.json")
    assert logged_row(response.json()["verificationId"]) is None
    [record] = [r for r in caplog.records if getattr(r, "event", None) == "verification.log_failed"]
    assert record.levelno == logging.ERROR
    logged = formatted_log(caplog, "verification.log_failed")
    assert logged["exception"] == "OperationalError"
    assert "NILAI-RAHASIA" not in json.dumps(logged) and "NILAI-RAHASIA" not in caplog.text


# Baris log tidak memuat isi berkas, teks dokumen hasil ekstraksi, hash berkas, kode referensi (utuh atau sebagian),
# maupun token partner.
def test_log_has_no_sensitive_values(client, partner_headers, install):
    install(proof=found_active())
    marked_file = b"%PDF-1.4\n%NILAI-RAHASIA-T106\n"
    response = post(client, partner_headers, code=CODE, file=marked_file, include_risk=True)
    assert response.status_code == 200, response.text
    row = logged_row(response.json()["verificationId"])
    assert row is not None and row["integrity_result"] == "MISMATCH"
    stored = json.dumps(row, default=str)
    extracted_text = load_example("internal/i-01.extraction-ok.json")["text"]
    sensitive = [
        "NILAI-RAHASIA",
        CODE,
        CODE.replace("-", ""),
        CODE.removeprefix("LTR-"),
        hashlib.sha256(marked_file).hexdigest(),
        get_settings().partner_token.get_secret_value(),
        *[line for line in extracted_text.splitlines() if len(line) > 8],
    ]
    assert [value for value in sensitive if value in stored] == []
