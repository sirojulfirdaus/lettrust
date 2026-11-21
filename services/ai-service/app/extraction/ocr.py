# Owner: B (PIC 5) | Status: STUB | Ref: PRD FR-05.03; SA §7.2, AD-10
# TODO: Render halaman dengan pypdfium2 pada OCR_DPI lalu Tesseract "ind+eng" dengan OCR_PAGE_TIMEOUT_SECONDS (CPU).
"""OCR halaman PDF hasil scan menggunakan Tesseract (ind+eng)."""

OCR_LANGUAGES = "ind+eng"


# Merender satu halaman PDF dan menjalankan OCR; timeout halaman → dianggap tanpa teks (string kosong).
def ocr_page(pdf_bytes: bytes, page_index: int, dpi: int, timeout_seconds: float) -> str:
    raise NotImplementedError("ocr.ocr_page belum diimplementasikan")
