# Owner: B (PIC 5) | Status: COMPLETE | Ref: PRD FR-05.03; SA §7.2, AD-10
"""OCR halaman PDF hasil scan menggunakan Tesseract (ind+eng)."""

import subprocess
from contextlib import closing
from io import BytesIO
from threading import Lock

import pypdfium2 as pdfium

from app.extraction.pdf_text import PdfUnreadableError

OCR_LANGUAGES = "ind+eng"
_RENDER_LOCK = Lock()


# Menserialkan akses PDFium yang tidak thread-safe dan merender PNG hanya dalam memori.
def _render_page(pdf_bytes: bytes, page_index: int, dpi: int) -> bytes:
    try:
        with _RENDER_LOCK, closing(pdfium.PdfDocument(pdf_bytes)) as document:
            with closing(document[page_index]) as page, closing(page.render(scale=dpi / 72)) as bitmap:
                with bitmap.to_pil() as image, BytesIO() as buffer:
                    image.save(buffer, format="PNG", dpi=(dpi, dpi))
                    return buffer.getvalue()
    except pdfium.PdfiumError as exc:
        raise PdfUnreadableError("Halaman PDF tidak dapat dirender") from exc


# Merender satu halaman PDF dan menjalankan OCR; timeout halaman → dianggap tanpa teks (string kosong).
def ocr_page(pdf_bytes: bytes, page_index: int, dpi: int, timeout_seconds: float) -> str:
    if page_index < 0 or dpi < 72 or timeout_seconds <= 0:
        raise ValueError("Parameter OCR tidak valid")
    image_bytes = _render_page(pdf_bytes, page_index, dpi)
    try:
        # stdin/stdout menghindari berkas sementara yang dibuat wrapper OCR berbasis path.
        result = subprocess.run(
            ["tesseract", "stdin", "stdout", "-l", OCR_LANGUAGES],
            input=image_bytes,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return ""
    if result.returncode != 0:
        raise RuntimeError("Tesseract gagal memproses halaman")
    return result.stdout.decode("utf-8")
