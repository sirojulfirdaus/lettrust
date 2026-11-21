# Owner: B (PIC 5) | Status: STUB | Ref: PRD FR-05.02; SA §7.2
# TODO: Buka PDF dengan pdfplumber (gagal/terenkripsi → PDF_UNREADABLE), ekstrak teks per halaman hingga AI_MAX_PAGES.
"""Ekstraksi lapisan teks PDF per halaman."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PageText:
    """Teks satu halaman beserta indeks halaman (mulai 0)."""

    index: int
    text: str


class PdfUnreadableError(Exception):
    """PDF rusak atau terenkripsi sehingga tidak dapat dibuka (NO_CONTENT: PDF_UNREADABLE)."""


# Mengembalikan jumlah halaman total dan teks lapisan teks untuk halaman 1..min(N, max_pages).
def extract_text_layer(pdf_bytes: bytes, max_pages: int) -> tuple[int, list[PageText]]:
    raise NotImplementedError("pdf_text.extract_text_layer belum diimplementasikan")
