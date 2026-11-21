# Owner: B (PIC 5) | Status: COMPLETE | Ref: PRD §8.4, §9.6.3
"""Test taksonomi tertutup: tujuh kode, tingkat sesuai PRD §8.4, label sesuai PRD §9.6.3."""

from app.analysis.taxonomy import TAXONOMY, get_indicator
from app.schemas import Severity

EXPECTED = {
    "PAYMENT_REQUEST": (Severity.HIGH, "Permintaan pembayaran kepada pelamar"),
    "SENSITIVE_DATA_REQUEST": (Severity.HIGH, "Permintaan data atau akses sensitif"),
    "UNOFFICIAL_CONTACT": (Severity.MEDIUM, "Kontak melalui kanal tidak resmi"),
    "URGENCY_PRESSURE": (Severity.MEDIUM, "Tekanan waktu atau ancaman"),
    "IDENTITY_INCONSISTENCY": (Severity.MEDIUM, "Informasi perusahaan atau penawaran tidak konsisten"),
    "UNREALISTIC_COMPENSATION": (Severity.LOW, "Kompensasi tidak wajar"),
    "VAGUE_JOB_DETAILS": (Severity.LOW, "Rincian pekerjaan tidak jelas"),
}


# Tepat tujuh kode dengan tingkat dan label yang ditetapkan PRD.
def test_taxonomy_codes_severities_labels():
    assert set(TAXONOMY) == set(EXPECTED)
    for code, (severity, label) in EXPECTED.items():
        indicator = get_indicator(code)
        assert indicator.code == code
        assert indicator.severity is severity
        assert indicator.label == label
        assert indicator.definition and indicator.positive_examples


# Contoh negatif: biaya yang ditanggung perusahaan bukan PAYMENT_REQUEST.
def test_payment_request_negative_example():
    negatives = " ".join(get_indicator("PAYMENT_REQUEST").negative_examples).lower()
    assert "ditanggung" in negatives and "perusahaan" in negatives
