# Owner: B (PIC 5) | Status: COMPLETE | Ref: PLAN T5-08; protocol §8.3
"""Pemulihan eksplisit run final; first-pass tetap utuh dan retry hanya menjadi bukti tambahan."""

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from time import sleep
from typing import Any

from _dataset import ROOT, Entry, sha256
from _eval_records import append_record, public_settings, write_json
from _eval_schema import EvaluationRecord
from _final_eval import load_frozen_entries, validate_final_run
from run_eval import evaluate_document, source_hashes, write_run_config

from app.analysis.provider import CompletionResult, LLMProvider, ProviderError, get_provider
from app.core.config import Settings


# Memuat JSON artefak lokal tanpa membaca environment file atau exception provider.
def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


# Memvalidasi record bersama sebelum menggabungkan bukti; duplikat first-pass selalu ditolak.
def read_records(path: Path) -> list[dict[str, Any]]:
    return [
        EvaluationRecord.model_validate_json(line).model_dump(mode="json", by_alias=True)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


# Membentuk indeks pasangan varian/dokumen tanpa menimpa observasi yang sudah dicoba.
def index_records(records: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    indexed = {(record["variant"], record["id"]): record for record in records}
    if len(indexed) != len(records):
        raise ValueError("Record first-pass duplikat.")
    return indexed


class DiagnosticProvider:
    """Merekam hanya status HTTP numerik bila tersedia; body/header/URL exception tidak disalin."""

    # Membungkus provider asli tanpa mengganti model, timeout, atau kebijakan runtime.
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider
        self.status_codes: list[int] = []

    # Menelusuri konteks error hanya untuk status numerik, lalu meneruskan error asli.
    def complete(self, messages: list[dict[str, str]]) -> CompletionResult:
        try:
            return self.provider.complete(messages)
        except ProviderError as error:
            cause: BaseException | None = error
            seen: set[int] = set()
            while cause is not None and id(cause) not in seen:
                seen.add(id(cause))
                status = getattr(cause, "status_code", None)
                if isinstance(status, int) and 100 <= status <= 599:
                    self.status_codes.append(status)
                cause = cause.__cause__ or cause.__context__
            raise


# Memastikan pemulihan masih memakai snapshot, parameter, referensi, dan fingerprint asli.
def check_profile(
    output: Path, directory: Path, snapshot: Path, reference: Path, settings: Settings
) -> tuple[dict[str, Any], list[Entry]]:
    original = read_json(output / "partial_run_config.json")
    checksums = read_json(output / "partial_checksums.json")
    if any(sha256((output / name).read_bytes()) != digest for name, digest in checksums["files"].items()):
        raise ValueError("Bukti parsial berubah.")
    entries, _ = load_frozen_entries(directory, snapshot)
    frozen_profile = validate_final_run(
        directory, entries, settings, ("pipeline", "baseline"), snapshot, reference, source_hashes()
    )
    if (
        original["sourceSha256"] != source_hashes()
        or original["settings"] != public_settings(settings)
        or original["manifestSha256"] != sha256((directory / "manifest.csv").read_bytes())
        or original["documents"] != [{"id": entry.id, "sha256": entry.sha256} for entry in entries]
        or original["freeze"] != frozen_profile
    ):
        raise ValueError("Profil/snapshot/kode berubah; pemulihan ditolak.")
    reservation = read_json(Path(original["reservation"]))
    if reservation["outputDirectory"] != str(output.resolve()):
        raise ValueError("Reservasi tidak cocok dengan direktori run.")
    return original, entries


# Menerbitkan first-pass lengkap; retry tidak pernah mengganti kegagalan atau latency awal.
def publish_primary(
    output: Path, original: dict[str, Any], entries: list[Entry], records: list[dict[str, Any]]
) -> None:
    indexed = index_records(records)
    expected = [(variant, entry.id) for entry in entries for variant in ("pipeline", "baseline")]
    if set(indexed) != set(expected):
        raise ValueError("Coverage first-pass belum lengkap atau mengandung dokumen asing.")
    captures = []
    for name in ("partial_model_outputs.jsonl", "completion_model_outputs.jsonl"):
        captures.extend(json.loads(line) for line in (output / name).read_text(encoding="utf-8").splitlines())
    if len(captures) != len(entries) or {item["id"] for item in captures} != {entry.id for entry in entries}:
        raise ValueError("Coverage output model first-pass tidak lengkap.")
    for name, items in (("raw.jsonl", [indexed[key] for key in expected]), ("model_outputs.jsonl", captures)):
        with (output / name).open("x", encoding="utf-8", newline="\n") as stream:
            for item in items:
                append_record(stream, item)
    config = dict(original)
    config.update(
        status="COMPLETE",
        finishedAt=datetime.now(UTC).isoformat(),
        stopReason=None,
        records=len(records),
        counts=dict(Counter(record["status"] for record in records)),
        lengthEvents=sum(attempt.get("lengthEvents", 0) for item in captures for attempt in item["attempts"]),
        completion={
            "decision": "User authorized missing documents and retries; original outcomes retained, 2026-11-26",
            "originalConfigSha256": sha256((output / "partial_run_config.json").read_bytes()),
            "originalStopReason": original["stopReason"],
            "originalStoppedAt": original["stoppedAt"],
            "primaryPolicy": "First observation per (variant,id); retries excluded from primary metrics",
            "helperSha256": sha256(Path(__file__).read_bytes()),
            "authorization": "completion_authorization.json",
        },
    )
    config.pop("stoppedAt", None)
    write_run_config(output, config)


# Memproses hanya pasangan yang belum dicoba, lalu mengulang kegagalan dalam berkas terpisah.
def complete_run(output: Path, directory: Path, snapshot: Path, reference: Path) -> int:
    original = read_json(output / "partial_run_config.json")
    settings = Settings(_env_file=None, llm_model=original["model"])
    original, entries = check_profile(output, directory, snapshot, reference, settings)
    if (output / "raw.jsonl").exists() or read_json(output / "run_config.json") != original:
        raise ValueError("Run sudah diterbitkan atau konfigurasi awal berubah.")
    provider = DiagnosticProvider(get_provider(settings))
    authorization = {
        "schemaVersion": 1,
        "createdAt": datetime.now(UTC).isoformat(),
        "decision": "Complete unattempted documents; retry failures until success; human review afterwards",
        "source": "Explicit user instruction in this session, 2026-11-26",
        "primaryPolicy": "Keep every original first-pass outcome; separate all retries",
        "settingsChanged": False,
        "helperSha256": sha256(Path(__file__).read_bytes()),
    }
    with (output / "completion_authorization.json").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(authorization, indent=2) + "\n")
    records = read_records(output / "partial_raw.jsonl") + read_records(output / "remaining_baseline.jsonl")
    indexed = index_records(records)
    with (
        (output / "completion_raw.jsonl").open("x", encoding="utf-8", newline="\n") as raw,
        (output / "completion_model_outputs.jsonl").open("x", encoding="utf-8", newline="\n") as models,
    ):
        for entry in entries:
            if ("baseline", entry.id) not in indexed:
                raise ValueError("Baseline belum lengkap; helper ini hanya memulihkan pipeline.")
            if ("pipeline", entry.id) in indexed:
                continue
            check_profile(output, directory, snapshot, reference, settings)
            record, capture = evaluate_document(entry, directory, settings, provider)
            append_record(raw, record)
            append_record(models, capture)
            records.append(record)
            print(json.dumps({"phase": "completion", "id": entry.id, "status": record["status"]}), flush=True)
            sleep(original["intervalSeconds"])
    check_profile(output, directory, snapshot, reference, settings)
    publish_primary(output, original, entries, records)
    indexed = index_records(records)
    retry_count = 0
    with (
        (output / "retry_raw.jsonl").open("x", encoding="utf-8", newline="\n") as raw,
        (output / "retry_model_outputs.jsonl").open("x", encoding="utf-8", newline="\n") as models,
        (output / "retry_attempts.jsonl").open("x", encoding="utf-8", newline="\n") as attempts,
    ):
        for entry in entries:
            record = indexed[("pipeline", entry.id)]
            document_attempt = 1
            while record["status"] != "OK":
                check_profile(output, directory, snapshot, reference, settings)
                provider.status_codes.clear()
                record, capture = evaluate_document(entry, directory, settings, provider)
                document_attempt += 1
                retry_count += 1
                append_record(raw, record)
                append_record(models, capture)
                append_record(
                    attempts,
                    {
                        "id": entry.id,
                        "documentAttempt": document_attempt,
                        "finishedAt": datetime.now(UTC).isoformat(),
                        "status": record["status"],
                        "error": record["error"],
                        "httpStatusCodes": provider.status_codes,
                    },
                )
                print(
                    json.dumps(
                        {
                            "phase": "retry",
                            "id": entry.id,
                            "attempt": document_attempt,
                            "status": record["status"],
                            "httpStatusCodes": provider.status_codes,
                        }
                    ),
                    flush=True,
                )
                if record["status"] != "OK":
                    code = record["error"]["code"]
                    if code in {"AI_QUOTA_EXCEEDED", "AI_PROVIDER_UNCONFIGURED"} or any(
                        status in {400, 401, 403, 404, 422} for status in provider.status_codes
                    ):
                        print(json.dumps({"blocked": code, "reason": "quota or permanent provider error"}), flush=True)
                        return 1
                    sleep(min(300, max(30, 30 * (document_attempt - 1))))
    check_profile(output, directory, snapshot, reference, settings)
    write_json(
        output / "completion_summary.json",
        {
            "schemaVersion": 1,
            "finishedAt": datetime.now(UTC).isoformat(),
            "primaryRecords": len(records),
            "primaryCounts": dict(Counter(record["status"] for record in records)),
            "supplementalRetries": retry_count,
            "pipelineDocumentsWithSuccessfulResponse": len(entries),
            "primaryFailuresRetained": [record["id"] for record in records if record["status"] != "OK"],
            "humanReview": "PENDING; no human review claimed by the runner",
            "snapshotSha256": original["freeze"]["snapshotSha256"],
        },
    )
    return 0


# CLI sengaja meminta persetujuan pemulihan eksplisit; tidak menjadi retry otomatis pada runner biasa.
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--reference-run", type=Path, required=True)
    parser.add_argument("--approved-recovery", action="store_true", required=True)
    args = parser.parse_args()
    return complete_run(args.output.resolve(), ROOT / "dataset", args.freeze, args.reference_run)


if __name__ == "__main__":
    raise SystemExit(main())
