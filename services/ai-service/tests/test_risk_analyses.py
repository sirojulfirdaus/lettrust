# Owner: B (PIC 5) | Status: COMPLETE | Ref: PLAN T5-04; SA §7.3–§7.7, §10.8
"""Uji API-08 lewat aplikasi asli dengan 17 skenario bersama dan kontrak metode ekstraksi aditif."""

import json
import logging
from collections.abc import Iterator

import pytest
from conftest import INTERNAL_TOKEN
from fastapi.testclient import TestClient

from app.analysis import service
from app.analysis.mock_provider import SCENARIOS, LLMScenario, MockLLMProvider
from app.analysis.provider import ProviderError, ProviderQuotaExceeded, ProviderTimeout
from app.core.config import get_settings
from app.core.errors import ERROR_HTTP_STATUS, ErrorCode
from app.schemas import ExtractionMethod, RiskAnalysisRequest

PATH = "/internal/v1/risk-analyses"
HEADERS = {"X-Internal-Token": INTERNAL_TOKEN, "X-Request-ID": "req_T504TEST0000001"}


# Cache settings dibersihkan agar perubahan konfigurasi test tidak memengaruhi test lain.
@pytest.fixture(autouse=True)
def fresh_settings() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# Mengganti hanya antarmuka provider; validasi, router, middleware, dan error handler tetap asli.
def install_mock(monkeypatch: pytest.MonkeyPatch, mock: MockLLMProvider) -> None:
    monkeypatch.setattr(service, "get_provider", lambda _: mock)


# Semua skenario bersama harus memenuhi kode, kategori, error, jumlah drop, dan batas retry yang disepakati.
@pytest.mark.parametrize("scenario", SCENARIOS.values(), ids=lambda scenario: scenario.name)
def test_shared_scenarios_via_api(client: TestClient, monkeypatch: pytest.MonkeyPatch, scenario: LLMScenario) -> None:
    mock = scenario.provider()
    install_mock(monkeypatch, mock)
    response = client.post(PATH, json={"documentContent": scenario.document_text}, headers=HEADERS)
    payload = response.json()
    if scenario.expected_error:
        assert response.status_code == ERROR_HTTP_STATUS[ErrorCode(scenario.expected_error)]
        assert payload["error"]["code"] == scenario.expected_error
        assert set(payload) == {"requestId", "error"}
    else:
        assert response.status_code == 200
        assert payload["category"] == scenario.expected_category
        assert {item["code"] for item in payload["indicatorDetails"]} == scenario.expected_codes
        assert payload["meta"]["droppedIndicators"] == scenario.expected_dropped
        assert payload["meta"]["model"] == get_settings().llm_model
        assert payload["meta"]["promptVersion"] == get_settings().prompt_version
        assert "state" not in payload
    assert response.headers["X-Request-ID"] == HEADERS["X-Request-ID"]
    assert mock.pending == 0
    assert len(mock.received) == len(scenario.responses)
    if len(mock.received) == 2:
        assert mock.received[0] == mock.received[1]


# Output invalid hanya diulang satu kali walaupun provider masih menyediakan respons ketiga yang valid.
def test_invalid_output_never_causes_third_call(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    mock = MockLLMProvider("invalid", "invalid again", '{"indicators": [], "explanation": "uji"}')
    install_mock(monkeypatch, mock)
    response = client.post(PATH, json={"documentContent": "Surat sintetis."}, headers=HEADERS)
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "AI_OUTPUT_INVALID"
    assert len(mock.received) == 2
    assert mock.pending == 1


# Kegagalan provider pada percobaan kedua tetap memakai kode kegagalan itu dan tidak memicu retry tambahan.
@pytest.mark.parametrize(
    "error", [ProviderQuotaExceeded("private"), ProviderTimeout("private"), ProviderError("private")]
)
def test_provider_error_after_invalid_output_is_not_retried(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, error: ProviderError
) -> None:
    mock = MockLLMProvider("invalid", error, '{"indicators": [], "explanation": "uji"}')
    install_mock(monkeypatch, mock)
    response = client.post(PATH, json={"documentContent": "Surat sintetis."}, headers=HEADERS)
    assert response.status_code == ERROR_HTTP_STATUS[error.code]
    assert response.json()["error"]["code"] == error.code.value
    assert len(mock.received) == 2
    assert mock.pending == 1


# Request kosong, terlalu panjang, tipe salah, dan field asing ditolak sebelum provider dipilih.
@pytest.mark.parametrize(
    "body",
    [
        {},
        {"documentContent": ""},
        {"documentContent": " \n\t"},
        {"documentContent": 5},
        {"documentContent": "a" * 12001},
        {"documentContent": "surat", "referenceCode": "secret"},
    ],
)
def test_invalid_request_never_calls_provider(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, body: dict[str, object]
) -> None:
    mock = MockLLMProvider()
    install_mock(monkeypatch, mock)
    response = client.post(PATH, json=body, headers=HEADERS)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert not mock.received


# Panjang tepat AI_MAX_CHARS diterima dan batas yang diubah lewat settings tetap digunakan.
def test_configured_character_limit(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "ai_max_chars", 80)
    mock = MockLLMProvider('{"indicators": [], "explanation": "Tidak ditemukan pola dari daftar indikator."}')
    install_mock(monkeypatch, mock)
    assert client.post(PATH, json={"documentContent": "x" * 80}, headers=HEADERS).status_code == 200
    assert client.post(PATH, json={"documentContent": "x" * 81}, headers=HEADERS).status_code == 400
    assert len(mock.received) == 1


# Key kosong menghasilkan 503 terkontrol tanpa membuka koneksi SDK.
def test_unconfigured_provider_returns_safe_error(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    # Bila sampai membuat SDK client, penjagaan key kosong belum bekerja.
    def unexpected_client(**kwargs: object) -> None:
        pytest.fail("SDK tidak boleh dibuat tanpa key.")

    monkeypatch.setattr("app.analysis.provider.OpenAI", unexpected_client)
    response = client.post(PATH, json={"documentContent": "Surat sintetis."}, headers=HEADERS)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AI_PROVIDER_UNCONFIGURED"


# Autentikasi internal selalu diperiksa sebelum analisis dijalankan.
@pytest.mark.parametrize("headers", [{}, {"X-Internal-Token": "wrong-token"}])
def test_unauthorized_request_never_calls_provider(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, headers: dict[str, str]
) -> None:
    mock = MockLLMProvider()
    install_mock(monkeypatch, mock)
    assert client.post(PATH, json={"documentContent": "Surat sintetis."}, headers=headers).status_code == 401
    assert not mock.received


# Ketiga metode eksplisit dan request D2 tanpa metode mempunyai perilaku fuzzy sesuai keputusan Dws.
@pytest.mark.parametrize("method", [None, "TEXT_LAYER", "OCR", "MIXED"])
def test_extraction_method_controls_evidence_matching(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, method: str | None
) -> None:
    content = json.dumps(
        {
            "indicators": [{"code": "PAYMENT_REQUEST", "evidence": ["wajib membayar biaya administrasi"]}],
            "explanation": "Surat meminta biaya administrasi.",
        }
    )
    install_mock(monkeypatch, MockLLMProvider(content))
    body = {"documentContent": "Pelamar wajib membayar biaya adminlstrasi sebelum bekerja."}
    if method is not None:
        body["extractionMethod"] = method
    response = client.post(PATH, json=body, headers=HEADERS)
    assert response.status_code == 200
    payload = response.json()
    fuzzy = method in {"OCR", "MIXED"}
    assert payload["category"] == ("HIGH" if fuzzy else "LOW")
    assert payload["meta"]["droppedIndicators"] == (0 if fuzzy else 1)


# Nilai metode di luar enum termasuk null ditolak sebelum provider dipanggil.
@pytest.mark.parametrize("method", [None, "UNKNOWN", "ocr", 1])
def test_invalid_extraction_method_is_rejected(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, method: object
) -> None:
    mock = MockLLMProvider()
    install_mock(monkeypatch, mock)
    response = client.post(PATH, json={"documentContent": "surat", "extractionMethod": method}, headers=HEADERS)
    assert response.status_code == 400
    assert not mock.received


# Request lama tetap round-trip tanpa field tambahan; nilai metode eksplisit tetap terserialisasi.
def test_request_model_preserves_legacy_and_explicit_fields() -> None:
    legacy = {"documentContent": "Surat sintetis."}
    parsed = RiskAnalysisRequest.model_validate(legacy)
    assert parsed.extraction_method is ExtractionMethod.TEXT_LAYER
    assert parsed.model_dump(by_alias=True, mode="json") == legacy
    for method in ExtractionMethod:
        body = {**legacy, "extractionMethod": method.value}
        assert RiskAnalysisRequest.model_validate(body).model_dump(by_alias=True, mode="json") == body


# Latensi kedua request dijumlahkan dan versi prompt pada metadata sama dengan yang dikirim ke model.
def test_retry_latency_and_prompt_version(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "prompt_version", "pipeline-test-v2")
    mock = MockLLMProvider("invalid", '{"indicators": [], "explanation": "uji"}', latency_ms=13)
    install_mock(monkeypatch, mock)
    response = client.post(PATH, json={"documentContent": "Surat sintetis."}, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["meta"]["latencyMs"] == 26
    assert response.json()["meta"]["promptVersion"] == "pipeline-test-v2"
    assert "pipeline-test-v2" in mock.received[0][0]["content"]


# Kegagalan parse dan provider tidak menyalin input, nama field asing, atau pesan error ke log dan respons error.
@pytest.mark.parametrize("failure", ["invalid_json", "invalid_schema", "provider_error"])
def test_failed_analysis_does_not_leak_content(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
    failure: str,
) -> None:
    document = "private-document-canary"
    raw = "private-model-output-canary"
    if failure == "provider_error":
        mock = MockLLMProvider(ProviderError(raw))
    else:
        content = raw if failure == "invalid_json" else json.dumps({raw: document})
        mock = MockLLMProvider(content, content)
    install_mock(monkeypatch, mock)
    with caplog.at_level(logging.DEBUG):
        response = client.post(PATH, json={"documentContent": document}, headers=HEADERS)
    assert response.status_code in {502, 503}
    captured = capsys.readouterr()
    public = response.text + caplog.text + captured.out + captured.err
    assert document not in public
    assert raw not in public
