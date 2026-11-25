# Owner: B (PIC 5) | Status: COMPLETE | Ref: PLAN T5-05; PRD §10.4; SA §7.9
"""Uji generator dengan surat sintetis sementara; sampel test tidak masuk dataset evaluasi."""

import csv
import json
from collections import Counter
from dataclasses import replace
from pathlib import Path

import generate_pdfs
import make_scans
import pytest
from _dataset import (
    DEFAULT_SEED,
    FIELDS,
    LABELS,
    assign_splits,
    inspect_pdf,
    load_letters,
    pdf_path,
    read_manifest,
    sha256,
    write_manifest,
    write_pdf,
)

from app.extraction.ocr import ocr_page


# Membuat sumber unit test yang terpisah dari templat Van/Pash dan tidak pernah dipakai untuk evaluasi model.
def write_templates(directory: Path, languages: tuple[str, ...] = ("id",)) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for lang in languages:
        for label in LABELS:
            codes = {"LOW": [], "MEDIUM": ["URGENCY_PRESSURE"], "HIGH": ["PAYMENT_REQUEST"]}[label]
            pattern = {
                "LOW": "Biaya relokasi ditanggung perusahaan; pelamar tidak membayar.",
                "MEDIUM": "Konfirmasi segera karena kuota terbatas.",
                "HIGH": "Pelamar wajib membayar deposit seragam sebelum bekerja.",
            }[label]
            english_pattern = {
                "LOW": "The employer covers relocation expenses; applicants are not asked to pay.",
                "MEDIUM": "Accept within thirty minutes or lose your place because the quota is limited.",
                "HIGH": "Applicants must pay a uniform deposit before starting work.",
            }[label]
            letters = [
                {
                    "id": f"{lang}-{label.lower()}-{index:02}",
                    "lang": lang,
                    "label": label,
                    "indicators": codes,
                    "text": (
                        f"PT Contoh Unit Test\nSurat Penawaran Kerja — Staf Administrasi\n\n"
                        f"Surat sintetis nomor {index}. Tugas mencatat stok dan menyusun laporan.\n{pattern}"
                        if lang == "id"
                        else f"Example Unit Test Company\nEmployment Offer — Inventory Clerk\n\n"
                        f"Synthetic letter number {index}. Duties include stock records and monthly reports.\n"
                        f"{english_pattern}\nConfirm through the official company contact."
                    ),
                    "notes": "ANNOTATION-UNIT-TEST: hanya untuk test generator, bukan sumber evaluasi.",
                }
                for index in range(1, 7)
            ]
            (directory / f"{lang}-{label.lower()}.json").write_text(json.dumps(letters), encoding="utf-8")


# Mode penuh menolak dependensi yang hilang; mode parsial tidak diam-diam membuat templat pengganti.
def test_full_generation_requires_english_templates(tmp_path: Path) -> None:
    templates, dataset = tmp_path / "templates", tmp_path / "dataset"
    write_templates(templates)
    with pytest.raises(ValueError, match="en-low.json"):
        generate_pdfs.generate_dataset(templates, dataset, ["id", "en"], DEFAULT_SEED)
    assert not dataset.exists()


# Struktur, ID, anotasi, dan panjang surat diperiksa sebelum PDF pertama ditulis.
@pytest.mark.parametrize(
    "defect", ["duplicate_id", "unknown_code", "wrong_label", "missing_notes", "wrong_type", "too_long"]
)
def test_invalid_source_is_rejected_before_output(tmp_path: Path, defect: str) -> None:
    templates, dataset = tmp_path / "templates", tmp_path / "dataset"
    write_templates(templates)
    path = templates / "id-low.json"
    letters = json.loads(path.read_text(encoding="utf-8"))
    if defect == "duplicate_id":
        letters[1]["id"] = letters[0]["id"]
    elif defect == "unknown_code":
        letters[0]["indicators"] = ["UNKNOWN_CODE"]
    elif defect == "wrong_label":
        letters[0]["indicators"] = ["PAYMENT_REQUEST"]
    elif defect == "missing_notes":
        del letters[0]["notes"]
    elif defect == "wrong_type":
        letters[0]["text"] = 123
    else:
        letters[0]["text"] = "x" * 12001
    path.write_text(json.dumps(letters), encoding="utf-8")
    with pytest.raises(ValueError):
        generate_pdfs.generate_dataset(templates, dataset, ["id"], DEFAULT_SEED)
    assert not dataset.exists()


# Split ditetapkan pada surat, seimbang per kategori, dan tidak berubah ketika bahasa Inggris ditambahkan.
def test_grouped_split_is_stable_when_english_arrives(tmp_path: Path) -> None:
    write_templates(tmp_path, ("id", "en"))
    indonesian = load_letters(tmp_path, ["id"])
    all_letters = load_letters(tmp_path, ["id", "en"])
    partial = assign_splits(indonesian, DEFAULT_SEED)
    full = assign_splits(all_letters, DEFAULT_SEED)
    assert partial == {identifier: split for identifier, split in full.items() if identifier.startswith("id-")}
    for lang in ("id", "en"):
        for label in LABELS:
            assert Counter(
                full[letter.id] for letter in all_letters if letter.lang == lang and letter.label == label
            ) == {"dev": 2, "test": 4}


# PDF mempertahankan isi sumber dan Unicode; label, notes, dan ID anotasi tidak dicetak.
def test_pdf_is_deterministic_and_contains_only_letter_text(tmp_path: Path) -> None:
    write_templates(tmp_path)
    letter = load_letters(tmp_path, ["id"])[0]
    first = generate_pdfs.render_text_pdf(letter.text)
    second = generate_pdfs.render_text_pdf(letter.text)
    assert first == second
    pages, extracted = inspect_pdf(first, expect_text=True)
    assert pages == 1
    assert "—" in extracted
    assert "ANNOTATION-UNIT-TEST" not in extracted
    assert letter.id not in extracted


# Dua belas ID dokumen dev dan dua puluh empat test dibuat dari 18 surat, dengan checksum dan pasangan konsisten.
def test_partial_generation_and_rerun_are_identical(tmp_path: Path) -> None:
    templates, dataset = tmp_path / "templates", tmp_path / "dataset"
    write_templates(templates)
    generate_pdfs.generate_dataset(templates, dataset, ["id"], DEFAULT_SEED)
    make_scans.generate_scans(dataset, ["id"], DEFAULT_SEED, 72)
    entries = read_manifest(dataset)
    before = (dataset / "manifest.csv").read_bytes()
    hashes = {entry.id: entry.sha256 for entry in entries}
    assert len(entries) == 36
    assert Counter(entry.split for entry in entries) == {"dev": 12, "test": 24}
    assert Counter(entry.format for entry in entries) == {"text": 18, "scan": 18}
    assert len({entry.id for entry in entries}) == 36
    for entry in entries:
        assert sha256(pdf_path(dataset, entry).read_bytes()) == entry.sha256
        inspect_pdf(pdf_path(dataset, entry).read_bytes(), expect_text=entry.format == "text")
    generate_pdfs.generate_dataset(templates, dataset, ["id"], DEFAULT_SEED)
    make_scans.generate_scans(dataset, ["id"], DEFAULT_SEED, 72)
    assert before == (dataset / "manifest.csv").read_bytes()
    assert hashes == {entry.id: entry.sha256 for entry in read_manifest(dataset)}


# Kehadiran sumber Inggris melengkapi dataset 72 PDF tanpa mengubah PDF atau split Indonesia sebelumnya.
def test_full_generation_preserves_partial_dataset(tmp_path: Path) -> None:
    templates, dataset = tmp_path / "templates", tmp_path / "dataset"
    write_templates(templates)
    generate_pdfs.generate_dataset(templates, dataset, ["id"], DEFAULT_SEED)
    make_scans.generate_scans(dataset, ["id"], DEFAULT_SEED, 72)
    before = {entry.id: entry for entry in read_manifest(dataset)}
    write_templates(templates, ("en",))
    generate_pdfs.generate_dataset(templates, dataset, ["id", "en"], DEFAULT_SEED)
    make_scans.generate_scans(dataset, ["id", "en"], DEFAULT_SEED, 72)
    entries = read_manifest(dataset)
    assert len(entries) == 72
    assert Counter(entry.split for entry in entries) == {"dev": 24, "test": 48}
    for entry in entries:
        if entry.id in before:
            assert entry == before[entry.id]


# Mutasi PDF lama terdeteksi sebelum dipakai sebagai sumber scan.
def test_checksum_drift_prevents_scan_generation(tmp_path: Path) -> None:
    templates, dataset = tmp_path / "templates", tmp_path / "dataset"
    write_templates(templates)
    entries = generate_pdfs.generate_dataset(templates, dataset, ["id"], DEFAULT_SEED)
    pdf_path(dataset, entries[0]).write_bytes(b"modified")
    with pytest.raises(ValueError, match="checksum berubah"):
        make_scans.generate_scans(dataset, ["id"], DEFAULT_SEED, 72)
    assert not list((dataset / "pdf").glob("*-scan.pdf"))


# PDF dan metadata lama tidak ditimpa ketika terjadi perbedaan isi atau perubahan split.
def test_existing_outputs_are_not_silently_replaced(tmp_path: Path) -> None:
    templates, dataset = tmp_path / "templates", tmp_path / "dataset"
    write_templates(templates)
    entries = generate_pdfs.generate_dataset(templates, dataset, ["id"], DEFAULT_SEED)
    with pytest.raises(ValueError, match="tidak ditimpa"):
        write_pdf(pdf_path(dataset, entries[0]), b"different")
    changed = replace(entries[0], split="dev" if entries[0].split == "test" else "test")
    before = (dataset / "manifest.csv").read_bytes()
    with pytest.raises(ValueError, match="Metadata dokumen lama berubah"):
        write_manifest(dataset, entries, [changed])
    assert (dataset / "manifest.csv").read_bytes() == before


# Path manifest tidak dapat mengarahkan generator ke berkas lain di luar dataset/pdf.
def test_manifest_path_cannot_escape_dataset(tmp_path: Path) -> None:
    templates, dataset = tmp_path / "templates", tmp_path / "dataset"
    write_templates(templates)
    entries = generate_pdfs.generate_dataset(templates, dataset, ["id"], DEFAULT_SEED)
    with pytest.raises(ValueError, match="Path PDF"):
        pdf_path(dataset, replace(entries[0], file="../outside.pdf"))


# Manifest memakai delapan kolom dan array JSON yang dapat dibaca kembali, termasuk indikator kosong.
def test_manifest_schema_and_json_indicators(tmp_path: Path) -> None:
    templates, dataset = tmp_path / "templates", tmp_path / "dataset"
    write_templates(templates)
    generate_pdfs.generate_dataset(templates, dataset, ["id"], DEFAULT_SEED)
    with (dataset / "manifest.csv").open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        assert reader.fieldnames == list(FIELDS)
        assert all(isinstance(json.loads(row["indicators"]), list) for row in reader)


# Scan benar-benar tidak memiliki text layer dan tetap terbaca oleh Tesseract ind+eng nyata.
@pytest.mark.parametrize("language, phrase", [("id", "administrasi"), ("en", "employment offer")])
def test_scan_supports_real_ocr(tmp_path: Path, language: str, phrase: str) -> None:
    write_templates(tmp_path, (language,))
    letter = load_letters(tmp_path, [language])[0]
    source = generate_pdfs.render_text_pdf(letter.text)
    scanned = make_scans.render_scan_pdf(source, letter.id, DEFAULT_SEED)
    assert inspect_pdf(scanned, expect_text=False)[1].strip() == ""
    assert scanned != source
    assert phrase in ocr_page(scanned, 0, 300, 20).lower()


# CLI penuh gagal jelas tanpa sumber Inggris; CLI parsial melaporkan cakupan yang sebenarnya.
def test_cli_reports_partial_coverage(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    templates, dataset = tmp_path / "templates", tmp_path / "dataset"
    write_templates(templates)
    args = ["--templates-dir", str(templates), "--dataset-dir", str(dataset)]
    assert generate_pdfs.main(args) == 1
    assert "Templat belum tersedia" in capsys.readouterr().err
    assert generate_pdfs.main([*args, "--languages", "id"]) == 0
    assert json.loads(capsys.readouterr().out)["coverage"] == "partial"
    assert make_scans.main(["--dataset-dir", str(dataset)]) == 1
    assert "PDF teks belum lengkap" in capsys.readouterr().err
    assert make_scans.main(["--dataset-dir", str(dataset), "--languages", "id", "--dpi", "72"]) == 0
    assert json.loads(capsys.readouterr().out)["pdfCount"] == 18


# Titik masuk pengujian tetap melalui launcher eval agar dependency dan OCR sama dengan runtime.
def main() -> int:
    return pytest.main(["-q", "-p", "no:cacheprovider", __file__])


if __name__ == "__main__":
    raise SystemExit(main())
