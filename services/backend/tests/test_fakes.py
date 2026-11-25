# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: SA §5.3, §5.6, §10.7, §10.8
"""Test fake bersama: pembaca bukti (API-07) dan ai-service HTTP palsu."""

import asyncio
import hashlib

import httpx
import pytest
from fakes import proofs as fake_proofs
from fakes.ai_service import (
    ANALYSIS_PATH,
    EXTRACTION_PATH,
    HEALTH_PATH,
    INTERNAL_TOKEN,
    FakeAiService,
    assert_internal_headers,
)
from fakes.contracts import load_example

from app.core.config import get_settings
from app.modules.proofs import service as proofs_service

HEADERS = {"X-Internal-Token": INTERNAL_TOKEN, "X-Request-ID": "req_TESTFAKEAI000001"}
PDF_FILES = {"file": ("offer.pdf", b"%PDF-1.4\n%sintetis\n", "application/pdf")}


# Factory proof reader identik dengan proofCheck pada contoh API-07 yang relevan.
@pytest.mark.parametrize(
    ("factory", "example"),
    [
        (fake_proofs.found_active, "api-07.reference-match-ai.json"),
        (fake_proofs.registry_unavailable, "api-07.registry-unavailable.json"),
        (fake_proofs.not_requested, "api-07.ai-only.json"),
        (fake_proofs.not_found, "api-07.not-found-code-only.json"),
        (fake_proofs.found_revoked, "api-07.revoked-mismatch.json"),
        (fake_proofs.found_issuer_not_verified, "api-07.issuer-not-verified.json"),
    ],
)
def test_proof_factories_match_examples(factory, example):
    read = factory()
    assert read.proof_check.model_dump(by_alias=True, mode="json") == load_example(example)["proofCheck"]
    found = read.proof_check.lookup.value == "FOUND"
    assert (read.registry_document_hash is not None) == found


# Hash registry fake = SHA-256 berkas MATCHING; berkas MISMATCHING berbeda.
def test_fake_hashes():
    assert fake_proofs.REGISTRY_DOCUMENT_HASH == hashlib.sha256(fake_proofs.MATCHING_FILE_BYTES).hexdigest()
    assert hashlib.sha256(fake_proofs.MISMATCHING_FILE_BYTES).hexdigest() != fake_proofs.REGISTRY_DOCUMENT_HASH


# FakeProofReader terpasang di atribut modul proofs.service dan mencatat panggilan; default NOT_FOUND.
def test_install_fake_proof_reader(monkeypatch):
    reader = fake_proofs.install_fake_proof_reader(
        monkeypatch, fake_proofs.FakeProofReader({"LTR-7K3M-9QX2-H4TD": fake_proofs.found_active()})
    )
    found = asyncio.run(proofs_service.read_proof_for_verification("LTR-7K3M-9QX2-H4TD"))
    missing = asyncio.run(proofs_service.read_proof_for_verification("LTR-0000-0000-0000"))
    assert found.proof_check.lookup.value == "FOUND"
    assert missing.proof_check.lookup.value == "NOT_FOUND"
    assert reader.calls == ["LTR-7K3M-9QX2-H4TD", "LTR-0000-0000-0000"]


# Menjalankan satu request ke fake ai-service dan mengembalikan respons.
def call(fake: FakeAiService, method: str, path: str, **kwargs) -> httpx.Response:
    with httpx.Client(base_url=get_settings().ai_service_url, transport=fake.transport()) as client:
        return client.request(method, path, **kwargs)


# Mode sukses mengembalikan contoh internal dan memantulkan X-Request-ID.
def test_success_modes():
    fake = FakeAiService(extraction="no_content", analysis="low", health="unconfigured")
    extraction = call(fake, "POST", EXTRACTION_PATH, files=PDF_FILES, headers=HEADERS)
    analysis = call(fake, "POST", ANALYSIS_PATH, json={"documentContent": "teks"}, headers=HEADERS)
    health = call(fake, "GET", HEALTH_PATH)
    assert extraction.json() == load_example("internal/i-01.extraction-no-content.json")
    assert analysis.json()["category"] == "LOW"
    assert health.json()["llm"] == "unconfigured"
    assert extraction.headers["X-Request-ID"] == "req_TESTFAKEAI000001"
    for request in fake.requests[:2]:
        assert_internal_headers(request, request_id="req_TESTFAKEAI000001")


# Token internal salah/tidak ada → 401 UNAUTHENTICATED; health tetap publik.
def test_token_required():
    fake = FakeAiService()
    response = call(fake, "POST", ANALYSIS_PATH, json={"documentContent": "teks"}, headers={"X-Request-ID": "req_A"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"
    assert response.json()["requestId"] == "req_A"
    assert call(fake, "GET", HEALTH_PATH).status_code == 200
    with pytest.raises(AssertionError):
        assert_internal_headers(fake.requests[0])


# Body tidak sesuai bentuk (I-01 bukan multipart, API-08 tanpa documentContent) → 400 VALIDATION_ERROR.
def test_body_validation():
    fake = FakeAiService()
    assert call(fake, "POST", EXTRACTION_PATH, content=b"x", headers=HEADERS).status_code == 400
    assert call(fake, "POST", ANALYSIS_PATH, json={"documentContent": ""}, headers=HEADERS).status_code == 400


# D-20: extractionMethod API-08 opsional; hanya TEXT_LAYER/OCR/MIXED diterima, null atau field asing → 400.
@pytest.mark.parametrize(
    ("extra", "status"),
    [
        ({}, 200),
        ({"extractionMethod": "OCR"}, 200),
        ({"extractionMethod": None}, 400),
        ({"extractionMethod": "PHOTO"}, 400),
        ({"category": "LOW"}, 400),
    ],
)
def test_analysis_extraction_method(extra, status):
    body = {"documentContent": "teks", **extra}
    assert call(FakeAiService(), "POST", ANALYSIS_PATH, json=body, headers=HEADERS).status_code == status


# Mode error AI dipetakan ke status dan kode SA §10.3.
@pytest.mark.parametrize(
    ("mode", "status", "code"),
    [
        ("validation_error", 400, "VALIDATION_ERROR"),
        ("unauthorized", 401, "UNAUTHENTICATED"),
        ("server_error", 500, "INTERNAL_ERROR"),
        ("quota_exceeded", 503, "AI_QUOTA_EXCEEDED"),
        ("provider_error", 503, "AI_PROVIDER_ERROR"),
        ("unconfigured", 503, "AI_PROVIDER_UNCONFIGURED"),
        ("output_invalid", 502, "AI_OUTPUT_INVALID"),
        ("provider_timeout", 504, "AI_TIMEOUT"),
    ],
)
def test_error_modes(mode, status, code):
    response = call(FakeAiService(analysis=mode), "POST", ANALYSIS_PATH, json={"documentContent": "x"}, headers=HEADERS)
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert response.json()["requestId"] == HEADERS["X-Request-ID"]


# Timeout dan koneksi ditolak muncul sebagai exception httpx di sisi client.
def test_transport_failures():
    with pytest.raises(httpx.ReadTimeout):
        call(FakeAiService(extraction="timeout"), "POST", EXTRACTION_PATH, files=PDF_FILES, headers=HEADERS)
    with pytest.raises(httpx.ConnectError):
        call(
            FakeAiService(analysis="unavailable"), "POST", ANALYSIS_PATH, json={"documentContent": "x"}, headers=HEADERS
        )
    with pytest.raises(ValueError):
        FakeAiService(analysis="mode-asing")


# Mode yang tidak mungkin dikembalikan endpoint nyata ditolak (AI_* hanya API-08; health tidak pernah error HTTP).
@pytest.mark.parametrize(
    "kwargs",
    [{"extraction": "quota_exceeded"}, {"analysis": "file_too_large"}, {"health": "validation_error"}],
)
def test_impossible_modes_rejected(kwargs):
    with pytest.raises(ValueError):
        FakeAiService(**kwargs)
