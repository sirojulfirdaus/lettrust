# Owner: Pash (PIC 4) | Status: COMPLETE | Ref: PLAN T4-07; PRD §10.3 MET-09–MET-15; SA §7.9
"""Menghitung metrik kategori, indikator, ekstraksi, reliabilitas, dan latensi dari satu direktori run."""

import argparse
import csv
import json
import math
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from _dataset import FIELDS, ROOT, Entry, validate_labels
from _eval_schema import EvaluationRecord

from app.analysis.scoring import score
from app.analysis.taxonomy import TAXONOMY

LABELS = ("LOW", "MEDIUM", "HIGH")
SUCCESS_STATUSES = {"OK", "COMPLETED"}


# Menghitung checksum SHA-256 file dalam blok agar manifest besar tidak dibaca sekaligus.
def file_sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


# Membaca manifest tanpa membuka PDF dan memvalidasi anotasi sebelum dipakai sebagai ground truth.
def load_manifest(path: Path) -> dict[str, Entry]:
    entries: dict[str, Entry] = {}
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(FIELDS):
            raise ValueError("Header manifest tidak sesuai SA §7.9.")
        for row in reader:
            if set(row) != set(FIELDS) or any(not isinstance(value, str) for value in row.values()):
                raise ValueError("Baris manifest tidak lengkap.")
            try:
                entry = Entry(**row)
                codes = json.loads(entry.indicators)
                validate_labels(codes, entry.label)
            except (TypeError, ValueError, json.JSONDecodeError):
                raise ValueError("Anotasi manifest tidak valid.") from None
            if entry.id in entries or entry.split not in {"dev", "test"}:
                raise ValueError("ID duplikat atau split manifest tidak valid.")
            entries[entry.id] = entry
    if not entries:
        raise ValueError("Manifest kosong.")
    return entries


# Membaca JSON object tanpa meneruskan error parser yang bisa memuat path atau data input.
def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ValueError(f"JSON tidak dapat dibaca: {path.name}.") from None
    if not isinstance(value, dict):
        raise ValueError(f"Format JSON tidak valid: {path.name}.")
    return value


# Memvalidasi lifecycle dan manifest run; format legacy hanya diterima jika producer menyatakan selesai.
def load_run(
    directory: Path, entries: dict[str, Entry], manifest_path: Path
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    config = read_json(directory / "run_config.json")
    manifest_hash = file_sha256(manifest_path)
    version = config.get("schemaVersion")
    if not isinstance(version, int) or isinstance(version, bool) or version != 1:
        raise ValueError("Versi run_config.schemaVersion tidak didukung.")
    if config.get("manifestSha256") != manifest_hash:
        raise ValueError("Checksum manifest tidak cocok dengan run.")
    if config.get("status") == "COMPLETE":
        variants = config.get("variants")
        if (
            not isinstance(variants, list)
            or not variants
            or len(variants) != len(set(variants))
            or set(variants) - {"pipeline", "baseline"}
        ):
            raise ValueError("Daftar variant run tidak valid.")
        expected_status = "COMPLETE"
        legacy = False
    elif config.get("state") in {"finished", "stopped"} and config.get("method") == "llm":
        variants = ["pipeline"]
        expected_status = config["state"]
        legacy = True
    else:
        raise ValueError("Run belum selesai atau format lifecycle tidak didukung.")
    split = config.get("split")
    if split not in {"dev", "test"}:
        raise ValueError("Split pada konfigurasi run tidak valid.")
    expected_entries = selected_entries(config, entries, split, legacy)
    if not expected_entries:
        raise ValueError("Manifest tidak memiliki dokumen pada split run.")
    try:
        raw_lines = (directory / "raw.jsonl").read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        raise ValueError("raw.jsonl tidak dapat dibaca.") from None
    if not raw_lines or any(not line.strip() for line in raw_lines):
        raise ValueError("raw.jsonl kosong atau memuat baris kosong.")
    records: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for line in raw_lines:
        try:
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError
            if legacy:
                record = validate_legacy_record(raw)
            else:
                validated = EvaluationRecord.model_validate(raw)
                record = validated.model_dump(mode="json", by_alias=True)
        except (json.JSONDecodeError, ValueError, TypeError):
            raise ValueError("Record raw.jsonl tidak sesuai skema run.") from None
        variant = record["variant"]
        identifier = record["id"]
        key = (variant, identifier)
        if variant not in variants or identifier not in expected_entries or key in seen:
            raise ValueError("Record memiliki variant/ID tak dikenal atau duplikat.")
        seen.add(key)
        records.append(record)
    expected = {(variant, identifier) for variant in variants for identifier in expected_entries}
    if seen != expected:
        raise ValueError("Jumlah atau cakupan record tidak cocok dengan manifest dan variant run.")
    if not legacy and config.get("records") != len(records):
        raise ValueError("Jumlah record tidak cocok dengan run_config.json.")
    if not legacy:
        actual_counts = Counter(record["status"] for record in records)
        configured_counts = config.get("counts")
        if not isinstance(configured_counts, dict) or configured_counts != dict(actual_counts):
            raise ValueError("Rincian status record tidak cocok dengan run_config.json.")
    if legacy:
        if any(not legacy_status_matches(record, expected_status) for record in records):
            raise ValueError("Status record run legacy tidak valid.")
    return config, records


# Memvalidasi subset dokumen run dan checksum-nya; tanpa daftar, kontrak v1 memakai seluruh split manifest.
def selected_entries(config: dict[str, Any], entries: dict[str, Entry], split: str, legacy: bool) -> dict[str, Entry]:
    split_entries = {identifier: entry for identifier, entry in entries.items() if entry.split == split}
    documents = config.get("documents")
    if documents is None and not legacy:
        return split_entries
    if not isinstance(documents, list) or not documents:
        raise ValueError("Daftar dokumen run tidak valid.")
    selected: dict[str, Entry] = {}
    for item in documents:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise ValueError("Daftar dokumen run tidak valid.")
        identifier = item["id"]
        entry = split_entries.get(identifier)
        if identifier in selected or entry is None or item.get("sha256") != entry.sha256:
            raise ValueError("Dokumen run tidak cocok dengan split/checksum manifest.")
        selected[identifier] = entry
    return selected


# Membedakan NO_CONTENT yang sudah diekstrak dari RUN_ABORTED yang belum mulai dikerjakan.
def legacy_status_matches(record: dict[str, Any], run_state: str) -> bool:
    if record["status"] in {"COMPLETED", "UNAVAILABLE"}:
        return True
    if record["status"] != "NOT_PERFORMED":
        return False
    error = record.get("error")
    if not isinstance(error, dict):
        return False
    if error.get("stage") == "extraction":
        extraction = record.get("extraction")
        return (
            run_state in {"finished", "stopped"}
            and error.get("code") in {"PDF_UNREADABLE", "NO_EXTRACTABLE_TEXT"}
            and isinstance(extraction, dict)
            and extraction.get("status") == "NO_CONTENT"
            and isinstance(record.get("latencyMs"), int)
            and not isinstance(record.get("latencyMs"), bool)
            and record["latencyMs"] >= 0
        )
    return (
        run_state == "stopped"
        and error.get("stage") == "run"
        and error.get("code") == "RUN_ABORTED"
        and record.get("extraction") is None
        and record.get("latencyMs") is None
    )


# Menormalisasi keluaran runner T5-07 lama secara eksplisit tanpa menganggap NOT_PERFORMED sebagai hasil sukses.
def validate_legacy_record(raw: dict[str, Any]) -> dict[str, Any]:
    identifier = raw.get("id")
    status = raw.get("status")
    if not isinstance(identifier, str) or status not in {"COMPLETED", "UNAVAILABLE", "NOT_PERFORMED"}:
        raise ValueError("Record legacy tidak valid.")
    result = raw.get("result")
    error = raw.get("error")
    extraction = raw.get("extraction")
    latency = raw.get("latencyMs")
    if latency is not None and (not isinstance(latency, int) or isinstance(latency, bool) or latency < 0):
        raise ValueError("Latensi legacy tidak valid.")
    if status == "COMPLETED":
        if not isinstance(result, dict) or not isinstance(result.get("indicatorDetails"), list):
            raise ValueError("Hasil COMPLETED legacy tidak valid.")
        if result.get("category") not in LABELS or not isinstance(extraction, dict):
            raise ValueError("Kategori atau metadata ekstraksi legacy tidak valid.")
        if error is not None or latency is None or extraction.get("status") != "OK":
            raise ValueError("Metadata sukses record legacy tidak konsisten.")
        codes = {item.get("code") for item in result["indicatorDetails"] if isinstance(item, dict)}
        if len(codes) != len(result["indicatorDetails"]) or codes - set(TAXONOMY):
            raise ValueError("Kode indikator record legacy tidak valid.")
        if score(codes).value != result["category"]:
            raise ValueError("Kategori record legacy tidak cocok dengan skoring indikator.")
        variant = "pipeline"
    elif result is not None or not isinstance(error, dict):
        raise ValueError("Record gagal legacy tidak valid.")
    else:
        variant = "pipeline"
    return {
        "id": identifier,
        "variant": variant,
        "status": status,
        "result": result,
        "extraction": extraction,
        "error": error,
        "latencyMs": latency,
    }


# Mengembalikan kode indikator dan jumlah yang dibuang dari record sukses.
def result_indicators(record: dict[str, Any]) -> set[str]:
    result = record.get("result")
    if not isinstance(result, dict):
        return set()
    details = result.get("indicatorDetails", [])
    codes = {item.get("code") for item in details if isinstance(item, dict)}
    if codes - set(TAXONOMY):
        raise ValueError("Record memuat kode indikator di luar taksonomi.")
    return codes


# Menghitung ukuran klasifikasi dengan penyebut hanya hasil yang memiliki kategori aktual dan prediksi.
def classification(records: list[dict[str, Any]], labels: dict[str, str]) -> dict[str, Any]:
    usable = [record for record in records if record["status"] in SUCCESS_STATUSES]
    confusion = {actual: {predicted: 0 for predicted in LABELS} for actual in LABELS}
    for record in usable:
        actual = labels[record["id"]]
        predicted = record["result"]["category"]
        if predicted not in LABELS:
            raise ValueError("Kategori prediksi tidak dikenal.")
        confusion[actual][predicted] += 1
    per_class: dict[str, dict[str, Any]] = {}
    f1_values = []
    for label in LABELS:
        tp = confusion[label][label]
        actual_count = sum(confusion[label].values())
        predicted_count = sum(confusion[actual][label] for actual in LABELS)
        precision = tp / predicted_count if predicted_count else 0.0
        recall = tp / actual_count if actual_count else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {"support": actual_count, "precision": precision, "recall": recall, "f1": f1}
        f1_values.append(f1)
    total = len(usable)
    correct = sum(confusion[label][label] for label in LABELS)
    return {
        "documents": len(records),
        "classified": total,
        "unavailableOrNotPerformed": len(records) - total,
        "accuracy": correct / total if total else None,
        "macroF1": statistics.fmean(f1_values) if f1_values else None,
        "perCategory": per_class,
        "confusion": confusion,
    }


# Menghitung precision/recall indikator dari kode taksonomi dan label manifest, bukan teks tampilan.
def indicator_metrics(records: list[dict[str, Any]], entries: dict[str, Entry]) -> dict[str, Any]:
    codes = {code: {"tp": 0, "fp": 0, "fn": 0, "support": 0} for code in TAXONOMY}
    for record in records:
        actual = set(json.loads(entries[record["id"]].indicators))
        predicted = result_indicators(record) if record["status"] in SUCCESS_STATUSES else set()
        for code in codes:
            if code in actual:
                codes[code]["support"] += 1
            codes[code]["tp"] += int(code in actual and code in predicted)
            codes[code]["fn"] += int(code in actual and code not in predicted)
            codes[code]["fp"] += int(code not in actual and code in predicted)
    output = {}
    for code, counts in codes.items():
        precision = counts["tp"] / (counts["tp"] + counts["fp"]) if counts["tp"] + counts["fp"] else 0.0
        recall = counts["tp"] / counts["support"] if counts["support"] else None
        output[code] = {**counts, "precision": precision, "recall": recall}
    return output


# Menghitung p95 dengan nearest-rank dan median hanya dari latencyMs yang benar-benar tersedia.
def latency_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    values = sorted(record["latencyMs"] for record in records if record.get("latencyMs") is not None)
    if not values:
        return {"count": 0, "medianMs": None, "p95Ms": None, "minMs": None, "maxMs": None}
    return {
        "count": len(values),
        "medianMs": statistics.median(values),
        "p95Ms": values[math.ceil(0.95 * len(values)) - 1],
        "minMs": values[0],
        "maxMs": values[-1],
    }


# Menghitung ekstraksi dan jumlah evidence drop, dengan metadata yang tidak tersedia tetap terlihat terpisah.
def quality_metrics(records: list[dict[str, Any]], entries: dict[str, Entry]) -> dict[str, Any]:
    extraction: dict[str, dict[str, int]] = {}
    drop_count = candidate_count = 0
    for record in records:
        entry = entries[record["id"]]
        bucket = extraction.setdefault(entry.format, {"documents": 0, "metadataAvailable": 0, "succeeded": 0})
        bucket["documents"] += 1
        metadata = record.get("extraction")
        if isinstance(metadata, dict):
            bucket["metadataAvailable"] += 1
            bucket["succeeded"] += int(metadata.get("status") == "OK")
        if record["status"] in SUCCESS_STATUSES:
            result = record["result"]
            details = result.get("indicatorDetails", [])
            meta = result.get("meta", {})
            dropped = meta.get("droppedIndicators", 0) if isinstance(meta, dict) else 0
            if not isinstance(dropped, int) or isinstance(dropped, bool) or dropped < 0:
                raise ValueError("Jumlah droppedIndicators tidak valid.")
            drop_count += dropped
            candidate_count += len(details) + dropped
    for bucket in extraction.values():
        bucket["successRate"] = bucket["succeeded"] / bucket["documents"] if bucket["documents"] else 0.0
        bucket["withoutMetadata"] = bucket["documents"] - bucket["metadataAvailable"]
    return {
        "extractionSuccessByFormat": extraction,
        "evidenceValidation": {
            "dropped": drop_count,
            "candidateIndicators": candidate_count,
            "dropRate": drop_count / candidate_count if candidate_count else None,
        },
    }


# Membentuk rincian reliabilitas dari status record dan error code aman tanpa menampilkan teks error.
def reliability(records: list[dict[str, Any]]) -> dict[str, Any]:
    succeeded = sum(record["status"] in SUCCESS_STATUSES for record in records)
    failures: Counter[str] = Counter()
    for record in records:
        if record["status"] not in SUCCESS_STATUSES:
            error = record.get("error")
            code = error.get("code", "UNKNOWN") if isinstance(error, dict) else "UNKNOWN"
            failures[str(code)] += 1
    return {
        "requests": len(records),
        "completed": succeeded,
        "unavailableOrNotPerformed": len(records) - succeeded,
        "completionRate": succeeded / len(records) if records else None,
        "failureReasons": dict(sorted(failures.items())),
    }


# Menulis satu baris confusion per variant dan pasangan kategori agar mudah dibaca alat spreadsheet.
def write_confusion(path: Path, variants: dict[str, dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("variant", "actual", "predicted", "count"))
        for variant in sorted(variants):
            matrix = variants[variant]["classification"]["confusion"]
            for actual in LABELS:
                for predicted in LABELS:
                    writer.writerow((variant, actual, predicted, matrix[actual][predicted]))


# Menghasilkan metrik semua variant, breakdown bahasa/format, dan selisih pada dokumen yang sama-sama sukses.
def calculate_metrics(
    config: dict[str, Any], records: list[dict[str, Any]], entries: dict[str, Entry]
) -> dict[str, Any]:
    labels = {identifier: entry.label for identifier, entry in entries.items()}
    variants = sorted({record["variant"] for record in records})
    output: dict[str, Any] = {
        "schemaVersion": 1,
        "split": config["split"],
        "manifestSha256": config["manifestSha256"],
        "recordCount": len(records),
        "variants": {},
        "baselineComparison": None,
        "definitions": {
            "categoryDenominator": "Hanya record sukses yang memiliki kategori; kegagalan dilaporkan terpisah.",
            "indicatorDenominator": "Semua dokumen run; record gagal tidak menghasilkan indikator prediksi.",
            "extractionSuccessRate": "Jumlah extraction.status=OK dibagi semua dokumen format tersebut.",
            "p95": "Nearest-rank percentile; latency null tidak disertakan.",
            "zeroDivision": "Metrik tanpa denominator bernilai 0; recall indikator tanpa support bernilai null.",
        },
    }
    report: dict[str, dict[str, Any]] = {}
    for variant in variants:
        selected = [record for record in records if record["variant"] == variant]
        classification_result = classification(selected, labels)
        indicator_result = indicator_metrics(selected, entries)
        quality = quality_metrics(selected, entries)
        dimensions: dict[str, Any] = {}
        for dimension in ("lang", "format"):
            values = sorted({getattr(entries[record["id"]], dimension) for record in selected})
            dimensions[f"classificationBy{dimension.capitalize()}"] = {
                value: classification(
                    [record for record in selected if getattr(entries[record["id"]], dimension) == value], labels
                )
                for value in values
            }
        errors: Counter[str] = Counter()
        for record in selected:
            if record["status"] not in SUCCESS_STATUSES:
                error = record.get("error")
                if isinstance(error, dict):
                    errors[f"{error.get('stage', 'UNKNOWN')}:{error.get('code', 'UNKNOWN')}"] += 1
        report[variant] = {
            "classification": classification_result,
            "indicators": indicator_result,
            "latency": latency_metrics(selected),
            "reliability": reliability(selected),
            **quality,
            **dimensions,
            "failureReasons": dict(sorted(errors.items())),
        }
        output["variants"][variant] = report[variant]
    if {"pipeline", "baseline"}.issubset(variants):
        pipeline = {record["id"]: record for record in records if record["variant"] == "pipeline"}
        baseline = {record["id"]: record for record in records if record["variant"] == "baseline"}
        common = sorted(
            identifier
            for identifier in pipeline.keys() & baseline.keys()
            if pipeline[identifier]["status"] in SUCCESS_STATUSES and baseline[identifier]["status"] in SUCCESS_STATUSES
        )
        paired_pipeline = [pipeline[identifier] for identifier in common]
        paired_baseline = [baseline[identifier] for identifier in common]
        pipeline_scores = classification(paired_pipeline, labels)
        baseline_scores = classification(paired_baseline, labels)
        pipeline_indicators = indicator_metrics(paired_pipeline, entries)
        baseline_indicators = indicator_metrics(paired_baseline, entries)
        output["baselineComparison"] = {
            "pairedSuccessfulDocuments": len(common),
            "pipelineMinusBaseline": {
                "accuracy": _difference(pipeline_scores["accuracy"], baseline_scores["accuracy"]),
                "macroF1": _difference(pipeline_scores["macroF1"], baseline_scores["macroF1"]),
                "perCategory": {
                    label: {
                        key: _difference(
                            pipeline_scores["perCategory"][label][key], baseline_scores["perCategory"][label][key]
                        )
                        for key in ("precision", "recall", "f1")
                    }
                    for label in LABELS
                },
                "indicators": {
                    code: {
                        key: _difference(pipeline_indicators[code][key], baseline_indicators[code][key])
                        for key in ("precision", "recall")
                    }
                    for code in TAXONOMY
                },
            },
        }
    return output


# Mengembalikan delta hanya jika kedua metrik terdefinisi.
def _difference(left: float | None, right: float | None) -> float | None:
    return left - right if left is not None and right is not None else None


# Menjalankan CLI atau test sintetis; output yang sudah ada hanya diganti dengan --force.
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", nargs="?", type=Path, help="Direktori run yang berisi raw.jsonl dan run_config.json")
    parser.add_argument("--dataset-dir", type=Path, default=ROOT / "dataset")
    parser.add_argument("--force", action="store_true", help="Izinkan mengganti metrics.json dan confusion.csv")
    parser.add_argument("--test", action="store_true", help="Jalankan test sintetis tanpa memakai dataset hasil eval")
    args = parser.parse_args(argv)
    if args.test:
        import pytest

        return pytest.main(["-q", "-p", "no:cacheprovider", str(Path(__file__).with_name("test_metrics.py"))])
    if args.run_dir is None:
        parser.error("run_dir wajib diisi kecuali saat memakai --test.")
    try:
        run_dir = args.run_dir.resolve()
        manifest_path = args.dataset_dir.resolve() / "manifest.csv"
        for name in ("metrics.json", "confusion.csv"):
            if (run_dir / name).exists() and not args.force:
                raise ValueError(f"{name} sudah ada; gunakan --force setelah memastikan hasil lama boleh diganti.")
        entries = load_manifest(manifest_path)
        config, records = load_run(run_dir, entries, manifest_path)
        metrics = calculate_metrics(config, records, entries)
        payload = json.dumps(metrics, ensure_ascii=False, indent=2) + "\n"
        (run_dir / "metrics.json").write_text(payload, encoding="utf-8", newline="\n")
        write_confusion(run_dir / "confusion.csv", metrics["variants"])
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"[metrics] gagal: {error}", file=sys.stderr)
        return 1
    summary = {
        "split": config["split"],
        "records": len(records),
        "variants": sorted(metrics["variants"]),
        "output": str(run_dir),
    }
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
