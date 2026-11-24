# Owner: B (PIC 5) | Status: COMPLETE | Ref: PRD FR-05.12, §10.4; SA §7.9; PLAN T5-05
"""Mengubah PDF teks menjadi gambar ber-derau ringan lalu PDF tanpa lapisan teks (PRD §10.4.2 butir 5)."""

import argparse
import hashlib
import json
import random
import sys
from contextlib import closing
from dataclasses import replace
from io import BytesIO
from pathlib import Path

import pypdfium2 as pdfium
from _dataset import (
    DEFAULT_SEED,
    LABELS,
    LANGUAGES,
    ROOT,
    Entry,
    inspect_pdf,
    pdf_path,
    read_manifest,
    sha256,
    write_manifest,
    write_pdf,
)
from PIL import Image, ImageDraw, ImageFilter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas

DEFAULT_DPI = 200


# Menambahkan rotasi kecil dan bintik abu-abu ringan secara deterministik, tanpa mengubah isi surat.
def degrade_image(image: Image.Image, seed: str) -> Image.Image:
    rng = random.Random(int(hashlib.sha256(seed.encode()).hexdigest(), 16))
    rotated = image.rotate(rng.uniform(-0.35, 0.35), resample=Image.Resampling.BICUBIC, fillcolor=255)
    try:
        degraded = rotated.filter(ImageFilter.GaussianBlur(0.25))
    finally:
        rotated.close()
    draw = ImageDraw.Draw(degraded)
    for _ in range(int(degraded.width * degraded.height * 0.0004)):
        draw.point((rng.randrange(degraded.width), rng.randrange(degraded.height)), fill=rng.randrange(200, 246))
    return degraded


# Membuat PDF gambar saja; seed per ID sumber menjaga hasil tidak berubah saat bahasa lain ditambahkan.
def render_scan_pdf(source: bytes, source_id: str, seed: int, dpi: int = DEFAULT_DPI) -> bytes:
    if not 72 <= dpi <= 300:
        raise ValueError("DPI scan harus berada pada rentang 72 sampai 300.")
    inspect_pdf(source, expect_text=True)
    with closing(pdfium.PdfDocument(source)) as document, BytesIO() as buffer:
        canvas = Canvas(buffer, invariant=1, pageCompression=1)
        canvas.setTitle("Surat penawaran kerja sintetis")
        canvas.setAuthor("Lettrust")
        for index in range(len(document)):
            with closing(document[index]) as page, closing(page.render(scale=dpi / 72)) as bitmap:
                width, height = page.get_size()
                with bitmap.to_pil() as original, original.convert("L") as gray:
                    with degrade_image(gray, f"{seed}:{source_id}:{index}") as image:
                        canvas.setPageSize((width, height))
                        canvas.drawImage(ImageReader(image), 0, 0, width=width, height=height)
                        canvas.showPage()
        canvas.save()
        content = buffer.getvalue()
    inspect_pdf(content, expect_text=False)
    return content


# Mengikuti split/anotasi PDF teks yang sudah tervalidasi tanpa menulis ulang surat atau label referensi.
def generate_scans(dataset_dir: Path, languages: list[str], seed: int, dpi: int) -> list[Entry]:
    if not languages or len(set(languages)) != len(languages) or set(languages) - set(LANGUAGES):
        raise ValueError("Pilih bahasa id/en tanpa duplikat.")
    existing = read_manifest(dataset_dir)
    sources = [entry for entry in existing if entry.format == "text" and entry.lang in languages]
    expected = {
        f"{lang}-{label.lower()}-{index:02}-text" for lang in languages for label in LABELS for index in range(1, 7)
    }
    if {entry.id for entry in sources} != expected:
        raise ValueError("PDF teks belum lengkap untuk bahasa yang dipilih; jalankan generate_pdfs terlebih dahulu.")
    additions = []
    for entry in sources:
        source_id = entry.id.removesuffix("-text")
        content = render_scan_pdf(pdf_path(dataset_dir, entry).read_bytes(), source_id, seed, dpi)
        identifier = f"{source_id}-scan"
        scan = replace(entry, id=identifier, format="scan", file=f"pdf/{identifier}.pdf", sha256=sha256(content))
        write_pdf(pdf_path(dataset_dir, scan), content)
        additions.append(scan)
    write_manifest(dataset_dir, existing, additions)
    return additions


# Menjalankan konversi di image ai-service; mode parsial tidak dilaporkan sebagai dataset 72 dokumen.
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, default=ROOT / "dataset")
    parser.add_argument("--languages", nargs="+", choices=LANGUAGES, default=list(LANGUAGES))
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--dpi", type=int, default=DEFAULT_DPI)
    args = parser.parse_args(argv)
    try:
        entries = generate_scans(args.dataset_dir, args.languages, args.seed, args.dpi)
    except (OSError, ValueError, pdfium.PdfiumError) as error:
        print(f"Generator gagal: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "stage": "scan",
                "coverage": "full" if len(args.languages) == 2 else "partial",
                "languages": sorted(args.languages),
                "pdfCount": len(entries),
                "dev": sum(entry.split == "dev" for entry in entries),
                "test": sum(entry.split == "test" for entry in entries),
                "seed": args.seed,
                "dpi": args.dpi,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
