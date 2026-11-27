# Owner: B (PIC 5) | Status: COMPLETE | Ref: PLAN T5-07; SA §7.9, §18.2
"""Uji runner dengan PDF sintetis sementara dan MockLLMProvider bersama; tidak membuat bukti evaluasi nyata."""

import csv
import json
import logging
from collections.abc import Iterator
from dataclasses import asdict, replace
from pathlib import Path

import _eval_records
import pytest
import run_eval
from _dataset import FIELDS, Entry, sha256
from _eval_records import load_dev_entries, public_settings
from _eval_schema import EvaluationRecord
from generate_pdfs import render_text_pdf
from pydantic import SecretStr

from app.analysis.mock_provider import MockLLMProvider, model_output
from app.analysis.provider import ProviderQuotaExceeded, ProviderTimeout
from app.core.config import Settings, get_settings
from app.schemas import ExtractionResponse

HIGH_TEXT = "Pelamar wajib membayar biaya administrasi sebesar Rp1.500.000 sebelum bekerja."
LOW_TEXT = "PT Contoh Unit menawarkan pekerjaan mencatat stok di Bandung; biaya seragam ditanggung perusahaan."
HIGH_OUTPUT = model_output([("PAYMENT_REQUEST", [HIGH_TEXT])], "Surat meminta pembayaran sebelum bekerja.")
LOW_OUTPUT = model_output([], "Tidak ditemukan pola dari daftar indikator.")


@pytest.fixture(autouse=True)
def settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[Settings]:
    """Mengaktifkan mock hanya pada APP_ENV=test dan mengosongkan API key agar tidak ada akses LLM nyata."""
    for name, value in {
        "APP_ENV": "test",
        "INTERNAL_API_TOKEN": "eval-unit-test-token",
        "LLM_API_KEY": "",
        "LLM_PROVIDER": "openai_compatible",
        "LLM_MODEL": "eval-unit-model",
        "PROMPT_VERSION": "unit-test",
    }.items():
        monkeypatch.setenv(name, value)
    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()


@pytest.fixture
def dataset(tmp_path: Path) -> Path:
    """Menyediakan dua PDF dev dan satu baris test tanpa berkas untuk membuktikan tidak ada akses PDF test."""
    directory = tmp_path / "dataset"
    (directory / "pdf").mkdir(parents=True)
    entries = []
    for identifier, label, codes, text in (
        ("id-high-01-text", "HIGH", ["PAYMENT_REQUEST"], HIGH_TEXT),
        ("id-low-01-text", "LOW", [], LOW_TEXT),
    ):
        content = render_text_pdf(text)
        file = f"pdf/{identifier}.pdf"
        (directory / file).write_bytes(content)
        entries.append(Entry(identifier, "dev", "id", "text", label, json.dumps(codes), file, sha256(content)))
    entries.append(Entry("id-low-02-text", "test", "id", "text", "LOW", "[]", "pdf/id-low-02-text.pdf", "0" * 64))
    with (directory / "manifest.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(asdict(entry) for entry in entries)
    return directory


# Pemilihan dev tidak mensyaratkan keberadaan PDF test dan tidak mengubah manifest ataupun berkas sumber.
def test_only_dev_files_are_read(dataset: Path) -> None:
    before = (dataset / "manifest.csv").read_bytes()
    entries = load_dev_entries(dataset)
    assert len(entries) == 2
    assert all(entry.split == "dev" for entry in entries)
    assert not (dataset / "pdf/id-low-02-text.pdf").exists()
    assert before == (dataset / "manifest.csv").read_bytes()


# Seluruh split pasangan diperiksa sebelum akses PDF, termasuk saat smoke test memakai limit.
@pytest.mark.parametrize("dev_format", ["text", "scan"])
@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("limit", [None, 1])
def test_cross_split_pair_is_rejected_before_pdf_access(
    dataset: Path, monkeypatch: pytest.MonkeyPatch, dev_format: str, reverse: bool, limit: int | None
) -> None:
    with (dataset / "manifest.csv").open(encoding="utf-8", newline="") as stream:
        original = Entry(**next(csv.DictReader(stream)))
    entries = [
        replace(
            original,
            id=f"id-high-01-{file_format}",
            format=file_format,
            file=f"pdf/id-high-01-{file_format}.pdf",
            split="dev" if file_format == dev_format else "test",
        )
        for file_format in ("text", "scan")
    ]
    if reverse:
        entries.reverse()
    with (dataset / "manifest.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(asdict(entry) for entry in entries)

    def forbidden_pdf_path(*args: object) -> Path:
        """Menggagalkan test bila runner mencoba mengakses PDF sebelum split seluruh manifest sah."""
        raise AssertionError("PDF tidak boleh diakses sebelum validasi split selesai")

    monkeypatch.setattr(_eval_records, "pdf_path", forbidden_pdf_path)
    with pytest.raises(ValueError, match="split"):
        load_dev_entries(dataset, limit)


# Checksum dev harus lolos sebelum satu pun provider dibuat atau dipanggil.
def test_changed_dev_pdf_is_rejected(dataset: Path) -> None:
    (dataset / "pdf/id-high-01-text.pdf").write_bytes(b"changed")
    with pytest.raises(ValueError, match="checksum berubah"):
        load_dev_entries(dataset)


# Subset smoke test ditetapkan deterministik dan batas nol/negatif ditolak.
def test_limit_is_deterministic(dataset: Path) -> None:
    assert load_dev_entries(dataset, 1) == load_dev_entries(dataset)[:1]
    with pytest.raises(ValueError):
        load_dev_entries(dataset, 0)


# Format manifest rusak harus ditolak secara eksplisit.
def test_invalid_manifest_header(dataset: Path) -> None:
    (dataset / "manifest.csv").write_text("id,split\nwrong,dev\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Header"):
        load_dev_entries(dataset)


# Pipeline runtime menghitung kategori dari bukti, sedangkan raw output menyimpan konten model sebelum validasi.
def test_runtime_response_and_original_model_output(dataset: Path, settings: Settings) -> None:
    entry = load_dev_entries(dataset)[0]
    provider = MockLLMProvider(HIGH_OUTPUT, latency_ms=7)
    record, captured = run_eval.evaluate_document(entry, dataset, settings, provider)
    assert set(record) == {"schemaVersion", "id", "variant", "status", "result", "extraction", "error", "latencyMs"}
    assert record["status"] == "OK" and record["variant"] == "pipeline"
    EvaluationRecord.model_validate(record)
    assert record["result"]["category"] == "HIGH"
    assert record["result"]["indicatorDetails"][0]["code"] == "PAYMENT_REQUEST"
    assert record["result"]["meta"]["latencyMs"] == 7
    assert record["extraction"]["method"] == "TEXT_LAYER"
    assert "text" not in record["extraction"]
    assert captured["attempts"][0]["content"] == HIGH_OUTPUT
    assert record["error"] is None
    assert entry.id not in provider.received[0][-1]["content"]


# Retry JSON tidak valid dilakukan runtime satu kali; kedua attempt tetap tersedia bagi analisis kegagalan.
def test_invalid_output_retry_is_preserved(dataset: Path, settings: Settings) -> None:
    provider = MockLLMProvider("not-json", HIGH_OUTPUT, latency_ms=4)
    record, captured = run_eval.evaluate_document(load_dev_entries(dataset)[0], dataset, settings, provider)
    assert record["status"] == "OK"
    assert record["result"]["meta"]["latencyMs"] == 8
    assert [attempt["content"] for attempt in captured["attempts"]] == ["not-json", HIGH_OUTPUT]
    assert len(provider.received) == 2


# Dua output tidak valid menjadi kegagalan, bukan kategori LOW atau baseline fallback.
def test_invalid_output_never_becomes_low(dataset: Path, settings: Settings) -> None:
    record, captured = run_eval.evaluate_document(
        load_dev_entries(dataset)[0], dataset, settings, MockLLMProvider("invalid", "invalid")
    )
    assert record["status"] == "UNAVAILABLE"
    assert record["result"] is None
    assert record["error"] == {"stage": "ANALYSIS", "code": "AI_OUTPUT_INVALID", "reasonDetail": None}
    assert len(captured["attempts"]) == 2


# Run berhenti setelah quota/timeout; hanya attempt nyata tersimpan di tmp, tanpa record atau latensi fiktif.
@pytest.mark.parametrize("failure", [ProviderQuotaExceeded("quota"), ProviderTimeout("timeout")])
def test_provider_failure_stops_run(
    dataset: Path, settings: Settings, tmp_path: Path, failure: ProviderQuotaExceeded | ProviderTimeout
) -> None:
    provider = MockLLMProvider(failure)
    output = tmp_path / "run"
    config = run_eval.execute_run(dataset, output, load_dev_entries(dataset), settings, provider=provider)
    rows = [json.loads(line) for line in (output / "tmp" / "raw.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(provider.received) == 1
    assert config["status"] == "RUNNING"
    assert config["stopReason"] == failure.code.value
    assert config["counts"] == {"UNAVAILABLE": 1}
    assert config["records"] == 1 and config["plannedRecords"] == 2
    assert not (output / "raw.jsonl").exists()
    assert all(row["result"] is None for row in rows)
    assert len(rows) == 1
    EvaluationRecord.model_validate(rows[0])


# Konfigurasi yang diserialisasi tidak mengandung kedua nilai secret maupun nama field kredensial.
def test_public_config_has_no_secrets(settings: Settings) -> None:
    settings = settings.model_copy(
        update={
            "llm_api_key": SecretStr("unit-secret-not-real"),
            "internal_api_token": SecretStr("unit-token-not-real"),
        }
    )
    serialized = json.dumps(public_settings(settings))
    for forbidden in ("unit-secret-not-real", "unit-token-not-real", "llm_api_key", "internal_api_token"):
        assert forbidden not in serialized


# Artefak hanya menyimpan origin; path berkredensial tidak bocor dan URL runtime tidak berubah.
@pytest.mark.parametrize(
    ("url", "origin"),
    [
        ("https://example.test/private/unit-path-secret-not-real/v1", "https://example.test"),
        ("https://example.test/private/unit%2Dpath%2Dsecret%2Dnot%2Dreal/v1", "https://example.test"),
        ("https://example.test:8443/v1", "https://example.test:8443"),
        ("http://[::1]:8080/v1", "http://[::1]:8080"),
    ],
)
def test_provider_path_is_not_written_to_artifacts(
    dataset: Path, settings: Settings, tmp_path: Path, url: str, origin: str
) -> None:
    configured = settings.model_copy(update={"llm_base_url": url})
    output = tmp_path / "origin-only"
    run_eval.execute_run(
        dataset, output, load_dev_entries(dataset, 1), configured, provider=MockLLMProvider(HIGH_OUTPUT)
    )
    config = json.loads((output / "run_config.json").read_text(encoding="utf-8"))
    assert config["settings"]["baseUrl"] == origin
    assert configured.llm_base_url == url
    for artifact in (path for path in output.rglob("*") if path.is_file()):
        content = artifact.read_text(encoding="utf-8")
        assert "unit-path-secret-not-real" not in content
        assert "unit%2Dpath%2Dsecret%2Dnot%2Dreal" not in content


# URL berkredensial/query ditolak sebelum menjadi konfigurasi atau bukti run.
@pytest.mark.parametrize("url", ["https://user:password@example.test/v1", "https://example.test/v1?key=private"])
def test_secret_bearing_base_url_is_rejected(settings: Settings, url: str) -> None:
    with pytest.raises(ValueError, match="kredensial"):
        public_settings(settings.model_copy(update={"llm_base_url": url}))


# Run berhasil mempunyai satu record per dokumen dan tidak dapat menimpa direktori bukti yang sudah ada.
def test_successful_run_and_overwrite_protection(dataset: Path, settings: Settings, tmp_path: Path) -> None:
    output = tmp_path / "run"
    provider = MockLLMProvider(HIGH_OUTPUT, LOW_OUTPUT)
    config = run_eval.execute_run(dataset, output, load_dev_entries(dataset), settings, provider=provider)
    assert config["status"] == "COMPLETE"
    assert config["counts"] == {"OK": 2}
    assert config["schemaVersion"] == 1 and config["split"] == "dev" and config["variants"] == ["pipeline"]
    assert len((output / "model_outputs.jsonl").read_text(encoding="utf-8").splitlines()) == 2
    with pytest.raises(FileExistsError):
        run_eval.execute_run(dataset, output, load_dev_entries(dataset), settings, provider=provider)
    assert len(provider.received) == 2


# Test split ditolak oleh parser sebelum Settings atau akses provider dijalankan.
def test_cli_refuses_test_split(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden_settings() -> Settings:
        """Membuktikan penolakan split terjadi sebelum pembacaan konfigurasi."""
        raise AssertionError("Settings tidak boleh dibaca")

    monkeypatch.setattr(run_eval, "get_settings", forbidden_settings)
    with pytest.raises(SystemExit) as failure:
        run_eval.main(["--split", "test"])
    assert failure.value.code == 2


# Dry run memvalidasi dev dan model tanpa key, jaringan, atau pembuatan direktori hasil.
def test_cli_dry_run_has_no_calls(dataset: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    output = tmp_path / "must-not-exist"
    assert run_eval.main(["--dataset-dir", str(dataset), "--output-dir", str(output), "--dry-run"]) == 0
    assert json.loads(capsys.readouterr().out)["calls"] == 0
    assert not output.exists()


# CLI tidak memakai mock walaupun APP_ENV=test dan tidak berjalan dengan key kosong.
def test_cli_rejects_mock_and_unconfigured(dataset: Path, monkeypatch: pytest.MonkeyPatch, settings: Settings) -> None:
    args = ["--dataset-dir", str(dataset)]
    assert run_eval.main(args) == 1
    monkeypatch.setattr(run_eval, "get_settings", lambda: settings.model_copy(update={"llm_provider": "mock"}))
    assert run_eval.main([*args, "--dry-run"]) == 1


# Event length dicatat tanpa menambahkan isi respons ke log; raw model tetap disimpan hanya pada artefak.
def test_truncation_event_is_counted(dataset: Path, settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    provider = MockLLMProvider(HIGH_OUTPUT)
    original = provider.complete

    def with_length_event(messages: list[dict[str, str]]) -> object:
        """Meniru event runtime yang aman tanpa memodifikasi mock bersama."""
        logging.getLogger("app.analysis.provider").warning(
            "ai.output_truncated", extra={"event": "ai.output_truncated"}
        )
        return original(messages)

    monkeypatch.setattr(provider, "complete", with_length_event)
    _, captured = run_eval.evaluate_document(load_dev_entries(dataset)[0], dataset, settings, provider)
    assert captured["attempts"][0]["lengthEvents"] == 1


# NO_CONTENT menghentikan analisis dokumen tanpa mengonsumsi respons mock maupun membuat kategori.
def test_no_content_never_calls_provider(dataset: Path, settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    empty = ExtractionResponse(
        status="NO_CONTENT",
        text=None,
        method=None,
        pagesTotal=1,
        pagesProcessed=1,
        truncated=False,
        language=None,
        reasonDetail="NO_EXTRACTABLE_TEXT",
    )
    monkeypatch.setattr(run_eval, "extract_document", lambda *_: empty)
    provider = MockLLMProvider()
    record, captured = run_eval.evaluate_document(load_dev_entries(dataset)[0], dataset, settings, provider)
    assert record["status"] == "UNAVAILABLE"
    assert record["error"] == {
        "stage": "EXTRACTION",
        "code": "EXTRACTION_NO_CONTENT",
        "reasonDetail": "NO_EXTRACTABLE_TEXT",
    }
    EvaluationRecord.model_validate(record)
    assert record["result"] is None and captured["attempts"] == []
    assert provider.received == []


# API execute_run juga menolak Entry test yang disisipkan langsung dan injeksi mock di luar APP_ENV=test.
def test_run_boundary_checks(dataset: Path, settings: Settings, tmp_path: Path) -> None:
    entries = load_dev_entries(dataset)
    with pytest.raises(ValueError, match="dokumen dev"):
        run_eval.execute_run(dataset, tmp_path / "bad-split", [replace(entries[0], split="test")], settings)
    with pytest.raises(ValueError, match="unit test"):
        run_eval.execute_run(
            dataset,
            tmp_path / "bad-injection",
            entries,
            settings.model_copy(update={"app_env": "local"}),
            provider=MockLLMProvider(),
        )


# Pipeline dan baseline memakai detector nyata masing-masing, format v1 yang sama, dan ID tanpa duplikat per varian.
def test_combined_run_conforms_to_shared_schema(dataset: Path, settings: Settings, tmp_path: Path) -> None:
    output = tmp_path / "combined"
    provider = MockLLMProvider(HIGH_OUTPUT, LOW_OUTPUT)
    config = run_eval.execute_run(
        dataset, output, load_dev_entries(dataset), settings, provider=provider, variants=("pipeline", "baseline")
    )
    records = [EvaluationRecord.model_validate_json(line) for line in (output / "raw.jsonl").read_text().splitlines()]
    assert config["status"] == "COMPLETE" and config["records"] == 4
    assert config["variants"] == ["pipeline", "baseline"]
    assert len({(r.variant, r.id) for r in records}) == 4
    assert all(r.status == "OK" for r in records)
    assert len(provider.received) == 2
    assert {r.result.meta.model for r in records} == {"eval-unit-model", "rule-based-baseline"}
    assert not (output / "tmp" / "raw.jsonl").exists()


# Baseline dapat berjalan tanpa key dan tidak pernah membuat provider LLM, termasuk pada CLI.
def test_baseline_only_does_not_construct_llm(
    dataset: Path, settings: Settings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden_provider(*args: object) -> object:
        """Mendeteksi panggilan LLM yang tidak diizinkan pada evaluasi baseline eksplisit."""
        raise AssertionError("Baseline tidak boleh memakai LLM")

    monkeypatch.setattr(run_eval, "get_provider", forbidden_provider)
    output = tmp_path / "baseline"
    assert run_eval.main(["--dataset-dir", str(dataset), "--output-dir", str(output), "--variants", "baseline"]) == 0
    config = json.loads((output / "run_config.json").read_text())
    assert config["model"] == "rule-based-baseline"
    assert config["baselineVersion"] == "rules-v1"
    assert "baseUrl" not in config["settings"] and "model" not in config["settings"]
    assert (output / "model_outputs.jsonl").read_text() == ""


# Perubahan manifest saat panggilan model terjadi menahan raw di tmp dan membuat run tidak layak dibaca metrics.
def test_manifest_change_prevents_publication(
    dataset: Path, settings: Settings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = MockLLMProvider(HIGH_OUTPUT, LOW_OUTPUT)
    original = provider.complete

    def mutate_manifest(messages: list[dict[str, str]]) -> object:
        """Meniru perubahan metadata bersamaan tanpa mengubah berkas evaluasi repository."""
        result = original(messages)
        manifest = dataset / "manifest.csv"
        manifest.write_bytes(manifest.read_bytes() + b"\n")
        return result

    monkeypatch.setattr(provider, "complete", mutate_manifest)
    output = tmp_path / "changed"
    with pytest.raises(ValueError, match="Manifest berubah"):
        run_eval.execute_run(dataset, output, load_dev_entries(dataset), settings, provider=provider)
    config = json.loads((output / "run_config.json").read_text())
    assert config["status"] == "RUNNING" and config["stopReason"] == "MANIFEST_CHANGED"
    assert not (output / "raw.jsonl").exists()
    assert (output / "tmp" / "raw.jsonl").exists()


# Seluruh output yang invalid tetap dicatat; COMPLETE berarti sudah dicoba, bukan semua prediksi berhasil.
def test_complete_run_retains_unavailable_records(dataset: Path, settings: Settings, tmp_path: Path) -> None:
    output = tmp_path / "invalid"
    config = run_eval.execute_run(
        dataset, output, load_dev_entries(dataset), settings, provider=MockLLMProvider("invalid", "invalid", LOW_OUTPUT)
    )
    records = [EvaluationRecord.model_validate_json(line) for line in (output / "raw.jsonl").read_text().splitlines()]
    assert config["status"] == "COMPLETE" and config["counts"] == {"UNAVAILABLE": 1, "OK": 1}
    assert records[0].result is None and records[0].error.code == "AI_OUTPUT_INVALID"


# Pemanggil Python tidak dapat menandai ulang entry test sebagai dev atau menyisipkan duplikat ID.
def test_entries_must_match_selected_manifest(dataset: Path, settings: Settings, tmp_path: Path) -> None:
    entries = load_dev_entries(dataset)
    for supplied in ([entries[0], entries[0]], [replace(entries[0], sha256="0" * 64)]):
        with pytest.raises(ValueError, match="metadata dev"):
            run_eval.execute_run(dataset, tmp_path / "invalid", supplied, settings, provider=MockLLMProvider())
    assert not (tmp_path / "invalid").exists()
