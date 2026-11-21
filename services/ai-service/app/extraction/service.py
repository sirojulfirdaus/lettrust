# Owner: B (PIC 5) | Status: STUB | Ref: PRD FR-05.02–FR-05.04; SA §7.2
# TODO: Gabungkan text layer + OCR per halaman, normalisasi NFKC, potong ke AI_MAX_CHARS, tentukan method/NO_CONTENT.
"""Orkestrasi ekstraksi I-01: TEXT_LAYER | OCR | MIXED atau NO_CONTENT."""

from app.core.config import Settings
from app.schemas import ExtractionResponse

# Minimum total karakter agar dokumen dapat dianalisis (SA §7.2).
MIN_TOTAL_CHARS = 40


# Mengekstrak teks dari byte PDF sesuai pipeline SA §7.2; berkas tidak ditulis ke disk.
def extract_document(pdf_bytes: bytes, settings: Settings) -> ExtractionResponse:
    raise NotImplementedError("extraction.extract_document belum diimplementasikan")
