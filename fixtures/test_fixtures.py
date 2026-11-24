# Owner: B (PIC 5) | Status: COMPLETE | Ref: PLAN T5-06; PRD §12.4.1; SA §7.9
"""Memeriksa artefak fixture dan pipeline ekstraksi nyata tanpa membuat prediksi LLM."""

import unicodedata
from contextlib import closing
from pathlib import Path

import pypdfium2 as pdfium
import pytest
from fixture_builder import FIXTURES, MAX_BYTES, build_fixtures, check_fixtures, letter_sources
from rapidfuzz.fuzz import ratio

from app.core.config import Settings
from app.extraction.service import extract_document


@pytest.fixture(scope="module")
def artifacts() -> dict[str, bytes]:
    """Membangun sepuluh fixture di memori agar pemeriksaan tidak menulis ulang berkas repository."""
    return build_fixtures()


# Membandingkan isi dengan mengabaikan pembungkusan baris PDF dan normalisasi Unicode runtime.
def normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).split())


# Byte repository dan checksum README harus cocok dengan generator pada environment terkunci yang sama.
def test_committed_artifacts_match_generator(artifacts: dict[str, bytes]) -> None:
    assert set(artifacts) == {f"FX-{index:02}" for index in range(1, 11)}
    check_fixtures(FIXTURES, artifacts)


# Generasi kedua harus menghasilkan byte identik, termasuk scan berderau dan PDF melebihi batas.
def test_rebuild_is_reproducible(artifacts: dict[str, bytes]) -> None:
    assert build_fixtures() == artifacts


# Perubahan satu nominal gaji adalah satu-satunya perubahan isi FX-02; hash berkas harus ikut berubah.
def test_modified_offer_has_one_salary_change(artifacts: dict[str, bytes]) -> None:
    sources = letter_sources()
    assert sources["FX-01"].count("Rp6.000.000") == 1
    assert sources["FX-02"] == sources["FX-01"].replace("Rp6.000.000", "Rp7.500.000")
    assert artifacts["FX-01"] != artifacts["FX-02"]


# PDF teks memakai ekstraktor runtime asli dan harus mempertahankan seluruh isi tanpa pemotongan.
@pytest.mark.parametrize("identifier", ["FX-01", "FX-02", "FX-03", "FX-05", "FX-06"])
def test_runtime_reads_text_fixture(identifier: str, artifacts: dict[str, bytes]) -> None:
    # Konfigurasi default fungsi murni; tidak memuat environment, token, atau provider LLM.
    result = extract_document(artifacts[identifier], Settings.model_construct())
    assert result.status.value == "OK"
    assert result.method.value == "TEXT_LAYER"
    assert result.pages_total == result.pages_processed == 1
    assert result.truncated is False
    assert normalize(result.text) == normalize(letter_sources()[identifier])


# Scan Inggris tidak mempunyai text layer dan dibaca dengan Tesseract ind+eng nyata melalui runtime.
def test_english_scan_uses_real_ocr(artifacts: dict[str, bytes]) -> None:
    with closing(pdfium.PdfDocument(artifacts["FX-04"])) as document:
        with closing(document[0]) as page, closing(page.get_textpage()) as text_page:
            assert text_page.get_text_range().strip() == ""
    result = extract_document(artifacts["FX-04"], Settings.model_construct())
    assert result.status.value == "OK"
    assert result.method.value == "OCR"
    assert result.pages_total == result.pages_processed == 1
    assert result.truncated is False
    assert ratio(normalize(result.text), normalize(letter_sources()["FX-04"])) >= 98
    assert "must pay a recruitment administration fee" in result.text


# Halaman kosong harus tetap tanpa konten sesudah OCR nyata, tanpa kategori atau teks rekaan.
def test_blank_page_has_no_content(artifacts: dict[str, bytes]) -> None:
    result = extract_document(artifacts["FX-07"], Settings.model_construct())
    assert result.status.value == "NO_CONTENT"
    assert result.reason_detail.value == "NO_EXTRACTABLE_TEXT"
    assert result.pages_total == result.pages_processed == 1
    assert result.text is result.method is None


# Header valid tidak cukup untuk parsing; FX-10 harus menghasilkan alasan PDF_UNREADABLE.
def test_broken_pdf_is_unreadable(artifacts: dict[str, bytes]) -> None:
    assert artifacts["FX-10"].startswith(b"%PDF-")
    result = extract_document(artifacts["FX-10"], Settings.model_construct())
    assert result.status.value == "NO_CONTENT"
    assert result.reason_detail.value == "PDF_UNREADABLE"
    assert result.text is result.method is None


# FX-08 benar-benar bukan PDF; ekstensi nama berkas tidak memperbaiki signature maupun struktur.
def test_non_pdf_has_no_pdf_signature(artifacts: dict[str, bytes]) -> None:
    assert not artifacts["FX-08"].startswith(b"%PDF-")
    with pytest.raises(pdfium.PdfiumError):
        pdfium.PdfDocument(artifacts["FX-08"])


# FX-09 merupakan PDF sah satu halaman di atas batas 5 MiB, bukan sekadar data rusak berukuran besar.
def test_oversized_fixture_is_a_valid_pdf(artifacts: dict[str, bytes]) -> None:
    content = artifacts["FX-09"]
    assert len(content) > MAX_BYTES == 5_242_880
    with closing(pdfium.PdfDocument(content)) as document:
        assert len(document) == 1


# Pemeriksaan integritas menolak perubahan berkas dan checksum dokumentasi tanpa mengubah fixture repository.
def test_check_rejects_modified_artifact_and_documentation(tmp_path: Path, artifacts: dict[str, bytes]) -> None:
    for identifier, content in artifacts.items():
        (tmp_path / f"{identifier}.pdf").write_bytes(content)
    readme = (FIXTURES / "README.md").read_bytes()
    (tmp_path / "README.md").write_bytes(readme)
    (tmp_path / "FX-01.pdf").write_bytes(b"changed")
    with pytest.raises(ValueError, match="byte berbeda: FX-01"):
        check_fixtures(tmp_path, artifacts)
    (tmp_path / "FX-01.pdf").write_bytes(artifacts["FX-01"])
    (tmp_path / "README.md").write_text("Tidak ada checksum.\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Checksum README"):
        check_fixtures(tmp_path, artifacts)
