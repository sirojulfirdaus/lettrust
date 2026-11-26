# Owner: B (PIC 5) | Status: COMPLETE | Ref: PLAN T5-08; PRD §10.4.3; SA §18.2
"""Uji gate final pada korpus unit sementara, tanpa memakai test set proyek atau API LLM."""

import json
from pathlib import Path

import freeze_testset
import pytest
import run_eval
from _dataset import LABELS, LANGUAGES, Entry, sha256, write_manifest
from _final_eval import load_frozen_entries
from generate_pdfs import render_text_pdf
from metrics import load_manifest, load_run
from test_run_eval import HIGH_TEXT, LOW_OUTPUT, LOW_TEXT
from test_run_eval import settings as settings

from app.analysis.mock_provider import MockLLMProvider
from app.analysis.provider import ProviderQuotaExceeded
from app.analysis.taxonomy import TAXONOMY
from app.core.config import Settings


@pytest.fixture
def final_setup(tmp_path: Path, settings: Settings) -> tuple[Path, Path, Path]:
    """Membuat korpus unit 72 PDF, snapshot nyata, dan referensi dev dengan provider mock eksplisit."""
    directory = tmp_path / "dataset"
    (directory / "pdf").mkdir(parents=True)
    entries = []
    for label in LABELS:
        text = {
            "LOW": LOW_TEXT,
            "MEDIUM": "Segera konfirmasi penerimaan tawaran ini hari ini sebelum pukul 18.00 agar kuota tidak habis.",
            "HIGH": HIGH_TEXT,
        }[label]
        content = render_text_pdf(text)
        codes = {"LOW": [], "MEDIUM": ["URGENCY_PRESSURE"], "HIGH": list(TAXONOMY)}[label]
        for lang in LANGUAGES:
            for index in range(1, 7):
                for form in ("text", "scan"):
                    identifier = f"{lang}-{label.lower()}-{index:02}-{form}"
                    filename = f"pdf/{identifier}.pdf"
                    (directory / filename).write_bytes(content)
                    entries.append(
                        Entry(
                            identifier,
                            "dev" if index <= 2 else "test",
                            lang,
                            form,
                            label,
                            json.dumps(codes),
                            filename,
                            sha256(content),
                        )
                    )
    write_manifest(directory, [], entries)
    snapshot = tmp_path / "freeze.json"
    freeze_testset.create_freeze(
        directory, snapshot, ("Pash", "Van"), sha256((directory / "manifest.csv").read_bytes())
    )
    reference = tmp_path / "reference"
    run_eval.execute_run(
        directory,
        reference,
        run_eval.load_dev_entries(directory),
        settings,
        provider=MockLLMProvider(*([LOW_OUTPUT] * 24)),
    )
    return directory, snapshot, reference


# Kedua varian wajib menghasilkan satu record per test dan dapat dibaca metrics bersama.
def test_final_run_is_complete_and_metrics_compatible(
    final_setup: tuple[Path, Path, Path], settings: Settings, tmp_path: Path
) -> None:
    directory, snapshot, reference = final_setup
    output = tmp_path / "final"
    entries, verified = load_frozen_entries(directory, snapshot)
    config = run_eval.execute_run(
        directory,
        output,
        entries,
        settings,
        provider=MockLLMProvider(*([LOW_OUTPUT] * 48)),
        variants=("pipeline", "baseline"),
        split="test",
        freeze=snapshot,
        reference_run=reference,
    )
    assert config["status"] == "COMPLETE" and config["records"] == 96
    assert config["purpose"] == "final-evaluation" and config["datasetStatus"] == "frozen"
    assert config["freeze"]["snapshotSha256"] == verified["snapshotSha256"]
    assert Path(config["reservation"]).is_file()
    _, records = load_run(output, load_manifest(directory / "manifest.csv"), directory / "manifest.csv")
    assert len({(row["variant"], row["id"]) for row in records}) == 96


# Snapshot salinan tidak membuka kesempatan mengulang run test pada manifest yang sama.
def test_final_reservation_survives_quota_failure(
    final_setup: tuple[Path, Path, Path], settings: Settings, tmp_path: Path
) -> None:
    directory, snapshot, reference = final_setup
    entries, _ = load_frozen_entries(directory, snapshot)
    output = tmp_path / "failed"
    config = run_eval.execute_run(
        directory,
        output,
        entries,
        settings,
        provider=MockLLMProvider(ProviderQuotaExceeded("synthetic")),
        variants=("pipeline", "baseline"),
        split="test",
        freeze=snapshot,
        reference_run=reference,
    )
    assert config["status"] == "RUNNING" and config["stopReason"] == "AI_QUOTA_EXCEEDED"
    assert config["records"] == 1 and not (output / "raw.jsonl").exists()
    assert (output / "partial_raw.jsonl").read_bytes() == (output / "tmp/raw.jsonl").read_bytes()
    copied = tmp_path / "copy.json"
    copied.write_bytes(snapshot.read_bytes())
    with pytest.raises(FileExistsError):
        run_eval.execute_run(
            directory,
            tmp_path / "second",
            entries,
            settings,
            provider=MockLLMProvider(),
            variants=("pipeline", "baseline"),
            split="test",
            freeze=copied,
            reference_run=reference,
        )
    assert not (tmp_path / "second").exists()


# Profil, cakupan, kode runtime, dan checksum wajib cocok sebelum reservasi atau panggilan model dibuat.
@pytest.mark.parametrize("failure", ["subset", "variant", "settings", "runtime", "pdf", "reference"])
def test_final_gate_rejects_changes_before_prediction(
    final_setup: tuple[Path, Path, Path],
    settings: Settings,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    directory, snapshot, reference = final_setup
    entries, _ = load_frozen_entries(directory, snapshot)
    variants = ("pipeline", "baseline")
    if failure == "subset":
        entries = entries[:1]
    elif failure == "variant":
        variants = ("pipeline",)
    elif failure == "settings":
        settings = Settings.model_validate(settings.model_dump() | {"evidence_fuzzy_threshold": 89})
    elif failure == "runtime":
        hashes = run_eval.source_hashes() | {"prompt": "changed"}
        monkeypatch.setattr(run_eval, "source_hashes", lambda: hashes)
    elif failure == "pdf":
        (directory / entries[0].file).write_bytes(b"changed")
    elif failure == "reference":
        path = reference / "run_config.json"
        config = json.loads(path.read_text())
        config["status"] = "RUNNING"
        path.write_text(json.dumps(config))
    with pytest.raises(ValueError):
        run_eval.execute_run(
            directory,
            tmp_path / "invalid",
            entries,
            settings,
            provider=MockLLMProvider(),
            variants=variants,
            split="test",
            freeze=snapshot,
            reference_run=reference,
        )
    assert not (tmp_path / "invalid").exists()
    assert not list((tmp_path / "results").glob("*.reservation.json"))


# CLI menolak gate yang hilang atau limit sebelum membaca Settings maupun PDF.
@pytest.mark.parametrize(
    "args",
    [[], ["--freeze", "missing"], ["--freeze", "missing", "--reference-run", "missing", "--limit", "1"]],
)
def test_test_cli_requires_full_gate(args: list[str], monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden_settings() -> Settings:
        """Mendeteksi konfigurasi dibaca sebelum penolakan argumen test yang tidak sah."""
        raise AssertionError("Settings belum boleh dibaca")

    monkeypatch.setattr(run_eval, "get_settings", forbidden_settings)
    with pytest.raises(SystemExit) as failure:
        run_eval.main(["--split", "test", *args])
    assert failure.value.code == 2


# Snapshot yang berubah di tengah proses membuat seluruh bukti tetap parsial dan tidak diterbitkan sebagai run lengkap.
def test_snapshot_change_prevents_final_publication(
    final_setup: tuple[Path, Path, Path], settings: Settings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    directory, snapshot, reference = final_setup
    entries, _ = load_frozen_entries(directory, snapshot)
    provider = MockLLMProvider(*([LOW_OUTPUT] * 48))
    original = provider.complete

    def change_snapshot(messages: list[dict[str, str]]) -> object:
        """Mengubah byte snapshot unit satu kali untuk menguji pemeriksaan sesudah prediksi."""
        result = original(messages)
        value = json.loads(snapshot.read_text())
        value["createdAt"] = "2026-01-01T00:00:00+00:00"
        snapshot.write_text(json.dumps(value))
        return result

    monkeypatch.setattr(provider, "complete", change_snapshot)
    output = tmp_path / "changed-snapshot"
    with pytest.raises(ValueError, match="Snapshot"):
        run_eval.execute_run(
            directory,
            output,
            entries,
            settings,
            provider=provider,
            variants=("pipeline", "baseline"),
            split="test",
            freeze=snapshot,
            reference_run=reference,
        )
    config = json.loads((output / "run_config.json").read_text())
    assert config["status"] == "RUNNING" and config["stopReason"] == "FREEZE_CHANGED"
    assert not (output / "raw.jsonl").exists()
    assert (output / "partial_raw.jsonl").is_file()
