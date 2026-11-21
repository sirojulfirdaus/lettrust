# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: SA §7.3–§7.6; PRD §8.4, §8.5
"""Test MockLLMProvider dan konsistensi skenario siap pakai terhadap taksonomi dan aturan skoring PRD."""

import json
import unicodedata

import pytest

from app.analysis.mock_provider import SCENARIOS, LLMScenario, MockLLMProvider
from app.analysis.provider import LLMProvider, ProviderError, ProviderQuotaExceeded
from app.analysis.taxonomy import TAXONOMY

MESSAGES = [{"role": "system", "content": "instruksi"}, {"role": "user", "content": "<document>x</document>"}]
ERROR_BY_TYPE = {
    "ProviderQuotaExceeded": "AI_QUOTA_EXCEEDED",
    "ProviderTimeout": "AI_TIMEOUT",
    "ProviderError": "AI_PROVIDER_ERROR",
    "ProviderUnconfigured": "AI_PROVIDER_UNCONFIGURED",
}


# Normalisasi sederhana SA §7.5 (NFKC, lowercase, whitespace tunggal) untuk memeriksa data skenario.
def normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).lower().split())


# Kategori menurut PRD §8.5 dihitung dari kode tervalidasi (pemeriksaan konsistensi data skenario saja).
def category_for(codes: frozenset[str]) -> str:
    severities = [TAXONOMY[c].severity.value for c in codes]
    if "HIGH" in severities:
        return "HIGH"
    if "MEDIUM" in severities or severities.count("LOW") >= 2:
        return "MEDIUM"
    return "LOW"


# Respons terjadwal dikonsumsi berurutan; pesan dicatat sebagai salinan; tanpa respons → AssertionError.
def test_scripted_responses_and_recording():
    messages = [dict(m) for m in MESSAGES]
    provider: LLMProvider = MockLLMProvider("satu", latency_ms=7)
    provider.queue("dua")
    first = provider.complete(messages)
    messages[0]["content"] = "diubah setelah panggilan"
    assert (first.content, first.latency_ms) == ("satu", 7)
    assert provider.complete(messages).content == "dua"
    assert provider.received[0][0]["content"] == "instruksi"
    assert provider.pending == 0
    with pytest.raises(AssertionError):
        provider.complete(messages)


# Exception terjadwal dilempar apa adanya; tipe respons lain ditolak.
def test_scripted_error_and_type_check():
    provider = MockLLMProvider(ProviderQuotaExceeded("429"))
    with pytest.raises(ProviderQuotaExceeded):
        provider.complete(MESSAGES)
    with pytest.raises(TypeError):
        provider.queue({"bukan": "string"})


# Skenario wajib: tiap tingkat, tanpa indikator, kutipan palsu, output rusak, kode asing, 429, timeout, unavailable.
def test_required_scenarios_present():
    required = {
        "all_severities",
        "no_indicators",
        "quote_not_in_document",
        "malformed_json_twice",
        "unknown_indicator_code",
        "rate_limited",
        "timeout",
        "provider_unavailable",
    }
    assert required <= set(SCENARIOS)
    severities = {TAXONOMY[c].severity.value for c in SCENARIOS["all_severities"].expected_codes}
    assert severities == {"HIGH", "MEDIUM", "LOW"}


# Data skenario konsisten: kutipan indikator yang diharapkan ada di dokumen; kategori sesuai PRD §8.5; error sesuai SA.
@pytest.mark.parametrize("scenario", SCENARIOS.values(), ids=lambda s: s.name)
def test_scenario_consistency(scenario: LLMScenario):
    if scenario.expected_error:
        assert scenario.expected_category is None and not scenario.expected_codes
        last = scenario.responses[-1]
        if isinstance(last, ProviderError):
            assert ERROR_BY_TYPE[type(last).__name__] == scenario.expected_error
            assert len(scenario.responses) == 1, "tidak ada retry untuk kegagalan provider (SA §7.4.1)"
        else:
            assert len(scenario.responses) == 2, "output tidak valid diulang tepat satu kali (SA §7.3)"
        return
    output = json.loads(scenario.responses[-1])
    document = normalize(scenario.document_text)
    valid, dropped = set(), 0
    for indicator in output["indicators"]:
        quotes_found = [q for q in indicator["evidence"] if normalize(q) in document]
        if indicator["code"] in TAXONOMY and quotes_found:
            valid.add(indicator["code"])
        else:
            dropped += 1
    assert valid == scenario.expected_codes
    assert dropped == scenario.expected_dropped
    assert scenario.expected_category == category_for(scenario.expected_codes)
    assert scenario.provider().complete(MESSAGES).content == scenario.responses[0]
