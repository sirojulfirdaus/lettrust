# Owner: B (PIC 5) | Status: STUB | Ref: PRD FR-05.05/AC-03, FR-05.08/AC-04; SA §7.5, TOI-07
# TODO: Normalisasi NFKC+lowercase+whitespace, substring match, fuzzy (rapidfuzz.partial_ratio) hanya untuk OCR/MIXED.
"""Validasi skema output model dan kutipan bukti terhadap teks dokumen."""

from dataclasses import dataclass

MIN_EVIDENCE_CHARS = 8


@dataclass(frozen=True)
class ValidatedIndicator:
    """Indikator dengan kode dalam taksonomi dan minimal satu kutipan valid."""

    code: str
    evidence: tuple[str, ...]


# Menormalisasi teks untuk pencocokan kutipan (NFKC → lowercase → whitespace tunggal → trim).
def normalize(text: str) -> str:
    raise NotImplementedError("validator.normalize belum diimplementasikan")


# Mem-parse JSON model ke struktur LLMOutput; ValueError bila tidak sesuai skema (memicu satu kali retry).
def parse_model_output(raw_content: str) -> dict:
    raise NotImplementedError("validator.parse_model_output belum diimplementasikan")


# Membuang kode di luar taksonomi dan kutipan yang tidak ditemukan; mengembalikan indikator valid dan jumlah dibuang.
def validate_indicators(
    raw_indicators: list[dict], document_text: str, extraction_method: str | None, fuzzy_threshold: int
) -> tuple[list[ValidatedIndicator], int]:
    raise NotImplementedError("validator.validate_indicators belum diimplementasikan")
