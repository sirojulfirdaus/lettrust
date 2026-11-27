# Owner: B (PIC 5) | Status: COMPLETE | Ref: PRD FR-05.12, §10.4; SA §7.9; PLAN T5-05
"""Merender hanya teks surat ke PDF deterministik; anotasi tetap berada di manifest."""

import argparse
import json
import sys
import unicodedata
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import pypdfium2 as pdfium
import reportlab
from _dataset import (
    DEFAULT_SEED,
    LANGUAGES,
    ROOT,
    Entry,
    assign_splits,
    entry_for,
    inspect_pdf,
    load_letters,
    pdf_path,
    read_manifest,
    write_manifest,
    write_pdf,
)
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

FONT_SIZE = 11
LEADING = 15
MARGIN = 54


# Memakai font Unicode yang sudah dibundel dependency terkunci, tanpa mengunduh atau memasang font sistem.
@lru_cache(maxsize=1)
def register_font() -> str:
    font_name = "LettrustDatasetVera"
    font_file = Path(reportlab.__file__).parent / "fonts" / "Vera.ttf"
    if not font_file.is_file():
        raise ValueError("Font bawaan ReportLab tidak tersedia.")
    pdfmetrics.registerFont(TTFont(font_name, str(font_file)))
    return font_name


# Membungkus baris pada batas kata tanpa menambah tanda hubung atau memotong kata pada margin.
def wrap_lines(text: str, font_name: str, width: float) -> list[str]:
    glyphs = pdfmetrics.getFont(font_name).face.charToGlyph
    if any(ord(character) not in glyphs for character in text if character not in "\n\r\t"):
        raise ValueError("Teks memuat karakter yang tidak didukung font dataset.")
    lines = []
    for paragraph in text.splitlines():
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        line = ""
        for word in words:
            if pdfmetrics.stringWidth(word, font_name, FONT_SIZE) > width:
                raise ValueError("Satu kata/URL terlalu panjang untuk layout dataset.")
            candidate = f"{line} {word}" if line else word
            if pdfmetrics.stringWidth(candidate, font_name, FONT_SIZE) > width:
                lines.append(line)
                line = word
            else:
                line = candidate
        lines.append(line)
    return lines


# Merender surat di memori dengan tanggal/ID PDF invariant; label, notes, dan ID sumber tidak dicetak.
def render_text_pdf(text: str) -> bytes:
    font_name = register_font()
    width, height = A4
    lines = wrap_lines(text, font_name, width - 2 * MARGIN)
    with BytesIO() as buffer:
        canvas = Canvas(buffer, pagesize=A4, invariant=1, pageCompression=1)
        canvas.setTitle("Surat penawaran kerja sintetis")
        canvas.setAuthor("Lettrust")
        y = height - MARGIN
        canvas.setFont(font_name, FONT_SIZE)
        for line in lines:
            if y < MARGIN:
                canvas.showPage()
                canvas.setFont(font_name, FONT_SIZE)
                y = height - MARGIN
            canvas.drawString(MARGIN, y, line)
            y -= LEADING
        canvas.save()
        content = buffer.getvalue()
    _, extracted = inspect_pdf(content, expect_text=True)
    if " ".join(unicodedata.normalize("NFKC", extracted).split()) != " ".join(
        unicodedata.normalize("NFKC", text).split()
    ):
        raise ValueError("Isi PDF teks berbeda dari surat sumber setelah normalisasi whitespace.")
    return content


# Menghasilkan seluruh kelompok bahasa yang diminta dan mempertahankan entri lama yang identik.
def generate_dataset(templates_dir: Path, dataset_dir: Path, languages: list[str], seed: int) -> list[Entry]:
    letters = load_letters(templates_dir, languages)
    splits = assign_splits(letters, seed)
    existing = read_manifest(dataset_dir)
    prepared = [(letter, render_text_pdf(letter.text)) for letter in letters]
    additions = []
    for letter, content in prepared:
        entry = entry_for(letter, splits[letter.id], "text", content)
        write_pdf(pdf_path(dataset_dir, entry), content)
        additions.append(entry)
    write_manifest(dataset_dir, existing, additions)
    return additions


# Menjalankan generator melalui launcher eval; bahasa parsial selalu harus dipilih secara eksplisit.
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--templates-dir", type=Path, default=ROOT / "templates")
    parser.add_argument("--dataset-dir", type=Path, default=ROOT / "dataset")
    parser.add_argument("--languages", nargs="+", choices=LANGUAGES, default=list(LANGUAGES))
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args(argv)
    try:
        entries = generate_dataset(args.templates_dir, args.dataset_dir, args.languages, args.seed)
    except (OSError, ValueError, pdfium.PdfiumError) as error:
        print(f"Generator gagal: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "stage": "text",
                "coverage": "full" if len(args.languages) == 2 else "partial",
                "languages": sorted(args.languages),
                "pdfCount": len(entries),
                "dev": sum(entry.split == "dev" for entry in entries),
                "test": sum(entry.split == "test" for entry in entries),
                "seed": args.seed,
                "review": "Konfirmasi review manusia dicatat di protokol evaluasi, bukan disahkan generator.",
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
