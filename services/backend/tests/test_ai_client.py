# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: PRD FR-05.01, FR-05.04, FR-05.09; SA §5.3.3, §7.2, §10.8, §17.1, §17.4
"""Test ai_client: model I-01/API-08 terhadap contoh internal dan pemetaan state AI dengan FakeAiService."""

import asyncio
import json
import logging

import httpx
import pytest
from fakes.ai_service import ANALYSIS_PATH, EXTRACTION_PATH, FakeAiService, assert_internal_headers
from fakes.contracts import example_index, load_example

from app.core.config import get_settings
from app.core.logging import JsonFormatter
from app.core.schemas import ErrorEnvelope
from app.modules.verifications import ai_client
from app.modules.verifications.schemas import RiskState

REQUEST_ID = "req_7K3M9QX2H4TDAB12"
FILE_BYTES = b"%PDF-1.4\n% offer letter sintetis untuk test ai_client\n%%EOF\n"
MODELS = {
    "ExtractionResponse": ai_client.ExtractionResponse,
    "RiskAnalysisRequest": ai_client.RiskAnalysisRequest,
    "RiskAnalysisResponse": ai_client.RiskAnalysisResponse,
    "ErrorEnvelope": ErrorEnvelope,
}
INTERNAL = [entry for entry in example_index() if entry.get("service") == "ai-service"]
# Bentuk riskAnalysis untuk state tanpa hasil diambil dari contoh API-07 publik.
API07_RISK = {
    ("UNAVAILABLE", "AI_SERVICE_UNAVAILABLE"): "api-07.ai-unavailable.json",
    ("UNAVAILABLE", "AI_QUOTA_EXCEEDED"): "api-07.ai-quota-exceeded.json",
    ("UNAVAILABLE", "AI_TIMEOUT"): "api-07.double-outage.json",
    ("NOT_PERFORMED", "DOCUMENT_CONTENT_UNAVAILABLE"): "api-07.ai-not-performed.json",
}


# Menjalankan pipeline terhadap transport fake dan mengembalikan riskAnalysis dalam bentuk JSON kontrak.
def run_pipeline(transport: httpx.AsyncBaseTransport) -> dict:
    result = asyncio.run(ai_client.run_risk_pipeline(FILE_BYTES, REQUEST_ID, transport=transport))
    return result.model_dump(by_alias=True, mode="json")


# Hasil tanpa analisis harus identik dengan riskAnalysis contoh API-07 yang sesuai.
def assert_matches_api07(risk: dict) -> None:
    example = API07_RISK[(risk["state"], risk["reason"])]
    assert risk == load_example(example)["riskAnalysis"]


# Setiap contoh internal yang dikonsumsi backend valid terhadap model backend dan round-trip identik.
@pytest.mark.parametrize("entry", [e for e in INTERNAL if e["schema"] in MODELS], ids=lambda e: e["file"])
def test_internal_example_matches_backend_model(entry):
    data = load_example(entry["file"])
    assert MODELS[entry["schema"]].model_validate(data).model_dump(by_alias=True, mode="json") == data


# Hanya contoh I-02 (dibaca modul health, bukan ai_client) yang tidak dimodelkan di sini.
def test_internal_examples_coverage():
    assert {e["schema"] for e in INTERNAL} - set(MODELS) == {"AiHealthResponse"}


# I-01 lalu API-08 dengan token internal, X-Request-ID diteruskan, dan timeout dari config; hasil COMPLETED.
def test_pipeline_completed_high():
    fake = FakeAiService(extraction="ok", analysis="high")
    risk = run_pipeline(fake.transport())
    extraction = load_example("internal/i-01.extraction-ok.json")
    analysis = load_example("internal/api-08.response-high.json")
    assert [r.url.path for r in fake.requests] == [EXTRACTION_PATH, ANALYSIS_PATH]
    for request in fake.requests:
        assert_internal_headers(request, request_id=REQUEST_ID)
    settings = get_settings()
    assert fake.requests[0].extensions["timeout"]["read"] == settings.ai_extraction_timeout_seconds
    assert fake.requests[1].extensions["timeout"]["read"] == settings.ai_analysis_timeout_seconds
    assert FILE_BYTES in fake.requests[0].content
    assert json.loads(fake.requests[1].content) == {"documentContent": extraction["text"]}
    assert risk == {
        "state": "COMPLETED",
        "reason": None,
        "category": "HIGH",
        "indicators": analysis["indicators"],
        "indicatorDetails": analysis["indicatorDetails"],
        "explanation": analysis["explanation"],
        "recommendation": analysis["recommendation"],
        "extractionMethod": "MIXED",
        "contentTruncated": False,
        "pagesAnalyzed": 2,
        "pagesTotal": 2,
    }


# Kategori dan metadata ekstraksi diambil apa adanya dari ai-service (tidak dihitung ulang backend).
@pytest.mark.parametrize("analysis", ["medium", "low"])
def test_pipeline_completed_categories(analysis):
    risk = run_pipeline(FakeAiService(extraction="ok_truncated", analysis=analysis).transport())
    extraction = load_example("internal/i-01.extraction-ok-truncated.json")
    assert risk["state"] == "COMPLETED"
    assert risk["category"] == load_example(f"internal/api-08.response-{analysis}.json")["category"]
    assert risk["contentTruncated"] is True
    assert (risk["pagesAnalyzed"], risk["pagesTotal"]) == (extraction["pagesProcessed"], extraction["pagesTotal"])


# NO_CONTENT (teks tidak terbaca / PDF rusak) → NOT_PERFORMED tanpa memanggil API-08.
@pytest.mark.parametrize("extraction", ["no_content", "unreadable"])
def test_no_content_not_performed(extraction):
    fake = FakeAiService(extraction=extraction)
    risk = run_pipeline(fake.transport())
    assert_matches_api07(risk)
    assert risk["state"] == RiskState.NOT_PERFORMED
    assert [r.url.path for r in fake.requests] == [EXTRACTION_PATH]


# Kegagalan I-01 (transport, 401, 5xx, 4xx tak terduga) → UNAVAILABLE; API-08 tidak dipanggil.
@pytest.mark.parametrize(
    ("mode", "reason"),
    [
        ("timeout", "AI_TIMEOUT"),
        ("unavailable", "AI_SERVICE_UNAVAILABLE"),
        ("unauthorized", "AI_SERVICE_UNAVAILABLE"),
        ("server_error", "AI_SERVICE_UNAVAILABLE"),
        ("validation_error", "AI_SERVICE_UNAVAILABLE"),
        ("file_too_large", "AI_SERVICE_UNAVAILABLE"),
        ("unsupported_media_type", "AI_SERVICE_UNAVAILABLE"),
        ("empty_file", "AI_SERVICE_UNAVAILABLE"),
    ],
)
def test_extraction_failures(mode, reason):
    fake = FakeAiService(extraction=mode)
    risk = run_pipeline(fake.transport())
    assert (risk["state"], risk["reason"], risk["category"]) == ("UNAVAILABLE", reason, None)
    assert [r.url.path for r in fake.requests] == [EXTRACTION_PATH]


# Kegagalan API-08 dipetakan sesuai SA §5.3.3; tidak ada fallback kategori.
@pytest.mark.parametrize(
    ("mode", "reason"),
    [
        ("timeout", "AI_TIMEOUT"),
        ("provider_timeout", "AI_TIMEOUT"),
        ("unavailable", "AI_SERVICE_UNAVAILABLE"),
        ("unauthorized", "AI_SERVICE_UNAVAILABLE"),
        ("server_error", "AI_SERVICE_UNAVAILABLE"),
        ("validation_error", "AI_SERVICE_UNAVAILABLE"),
        ("unconfigured", "AI_SERVICE_UNAVAILABLE"),
        ("provider_error", "AI_SERVICE_UNAVAILABLE"),
        ("quota_exceeded", "AI_QUOTA_EXCEEDED"),
        ("output_invalid", "AI_OUTPUT_INVALID"),
    ],
)
def test_analysis_failures(mode, reason):
    fake = FakeAiService(extraction="ok", analysis=mode)
    risk = run_pipeline(fake.transport())
    assert (risk["state"], risk["reason"], risk["category"]) == ("UNAVAILABLE", reason, None)
    assert risk["indicators"] == [] and risk["extractionMethod"] is None
    if (risk["state"], risk["reason"]) in API07_RISK:
        assert_matches_api07(risk)
    assert [r.url.path for r in fake.requests] == [EXTRACTION_PATH, ANALYSIS_PATH]


# Respons ai-service yang melanggar kontrak (skema salah, kode indikator di luar taksonomi, error tanpa envelope)
# → UNAVAILABLE / AI_SERVICE_UNAVAILABLE, bukan COMPLETED.
@pytest.mark.parametrize("defect", ["extraction_schema", "unknown_indicator", "gateway_without_envelope"])
def test_contract_violations_unavailable(defect):
    extraction = load_example("internal/i-01.extraction-ok.json")
    analysis = load_example("internal/api-08.response-high.json")
    if defect == "extraction_schema":
        extraction = {**extraction, "unexpected": True}
    if defect == "unknown_indicator":
        analysis["indicatorDetails"][0]["code"] = "NOT_IN_TAXONOMY"

    # Handler transport kecil: I-01 dan API-08 mengembalikan respons cacat sesuai skenario.
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == EXTRACTION_PATH:
            return httpx.Response(200, json=extraction)
        if defect == "gateway_without_envelope":
            return httpx.Response(502, text="Bad Gateway")
        return httpx.Response(200, json=analysis)

    risk = run_pipeline(httpx.MockTransport(handler))
    assert (risk["state"], risk["reason"], risk["category"]) == ("UNAVAILABLE", "AI_SERVICE_UNAVAILABLE", None)


# Mengambil satu record ai.pipeline_failed dan memformatnya dengan JsonFormatter produksi.
def pipeline_failed_log(caplog) -> dict:
    [record] = [r for r in caplog.records if getattr(r, "event", None) == "ai.pipeline_failed"]
    return json.loads(JsonFormatter(service="backend").format(record))


# Pelanggaran skema (termasuk body bukan JSON dan OK tanpa teks) dicatat sebagai reason=schema_violation dengan
# lokasi field saja; key tak dikenal ditulis `<unknown_field>`, nama key maupun nilainya tidak pernah disalin.
# `fields=None` berarti pelanggaran tanpa lokasi field sehingga key `fields` tidak muncul di log.
@pytest.mark.parametrize(
    ("defect", "path", "fields"),
    [
        ("extraction_extra_field", EXTRACTION_PATH, ["<unknown_field>"]),
        ("analysis_nested_extra_field", ANALYSIS_PATH, ["meta.<unknown_field>"]),
        ("analysis_missing_field", ANALYSIS_PATH, ["explanation"]),
        ("unknown_indicator", ANALYSIS_PATH, ["indicatorDetails.0.code"]),
        ("extraction_ok_text_null", EXTRACTION_PATH, ["text"]),
        ("extraction_ok_text_empty", EXTRACTION_PATH, ["text"]),
        ("extraction_not_json", EXTRACTION_PATH, None),
        ("analysis_not_json", ANALYSIS_PATH, None),
    ],
)
def test_schema_violation_logs_field_locations(caplog, defect, path, fields):
    extraction = load_example("internal/i-01.extraction-ok.json")
    analysis = load_example("internal/api-08.response-high.json")
    if defect == "extraction_extra_field":
        extraction["KUNCI-RAHASIA-EKSTRAKSI"] = "NILAI-RAHASIA-EKSTRAKSI"
    if defect == "analysis_nested_extra_field":
        analysis["meta"]["KUNCI-RAHASIA-META"] = "NILAI-RAHASIA-META"
    if defect == "analysis_missing_field":
        del analysis["explanation"]
    if defect == "unknown_indicator":
        analysis["indicatorDetails"][0]["code"] = "NILAI-RAHASIA-KODE"
    if defect == "extraction_ok_text_null":
        extraction["text"] = None
    if defect == "extraction_ok_text_empty":
        extraction["text"] = ""

    # I-01 dan API-08 mengembalikan 200 dengan body yang melanggar skema sesuai skenario.
    def handler(request: httpx.Request) -> httpx.Response:
        if defect.endswith("not_json") and request.url.path == path:
            return httpx.Response(200, text="<html>NILAI-RAHASIA bukan JSON</html>")
        return httpx.Response(200, json=extraction if request.url.path == EXTRACTION_PATH else analysis)

    with caplog.at_level(logging.WARNING):
        risk = run_pipeline(httpx.MockTransport(handler))
    assert (risk["state"], risk["reason"], risk["category"]) == ("UNAVAILABLE", "AI_SERVICE_UNAVAILABLE", None)
    logged = pipeline_failed_log(caplog)
    assert logged["reason"] == "schema_violation"
    assert logged.get("fields") == fields
    assert (logged["path"], logged["status"], logged["errorCode"]) == (path, 200, "AI_SERVICE_UNAVAILABLE")
    for marker in ("NILAI-RAHASIA", "KUNCI-RAHASIA"):
        assert marker not in json.dumps(logged) and marker not in caplog.text


# Body yang gagal di-decode (gzip rusak → httpx.DecodingError) dipetakan seperti kegagalan transport: UNAVAILABLE
# tanpa schema_violation, dan pipeline tidak meneruskan exception.
@pytest.mark.parametrize("path", [EXTRACTION_PATH, ANALYSIS_PATH])
def test_decoding_error_unavailable(caplog, path):
    extraction = load_example("internal/i-01.extraction-ok.json")

    # Endpoint yang diuji mengirim header gzip dengan body bukan gzip; stream dibaca client, bukan di handler.
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == path:
            headers = {"Content-Type": "application/json", "Content-Encoding": "gzip"}
            return httpx.Response(200, headers=headers, stream=httpx.ByteStream(b"bukan-gzip"))
        return httpx.Response(200, json=extraction)

    with caplog.at_level(logging.WARNING):
        risk = run_pipeline(httpx.MockTransport(handler))
    assert (risk["state"], risk["reason"], risk["category"]) == ("UNAVAILABLE", "AI_SERVICE_UNAVAILABLE", None)
    logged = pipeline_failed_log(caplog)
    assert logged["path"] == path
    assert "status" not in logged and "reason" not in logged and "fields" not in logged


# Kegagalan non-skema (mis. kuota) tidak diberi reason schema_violation.
def test_non_schema_failure_has_no_schema_reason(caplog):
    with caplog.at_level(logging.WARNING):
        run_pipeline(FakeAiService(extraction="ok", analysis="quota_exceeded").transport())
    logged = pipeline_failed_log(caplog)
    assert "reason" not in logged and "fields" not in logged


# Log kegagalan hanya memuat reason/path/status; isi berkas, teks ekstraksi, dan token internal tidak tercatat.
def test_failure_log_has_no_content(caplog, capfd):
    extracted_text = load_example("internal/i-01.extraction-ok.json")["text"]
    with caplog.at_level(logging.DEBUG):
        run_pipeline(FakeAiService(extraction="ok", analysis="quota_exceeded").transport())
    captured = capfd.readouterr()
    token = get_settings().internal_api_token.get_secret_value()
    records = [r for r in caplog.records if getattr(r, "event", None) == "ai.pipeline_failed"]
    assert len(records) == 1
    assert (records[0].errorCode, records[0].path, records[0].status) == ("AI_QUOTA_EXCEEDED", ANALYSIS_PATH, 503)
    for text in (caplog.text, captured.out, captured.err):
        assert extracted_text not in text
        assert "offer letter sintetis" not in text
        assert token not in text
