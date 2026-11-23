# Owner: B (PIC 5) | Status: COMPLETE | Ref: PRD FR-05.02–FR-05.04; SA §7.2
"""Orkestrasi ekstraksi I-01: TEXT_LAYER | OCR | MIXED atau NO_CONTENT."""

import unicodedata

from app.core.config import Settings
from app.extraction import ocr, pdf_text
from app.schemas import ExtractionMethod, ExtractionResponse, ExtractionStatus, NoContentReason

# Minimum total karakter agar dokumen dapat dianalisis (SA §7.2).
MIN_TOTAL_CHARS = 40


# Mengekstrak teks dari byte PDF sesuai pipeline SA §7.2; berkas tidak ditulis ke disk.
def extract_document(pdf_bytes: bytes, settings: Settings) -> ExtractionResponse:
    try:
        pages_total, pages = pdf_text.extract_text_layer(pdf_bytes, settings.ai_max_pages)
        texts: list[str] = []
        methods: set[ExtractionMethod] = set()
        for page in pages:
            text = page.text
            method = ExtractionMethod.TEXT_LAYER
            if len(text.strip()) < settings.ocr_min_chars_per_page:
                text = ocr.ocr_page(pdf_bytes, page.index, settings.ocr_dpi, settings.ocr_page_timeout_seconds)
                method = ExtractionMethod.OCR
            texts.append(text)
            methods.add(method)
    except pdf_text.PdfUnreadableError:
        return ExtractionResponse(
            status=ExtractionStatus.NO_CONTENT,
            text=None,
            method=None,
            pages_total=None,
            pages_processed=None,
            truncated=False,
            language=None,
            reason_detail=NoContentReason.PDF_UNREADABLE,
        )

    normalized = unicodedata.normalize("NFKC", "\n".join(texts))
    text = "\n".join(" ".join(line.split()) for line in normalized.splitlines()).strip()
    truncated = pages_total > len(pages) or len(text) > settings.ai_max_chars
    text = text[: settings.ai_max_chars]
    has_content = len(text.strip()) >= MIN_TOTAL_CHARS
    method = ExtractionMethod.MIXED if len(methods) > 1 else next(iter(methods), None)
    return ExtractionResponse(
        status=ExtractionStatus.OK if has_content else ExtractionStatus.NO_CONTENT,
        text=text if has_content else None,
        method=method if has_content else None,
        pages_total=pages_total,
        pages_processed=len(pages),
        truncated=truncated,
        language=None,
        reason_detail=None if has_content else NoContentReason.NO_EXTRACTABLE_TEXT,
    )
