# Owner: B (PIC 5) | Status: COMPLETE | Ref: PLAN T5-05; PRD §10.4.1–§10.4.2; SA §7.9
"""Validasi templat, pemisahan surat sumber, dan manifest dataset sintetis."""

import csv
import hashlib
import json
import random
import re
from dataclasses import asdict, dataclass
from io import StringIO
from pathlib import Path

import pypdfium2 as pdfium

from app.analysis.scoring import score
from app.analysis.taxonomy import TAXONOMY

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ("id", "split", "lang", "format", "label", "indicators", "file", "sha256")
LANGUAGES = ("id", "en")
LABELS = ("LOW", "MEDIUM", "HIGH")
DEFAULT_SEED = 20261121
# Batas dokumen baseline SA §7.2; generator tidak mengubah konfigurasi runtime.
MAX_PAGES = 5
MAX_CHARS = 12000
MAX_BYTES = 5242880
SOURCE_ID = re.compile(r"^(id|en)-(low|medium|high)-0[1-6]$")


@dataclass(frozen=True)
class Letter:
    """Surat sumber dengan anotasi terpisah dari teks yang akan dirender."""

    id: str
    lang: str
    label: str
    indicators: tuple[str, ...]
    text: str
    notes: str


@dataclass(frozen=True)
class Entry:
    """Satu dokumen PDF pada manifest; indicators disimpan sebagai array JSON dalam sel CSV."""

    id: str
    split: str
    lang: str
    format: str
    label: str
    indicators: str
    file: str
    sha256: str


# Menghitung checksum dari byte asli PDF, bukan teks hasil ekstraksi.
def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


# Memvalidasi kode dan kategori referensi memakai taksonomi serta skoring yang sama dengan runtime.
def validate_labels(codes: object, label: str) -> tuple[str, ...]:
    if not isinstance(codes, list) or any(not isinstance(code, str) or code not in TAXONOMY for code in codes):
        raise ValueError("Indikator referensi harus berupa array kode taksonomi.")
    if len(codes) != len(set(codes)) or score(set(codes)).value != label:
        raise ValueError("Indikator duplikat atau kategori tidak cocok dengan aturan skoring.")
    return tuple(code for code in TAXONOMY if code in codes)


# Memuat enam surat per kelompok lengkap; bahasa yang belum tersedia tidak diganti dengan data buatan.
def load_letters(directory: Path, languages: list[str]) -> list[Letter]:
    if not languages or len(set(languages)) != len(languages) or set(languages) - set(LANGUAGES):
        raise ValueError("Pilih bahasa id/en tanpa duplikat.")
    expected = [directory / f"{lang}-{label.lower()}.json" for lang in languages for label in LABELS]
    missing = [path.name for path in expected if not path.is_file()]
    if missing:
        raise ValueError(
            "Templat belum tersedia: " + ", ".join(missing) + ". Pilih --languages secara eksplisit untuk draf."
        )
    result = []
    for path in expected:
        try:
            objects = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            raise ValueError(f"JSON templat tidak valid: {path.name}.") from None
        if not isinstance(objects, list) or len(objects) != 6:
            raise ValueError(f"Templat harus berisi tepat enam surat: {path.name}.")
        lang, label = path.stem.split("-")
        expected_ids = {f"{path.stem}-{index:02}" for index in range(1, 7)}
        found_ids = set()
        for item in objects:
            if not isinstance(item, dict) or set(item) != {"id", "lang", "label", "indicators", "text", "notes"}:
                raise ValueError(f"Field templat tidak sesuai format T5-01: {path.name}.")
            if any(
                not isinstance(item[key], str) or not item[key].strip()
                for key in ("id", "lang", "label", "text", "notes")
            ):
                raise ValueError(f"Field string templat kosong atau salah tipe: {path.name}.")
            if (
                item["id"] not in expected_ids
                or item["id"] in found_ids
                or item["lang"] != lang
                or item["label"] != label.upper()
            ):
                raise ValueError(f"ID/bahasa/kategori templat tidak konsisten: {path.name}.")
            if len(item["text"]) > MAX_CHARS:
                raise ValueError(f"Surat melebihi batas teks baseline: {item['id']}.")
            found_ids.add(item["id"])
            result.append(
                Letter(
                    item["id"],
                    lang,
                    label.upper(),
                    validate_labels(item["indicators"], item["label"]),
                    item["text"],
                    item["notes"],
                )
            )
    return sorted(result, key=lambda letter: letter.id)


# Memilih dua surat dev per bahasa/kategori; penambahan bahasa lain tidak mengubah split yang sudah ada.
def assign_splits(letters: list[Letter], seed: int) -> dict[str, str]:
    splits = {}
    for lang in LANGUAGES:
        for label in LABELS:
            identifiers = sorted(letter.id for letter in letters if letter.lang == lang and letter.label == label)
            if not identifiers:
                continue
            if len(identifiers) != 6:
                raise ValueError("Setiap bahasa/kategori harus memiliki enam surat sebelum split ditetapkan.")
            random.Random(f"{seed}:{lang}:{label}").shuffle(identifiers)
            splits.update({identifier: "dev" if index < 2 else "test" for index, identifier in enumerate(identifiers)})
    return splits


# Menetapkan identitas dokumen unik; pasangan teks/scan berbagi ID sumber dan split.
def entry_for(letter: Letter, split: str, file_format: str, content: bytes) -> Entry:
    identifier = f"{letter.id}-{file_format}"
    return Entry(
        identifier,
        split,
        letter.lang,
        file_format,
        letter.label,
        json.dumps(letter.indicators, separators=(",", ":")),
        f"pdf/{identifier}.pdf",
        sha256(content),
    )


# Membatasi setiap file manifest ke nama PDF generator di bawah dataset/pdf, termasuk ketika ada symlink.
def pdf_path(directory: Path, entry: Entry) -> Path:
    if entry.file != f"pdf/{entry.id}.pdf":
        raise ValueError("Path PDF tidak sesuai ID manifest.")
    path = directory / entry.file
    pdf_directory = (directory / "pdf").resolve()
    if not pdf_directory.is_relative_to(directory.resolve()) or not path.resolve().is_relative_to(pdf_directory):
        raise ValueError("Path PDF keluar dari direktori dataset.")
    return path


# Memeriksa checksum dan metadata manifest sebelum hasil generator lama dipakai kembali.
def read_manifest(directory: Path) -> list[Entry]:
    manifest = directory / "manifest.csv"
    if not manifest.exists():
        return []
    with manifest.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(FIELDS):
            raise ValueError("Header manifest tidak sesuai SA §7.9.")
        entries = []
        for row in reader:
            if set(row) != set(FIELDS) or any(not isinstance(value, str) for value in row.values()):
                raise ValueError("Baris manifest tidak memiliki delapan kolom yang lengkap.")
            entries.append(Entry(**row))
    identifiers = set()
    pairs: dict[str, tuple[str, str, str, str]] = {}
    for entry in entries:
        source_id, separator, file_format = entry.id.rpartition("-")
        if not separator or not SOURCE_ID.fullmatch(source_id) or file_format not in {"text", "scan"}:
            raise ValueError("ID dokumen manifest tidak valid.")
        if entry.id in identifiers or entry.format != file_format or entry.split not in {"dev", "test"}:
            raise ValueError("ID duplikat, format, atau split manifest tidak valid.")
        if entry.lang != source_id.split("-")[0] or entry.label != source_id.split("-")[1].upper():
            raise ValueError("Bahasa/kategori manifest tidak sesuai ID sumber.")
        try:
            validate_labels(json.loads(entry.indicators), entry.label)
        except json.JSONDecodeError:
            raise ValueError("Sel indicators manifest harus berupa array JSON.") from None
        metadata = (entry.split, entry.lang, entry.label, entry.indicators)
        if source_id in pairs and pairs[source_id] != metadata:
            raise ValueError("Pasangan teks/scan memiliki split atau anotasi yang berbeda.")
        pairs[source_id] = metadata
        path = pdf_path(directory, entry)
        if not path.is_file() or sha256(path.read_bytes()) != entry.sha256:
            raise ValueError(f"PDF hilang atau checksum berubah: {entry.id}.")
        identifiers.add(entry.id)
    return entries


# Menulis hanya keluaran baru atau byte yang identik; perubahan dataset lama harus ditinjau secara eksplisit.
def write_pdf(path: Path, content: bytes) -> None:
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError(f"PDF sudah ada dengan isi berbeda; tidak ditimpa: {path.name}.")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


# Menggabungkan keluaran tanpa menggandakan baris atau mengganti split/anotasi lama secara diam-diam.
def write_manifest(directory: Path, existing: list[Entry], additions: list[Entry]) -> None:
    entries = {entry.id: entry for entry in existing}
    for entry in additions:
        if entry.id in entries and entries[entry.id] != entry:
            raise ValueError(f"Metadata dokumen lama berubah; perlu tinjauan: {entry.id}.")
        entries[entry.id] = entry
    with StringIO(newline="") as buffer:
        writer = csv.DictWriter(buffer, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(asdict(entries[key]) for key in sorted(entries))
        content = buffer.getvalue()
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "manifest.csv").write_text(content, encoding="utf-8", newline="\n")


# Memastikan PDF sah, tidak melewati batas demo, dan mempunyai atau tidak mempunyai lapisan teks sesuai format.
def inspect_pdf(content: bytes, expect_text: bool) -> tuple[int, str]:
    if not content.startswith(b"%PDF-") or len(content) > MAX_BYTES:
        raise ValueError("PDF tidak valid atau melebihi batas unggahan baseline.")
    document = pdfium.PdfDocument(content)
    try:
        if not 1 <= len(document) <= MAX_PAGES:
            raise ValueError("Jumlah halaman di luar batas baseline.")
        texts = []
        for index in range(len(document)):
            page = document[index]
            try:
                text_page = page.get_textpage()
                try:
                    text = text_page.get_text_range()
                finally:
                    text_page.close()
                if expect_text != bool(text.strip()):
                    raise ValueError("Lapisan teks PDF tidak sesuai format yang diharapkan.")
                texts.append(text)
            finally:
                page.close()
        return len(document), "\n".join(texts)
    finally:
        document.close()
