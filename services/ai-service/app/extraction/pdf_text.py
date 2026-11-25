# Owner: B (PIC 5) | Status: COMPLETE | Ref: PRD FR-05.02; SA §7.2
"""Ekstraksi lapisan teks PDF per halaman."""

import logging
from dataclasses import dataclass
from io import BytesIO

import pdfplumber
from pdfminer.pdfexceptions import PDFException, PSException
from pdfplumber.utils.exceptions import PdfminerException

# Log parser dapat memuat isi PDF, termasuk saat LOG_LEVEL=DEBUG; jangan teruskan ke log aplikasi.
for logger_name in ("pdfminer", "pdfplumber", *tuple(logging.Logger.manager.loggerDict)):
    if logger_name in ("pdfminer", "pdfplumber") or logger_name.startswith(("pdfminer.", "pdfplumber.")):
        parser_logger = logging.getLogger(logger_name)
        parser_logger.disabled = True
        parser_logger.addHandler(logging.NullHandler())
        parser_logger.propagate = False


@dataclass(frozen=True)
class PageText:
    """Teks satu halaman beserta indeks halaman (mulai 0)."""

    index: int
    text: str


class PdfUnreadableError(Exception):
    """PDF rusak atau terenkripsi sehingga tidak dapat dibuka (NO_CONTENT: PDF_UNREADABLE)."""


# Mengembalikan jumlah halaman total dan teks lapisan teks untuk halaman 1..min(N, max_pages).
def extract_text_layer(pdf_bytes: bytes, max_pages: int) -> tuple[int, list[PageText]]:
    if max_pages < 1:
        raise ValueError("max_pages harus positif")
    try:
        with BytesIO(pdf_bytes) as stream, pdfplumber.open(stream) as document:
            if document.doc.encryption is not None:
                raise PdfUnreadableError("PDF terenkripsi tidak didukung")
            pages = document.pages
            return len(pages), [
                PageText(index=index, text=page.extract_text() or "") for index, page in enumerate(pages[:max_pages])
            ]
    except (PdfminerException, PDFException, PSException, ValueError) as exc:
        raise PdfUnreadableError("PDF tidak dapat dibaca") from exc
