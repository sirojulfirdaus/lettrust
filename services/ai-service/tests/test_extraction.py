# Owner: B (PIC 5) | Status: COMPLETE | Ref: PLAN T5-02; PRD FR-05.02–FR-05.04; SA §7.2, §10.8
"""Pengujian ekstraksi PDF sintetis, OCR CPU, validasi unggahan, dan kontrak I-01."""

import builtins
import json
import logging
import os
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path
from typing import IO, Any
from unittest.mock import Mock

import pdfplumber
import pytest
from conftest import INTERNAL_TOKEN
from fastapi.testclient import TestClient
from reportlab.lib.pdfencrypt import StandardEncryption
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas

from app.core.config import get_settings
from app.extraction import ocr, pdf_text, service
from app.routers import extractions
from app.schemas import ExtractionResponse

URL = "/internal/v1/document-extractions"
AUTH = {"X-Internal-Token": INTERNAL_TOKEN, "X-Request-ID": "req_EXTRACTIONTEST"}
ID_TEXT = (
    "PT Awan Kertas Contoh\nSurat Penawaran Kerja Staf Administrasi\n"
    "Tugas Anda adalah mencatat surat dan menyusun laporan mingguan."
)
EN_TEXT = (
    "Blue Paper Example Company\nEmployment Offer for Inventory Clerk\n"
    "Your duties include stock records and weekly inventory reports."
)


# Menulis halaman sintetis dengan font dan posisi tetap agar uji OCR dapat diulang.
def draw_text(canvas: Canvas, text: str) -> None:
    content = canvas.beginText(54, 730)
    content.setFont("Helvetica", 14)
    content.setLeading(22)
    for line in text.splitlines():
        content.textLine(line)
    canvas.drawText(content)


# Membuat PDF teks/scan/campuran di memori; enkripsi hanya dipakai untuk uji penolakan.
def make_pdf(pages: list[str], scanned: set[int] | None = None, password: str | None = None) -> bytes:
    with BytesIO() as buffer:
        encryption = StandardEncryption(password) if password is not None else None
        canvas = Canvas(buffer, pagesize=(612, 792), encrypt=encryption)
        for index, text in enumerate(pages):
            if scanned and index in scanned:
                source = make_pdf([text])
                image = ocr._render_page(source, 0, 150)
                canvas.drawImage(ImageReader(BytesIO(image)), 0, 0, width=612, height=792)
            else:
                draw_text(canvas, text)
            canvas.showPage()
        canvas.save()
        return buffer.getvalue()


# PDF teks Indonesia dan Inggris diproses tanpa memanggil OCR.
@pytest.mark.parametrize("text", [ID_TEXT, EN_TEXT], ids=["id", "en"])
def test_text_pdf_preserves_lines_without_ocr(text: str, monkeypatch: pytest.MonkeyPatch) -> None:
    unused_ocr = Mock(side_effect=AssertionError("OCR tidak boleh dipanggil"))
    monkeypatch.setattr(ocr, "ocr_page", unused_ocr)
    result = service.extract_document(make_pdf([text]), get_settings())
    assert result.status == "OK"
    assert result.method == "TEXT_LAYER"
    assert result.text == text
    assert (result.pages_total, result.pages_processed, result.truncated) == (1, 1, False)
    assert result.language is None and result.reason_detail is None
    unused_ocr.assert_not_called()


# PDF tanpa lapisan teks dibaca Tesseract ind+eng sungguhan; tidak memakai mock OCR.
@pytest.mark.parametrize("text, phrase", [(ID_TEXT, "Surat Penawaran Kerja"), (EN_TEXT, "Employment Offer")])
def test_scanned_pdf_uses_real_ocr(text: str, phrase: str) -> None:
    pdf_bytes = make_pdf([text], scanned={0})
    assert pdf_text.extract_text_layer(pdf_bytes, 5)[1][0].text == ""
    result = service.extract_document(pdf_bytes, get_settings())
    assert result.status == "OK"
    assert result.method == "OCR"
    assert phrase.lower() in result.text.lower()
    assert result.pages_processed == 1


# Halaman teks dan scan dalam dokumen yang sama menghasilkan metode MIXED.
def test_mixed_pdf_uses_real_ocr() -> None:
    result = service.extract_document(make_pdf([ID_TEXT, EN_TEXT], scanned={1}), get_settings())
    assert result.method == "MIXED"
    assert ID_TEXT in result.text
    assert "employment offer" in result.text.lower()
    assert (result.pages_total, result.pages_processed) == (2, 2)


# Halaman kosong diproses OCR sungguhan lalu menghasilkan NO_CONTENT tanpa teks atau metode rekaan.
def test_blank_pdf_returns_no_content_with_real_ocr() -> None:
    result = service.extract_document(make_pdf([""]), get_settings())
    assert result.model_dump(by_alias=True, mode="json") == {
        "status": "NO_CONTENT",
        "text": None,
        "method": None,
        "pagesTotal": 1,
        "pagesProcessed": 1,
        "truncated": False,
        "language": None,
        "reasonDetail": "NO_EXTRACTABLE_TEXT",
    }


# PDF rusak atau terenkripsi, termasuk password kosong, dinyatakan tidak terbaca.
@pytest.mark.parametrize("password", [None, "synthetic-password", ""])
def test_unreadable_pdf_returns_contract_example(password: str | None) -> None:
    pdf_bytes = b"%PDF-1.4\nrusak" if password is None else make_pdf([ID_TEXT], password=password)
    result = service.extract_document(pdf_bytes, get_settings())
    # Pilih mount container sebelum menghitung lokasi relatif pada jalur native.
    contracts = (
        Path(os.environ["CONTRACTS_DIR"])
        if os.environ.get("CONTRACTS_DIR")
        else Path(__file__).parents[3] / "contracts"
    )
    example = contracts / "examples/internal/i-01.extraction-unreadable.json"
    assert result.model_dump(by_alias=True, mode="json") == json.loads(example.read_text(encoding="utf-8"))


# Batas lima halaman menghentikan ekstraksi teks dan OCR sebelum halaman keenam.
def test_page_limit_is_reported_and_later_page_is_not_extracted(monkeypatch: pytest.MonkeyPatch) -> None:
    original_extract = pdfplumber.page.Page.extract_text
    calls: list[int] = []

    # Mencatat halaman yang benar-benar diekstraksi tanpa mengganti parser PDF nyata.
    def track_extract(page: pdfplumber.page.Page, *args: Any, **kwargs: Any) -> str:
        calls.append(page.page_number)
        return original_extract(page, *args, **kwargs)

    monkeypatch.setattr(pdfplumber.page.Page, "extract_text", track_extract)
    result = service.extract_document(make_pdf([ID_TEXT] * 5 + ["PAGE SIX MUST NOT BE READ"]), get_settings())
    assert calls == [1, 2, 3, 4, 5]
    assert (result.pages_total, result.pages_processed, result.truncated) == (6, 5, True)
    assert "PAGE SIX" not in result.text


# Pemotongan karakter mengikuti konfigurasi dan tidak ditandai bila panjang tepat pada batas.
@pytest.mark.parametrize("limit, truncated", [(60, True), (len(ID_TEXT), False)])
def test_character_limit(limit: int, truncated: bool) -> None:
    settings = get_settings().model_copy(update={"ai_max_chars": limit})
    result = service.extract_document(make_pdf([ID_TEXT]), settings)
    assert result.text == ID_TEXT[:limit]
    assert result.truncated is truncated


# Normalisasi NFKC dan spasi menjaga pergantian baris dan tidak mengubah kata.
def test_normalization_preserves_lines(monkeypatch: pytest.MonkeyPatch) -> None:
    text = "  ＰＴ\t Awan   Kertas\r\n\nPenawaran  kerja sintetis untuk staf administrasi.  "
    monkeypatch.setattr(pdf_text, "extract_text_layer", Mock(return_value=(1, [pdf_text.PageText(0, text)])))
    result = service.extract_document(b"synthetic", get_settings())
    assert result.text == "PT Awan Kertas\n\nPenawaran kerja sintetis untuk staf administrasi."


# Ambang OCR berlaku per halaman dan hanya dijalankan bila jumlah karakter di bawah ambang.
@pytest.mark.parametrize("count, expected_calls", [(24, 1), (25, 0)])
def test_ocr_threshold(count: int, expected_calls: int, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pdf_text, "extract_text_layer", Mock(return_value=(1, [pdf_text.PageText(0, "a" * count)])))
    reader = Mock(return_value=ID_TEXT)
    monkeypatch.setattr(ocr, "ocr_page", reader)
    result = service.extract_document(b"synthetic", get_settings())
    assert reader.call_count == expected_calls
    if expected_calls:
        reader.assert_called_once_with(b"synthetic", 0, 300, 20)
        assert result.method == "OCR"
    else:
        assert result.reason_detail == "NO_EXTRACTABLE_TEXT"


# Teks kurang dari minimum tidak menghasilkan konten; panjang tepat minimum diterima.
@pytest.mark.parametrize("length, status", [(39, "NO_CONTENT"), (40, "OK")])
def test_minimum_content_length(length: int, status: str) -> None:
    result = service.extract_document(make_pdf(["a" * length]), get_settings())
    assert result.status == status
    assert result.text == ("a" * length if status == "OK" else None)


# OCR mengirim PNG melalui stdin/stdout dengan bahasa dan timeout yang ditetapkan, tanpa berkas sementara.
def test_ocr_invocation_uses_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    process = Mock(return_value=subprocess.CompletedProcess([], 0, b"hasil OCR sintetis", b""))
    monkeypatch.setattr(ocr.subprocess, "run", process)
    assert ocr.ocr_page(make_pdf([ID_TEXT]), 0, 144, 7) == "hasil OCR sintetis"
    args, kwargs = process.call_args
    assert args == (["tesseract", "stdin", "stdout", "-l", "ind+eng"],)
    assert kwargs["input"].startswith(b"\x89PNG\r\n\x1a\n")
    assert kwargs["timeout"] == 7 and kwargs["capture_output"] is True


# Timeout per halaman menghasilkan teks kosong, bukan hasil OCR palsu.
def test_ocr_timeout_returns_no_content(monkeypatch: pytest.MonkeyPatch) -> None:
    process = Mock(side_effect=subprocess.TimeoutExpired("tesseract", 1))
    monkeypatch.setattr(ocr.subprocess, "run", process)
    result = service.extract_document(make_pdf([""]), get_settings())
    assert result.status == "NO_CONTENT"
    assert result.reason_detail == "NO_EXTRACTABLE_TEXT"


# Kegagalan proses atau instalasi OCR diteruskan, tanpa membocorkan stderr atau menyamarkannya sebagai tanpa konten.
@pytest.mark.parametrize("missing", [False, True])
def test_ocr_infrastructure_failure_is_explicit(missing: bool, monkeypatch: pytest.MonkeyPatch) -> None:
    process = (
        Mock(side_effect=FileNotFoundError("tesseract"))
        if missing
        else Mock(return_value=subprocess.CompletedProcess([], 1, b"", b"private stderr"))
    )
    monkeypatch.setattr(ocr.subprocess, "run", process)
    with pytest.raises(FileNotFoundError if missing else RuntimeError) as error:
        service.extract_document(make_pdf([""]), get_settings())
    assert "private stderr" not in str(error.value)


# Renderer menolak PDF rusak dengan exception domain yang dipetakan ke PDF_UNREADABLE.
def test_rendering_unreadable_pdf_raises_domain_error() -> None:
    with pytest.raises(pdf_text.PdfUnreadableError):
        ocr._render_page(b"%PDF-1.4\nrusak", 0, 300)


# Ekstraksi/OCR tidak membuka berkas tulis; Tesseract diganti hanya pada batas proses untuk inspeksi I/O.
def test_document_processing_does_not_write_files(monkeypatch: pytest.MonkeyPatch) -> None:
    pdf_bytes = make_pdf([ID_TEXT], scanned={0})
    original_open = builtins.open

    # Menolak setiap upaya menulis file dari pipeline Python selama pemrosesan dokumen.
    def read_only_open(file: Any, mode: str = "r", *args: Any, **kwargs: Any) -> IO[Any]:
        assert not any(flag in mode for flag in "wax+")
        return original_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", read_only_open)
    monkeypatch.setattr(
        ocr.subprocess, "run", Mock(return_value=subprocess.CompletedProcess([], 0, ID_TEXT.encode(), b""))
    )
    assert service.extract_document(pdf_bytes, get_settings()).method == "OCR"


# Validasi gagal sebelum parser PDF/OCR dipanggil dan memakai envelope yang memantulkan request ID.
@pytest.mark.parametrize(
    "content, expected_status, expected_code",
    [(b"", 400, "EMPTY_FILE"), (b"not a PDF", 415, "UNSUPPORTED_MEDIA_TYPE")],
)
def test_upload_validation(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    content: bytes,
    expected_status: int,
    expected_code: str,
) -> None:
    reader = Mock(side_effect=AssertionError("Ekstraksi tidak boleh dipanggil"))
    monkeypatch.setattr(service, "extract_document", reader)
    response = client.post(URL, headers=AUTH, files={"file": ("offer.pdf", content, "application/pdf")})
    assert response.status_code == expected_status
    assert response.json()["error"]["code"] == expected_code
    assert response.json()["requestId"] == AUTH["X-Request-ID"]
    reader.assert_not_called()


# Dua berkas, baik pada nama field sama maupun berbeda, ditolak sebelum ekstraksi.
@pytest.mark.parametrize("first_field, second_field", [("file", "file"), ("file", "other"), ("first", "second")])
def test_multiple_files_are_rejected(client: TestClient, first_field: str, second_field: str) -> None:
    upload = ("offer.pdf", make_pdf([ID_TEXT]), "application/pdf")
    response = client.post(URL, headers=AUTH, files=[(first_field, upload), (second_field, upload)])
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "MULTIPLE_FILES"


# Batas ukuran memeriksa byte berkas: tepat batas diterima; satu byte lebih ditolak.
@pytest.mark.parametrize("size, status", [(64, 200), (65, 413)])
def test_upload_size_boundary(client: TestClient, size: int, status: int, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings().model_copy(update={"max_upload_bytes": 64})
    monkeypatch.setattr(extractions, "get_settings", lambda: settings)
    pdf_bytes = b"%PDF-1.4\n".ljust(size, b" ")
    response = client.post(URL, headers=AUTH, files={"file": ("offer.pdf", pdf_bytes, "application/pdf")})
    assert response.status_code == status
    if status == 413:
        assert response.json()["error"]["code"] == "FILE_TOO_LARGE"
    else:
        assert response.json()["reasonDetail"] == "PDF_UNREADABLE"


# Tanda tangan byte PDF menjadi acuan, sehingga ekstensi dan MIME tidak menentukan validitas isi.
def test_pdf_signature_is_used_instead_of_filename_or_mime(client: TestClient) -> None:
    response = client.post(URL, headers=AUTH, files={"file": ("offer.txt", make_pdf([ID_TEXT]), "text/plain")})
    assert response.status_code == 200
    body = response.json()
    ExtractionResponse.model_validate(body)
    assert body == {
        "status": "OK",
        "text": ID_TEXT,
        "method": "TEXT_LAYER",
        "pagesTotal": 1,
        "pagesProcessed": 1,
        "truncated": False,
        "language": None,
        "reasonDetail": None,
    }
    assert response.headers["X-Request-ID"] == AUTH["X-Request-ID"]


# Unggahan di atas 1 MiB tidak berpindah ke disk pada parser multipart.
def test_large_upload_never_rolls_to_disk(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    rollover = Mock(side_effect=AssertionError("Unggahan tidak boleh ditulis ke disk"))
    monkeypatch.setattr(tempfile.SpooledTemporaryFile, "rollover", rollover)
    pdf_bytes = make_pdf([ID_TEXT]) + b" " * (2 * 1024 * 1024)
    response = client.post(URL, headers=AUTH, files={"file": ("offer.pdf", pdf_bytes, "application/pdf")})
    assert response.status_code == 200
    assert response.json()["text"] == ID_TEXT
    rollover.assert_not_called()


# Log aplikasi maupun parser pada level DEBUG tidak memuat teks dokumen atau token internal.
def test_document_content_is_not_logged(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG):
        response = client.post(URL, headers=AUTH, files={"file": ("offer.pdf", make_pdf([ID_TEXT]), "application/pdf")})
    assert response.status_code == 200
    assert "PT Awan Kertas Contoh" not in caplog.text
    assert INTERNAL_TOKEN not in caplog.text
