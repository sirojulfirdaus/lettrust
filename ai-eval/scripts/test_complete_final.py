# Owner: B (PIC 5) | Status: COMPLETE | Ref: PLAN T5-08; protocol §8.3
"""Uji pemulihan sintetis: hasil pertama tidak ditimpa dan hanya kegagalan yang diulang."""

import json
from pathlib import Path
from typing import Any

import complete_final
import pytest
from _dataset import Entry
from _eval_records import write_json
from baseline import analyze_text
from test_run_eval import settings as settings

from app.core.config import Settings


# Membuat observasi unit tanpa PDF proyek, API key, atau panggilan LLM.
def observation(identifier: str, variant: str, success: bool = True) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "id": identifier,
        "variant": variant,
        "status": "OK" if success else "UNAVAILABLE",
        "result": analyze_text("Posisi staf gudang di Bandung.").model_dump(mode="json", by_alias=True)
        if success
        else None,
        "extraction": {
            "status": "OK",
            "method": "TEXT_LAYER",
            "pagesTotal": 1,
            "pagesProcessed": 1,
            "truncated": False,
            "language": "id",
            "reasonDetail": None,
        },
        "error": None if success else {"stage": "ANALYSIS", "code": "AI_PROVIDER_ERROR", "reasonDetail": None},
        "latencyMs": 7,
    }


# Menyimpan JSONL unit agar jalur baca/publikasi yang sesungguhnya ikut diuji.
def save_lines(path: Path, items: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(item) + "\n" for item in items), encoding="utf-8")


# Gagal awal tetap UNAVAILABLE pada raw utama walau percobaan tambahan berhasil.
def test_recovery_keeps_first_failure_and_does_not_repeat_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, settings: Settings
) -> None:
    entries = [Entry(f"id-low-0{i}-text", "test", "id", "text", "LOW", "[]", "unit.pdf", "0" * 64) for i in (1, 2, 3)]
    original = {
        "model": settings.llm_model,
        "intervalSeconds": 0,
        "status": "RUNNING",
        "stopReason": "AI_PROVIDER_ERROR",
        "stoppedAt": "unit-stop",
        "freeze": {"snapshotSha256": "unit"},
    }
    write_json(tmp_path / "partial_run_config.json", original)
    write_json(tmp_path / "run_config.json", original)
    (tmp_path / "tmp").mkdir()
    initial = [observation(entries[0].id, "pipeline", False), observation(entries[1].id, "pipeline")]
    initial += [observation(entry.id, "baseline") for entry in entries]
    save_lines(tmp_path / "partial_raw.jsonl", initial)
    save_lines(tmp_path / "remaining_baseline.jsonl", [])
    save_lines(tmp_path / "partial_model_outputs.jsonl", [{"id": entry.id, "attempts": []} for entry in entries[:2]])
    original_bytes = (tmp_path / "partial_raw.jsonl").read_bytes()
    calls = []

    # Menyediakan profil unit tetap tanpa mengakses snapshot/PDF proyek.
    def profile(*args: object) -> tuple[dict[str, Any], list[Entry]]:
        return original, entries

    # Meniru respons sukses agar test hanya menilai pilihan ID dan pemisahan artefak.
    def evaluate(entry: Entry, *args: object) -> tuple[dict[str, Any], dict[str, Any]]:
        calls.append(entry.id)
        return observation(entry.id, "pipeline"), {"id": entry.id, "attempts": []}

    monkeypatch.setattr(complete_final, "check_profile", profile)
    monkeypatch.setattr(complete_final, "get_provider", lambda config: None)
    monkeypatch.setattr(complete_final, "evaluate_document", evaluate)
    monkeypatch.setattr(complete_final, "sleep", lambda seconds: None)
    assert complete_final.complete_run(tmp_path, tmp_path, tmp_path, tmp_path) == 0
    assert calls == [entries[2].id, entries[0].id]
    records = complete_final.read_records(tmp_path / "raw.jsonl")
    assert len(records) == 6
    assert complete_final.index_records(records)[("pipeline", entries[0].id)]["status"] == "UNAVAILABLE"
    assert (tmp_path / "partial_raw.jsonl").read_bytes() == original_bytes
    assert len(complete_final.read_records(tmp_path / "retry_raw.jsonl")) == 1
    assert complete_final.read_json(tmp_path / "run_config.json")["counts"] == {"OK": 5, "UNAVAILABLE": 1}
    with pytest.raises(ValueError, match="diterbitkan"):
        complete_final.complete_run(tmp_path, tmp_path, tmp_path, tmp_path)
    assert calls == [entries[2].id, entries[0].id]


# Observasi first-pass ganda tidak boleh lolos melalui penggabungan dictionary.
def test_duplicate_first_observations_rejected() -> None:
    record = observation("id-low-01-text", "pipeline")
    with pytest.raises(ValueError, match="duplikat"):
        complete_final.index_records([record, record])
