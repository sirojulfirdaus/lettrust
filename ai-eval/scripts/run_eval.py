# Owner: B (PIC 5) | Status: COMPLETE | Ref: PLAN T5-07; PRD §10.4.3; SA §7.9
"""Runner pemilihan model di dev: pipeline runtime, output mentah, dan konfigurasi tanpa secret.

Test split dan integrasi baseline bukan bagian runner dev T5-07; keduanya menunggu T5-08/T6-05.
"""

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
from _eval_records import append_record, load_dev_entries, public_settings, write_json
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
    entry: Entry, directory: Path, settings: Settings, provider: LLMProvider
) -> tuple[dict[str, Any], dict[str, Any]]:
    started = perf_counter()
    record: dict[str, Any] = {
        "id": entry.id,
        "status": "UNAVAILABLE",
        "result": None,
        "extraction": None,
        "error": None,
        "latencyMs": None,
    }
    captured = RecordingProvider(provider)
    stage = "input"
    try:
        content = pdf_path(directory, entry).read_bytes()
        if sha256(content) != entry.sha256:
            record["error"] = {"stage": stage, "code": "DATASET_CHECKSUM_CHANGED"}
        else:
            stage = "extraction"
            extraction = extract_document(content, settings)
            record["extraction"] = extraction.model_dump(mode="json", by_alias=True, exclude={"text"})
            if extraction.status.value == "NO_CONTENT":
                record["status"] = "NOT_PERFORMED"
                record["error"] = {"stage": stage, "code": extraction.reason_detail.value}
            else:
                stage = "analysis"
                result = analyze_document(extraction.text, settings, extraction.method.value, provider=captured)
                record.update(status="COMPLETED", result=result.model_dump(mode="json", by_alias=True))
    except AppError as error:
        record["error"] = {"stage": stage, "code": error.code.value}
    except OSError:
        record["error"] = {"stage": stage, "code": "FILE_IO_ERROR"}
    except RuntimeError:
        if stage != "extraction":
            raise
        record["error"] = {"stage": stage, "code": "EXTRACTION_FAILED"}
    record["latencyMs"] = max(0, round((perf_counter() - started) * 1000))
    return record, {"id": entry.id, "attempts": captured.attempts}


# Mencatat fingerprint kode yang menentukan prompt, output, dan ekstraksi; tidak membuka file environment.
def source_hashes() -> dict[str, str]:
    sources = {
        "runner": Path(__file__),
        "records": Path(__file__).with_name("_eval_records.py"),
        "provider": Path(OpenAICompatibleProvider.complete.__code__.co_filename),
        "prompt": Path(build_messages.__code__.co_filename),
        "analysis": Path(analyze_document.__code__.co_filename),
        "extraction": Path(extract_document.__code__.co_filename),
    }
    return {name: sha256(path.read_bytes()) for name, path in sources.items()}


# Menulis satu run terpisah per model; status gagal dan dokumen yang dibatalkan tetap tercatat.
def execute_run(
    directory: Path,
    output: Path,
    entries: list[Entry],
    settings: Settings,
    interval_seconds: float = 0,
    provider: LLMProvider | None = None,
) -> dict[str, Any]:
    if not entries or any(entry.split != "dev" for entry in entries):
        raise ValueError("Runner T5-07 hanya menerima dokumen dev.")
    if not math.isfinite(interval_seconds) or not 0 <= interval_seconds <= 60:
        raise ValueError("Interval harus berada pada rentang 0 sampai 60 detik.")
    if settings.llm_provider != "openai_compatible":
        raise ValueError("Evaluasi nyata tidak boleh memakai provider mock.")
    if provider is not None and settings.app_env != "test":
        raise ValueError("Injeksi provider hanya diizinkan untuk unit test.")
    config: dict[str, Any] = {
        "schemaVersion": 1,
        "method": "llm",
        "split": "dev",
        "purpose": "provisional-model-selection",
        "datasetStatus": "draft-not-frozen",
        "startedAt": datetime.now(UTC).isoformat(),
        "state": "running",
        "settings": public_settings(settings),
        "manifestSha256": sha256((directory / "manifest.csv").read_bytes()),
        "documents": [{"id": entry.id, "sha256": entry.sha256} for entry in entries],
        "sourceSha256": source_hashes(),
        "intervalSeconds": interval_seconds,
        "latencyDefinition": "extraction+analysis+runtime-output-retry; excludes inter-document delay",
    }
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "run_config.json", config)
    selected_provider = provider if provider is not None else get_provider(settings)
    counts: Counter[str] = Counter()
    length_events = 0
    stop_reason = None
    try:
        with (
            (output / "raw.jsonl").open("x", encoding="utf-8", newline="\n") as raw,
            (output / "model_outputs.jsonl").open("x", encoding="utf-8", newline="\n") as model_outputs,
        ):
            for index, entry in enumerate(entries):
                if stop_reason:
                    record = {
                        "id": entry.id,
                        "status": "NOT_PERFORMED",
                        "result": None,
                        "extraction": None,
                        "error": {"stage": "run", "code": "RUN_ABORTED"},
                        "latencyMs": None,
                    }
                    captured = {"id": entry.id, "attempts": []}
                else:
                    if index and interval_seconds:
                        sleep(interval_seconds)
                    record, captured = evaluate_document(entry, directory, settings, selected_provider)
                    code = record["error"]["code"] if record["error"] else None
                    if code in STOP_CODES:
                        stop_reason = code
                append_record(raw, record)
                append_record(model_outputs, captured)
                counts[record["status"]] += 1
                length_events += sum(attempt["lengthEvents"] for attempt in captured["attempts"])
                print(
                    json.dumps({"processed": index + 1, "total": len(entries), "status": record["status"]}), flush=True
                )
        config["state"] = "stopped" if stop_reason else "finished"
    finally:
        if config["state"] == "running":
            config["state"] = "interrupted"
        config.update(
            finishedAt=datetime.now(UTC).isoformat(),
            statusCounts=dict(counts),
            stopReason=stop_reason,
            lengthEvents=length_events,
        )
        write_json(output / "run_config.json", config)
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


# CLI ini menolak test split sebelum membaca dataset, membangun Settings, atau memanggil provider.
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=["dev"], default="dev")
    parser.add_argument("--dataset-dir", type=Path, default=ROOT / "dataset")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--model")
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
    if args.test:
        import pytest

        return pytest.main(["-q", "-p", "no:cacheprovider", str(Path(__file__).with_name("test_run_eval.py"))])
    try:
        entries = load_dev_entries(args.dataset_dir, args.limit)
        settings = experiment_settings(args)
        if settings.llm_provider != "openai_compatible":
            raise ValueError("Runner nyata tidak menerima provider mock.")
        public_settings(settings)
        if args.dry_run:
            print(json.dumps({"split": "dev", "documents": len(entries), "model": settings.llm_model, "calls": 0}))
            return 0
        if not settings.llm_configured:
            print(
                "Evaluasi tidak dijalankan: LLM_API_KEY belum dikonfigurasi pada environment container.",
                file=sys.stderr,
            )
            return 1
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        output = args.output_dir or ROOT / "results" / f"{stamp}-{uuid4().hex[:8]}"
        config = execute_run(args.dataset_dir, output, entries, settings, args.interval_seconds)
    except (OSError, ValueError, ValidationError) as error:
        # Pesan validasi Settings/SDK dapat memuat input sensitif; jangan mencetak exception aslinya.
        print(
            f"Evaluasi gagal pada validasi atau penyimpanan ({type(error).__name__}); periksa argumen/dataset.",
            file=sys.stderr,
        )
        return 1
    print(
        json.dumps(
            {"outputDir": str(output), "statusCounts": config["statusCounts"], "lengthEvents": config["lengthEvents"]}
        )
    )
    return 0 if config["statusCounts"] == {"COMPLETED": len(entries)} else 1


if __name__ == "__main__":
    raise SystemExit(main())
