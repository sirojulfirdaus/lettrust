# Owner: B (PIC 5) | Status: COMPLETE | Ref: PLAN T5-08; PRD §10.4.3; SA §7.9
"""Tooling checksum freeze; integrasi run final menunggu T4-07 dan T6-05.

--check memeriksa metadata/prasyarat tanpa membuka PDF atau membuat artefak.
Freeze memakai target awal protokol 72 PDF berpasangan ID/EN, seimbang per kelompok.
Komposisi lain memerlukan keputusan OI-02 dan penyesuaian validator, bukan bypass.
Konfirmasi manusia Pash/Van harus mencakup review tiap surat, data sintetis,
provenance model bantu, dan komposisi final; agent tidak boleh mengisinya sendiri.
--reviewed-manifest-sha256 mengikat konfirmasi itu ke byte manifest yang ditinjau.
Flag ini merekam pernyataan manusia; tidak membuktikan identitas/review secara otomatis.

Contoh pemeriksaan aman: python scripts/dev.py eval freeze_testset --check
Setelah seluruh prasyarat selesai, human dapat membuat snapshot dengan --output,
--reviewed-by Pash --reviewed-by Van, serta --reviewed-manifest-sha256 HASH.
Gunakan --verify FILE untuk memeriksa freeze; snapshot lama tidak ditimpa.
Tidak ada panggilan LLM, perubahan manifest, atau eksekusi baseline/metrics di sini.
"""

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from _dataset import LABELS, LANGUAGES, ROOT, Entry, pdf_path, sha256, validate_labels
from _eval_records import parse_manifest_metadata

from app.analysis.taxonomy import TAXONOMY

REVIEWERS = {"Pash", "Van"}
KIND = "lettrust-testset-freeze"


# Memeriksa ketersediaan implementasi tanpa mengimpor atau mengarang antarmuka baseline/metrics yang masih STUB.
def dependency_issues() -> list[str]:
    issues = []
    for filename, code in (("baseline.py", "T6_05_NOT_AVAILABLE"), ("metrics.py", "T4_07_NOT_AVAILABLE")):
        path = Path(__file__).with_name(filename)
        lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
        if not lines or "Status: COMPLETE" not in lines[0]:
            issues.append(code)
    return issues


# Memeriksa komposisi target dan anotasi dari metadata saja; PDF test belum dibaca pada preflight.
def candidate_metadata(directory: Path) -> tuple[list[Entry], str, list[str]]:
    content = (directory / "manifest.csv").read_bytes()
    entries = parse_manifest_metadata(content)
    expected = {
        f"{lang}-{label.lower()}-{index:02}-{file_format}"
        for lang in LANGUAGES
        for label in LABELS
        for index in range(1, 7)
        for file_format in ("text", "scan")
    }
    issues = []
    if {entry.id for entry in entries} != expected:
        issues.append("DATASET_INCOMPLETE")
    groups = Counter((entry.split, entry.lang, entry.label, entry.format) for entry in entries)
    for split in ("dev", "test"):
        sizes = {
            groups[split, lang, label, form] for lang in LANGUAGES for label in LABELS for form in ("text", "scan")
        }
        if 0 in sizes or len(sizes) != 1:
            issues.append(f"{split.upper()}_COMPOSITION_UNBALANCED")
    pairs = {}
    coverage: dict[str, set[str]] = {"dev": set(), "test": set()}
    for entry in entries:
        codes = validate_labels(json.loads(entry.indicators), entry.label)
        source = entry.id.rsplit("-", 1)[0]
        if source in pairs and pairs[source] != codes:
            raise ValueError("Anotasi pasangan teks/scan tidak konsisten.")
        pairs[source] = codes
        coverage[entry.split].update(codes)
    if any(codes != set(TAXONOMY) for codes in coverage.values()):
        issues.append("TAXONOMY_COVERAGE_INCOMPLETE")
    return entries, sha256(content), issues


# Mengembalikan prasyarat yang belum tersedia; nama reviewer dan checksum hanya sah setelah konfirmasi manusia.
def check_readiness(
    directory: Path, reviewed_by: tuple[str, ...] = (), reviewed_manifest_sha256: str | None = None
) -> dict[str, Any]:
    entries, manifest_hash, issues = candidate_metadata(directory)
    issues.extend(dependency_issues())
    if set(reviewed_by) != REVIEWERS or len(reviewed_by) != len(REVIEWERS):
        issues.append("HUMAN_REVIEW_NOT_CONFIRMED")
    if reviewed_manifest_sha256 != manifest_hash:
        issues.append("REVIEW_MANIFEST_NOT_CONFIRMED")
    return {
        "ready": not issues,
        "issues": issues,
        "documents": len(entries),
        "testDocuments": sum(entry.split == "test" for entry in entries),
        "manifestSha256": manifest_hash,
        "pdfsOpened": 0,
    }


# Memeriksa hanya byte PDF test yang sudah disahkan; dev tidak dibaca dan manifest tidak ditulis ulang.
def checked_test_documents(directory: Path, entries: list[Entry]) -> list[dict[str, str]]:
    documents = []
    for entry in sorted((entry for entry in entries if entry.split == "test"), key=lambda item: item.id):
        if sha256(pdf_path(directory, entry).read_bytes()) != entry.sha256:
            raise ValueError("Checksum PDF test berubah.")
        document = asdict(entry)
        document["indicators"] = json.dumps(
            validate_labels(json.loads(entry.indicators), entry.label), separators=(",", ":")
        )
        documents.append(document)
    return documents


# Menulis snapshot baru setelah seluruh gate lolos; open eksklusif mencegah penimpaan bukti freeze sebelumnya.
def create_freeze(
    directory: Path, output: Path, reviewed_by: tuple[str, ...], reviewed_manifest_sha256: str
) -> dict[str, Any]:
    readiness = check_readiness(directory, reviewed_by, reviewed_manifest_sha256)
    if not readiness["ready"]:
        raise ValueError("Prasyarat freeze belum lengkap.")
    if output.resolve().is_relative_to(directory.resolve()):
        raise ValueError("Snapshot freeze harus berada di luar dataset.")
    if output.exists():
        raise FileExistsError("Snapshot freeze sudah ada.")
    entries, manifest_hash, issues = candidate_metadata(directory)
    if issues or manifest_hash != reviewed_manifest_sha256:
        raise ValueError("Manifest berubah setelah pemeriksaan prasyarat.")
    snapshot = {
        "schemaVersion": 1,
        "kind": KIND,
        "createdAt": datetime.now(UTC).isoformat(),
        "manifestSha256": manifest_hash,
        "reviewedBy": sorted(reviewed_by),
        "documents": checked_test_documents(directory, entries),
    }
    if sha256((directory / "manifest.csv").read_bytes()) != manifest_hash:
        raise ValueError("Manifest berubah selama perhitungan checksum.")
    serialized = json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(serialized)
    return snapshot


# Membandingkan metadata dan checksum test dengan snapshot asli; perubahan data tidak diterima diam-diam.
def verify_freeze(directory: Path, snapshot_path: Path) -> dict[str, Any]:
    snapshot_content = snapshot_path.read_bytes()
    snapshot = json.loads(snapshot_content)
    if (
        not isinstance(snapshot, dict)
        or set(snapshot) != {"schemaVersion", "kind", "createdAt", "manifestSha256", "reviewedBy", "documents"}
        or type(snapshot["schemaVersion"]) is not int
        or snapshot["schemaVersion"] != 1
        or snapshot["kind"] != KIND
        or snapshot["reviewedBy"] != sorted(REVIEWERS)
        or not isinstance(snapshot["createdAt"], str)
    ):
        raise ValueError("Format snapshot freeze tidak valid.")
    if datetime.fromisoformat(snapshot["createdAt"]).utcoffset() is None:
        raise ValueError("Timestamp snapshot harus mempunyai zona waktu.")
    entries, manifest_hash, issues = candidate_metadata(directory)
    if issues or manifest_hash != snapshot["manifestSha256"]:
        raise ValueError("Manifest berbeda dari snapshot freeze.")
    if checked_test_documents(directory, entries) != snapshot["documents"]:
        raise ValueError("Dokumen test berbeda dari snapshot freeze.")
    if sha256((directory / "manifest.csv").read_bytes()) != manifest_hash:
        raise ValueError("Manifest berubah selama verifikasi.")
    return {"verified": True, "documents": len(snapshot["documents"]), "snapshotSha256": sha256(snapshot_content)}


# CLI preflight tidak membaca PDF; freeze nyata tetap memerlukan seluruh dependensi dan konfirmasi review manusia.
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset-dir", type=Path, default=ROOT / "dataset")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--check", action="store_true")
    action.add_argument("--verify", type=Path, metavar="FILE")
    action.add_argument("--test", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--reviewed-by", choices=sorted(REVIEWERS), action="append", default=[])
    parser.add_argument("--reviewed-manifest-sha256")
    args = parser.parse_args(argv)
    if args.test:
        import pytest

        return pytest.main(["-q", "-p", "no:cacheprovider", str(Path(__file__).with_name("test_freeze_testset.py"))])
    try:
        if args.verify:
            print(json.dumps(verify_freeze(args.dataset_dir, args.verify)))
            return 0
        readiness = check_readiness(args.dataset_dir, tuple(args.reviewed_by), args.reviewed_manifest_sha256)
        if args.check or not readiness["ready"]:
            print(json.dumps(readiness))
            return 0 if readiness["ready"] else 1
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        output = args.output or ROOT / "results" / f"freeze-{stamp}" / "testset.freeze.json"
        snapshot = create_freeze(args.dataset_dir, output, tuple(args.reviewed_by), args.reviewed_manifest_sha256)
        print(json.dumps({"output": str(output), "documents": len(snapshot["documents"])}))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as error:
        # Isi exception dapat memuat input/path; hanya jenis error aman yang ditampilkan.
        print(f"Freeze gagal ({type(error).__name__}); periksa metadata, checksum, dan prasyarat.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
