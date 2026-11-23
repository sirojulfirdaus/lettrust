# Owner: B (PIC 5) | Status: COMPLETE | Ref: PLAN T5-04; PRD §8.5; SA §7.6
"""Uji prioritas HIGH, MEDIUM, dan dua indikator LOW berbeda sesuai aturan bisnis."""

import pytest

from app.analysis.scoring import score
from app.schemas import RiskCategory


# Tabel keputusan meliputi setiap kode, kategori kosong, dan prioritas kombinasi lintas tingkat.
@pytest.mark.parametrize(
    ("codes", "expected"),
    [
        (set(), "LOW"),
        ({"PAYMENT_REQUEST"}, "HIGH"),
        ({"SENSITIVE_DATA_REQUEST"}, "HIGH"),
        ({"UNOFFICIAL_CONTACT"}, "MEDIUM"),
        ({"URGENCY_PRESSURE"}, "MEDIUM"),
        ({"IDENTITY_INCONSISTENCY"}, "MEDIUM"),
        ({"UNREALISTIC_COMPENSATION"}, "LOW"),
        ({"VAGUE_JOB_DETAILS"}, "LOW"),
        ({"UNREALISTIC_COMPENSATION", "VAGUE_JOB_DETAILS"}, "MEDIUM"),
        ({"URGENCY_PRESSURE", "VAGUE_JOB_DETAILS"}, "MEDIUM"),
        ({"PAYMENT_REQUEST", "URGENCY_PRESSURE", "VAGUE_JOB_DETAILS"}, "HIGH"),
        ({"SENSITIVE_DATA_REQUEST", "UNREALISTIC_COMPENSATION", "VAGUE_JOB_DETAILS"}, "HIGH"),
    ],
)
def test_business_rules(codes: set[str], expected: str) -> None:
    assert score(codes) is RiskCategory(expected)


# Pengulangan kode LOW yang sama tidak dapat menaikkan kategori.
def test_duplicate_low_indicator_counts_once() -> None:
    assert score(set(["VAGUE_JOB_DETAILS"] * 4)) is RiskCategory.LOW


# Kode asing tidak diam-diam diberi tingkat risiko.
def test_unknown_code_has_no_score() -> None:
    with pytest.raises(ValueError, match="taksonomi"):
        score({"UNKNOWN_CODE"})
