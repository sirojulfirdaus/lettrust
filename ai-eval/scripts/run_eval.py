# Owner: B (PIC 5) | Status: COMPLETE | Ref: PLAN T5-07/T5-08; PRD §10.4.3; SA §7.9
"""Runner dev/final pipeline dan baseline; test memerlukan freeze, profil dev, dan reservasi satu run."""

import argparse
import json
import logging
import math
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter, sleep
from typing import Any
from uuid import uuid4

from _dataset import ROOT, Entry, pdf_path, sha256
from _eval_records import append_record, load_dev_entries, parse_manifest_metadata, public_settings, write_json
from _eval_schema import EvaluationError, EvaluationRecord, ExtractionMetadata
from _final_eval import load_frozen_entries, reserve_final_run, validate_final_run
from baseline import BASELINE_VERSION, analyze_text
from freeze_testset import verify_freeze
from pydantic import ValidationError

from app.analysis.prompt import build_messages
from app.analysis.provider import CompletionResult, LLMProvider, OpenAICompatibleProvider, ProviderError, get_provider
from app.analysis.service import analyze_document
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.extraction.service import extract_document

STOP_CODES = {"AI_QUOTA_EXCEEDED", "AI_PROVIDER_UNCONFIGURED", "AI_PROVIDER_ERROR", "AI_TIMEOUT"}


class LengthEvents(logging.Handler):
    """Menghitung event finish_reason=length tanpa membaca atau merekam isi log provider."""

    # Menyiapkan penghitung per panggilan provider.
    def __init__(self) -> None:
        super().__init__()
        self.count = 0

    # Mengambil hanya nama event aman yang memang dipancarkan adapter runtime.
    def emit(self, record: logging.LogRecord) -> None:
        if getattr(record, "event", None) == "ai.output_truncated":
            self.count += 1


class RecordingProvider:
    """Mendelegasikan panggilan asli sambil menyimpan output sintetis tiap attempt untuk artefak evaluasi."""

    # Provider diinjeksikan oleh test saja; CLI selalu memakai get_provider runtime tanpa fallback.
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider
        self.attempts: list[dict[str, Any]] = []

    # Retry output tidak valid tetap dilakukan analyze_document; quota/timeout tidak diulang di sini.
    def complete(self, messages: list[dict[str, str]]) -> CompletionResult:
        events = LengthEvents()
        logger = logging.getLogger("app.analysis.provider")
        logger.addHandler(events)
        started = perf_counter()
        attempt = {"attempt": len(self.attempts) + 1, "content": None, "error": None}
        try:
            completion = self.provider.complete(messages)
            attempt.update(content=completion.content, latencyMs=completion.latency_ms)
            return completion
        except ProviderError as error:
            attempt.update(error=error.code.value, latencyMs=max(0, round((perf_counter() - started) * 1000)))
            raise
        finally:
            logger.removeHandler(events)
            attempt["lengthEvents"] = events.count
            self.attempts.append(attempt)


# Mengukur satu dokumen tanpa memasukkan label referensi/notes ke prompt dan tanpa menulis teks ekstraksi ke log.
def evaluate_document(
    entry: Entry, directory: Path, settings: Settings, provider: LLMProvider | None, variant: str = "pipeline"
) -> tuple[dict[str, Any], dict[str, Any]]:
    if variant not in {"pipeline", "baseline"}:
        raise ValueError("Varian evaluasi tidak valid.")
    started = perf_counter()
    result = None
    metadata = None
    error = None
    captured = RecordingProvider(provider) if provider is not None and variant == "pipeline" else None
    stage = "INPUT"
    try:
        content = pdf_path(directory, entry).read_bytes()
        if sha256(content) != entry.sha256:
            error = EvaluationError(stage=stage, code="CHECKSUM_MISMATCH")
        else:
            stage = "EXTRACTION"
            extraction = extract_document(content, settings)
            metadata = ExtractionMetadata.from_response(extraction)
            if extraction.status.value == "NO_CONTENT":
                error = EvaluationError(
                    stage=stage, code="EXTRACTION_NO_CONTENT", reason_detail=extraction.reason_detail
                )
            else:
                stage = "ANALYSIS"
                if variant == "baseline":
                    result = analyze_text(extraction.text)
                else:
                    if captured is None:
                        raise ValueError("Varian pipeline memerlukan provider eksplisit.")
                    result = analyze_document(extraction.text, settings, extraction.method.value, provider=captured)
    except AppError as failure:
        error = EvaluationError(stage=stage, code=failure.code.value)
    except OSError:
        error = EvaluationError(stage=stage, code="DOCUMENT_READ_ERROR" if stage == "INPUT" else "EXTRACTION_FAILED")
    except RuntimeError:
        if stage != "EXTRACTION":
            raise
        error = EvaluationError(stage=stage, code="EXTRACTION_FAILED")
    except ValueError:
        if stage != "EXTRACTION" and not (stage == "ANALYSIS" and variant == "baseline"):
            raise
        error = EvaluationError(stage=stage, code="EXTRACTION_FAILED" if stage == "EXTRACTION" else "ANALYSIS_INVALID")
    record = EvaluationRecord(
        id=entry.id,
        variant=variant,
        status="OK" if result is not None else "UNAVAILABLE",
        result=result,
        extraction=metadata,
        error=error,
        latency_ms=max(0, round((perf_counter() - started) * 1000)),
    )
    return record.model_dump(mode="json", by_alias=True), {
        "schemaVersion": 1,
        "id": entry.id,
        "variant": variant,
        "attempts": captured.attempts if captured else [],
    }


# Mencatat fingerprint kode yang menentukan prompt, output, dan ekstraksi; tidak membuka file environment.
def source_hashes() -> dict[str, str]:
    sources = {
        "runner": Path(__file__),
        "records": Path(__file__).with_name("_eval_records.py"),
        "provider": Path(OpenAICompatibleProvider.complete.__code__.co_filename),
        "prompt": Path(build_messages.__code__.co_filename),
        "analysis": Path(analyze_document.__code__.co_filename),
        "extraction": Path(extract_document.__code__.co_filename),
        "baseline": Path(analyze_text.__code__.co_filename),
        "schema": Path(__file__).with_name("_eval_schema.py"),
        "finalGate": Path(__file__).with_name("_final_eval.py"),
        "freeze": Path(__file__).with_name("freeze_testset.py"),
        "metrics": Path(__file__).with_name("metrics.py"),
        **{
            name: Path(OpenAICompatibleProvider.complete.__code__.co_filename).with_name(f"{name}.py")
            for name in ("scoring", "taxonomy", "validator", "compose")
        },
    }
    return {name: sha256(path.read_bytes()) for name, path in sources.items()}


# Memperbarui konfigurasi atomik; pembaca tidak pernah menerima JSON yang setengah tertulis.
def write_run_config(output: Path, config: dict[str, Any]) -> None:
    temporary = output / "tmp" / "run_config.json"
    write_json(temporary, config)
    temporary.replace(output / "run_config.json")


# Baseline hanya merekam parameter ekstraksi; konfigurasi LLM tidak dibaca atau disiratkan sebagai model baseline.
def public_run_settings(settings: Settings, variants: tuple[str, ...]) -> dict[str, Any]:
    if "pipeline" in variants:
        return public_settings(settings)
    return {
        "aiMaxPages": settings.ai_max_pages,
        "aiMaxChars": settings.ai_max_chars,
        "ocrMinCharsPerPage": settings.ocr_min_chars_per_page,
        "ocrDpi": settings.ocr_dpi,
        "ocrPageTimeoutSeconds": settings.ocr_page_timeout_seconds,
    }


# Menerbitkan raw hanya setelah seluruh dokumen dicoba; run terputus tetap RUNNING dengan bukti parsial di tmp.
def execute_run(
    directory: Path,
    output: Path,
    entries: list[Entry],
    settings: Settings,
    interval_seconds: float = 0,
    provider: LLMProvider | None = None,
    *,
    variants: tuple[str, ...] = ("pipeline",),
    split: str = "dev",
    freeze: Path | None = None,
    reference_run: Path | None = None,
) -> dict[str, Any]:
    if split not in {"dev", "test"} or not entries or any(entry.split != split for entry in entries):
        raise ValueError("Runner hanya menerima dokumen dev/test sesuai split yang dipilih.")
    if split == "test" and (freeze is None or reference_run is None):
        raise ValueError("Run test memerlukan snapshot freeze dan referensi dev.")
    if not math.isfinite(interval_seconds) or not 0 <= interval_seconds <= 60:
        raise ValueError("Interval harus berada pada rentang 0 sampai 60 detik.")
    if not variants or len(set(variants)) != len(variants) or set(variants) - {"pipeline", "baseline"}:
        raise ValueError("Varian harus pipeline/baseline tanpa duplikat.")
    if "pipeline" in variants and settings.llm_provider != "openai_compatible":
        raise ValueError("Evaluasi nyata tidak boleh memakai provider mock.")
    if provider is not None and settings.app_env != "test":
        raise ValueError("Injeksi provider hanya diizinkan untuk unit test.")
    if output.resolve().is_relative_to(directory.resolve()):
        raise ValueError("Output evaluasi harus berada di luar dataset.")
    manifest_content = (directory / "manifest.csv").read_bytes()
    metadata = {entry.id: entry for entry in parse_manifest_metadata(manifest_content) if entry.split == split}
    if len({entry.id for entry in entries}) != len(entries) or any(
        metadata.get(entry.id) != entry for entry in entries
    ):
        raise ValueError(f"Dokumen run tidak cocok dengan metadata {split}.")
    hashes = source_hashes()
    final_metadata = (
        validate_final_run(directory, entries, settings, variants, freeze, reference_run, hashes)
        if split == "test"
        else None
    )
    config: dict[str, Any] = {
        "schemaVersion": 1,
        "status": "RUNNING",
        "variants": list(variants),
        "split": split,
        "purpose": "final-evaluation" if split == "test" else "provisional-model-selection",
        "datasetStatus": "frozen" if split == "test" else "not-frozen",
        "startedAt": datetime.now(UTC).isoformat(),
        "finishedAt": None,
        "settings": public_run_settings(settings, variants),
        "model": settings.llm_model if "pipeline" in variants else "rule-based-baseline",
        "promptVersion": settings.prompt_version if "pipeline" in variants else BASELINE_VERSION,
        "baselineVersion": BASELINE_VERSION if "baseline" in variants else None,
        "languages": sorted({entry.lang for entry in entries}),
        "formats": sorted({entry.format for entry in entries}),
        "manifestSha256": sha256(manifest_content),
        "documents": [{"id": entry.id, "sha256": entry.sha256} for entry in entries],
        "sourceSha256": hashes,
        "intervalSeconds": interval_seconds,
        "latencyDefinition": "extraction+analysis+runtime-output-retry; excludes inter-document delay",
        "plannedRecords": len(entries) * len(variants),
        "records": 0,
        "counts": {},
    }
    if final_metadata is not None:
        config["freeze"] = final_metadata
        if output.exists():
            raise FileExistsError("Direktori run sudah ada.")
        reservation = reserve_final_run(directory, output, final_metadata, config["manifestSha256"])
        config["reservation"] = str(reservation)
    output.mkdir(parents=True, exist_ok=False)
    temporary = output / "tmp"
    temporary.mkdir()
    write_run_config(output, config)
    counts: Counter[str] = Counter()
    length_events = 0
    stop_reason = None
    try:
        selected_provider = (
            (provider if provider is not None else get_provider(settings)) if "pipeline" in variants else None
        )
        with (
            (temporary / "raw.jsonl").open("x", encoding="utf-8", newline="\n") as raw,
            (temporary / "model_outputs.jsonl").open("x", encoding="utf-8", newline="\n") as model_outputs,
        ):
            for index, entry in enumerate(entries):
                if index and interval_seconds and "pipeline" in variants:
                    sleep(interval_seconds)
                for variant in variants:
                    record, captured = evaluate_document(entry, directory, settings, selected_provider, variant)
                    validated = EvaluationRecord.model_validate(record)
                    raw.write(validated.model_dump_json(by_alias=True) + "\n")
                    raw.flush()
                    if variant == "pipeline":
                        append_record(model_outputs, captured)
                    counts[record["status"]] += 1
                    length_events += sum(attempt["lengthEvents"] for attempt in captured["attempts"])
                    print(
                        json.dumps(
                            {
                                "processed": sum(counts.values()),
                                "total": config["plannedRecords"],
                                "variant": variant,
                                "status": record["status"],
                            }
                        ),
                        flush=True,
                    )
                    code = record["error"]["code"] if record["error"] else None
                    if code in STOP_CODES:
                        stop_reason = code
                        break
                if stop_reason:
                    break
        if sha256((directory / "manifest.csv").read_bytes()) != config["manifestSha256"]:
            stop_reason = "MANIFEST_CHANGED"
            raise ValueError("Manifest berubah selama evaluasi.")
        if final_metadata is not None:
            if source_hashes() != hashes:
                stop_reason = "CODE_CHANGED"
                raise ValueError("Kode evaluasi berubah selama run final.")
            try:
                verified = verify_freeze(directory, freeze)
                if verified["snapshotSha256"] != final_metadata["snapshotSha256"]:
                    raise ValueError("Snapshot berubah selama evaluasi.")
            except (OSError, ValueError, TypeError, KeyError):
                stop_reason = "FREEZE_CHANGED"
                raise ValueError("Snapshot atau test set berubah selama evaluasi.") from None
        if not stop_reason:
            (temporary / "model_outputs.jsonl").replace(output / "model_outputs.jsonl")
            (temporary / "raw.jsonl").replace(output / "raw.jsonl")
            config.update(status="COMPLETE", finishedAt=datetime.now(UTC).isoformat())
    finally:
        config.update(
            records=sum(counts.values()),
            counts=dict(counts),
            stopReason=stop_reason or ("INTERRUPTED" if config["status"] != "COMPLETE" else None),
            lengthEvents=length_events,
        )
        if config["status"] != "COMPLETE":
            config["stoppedAt"] = datetime.now(UTC).isoformat()
            if split == "test":
                for name in ("raw.jsonl", "model_outputs.jsonl"):
                    source = temporary / name
                    if source.exists():
                        with (output / f"partial_{name}").open("xb") as stream:
                            stream.write(source.read_bytes())
        write_run_config(output, config)
    return config


# Memvalidasi override eksperimen hanya dalam proses runner; konfigurasi layanan dan file bersama tidak ditulis.
def experiment_settings(args: argparse.Namespace) -> Settings:
    settings = get_settings()
    fields = {
        "llm_model": args.model,
        "llm_max_output_tokens": args.max_output_tokens,
        "llm_reasoning_effort": args.reasoning_effort,
        "ocr_dpi": args.ocr_dpi,
        "ocr_min_chars_per_page": args.ocr_min_chars,
        "evidence_fuzzy_threshold": args.fuzzy_threshold,
    }
    overrides = {key: value for key, value in fields.items() if value is not None}
    settings = Settings.model_validate(settings.model_dump() | overrides)
    if not 0 <= settings.evidence_fuzzy_threshold <= 100:
        raise ValueError("Ambang fuzzy harus berada pada rentang 0 sampai 100.")
    return settings


# CLI test menolak subset atau gate yang hilang sebelum membaca PDF dan memanggil provider.
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=["dev", "test"], default="dev")
    parser.add_argument("--freeze", type=Path)
    parser.add_argument("--reference-run", type=Path)
    parser.add_argument("--dataset-dir", type=Path, default=ROOT / "dataset")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--model")
    parser.add_argument("--variants", nargs="+", choices=["pipeline", "baseline"])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--interval-seconds", type=float, default=10)
    parser.add_argument("--max-output-tokens", type=int)
    parser.add_argument("--reasoning-effort", choices=["", "low", "medium", "high"])
    parser.add_argument("--ocr-dpi", type=int)
    parser.add_argument("--ocr-min-chars", type=int)
    parser.add_argument("--fuzzy-threshold", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args(argv)
    args.variants = args.variants or (["pipeline", "baseline"] if args.split == "test" else ["pipeline"])
    if args.split == "test" and (not args.freeze or not args.reference_run or args.limit is not None):
        parser.error("Test memerlukan --freeze dan --reference-run serta tidak menerima --limit.")
    if len(set(args.variants)) != len(args.variants):
        parser.error("Varian tidak boleh duplikat.")
    if args.test:
        import pytest

        return pytest.main(
            [
                "-q",
                "-p",
                "no:cacheprovider",
                str(Path(__file__).with_name("test_run_eval.py")),
                str(Path(__file__).with_name("test_final_eval.py")),
            ]
        )
    try:
        entries = (
            load_dev_entries(args.dataset_dir, args.limit)
            if args.split == "dev"
            else load_frozen_entries(args.dataset_dir, args.freeze)[0]
        )
        settings = experiment_settings(args)
        if "pipeline" in args.variants and settings.llm_provider != "openai_compatible":
            raise ValueError("Runner nyata tidak menerima provider mock.")
        public_run_settings(settings, tuple(args.variants))
        if args.split == "test":
            validate_final_run(
                args.dataset_dir,
                entries,
                settings,
                tuple(args.variants),
                args.freeze,
                args.reference_run,
                source_hashes(),
            )
        if args.dry_run:
            print(
                json.dumps(
                    {
                        "split": args.split,
                        "documents": len(entries),
                        "variants": args.variants,
                        "model": settings.llm_model if "pipeline" in args.variants else "rule-based-baseline",
                        "calls": 0,
                    }
                )
            )
            return 0
        if "pipeline" in args.variants and not settings.llm_configured:
            print(
                "Evaluasi tidak dijalankan: LLM_API_KEY belum dikonfigurasi pada environment container.",
                file=sys.stderr,
            )
            return 1
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        output = args.output_dir or ROOT / "results" / f"{stamp}-{uuid4().hex[:8]}"
        config = execute_run(
            args.dataset_dir,
            output,
            entries,
            settings,
            args.interval_seconds,
            variants=tuple(args.variants),
            split=args.split,
            freeze=args.freeze,
            reference_run=args.reference_run,
        )
    except (OSError, ValueError, ValidationError) as error:
        # Pesan validasi Settings/SDK dapat memuat input sensitif; jangan mencetak exception aslinya.
        print(
            f"Evaluasi gagal pada validasi atau penyimpanan ({type(error).__name__}); periksa argumen/dataset.",
            file=sys.stderr,
        )
        return 1
    print(
        json.dumps(
            {
                "outputDir": str(output),
                "status": config["status"],
                "counts": config["counts"],
                "records": config["records"],
                "stopReason": config["stopReason"],
                "lengthEvents": config["lengthEvents"],
            }
        )
    )
    return 0 if config["status"] == "COMPLETE" and config["counts"] == {"OK": config["plannedRecords"]} else 1


if __name__ == "__main__":
    raise SystemExit(main())
