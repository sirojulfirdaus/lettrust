# Owner: B (PIC 5) | Status: COMPLETE | Ref: PLAN T5-08; PRD §10.4.3; SA §7.9
"""Gate run test: snapshot sah, konfigurasi dev tetap, dan satu reservasi per manifest."""

import json
from pathlib import Path
from typing import Any

from _dataset import Entry, sha256
from _eval_records import load_dev_entries, parse_manifest_metadata, public_settings
from freeze_testset import verify_freeze
from metrics import load_manifest, load_run

from app.core.config import Settings


# Memuat seluruh test dari manifest hanya setelah snapshot dan checksum PDF-nya sah.
def load_frozen_entries(directory: Path, snapshot_path: Path) -> tuple[list[Entry], dict[str, Any]]:
    verified = verify_freeze(directory, snapshot_path)
    entries = sorted(
        (
            entry
            for entry in parse_manifest_metadata((directory / "manifest.csv").read_bytes())
            if entry.split == "test"
        ),
        key=lambda entry: entry.id,
    )
    return entries, verified


# Mengikat parameter dan kode detektor ke run dev lengkap; perubahan tooling final saja diperbolehkan.
def validate_reference(directory: Path, reference: Path, settings: Settings, hashes: dict[str, str]) -> dict[str, str]:
    manifest = directory / "manifest.csv"
    config, _ = load_run(reference, load_manifest(manifest), manifest)
    expected = [{"id": entry.id, "sha256": entry.sha256} for entry in load_dev_entries(directory)]
    if (
        config.get("status") != "COMPLETE"
        or config.get("split") != "dev"
        or "pipeline" not in config.get("variants", [])
        or config.get("documents") != expected
        or config.get("settings") != public_settings(settings)
    ):
        raise ValueError("Parameter final harus sama dengan run dev pipeline lengkap yang dirujuk.")
    runtime_names = set(hashes) - {"runner", "finalGate", "freeze", "metrics"}
    if any(config.get("sourceSha256", {}).get(name) != hashes[name] for name in runtime_names):
        raise ValueError("Kode runtime berubah sejak run dev; final test tidak boleh dipakai untuk tuning.")
    return {
        "configSha256": sha256((reference / "run_config.json").read_bytes()),
        "rawSha256": sha256((reference / "raw.jsonl").read_bytes()),
    }


# Menolak subset, varian tunggal, dan entry yang diganti sebelum satu pun prediksi test dilakukan.
def validate_final_run(
    directory: Path,
    entries: list[Entry],
    settings: Settings,
    variants: tuple[str, ...],
    snapshot: Path,
    reference: Path,
    hashes: dict[str, str],
) -> dict[str, Any]:
    frozen, verified = load_frozen_entries(directory, snapshot)
    if entries != frozen or variants != ("pipeline", "baseline"):
        raise ValueError("Run final wajib seluruh test dengan varian pipeline lalu baseline.")
    profile = validate_reference(directory, reference, settings, hashes)
    return {"snapshotSha256": verified["snapshotSha256"], "reference": profile}


# Membatasi satu run final per manifest, termasuk run gagal; reservasi tidak dihapus otomatis.
def reserve_final_run(directory: Path, output: Path, metadata: dict[str, Any], manifest_hash: str) -> Path:
    results = directory.resolve().parent / "results"
    results.mkdir(parents=True, exist_ok=True)
    reservation = results / f"final-test-{manifest_hash}.reservation.json"
    payload = {
        "schemaVersion": 1,
        "manifestSha256": manifest_hash,
        "snapshotSha256": metadata["snapshotSha256"],
        "outputDirectory": str(output.resolve()),
    }
    with reservation.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, indent=2) + "\n")
    return reservation
