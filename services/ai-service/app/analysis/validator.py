# Owner: B (PIC 5) | Status: COMPLETE | Ref: PRD FR-05.05/AC-03, FR-05.08/AC-04; SA §7.5, TOI-07
"""Validasi skema output model dan kutipan bukti terhadap teks dokumen."""

import unicodedata
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError
from rapidfuzz.fuzz import partial_ratio

from app.analysis.taxonomy import TAXONOMY

MIN_EVIDENCE_CHARS = 8


@dataclass(frozen=True)
class ValidatedIndicator:
    """Indikator dengan kode dalam taksonomi dan minimal satu kutipan valid."""

    code: str
    evidence: tuple[str, ...]


class _ModelIndicator(BaseModel):
    """Skema entri model; kode asing dan bukti kosong dibuang pada tahap validasi indikator."""

    model_config = ConfigDict(strict=True, extra="forbid")

    code: str
    evidence: list[str]


class LLMOutput(BaseModel):
    """Skema JSON model; model tidak boleh menentukan kategori, skor, atau rekomendasi."""

    model_config = ConfigDict(strict=True, extra="forbid")

    indicators: list[_ModelIndicator]
    explanation: str


# Menormalisasi teks untuk pencocokan kutipan (NFKC → lowercase → whitespace tunggal → trim).
def normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).lower().split())


# Mem-parse JSON model ke struktur LLMOutput; ValueError bila tidak sesuai skema (memicu satu kali retry).
def parse_model_output(raw_content: str) -> dict[str, Any]:
    try:
        return LLMOutput.model_validate_json(raw_content).model_dump()
    except ValidationError:
        # Nilai input dan rincian error Pydantic dapat memuat konten dokumen; jangan diteruskan.
        raise ValueError("Output model tidak sesuai skema analisis.") from None


# Membuang kode di luar taksonomi dan kutipan yang tidak ditemukan; mengembalikan indikator valid dan jumlah dibuang.
def validate_indicators(
    raw_indicators: list[dict[str, Any]], document_text: str, extraction_method: str | None, fuzzy_threshold: int
) -> tuple[list[ValidatedIndicator], int]:
    if not 0 <= fuzzy_threshold <= 100:
        raise ValueError("Ambang fuzzy harus berada pada rentang 0 sampai 100.")
    document = normalize(document_text)
    allow_fuzzy = extraction_method in {"OCR", "MIXED"}
    accepted: dict[str, list[str]] = {}
    seen_quotes: dict[str, set[str]] = {}
    dropped = 0
    for item in raw_indicators:
        code = item["code"]
        if code not in TAXONOMY:
            dropped += 1
            continue
        quotes = []
        for quote in item["evidence"]:
            normalized_quote = normalize(quote)
            if len(normalized_quote) < MIN_EVIDENCE_CHARS:
                continue
            if normalized_quote in document or (
                allow_fuzzy and partial_ratio(normalized_quote, document) >= fuzzy_threshold
            ):
                quotes.append((quote, normalized_quote))
        if not quotes:
            dropped += 1
            continue
        accepted.setdefault(code, [])
        seen_quotes.setdefault(code, set())
        for quote, normalized_quote in quotes:
            if normalized_quote not in seen_quotes[code] and len(accepted[code]) < 3:
                accepted[code].append(quote)
                seen_quotes[code].add(normalized_quote)
    return [ValidatedIndicator(code, tuple(accepted[code])) for code in TAXONOMY if code in accepted], dropped
