"""Test sintetis pembaca metrik tanpa menjalankan ekstraksi PDF atau memanggil LLM."""

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import metrics
import pytest
from _dataset import FIELDS


# Menulis dataset dan run kontrak legacy kecil supaya CLI tidak bergantung pada artefak evaluasi nyata.
def synthetic_run(tmp_path: Path) -> tuple[Path, Path, list[dict[str, Any]]]:
    dataset = tmp_path / "dataset"
    run = tmp_path / "run"
    dataset.mkdir()
    run.mkdir()
    rows = [
        {
            "id": "id-high-01-text",
            "split": "dev",
            "lang": "id",
            "format": "text",
            "label": "HIGH",
            "indicators": '["PAYMENT_REQUEST"]',
            "file": "pdf/id-high-01-text.pdf",
            "sha256": "a" * 64,
        },
        {
            "id": "id-low-01-scan",
            "split": "dev",
            "lang": "id",
            "format": "scan",
            "label": "LOW",
            "indicators": "[]",
            "file": "pdf/id-low-01-scan.pdf",
            "sha256": "b" * 64,
        },
    ]
    manifest = dataset / "manifest.csv"
    with manifest.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    high = {
        "id": rows[0]["id"],
        "status": "COMPLETED",
        "result": {
            "category": "HIGH",
            "indicatorDetails": [{"code": "PAYMENT_REQUEST"}],
            "meta": {"droppedIndicators": 1},
        },
        "extraction": {"status": "OK", "method": "TEXT_LAYER"},
        "error": None,
        "latencyMs": 100,
    }
    low = {
        "id": rows[1]["id"],
        "status": "COMPLETED",
        "result": {"category": "LOW", "indicatorDetails": [], "meta": {"droppedIndicators": 0}},
        "extraction": {"status": "OK", "method": "OCR"},
        "error": None,
        "latencyMs": 300,
    }
    records = [high, low]
    (run / "raw.jsonl").write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")
    config = {
        "schemaVersion": 1,
        "manifestSha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "split": "dev",
        "method": "llm",
        "state": "finished",
        "documents": [{"id": row["id"], "sha256": row["sha256"]} for row in rows],
    }
    (run / "run_config.json").write_text(json.dumps(config), encoding="utf-8")
    return dataset, run, records


# Memastikan kategori, indikator, extraction, drop-rate, latensi, dan artefak confusion terhitung akurat.
def test_metrics_cli_outputs_expected_synthetic_metrics(tmp_path: Path) -> None:
    dataset, run, _ = synthetic_run(tmp_path)
    assert metrics.main([str(run), "--dataset-dir", str(dataset)]) == 0
    result = json.loads((run / "metrics.json").read_text(encoding="utf-8"))
    pipeline = result["variants"]["pipeline"]
    assert pipeline["classification"]["accuracy"] == 1.0
    assert pipeline["classification"]["perCategory"]["MEDIUM"]["support"] == 0
    assert pipeline["indicators"]["PAYMENT_REQUEST"]["recall"] == 1.0
    assert pipeline["indicators"]["PAYMENT_REQUEST"]["precision"] == 1.0
    assert pipeline["latency"] == {"count": 2, "medianMs": 200.0, "p95Ms": 300, "minMs": 100, "maxMs": 300}
    assert pipeline["extractionSuccessByFormat"]["scan"]["successRate"] == 1.0
    assert pipeline["evidenceValidation"] == {"dropped": 1, "candidateIndicators": 2, "dropRate": 0.5}
    with (run / "confusion.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 9
    assert next(row for row in rows if row["actual"] == "HIGH" and row["predicted"] == "HIGH")["count"] == "1"


# Menerima subset kontrak v1 dari documents hanya jika checksum setiap dokumen cocok dengan manifest.
@pytest.mark.parametrize("failure", [None, "checksum", "version"])
def test_metrics_accepts_valid_v1_subset_and_rejects_invalid_metadata(tmp_path: Path, failure: str | None) -> None:
    dataset, run, records = synthetic_run(tmp_path)
    normalized = []
    for record in records:
        indicator_details = (
            [
                {
                    "code": "PAYMENT_REQUEST",
                    "label": "Permintaan pembayaran kepada pelamar",
                    "severity": "HIGH",
                    "evidence": ["Bukti sintetis."],
                }
            ]
            if record["id"] == "id-high-01-text"
            else []
        )
        category = "HIGH" if indicator_details else "LOW"
        normalized.append(
            {
                "schemaVersion": 1,
                "id": record["id"],
                "variant": "pipeline",
                "status": "OK",
                "result": {
                    "category": category,
                    "indicators": ["Permintaan pembayaran kepada pelamar"] if indicator_details else [],
                    "indicatorDetails": indicator_details,
                    "explanation": "Hasil sintetis.",
                    "recommendation": "Tinjau informasi.",
                    "meta": {
                        "model": "synthetic-test",
                        "promptVersion": "test-v1",
                        "latencyMs": 1,
                        "droppedIndicators": 0,
                    },
                },
                "extraction": {
                    "status": "OK",
                    "method": "TEXT_LAYER",
                    "pagesTotal": 1,
                    "pagesProcessed": 1,
                    "truncated": False,
                    "language": "id",
                    "reasonDetail": None,
                },
                "error": None,
                "latencyMs": 50,
            }
        )
    normalized = normalized[:1]
    (run / "raw.jsonl").write_text("".join(json.dumps(record) + "\n" for record in normalized), encoding="utf-8")
    config = json.loads((run / "run_config.json").read_text(encoding="utf-8"))
    config.update(
        status="COMPLETE",
        variants=["pipeline"],
        records=len(normalized),
        counts={"OK": len(normalized)},
        documents=[{"id": normalized[0]["id"], "sha256": "a" * 64}],
    )
    if failure == "checksum":
        config["documents"][0]["sha256"] = "0" * 64
    if failure == "version":
        config["schemaVersion"] = 99
    config.pop("method")
    config.pop("state")
    (run / "run_config.json").write_text(json.dumps(config), encoding="utf-8")
    expected = 0 if failure is None else 1
    assert metrics.main([str(run), "--dataset-dir", str(dataset)]) == expected
    if failure is not None:
        assert not (run / "metrics.json").exists()
        return
    output = json.loads((run / "metrics.json").read_text(encoding="utf-8"))
    assert output["variants"]["pipeline"]["classification"]["accuracy"] == 1.0
    assert output["recordCount"] == 1


# Menghitung NO_CONTENT dengan latensi ekstraksi, tetapi tidak memberi RUN_ABORTED kategori atau latensi.
def test_legacy_no_content_latency_is_distinct_from_run_aborted(tmp_path: Path) -> None:
    dataset, run, _ = synthetic_run(tmp_path)
    records = [
        {
            "id": "id-high-01-text",
            "status": "NOT_PERFORMED",
            "result": None,
            "extraction": {"status": "NO_CONTENT", "reasonDetail": "NO_EXTRACTABLE_TEXT"},
            "error": {"stage": "extraction", "code": "NO_EXTRACTABLE_TEXT"},
            "latencyMs": 42,
        },
        {
            "id": "id-low-01-scan",
            "status": "NOT_PERFORMED",
            "result": None,
            "extraction": None,
            "error": {"stage": "run", "code": "RUN_ABORTED"},
            "latencyMs": None,
        },
    ]
    (run / "raw.jsonl").write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")
    config_path = run / "run_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["state"] = "stopped"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    assert metrics.main([str(run), "--dataset-dir", str(dataset)]) == 0
    result = json.loads((run / "metrics.json").read_text(encoding="utf-8"))
    pipeline = result["variants"]["pipeline"]
    assert pipeline["latency"] == {"count": 1, "medianMs": 42, "p95Ms": 42, "minMs": 42, "maxMs": 42}
    assert pipeline["reliability"]["failureReasons"] == {"NO_EXTRACTABLE_TEXT": 1, "RUN_ABORTED": 1}


# Menolak keluaran incomplete, duplikat, dan perbedaan checksum sebelum menghasilkan file metrik.
@pytest.mark.parametrize("failure", ["checksum", "incomplete", "duplicate"])
def test_metrics_rejects_inconsistent_run(tmp_path: Path, failure: str) -> None:
    dataset, run, records = synthetic_run(tmp_path)
    config_path = run / "run_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if failure == "checksum":
        config["manifestSha256"] = "0" * 64
    elif failure == "incomplete":
        config["state"] = "running"
    else:
        records.append(records[0])
        (run / "raw.jsonl").write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")
    config_path.write_text(json.dumps(config), encoding="utf-8")
    assert metrics.main([str(run), "--dataset-dir", str(dataset)]) == 1
    assert not (run / "metrics.json").exists()


# Melindungi artefak hasil sebelumnya; pengguna harus menyatakan --force untuk mengganti keluaran.
def test_existing_outputs_require_force(tmp_path: Path) -> None:
    dataset, run, _ = synthetic_run(tmp_path)
    output = run / "metrics.json"
    output.write_text("existing", encoding="utf-8")
    assert metrics.main([str(run), "--dataset-dir", str(dataset)]) == 1
    assert output.read_text(encoding="utf-8") == "existing"
