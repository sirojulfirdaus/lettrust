# Owner: B (PIC 5) | Status: COMPLETE | Ref: PLAN T5-04; SA §7.7; FR-05.07
"""Uji label kanonis, penjelasan yang mengikuti bukti, dan rekomendasi deterministik."""

import pytest

from app.analysis.compose import build_recommendation, compose_result
from app.analysis.taxonomy import TAXONOMY
from app.analysis.validator import ValidatedIndicator
from app.schemas import AnalysisMeta, RiskCategory


# Menyediakan metadata sintetis tanpa key atau identitas dokumen.
def analysis_meta(dropped: int = 0) -> AnalysisMeta:
    return AnalysisMeta(model="synthetic-model", prompt_version="test-v1", latency_ms=7, dropped_indicators=dropped)


# Rekomendasi selalu meminta konfirmasi kanal resmi dan menambahkan larangan sesuai indikator.
@pytest.mark.parametrize(
    ("category", "codes", "payment", "sensitive", "low_note"),
    [
        (RiskCategory.LOW, set(), False, False, True),
        (RiskCategory.LOW, {"VAGUE_JOB_DETAILS"}, False, False, True),
        (RiskCategory.MEDIUM, {"URGENCY_PRESSURE"}, False, False, False),
        (RiskCategory.HIGH, {"PAYMENT_REQUEST"}, True, False, False),
        (RiskCategory.HIGH, {"SENSITIVE_DATA_REQUEST"}, False, True, False),
        (RiskCategory.HIGH, {"PAYMENT_REQUEST", "SENSITIVE_DATA_REQUEST"}, True, True, False),
    ],
)
def test_recommendation_templates(
    category: RiskCategory, codes: set[str], payment: bool, sensitive: bool, low_note: bool
) -> None:
    recommendation = build_recommendation(category, codes)
    assert "kontak resmi perusahaan yang Anda cari sendiri" in recommendation
    assert ("Jangan melakukan pembayaran" in recommendation) is payment
    assert ("Jangan memberikan OTP" in recommendation) is sensitive
    assert ("Risiko rendah tidak menjamin surat aman." in recommendation) is low_note


# Label dan severity selalu berasal dari taksonomi, sedangkan kutipan ditampilkan sebagai teks biasa.
def test_response_uses_canonical_labels_and_camel_case() -> None:
    quote = "pelamar wajib membayar deposit seragam"
    result = compose_result(
        [ValidatedIndicator("PAYMENT_REQUEST", (quote,))],
        RiskCategory.HIGH,
        "Surat meminta pelamar membayar deposit seragam.",
        analysis_meta(),
    )
    payload = result.model_dump(by_alias=True, mode="json")
    assert payload["indicators"] == [f"{TAXONOMY['PAYMENT_REQUEST'].label}: “{quote}”"]
    assert payload["indicatorDetails"] == [
        {"code": "PAYMENT_REQUEST", "label": TAXONOMY["PAYMENT_REQUEST"].label, "severity": "HIGH", "evidence": [quote]}
    ]
    assert payload["explanation"] == "Surat meminta pelamar membayar deposit seragam."
    assert payload["meta"] == {
        "model": "synthetic-model",
        "promptVersion": "test-v1",
        "latencyMs": 7,
        "droppedIndicators": 0,
    }
    assert "state" not in payload


# Teks model yang kosong, panjang, berlebihan, atau mengandung vonis diganti dengan label indikator tervalidasi.
@pytest.mark.parametrize(
    "explanation",
    [None, "", "   ", "x" * 601, "Satu. Dua. Tiga. Empat.", "Surat ini palsu.", "This is a safe offer."],
)
def test_invalid_explanation_uses_template(explanation: str | None) -> None:
    result = compose_result(
        [ValidatedIndicator("URGENCY_PRESSURE", ("kuota terbatas",))],
        RiskCategory.MEDIUM,
        explanation,
        analysis_meta(),
    )
    assert result.explanation == f"Indikator yang ditemukan: {TAXONOMY['URGENCY_PRESSURE'].label}."


# Setelah indikator dibuang, penjelasan tidak boleh tetap menyatakan indikator yang gagal dibuktikan.
def test_dropped_indicator_removes_stale_model_explanation() -> None:
    result = compose_result([], RiskCategory.LOW, "Pelamar diminta membayar biaya administrasi.", analysis_meta(1))
    assert result.explanation == "Tidak ditemukan pola dari daftar indikator."
    assert result.indicators == result.indicator_details == []
    assert "Risiko rendah tidak menjamin surat aman." in result.recommendation


# Bila hanya sebagian indikator bertahan, penjelasan disusun ulang dari bagian yang tervalidasi.
def test_partial_drop_explanation_lists_only_remaining_indicators() -> None:
    result = compose_result(
        [ValidatedIndicator("URGENCY_PRESSURE", ("kuota terbatas",))],
        RiskCategory.MEDIUM,
        "Surat meminta biaya administrasi dan memberi tekanan kuota.",
        analysis_meta(1),
    )
    assert "biaya administrasi" not in result.explanation
    assert TAXONOMY["URGENCY_PRESSURE"].label in result.explanation
