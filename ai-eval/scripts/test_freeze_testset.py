# Owner: B (PIC 5) | Status: COMPLETE | Ref: PLAN T5-08; PRD §10.4.3; SA §7.9
"""Uji freeze pada metadata dan byte sintetis sementara; tidak membekukan korpus evaluasi atau memanggil LLM."""

import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import freeze_testset
import pytest
from _dataset import LABELS, LANGUAGES, Entry, sha256, write_manifest
from _eval_records import parse_manifest_metadata

from app.analysis.taxonomy import TAXONOMY


@pytest.fixture
def dataset(tmp_path: Path) -> Path:
    """Menyediakan 72 berkas byte untuk checksum saja; berkas ini bukan PDF bagi evaluasi atau ekstraksi."""
    directory = tmp_path / "dataset"
    (directory / "pdf").mkdir(parents=True)
    entries = []
    for lang in LANGUAGES:
        for label in LABELS:
            codes = {"LOW": [], "MEDIUM": ["URGENCY_PRESSURE"], "HIGH": list(TAXONOMY)}[label]
            for index in range(1, 7):
                for form in ("text", "scan"):
                    identifier = f"{lang}-{label.lower()}-{index:02}-{form}"
                    content = f"unit-checksum-bytes:{identifier}".encode()
                    file = f"pdf/{identifier}.pdf"
                    (directory / file).write_bytes(content)
                    entries.append(
                        Entry(
                            identifier,
                            "dev" if index <= 2 else "test",
                            lang,
                            form,
                            label,
                            json.dumps(codes),
                            file,
                            sha256(content),
                        )
                    )
    write_manifest(directory, [], entries)
    return directory


@pytest.fixture
def available_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mengisolasi status ketersediaan; tidak meniru antarmuka atau hasil baseline/metrics yang belum tersedia."""
    monkeypatch.setattr(freeze_testset, "dependency_issues", lambda: [])


# Memeriksa seluruh metadata tanpa akses PDF atau penulisan artefak, termasuk saat output diminta.
def test_preflight_does_not_open_pdfs_or_write(
    dataset: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    original = Path.read_bytes

    def metadata_only(path: Path) -> bytes:
        """Menolak pembacaan PDF pada preflight, walaupun seluruh berkas tersedia."""
        assert path.suffix != ".pdf"
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", metadata_only)
    output = tmp_path / "unused" / "freeze.json"
    assert freeze_testset.main(["--check", "--dataset-dir", str(dataset), "--output", str(output)]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["documents"] == 72 and report["testDocuments"] == 48 and report["pdfsOpened"] == 0
    assert "HUMAN_REVIEW_NOT_CONFIRMED" in report["issues"]
    assert not output.parent.exists()


# Header diperiksa tanpa impor modul atau eksekusi main milik Sat/Pash.
def test_dependency_headers_are_checked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(freeze_testset, "__file__", str(tmp_path / "freeze_testset.py"))
    (tmp_path / "baseline.py").write_text("# Status: STUB\nraise AssertionError('must not import')\n")
    (tmp_path / "metrics.py").write_text("# Status: COMPLETE\nraise AssertionError('must not import')\n")
    assert freeze_testset.dependency_issues() == ["T6_05_NOT_AVAILABLE"]
    (tmp_path / "baseline.py").write_text("# Status: COMPLETE\n")
    assert freeze_testset.dependency_issues() == []


# Data Indonesia saja tidak dapat dibekukan meskipun checksum dan konfirmasi review diberikan.
def test_partial_dataset_is_rejected(dataset: Path, tmp_path: Path, available_dependencies: None) -> None:
    entries = parse_manifest_metadata((dataset / "manifest.csv").read_bytes())
    write_manifest(dataset, [], [entry for entry in entries if entry.lang == "id"])
    digest = sha256((dataset / "manifest.csv").read_bytes())
    report = freeze_testset.check_readiness(dataset, ("Pash", "Van"), digest)
    assert "DATASET_INCOMPLETE" in report["issues"]
    with pytest.raises(ValueError, match="Prasyarat"):
        freeze_testset.create_freeze(dataset, tmp_path / "freeze.json", ("Pash", "Van"), digest)
    assert not (tmp_path / "freeze.json").exists()


# Konfirmasi harus lengkap dan terikat ke byte manifest saat ini; nama atau hash usang tidak cukup.
@pytest.mark.parametrize(
    "reviewers,valid_hash", [((), True), (("Pash",), True), (("Pash", "Van", "Pash"), True), (("Pash", "Van"), False)]
)
def test_review_confirmation_is_required(
    dataset: Path, tmp_path: Path, available_dependencies: None, reviewers: tuple[str, ...], valid_hash: bool
) -> None:
    digest = sha256((dataset / "manifest.csv").read_bytes()) if valid_hash else "0" * 64
    with pytest.raises(ValueError, match="Prasyarat"):
        freeze_testset.create_freeze(dataset, tmp_path / "freeze.json", reviewers, digest)
    assert not (tmp_path / "freeze.json").exists()


# Perubahan manifest setelah tinjauan membuat konfirmasi checksum tidak berlaku lagi.
def test_review_cannot_be_reused_after_manifest_changes(
    dataset: Path, tmp_path: Path, available_dependencies: None
) -> None:
    manifest = dataset / "manifest.csv"
    digest = sha256(manifest.read_bytes())
    manifest.write_bytes(manifest.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="Prasyarat"):
        freeze_testset.create_freeze(dataset, tmp_path / "freeze.json", ("Pash", "Van"), digest)


# Dependensi STUB tetap menghalangi freeze; test ini tidak mengarang hasil baseline atau metrics.
def test_missing_dependency_blocks_freeze(dataset: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(freeze_testset, "dependency_issues", lambda: ["T4_07_NOT_AVAILABLE"])
    digest = sha256((dataset / "manifest.csv").read_bytes())
    with pytest.raises(ValueError, match="Prasyarat"):
        freeze_testset.create_freeze(dataset, tmp_path / "freeze.json", ("Pash", "Van"), digest)
    assert not (tmp_path / "freeze.json").exists()


# Freeze dan verifikasi hanya membaca PDF test; metadata dan PDF dev tidak diubah atau dibuka.
def test_round_trip_preserves_dataset_and_skips_dev_pdfs(
    dataset: Path, tmp_path: Path, available_dependencies: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    before = (dataset / "manifest.csv").read_bytes()
    entries = parse_manifest_metadata(before)
    dev_files = {dataset / entry.file for entry in entries if entry.split == "dev"}
    original = Path.read_bytes

    def test_files_only(path: Path) -> bytes:
        """Membuktikan freeze/verifikasi tidak membutuhkan byte PDF dev."""
        assert path not in dev_files
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", test_files_only)
    output = tmp_path / "freeze.json"
    snapshot = freeze_testset.create_freeze(dataset, output, ("Pash", "Van"), sha256(before))
    assert len(snapshot["documents"]) == 48
    assert all(row["split"] == "test" for row in snapshot["documents"])
    assert datetime.fromisoformat(snapshot["createdAt"]).utcoffset() is not None
    assert freeze_testset.verify_freeze(dataset, output)["verified"] is True
    assert before == (dataset / "manifest.csv").read_bytes()
    frozen = output.read_bytes()
    with pytest.raises(FileExistsError):
        freeze_testset.create_freeze(dataset, output, ("Pash", "Van"), sha256(before))
    assert output.read_bytes() == frozen


# Snapshot tidak boleh ditulis ke dalam dataset, walaupun file tujuan belum ada.
def test_output_cannot_be_inside_dataset(dataset: Path, available_dependencies: None) -> None:
    digest = sha256((dataset / "manifest.csv").read_bytes())
    with pytest.raises(ValueError, match="di luar dataset"):
        freeze_testset.create_freeze(dataset, dataset / "freeze.json", ("Pash", "Van"), digest)
    assert not (dataset / "freeze.json").exists()


# Perubahan byte, anotasi, split, atau keanggotaan test membuat snapshot lama gagal diverifikasi.
@pytest.mark.parametrize("defect", ["bytes", "annotation", "split", "missing"])
def test_dataset_changes_invalidate_freeze(
    dataset: Path, tmp_path: Path, available_dependencies: None, defect: str
) -> None:
    output = tmp_path / "freeze.json"
    manifest = dataset / "manifest.csv"
    freeze_testset.create_freeze(dataset, output, ("Pash", "Van"), sha256(manifest.read_bytes()))
    entries = parse_manifest_metadata(manifest.read_bytes())
    index = next(i for i, entry in enumerate(entries) if entry.split == "test" and entry.label == "HIGH")
    if defect == "bytes":
        (dataset / entries[index].file).write_bytes(b"changed-unit-bytes")
    else:
        if defect == "annotation":
            entries[index] = replace(entries[index], indicators='["PAYMENT_REQUEST"]')
        elif defect == "split":
            entries[index] = replace(entries[index], split="dev")
        else:
            entries.pop(index)
        write_manifest(dataset, [], entries)
    with pytest.raises(ValueError):
        freeze_testset.verify_freeze(dataset, output)


# Snapshot dengan versi, reviewer, atau daftar dokumen yang diubah tidak dianggap valid.
@pytest.mark.parametrize(
    "field,value",
    [
        ("schemaVersion", 99),
        ("schemaVersion", True),
        ("reviewedBy", ["B"]),
        ("documents", []),
        ("createdAt", "invalid"),
        ("createdAt", "2026-11-25T00:00:00"),
    ],
)
def test_altered_snapshot_is_rejected(
    dataset: Path, tmp_path: Path, available_dependencies: None, field: str, value: object
) -> None:
    output = tmp_path / "freeze.json"
    snapshot = freeze_testset.create_freeze(
        dataset, output, ("Pash", "Van"), sha256((dataset / "manifest.csv").read_bytes())
    )
    snapshot[field] = value
    output.write_text(json.dumps(snapshot), encoding="utf-8")
    with pytest.raises(ValueError):
        freeze_testset.verify_freeze(dataset, output)


# CLI menghasilkan freeze dan verifikasi hanya pada direktori sintetis dengan prasyarat unit test yang lengkap.
def test_cli_round_trip(
    dataset: Path, tmp_path: Path, available_dependencies: None, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "freeze.json"
    args = [
        "--dataset-dir",
        str(dataset),
        "--output",
        str(output),
        "--reviewed-by",
        "Pash",
        "--reviewed-by",
        "Van",
        "--reviewed-manifest-sha256",
        sha256((dataset / "manifest.csv").read_bytes()),
    ]
    assert freeze_testset.main([*args, "--check"]) == 0
    assert not output.exists()
    capsys.readouterr()
    assert freeze_testset.main(args) == 0
    capsys.readouterr()
    assert freeze_testset.main(["--dataset-dir", str(dataset), "--verify", str(output)]) == 0
    assert json.loads(capsys.readouterr().out)["documents"] == 48


# Error JSON tidak mencetak isi input atau path yang mungkin sensitif.
def test_cli_errors_are_sanitized(dataset: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_text("unit-sensitive-not-real", encoding="utf-8")
    assert freeze_testset.main(["--dataset-dir", str(dataset), "--verify", str(invalid)]) == 1
    captured = capsys.readouterr()
    assert "unit-sensitive-not-real" not in captured.err + captured.out
    assert "JSONDecodeError" in captured.err
