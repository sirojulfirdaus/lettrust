# Owner: B (PIC 5) | Status: COMPLETE | Ref: PLAN T5-04; SA §7.3, §7.5
"""Uji skema model, taksonomi tertutup, dan pencocokan bukti dengan OCR eksplisit."""

import json
import traceback

import pytest

from app.analysis.validator import normalize, parse_model_output, validate_indicators


# NFKC, lowercase, dan whitespace diterapkan sebelum pencocokan bukti.
def test_normalize_unicode_and_whitespace() -> None:
    assert normalize("  ＢＩＡＹＡ\u00a0Administrasi\n\tRp５００．０００  ") == "biaya administrasi rp500.000"


# Skema tidak memberi model kendali atas kategori/rekomendasi dan tidak melakukan coercion tipe.
@pytest.mark.parametrize(
    "raw",
    [
        "not-json",
        '```json\n{"indicators": [], "explanation": "uji"}\n```',
        "[]",
        '{"indicators": []}',
        '{"indicators": "PAYMENT_REQUEST", "explanation": "uji"}',
        '{"indicators": [], "explanation": 12}',
        '{"indicators": [], "explanation": "uji", "category": "HIGH"}',
        '{"indicators": [{"code": 1, "evidence": []}], "explanation": "uji"}',
        '{"indicators": [{"code": "PAYMENT_REQUEST", "evidence": "biaya"}], "explanation": "uji"}',
        '{"indicators": [{"code": "PAYMENT_REQUEST", "evidence": [1]}], "explanation": "uji"}',
        '{"indicators": [{"code": "PAYMENT_REQUEST", "evidence": [], "severity": "LOW"}], "explanation": "uji"}',
    ],
)
def test_invalid_output_raises_safe_error(raw: str) -> None:
    with pytest.raises(ValueError, match="tidak sesuai skema") as error:
        parse_model_output(raw)
    assert raw not in "".join(traceback.format_exception(error.value))


# Kode asing lolos tahap bentuk JSON agar dibuang sebagai indikator, bukan memicu retry seluruh output.
def test_unknown_code_is_filtered_after_schema_parsing() -> None:
    parsed = parse_model_output(
        json.dumps(
            {
                "indicators": [
                    {"code": "UNKNOWN_CODE", "evidence": ["transfer biaya administrasi"]},
                    {"code": "PAYMENT_REQUEST", "evidence": ["transfer biaya administrasi"]},
                ],
                "explanation": "Surat meminta biaya administrasi.",
            }
        )
    )
    accepted, dropped = validate_indicators(parsed["indicators"], "transfer biaya administrasi", None, 90)
    assert [item.code for item in accepted] == ["PAYMENT_REQUEST"]
    assert dropped == 1


# Bukti yang hanya berbeda Unicode, kapital, atau whitespace diterima dengan kutipan asli tetap dipertahankan.
def test_exact_match_uses_normalization_and_keeps_quote() -> None:
    quote = "Ｂｉａｙａ\n ADMINISTRASI"
    accepted, dropped = validate_indicators(
        [{"code": "PAYMENT_REQUEST", "evidence": [quote]}],
        "Silakan membayar biaya administrasi sebelum bergabung.",
        "TEXT_LAYER",
        90,
    )
    assert accepted[0].evidence == (quote,)
    assert dropped == 0


# Kutipan terlalu pendek, kosong, dan tidak ada dalam dokumen dibuang tanpa memengaruhi kode lain.
def test_unsubstantiated_and_short_evidence_are_dropped() -> None:
    accepted, dropped = validate_indicators(
        [
            {"code": "PAYMENT_REQUEST", "evidence": [" ", "bayar", "transfer biaya palsu"]},
            {"code": "SENSITIVE_DATA_REQUEST", "evidence": []},
            {"code": "URGENCY_PRESSURE", "evidence": ["kuota terbatas"]},
        ],
        "Konfirmasi segera karena kuota terbatas.",
        None,
        90,
    )
    assert [item.code for item in accepted] == ["URGENCY_PRESSURE"]
    assert dropped == 2


# Batas delapan karakter dihitung setelah normalisasi, bukan panjang whitespace mentah.
def test_evidence_minimum_length_is_normalized() -> None:
    accepted, dropped = validate_indicators(
        [
            {"code": "PAYMENT_REQUEST", "evidence": ["  abc   def  "]},
            {"code": "URGENCY_PRESSURE", "evidence": ["abcdefgh"]},
        ],
        "abc def abcdefgh",
        None,
        90,
    )
    assert [item.code for item in accepted] == ["URGENCY_PRESSURE"]
    assert dropped == 1


# Typo kecil hanya ditoleransi dengan metode OCR/MIXED yang diketahui.
@pytest.mark.parametrize("method", [None, "TEXT_LAYER", "OCR", "MIXED", "UNKNOWN"])
def test_fuzzy_matching_requires_ocr_method(method: str | None) -> None:
    accepted, dropped = validate_indicators(
        [{"code": "PAYMENT_REQUEST", "evidence": ["wajib membayar biaya administrasi"]}],
        "Pelamar wajib membayar biaya adminlstrasi sebelum bekerja.",
        method,
        90,
    )
    assert bool(accepted) is (method in {"OCR", "MIXED"})
    assert dropped == (0 if accepted else 1)


# Ambang fuzzy dari konfigurasi berlaku; bukti berbeda satu karakter tidak memenuhi ambang 100.
def test_fuzzy_threshold_is_respected() -> None:
    raw = [{"code": "PAYMENT_REQUEST", "evidence": ["wajib membayar biaya administrasi"]}]
    document = "Pelamar wajib membayar biaya adminlstrasi sebelum bekerja."
    assert validate_indicators(raw, document, "OCR", 90)[1] == 0
    assert validate_indicators(raw, document, "OCR", 100)[1] == 1
    assert validate_indicators(raw, "Penawaran bekerja tanpa biaya kepada pelamar.", "OCR", 90)[1] == 1


# Bukti berulang tidak menggandakan indikator; maksimal tiga kutipan unik dipertahankan per kode.
def test_duplicate_codes_merge_up_to_three_distinct_quotes() -> None:
    quotes = ["biaya administrasi", "deposit seragam", "biaya pelatihan", "biaya tiket"]
    accepted, dropped = validate_indicators(
        [
            {"code": "PAYMENT_REQUEST", "evidence": [quotes[0], quotes[0].upper()]},
            {"code": "PAYMENT_REQUEST", "evidence": quotes[1:]},
        ],
        "; ".join(quotes),
        None,
        90,
    )
    assert len(accepted) == 1
    assert accepted[0].evidence == tuple(quotes[:3])
    assert dropped == 0


# Kutipan invalid dibuang walaupun kutipan lain pada indikator yang sama valid.
def test_only_supported_quotes_survive() -> None:
    accepted, dropped = validate_indicators(
        [{"code": "PAYMENT_REQUEST", "evidence": ["kutipan yang tidak ada", "biaya administrasi"]}],
        "Pelamar membayar biaya administrasi.",
        None,
        90,
    )
    assert accepted[0].evidence == ("biaya administrasi",)
    assert dropped == 0


# Konfigurasi ambang di luar domain persentase ditolak secara eksplisit.
@pytest.mark.parametrize("threshold", [-1, 101])
def test_invalid_fuzzy_threshold_is_rejected(threshold: int) -> None:
    with pytest.raises(ValueError, match="Ambang fuzzy"):
        validate_indicators([], "surat sintetis", None, threshold)
