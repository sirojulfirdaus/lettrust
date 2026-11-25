# Owner: Sat (PIC 6) | Status: COMPLETE | Ref: PLAN T6-05; SA §7.8; PRD §8.4–§8.5
"""Regresi baseline memakai kalimat/PDF sintetis mandiri, tanpa membaca atau menyesuaikan test set evaluasi."""

import csv
import json
from pathlib import Path
from typing import Any, Literal

import baseline
import generate_pdfs
import pytest
from _dataset import FIELDS, MAX_CHARS, Entry, sha256
from _eval_schema import EvaluationRecord, ExtractionMetadata
from pydantic import ValidationError

from app.core.config import Settings
from app.schemas import ExtractionMethod, ExtractionResponse, ExtractionStatus, NoContentReason, RiskAnalysisResponse

POSITIVE = [
    ("PAYMENT_REQUEST", "Pelamar wajib membayar biaya administrasi sebelum mulai bekerja."),
    ("PAYMENT_REQUEST", "Applicants must pay a uniform deposit before starting work."),
    ("SENSITIVE_DATA_REQUEST", "Kirimkan OTP dan PIN Anda kepada petugas rekrutmen."),
    ("SENSITIVE_DATA_REQUEST", "Send your password and OTP to the recruitment contact."),
    ("UNOFFICIAL_CONTACT", "Komunikasi hanya melalui WhatsApp pribadi."),
    ("UNOFFICIAL_CONTACT", "Please contact HR at hiring@gmail.com for recruitment."),
    ("URGENCY_PRESSURE", "Konfirmasi segera karena kuota terbatas."),
    ("URGENCY_PRESSURE", "Confirm immediately or lose your place."),
    ("IDENTITY_INCONSISTENCY", "Nama perusahaan pada kop berbeda dengan penanda tangan surat."),
    ("IDENTITY_INCONSISTENCY", "The company address is inconsistent with the signed offer."),
    ("UNREALISTIC_COMPENSATION", "Gaji sangat tinggi dan jauh melebihi kewajaran untuk posisi ini."),
    ("UNREALISTIC_COMPENSATION", "Our compensation is unusually high for this position."),
    ("VAGUE_JOB_DETAILS", "Rincian tugas dan lokasi akan menyusul."),
    ("VAGUE_JOB_DETAILS", "Job details and responsibilities will be provided later."),
]


# Ketujuh kode harus dikenali pada ID/EN dengan kutipan yang merupakan potongan teks asli.
@pytest.mark.parametrize(("code", "text"), POSITIVE)
def test_bilingual_indicators_have_literal_evidence(code: str, text: str) -> None:
    result = baseline.analyze_text(text)
    assert {detail.code for detail in result.indicator_details} == {code}
    assert result.indicator_details[0].evidence == [text]
    assert RiskAnalysisResponse.model_validate(result.model_dump(by_alias=True)) == result
    assert result.meta.model == "rule-based-baseline"


# Pengecualian mencegah biaya perusahaan, peringatan data sensitif, dan penyangkalan menjadi indikator positif.
@pytest.mark.parametrize(
    "text",
    [
        "Biaya administrasi ditanggung perusahaan.",
        "The employer covers all training fees.",
        "Pelamar tidak perlu membayar deposit.",
        "You are not required to pay a deposit.",
        "Jangan bagikan OTP atau PIN kepada siapa pun.",
        "Never share your password or OTP.",
        "Anda tidak perlu segera konfirmasi.",
        "The company is not inconsistent with the signed offer.",
        "Contact HR at jobs@example.test for information.",
    ],
)
def test_exceptions_do_not_raise_indicators(text: str) -> None:
    result = baseline.analyze_text(text)
    assert result.indicator_details == []
    assert result.category.value == "LOW"


# Larangan berbagi kredensial tetap LOW untuk bentuk verba ID/EN yang dikenali detektor positif.
@pytest.mark.parametrize(
    "text",
    [
        "Jangan kirimkan OTP kepada siapa pun.",
        "Dilarang kirimkan PIN kepada pihak lain.",
        "Jangan serahkan PIN kepada siapa pun.",
        "Dilarang serahkan kata sandi kepada pihak lain.",
        "Jangan beri password kepada siapa pun.",
        "Jangan berikan OTP kepada siapa pun.",
        "Do not submit your password to anyone.",
        "Don't submit your OTP to anyone.",
        "Never submit your PIN to anyone.",
        "You must not submit your password to anyone.",
    ],
)
def test_sensitive_data_warnings_do_not_raise_indicators(text: str) -> None:
    result = baseline.analyze_text(text)
    assert result.indicator_details == []
    assert result.category.value == "LOW"


# Pengecualian baru tidak boleh menutupi permintaan kredensial afirmatif dengan verba yang sama.
@pytest.mark.parametrize(
    "text",
    [
        "Serahkan PIN Anda kepada petugas rekrutmen.",
        "Beri kata sandi Anda kepada petugas rekrutmen.",
        "Submit your password to the recruitment contact.",
    ],
)
def test_sensitive_data_requests_remain_high(text: str) -> None:
    result = baseline.analyze_text(text)
    assert {detail.code for detail in result.indicator_details} == {"SENSITIVE_DATA_REQUEST"}
    assert result.category.value == "HIGH"
    assert result.indicator_details[0].evidence == [text]


# Peringatan kredensial pada klausa lain tidak boleh membatalkan permintaan yang benar-benar terdeteksi.
@pytest.mark.parametrize(
    "text",
    [
        "Jangan kirimkan OTP kepada orang lain, tetapi serahkan PIN kepada petugas rekrutmen.",
        "Serahkan PIN kepada petugas rekrutmen, tetapi jangan kirimkan OTP kepada orang lain.",
        "Do not submit your password to strangers, but submit your PIN to the recruitment contact.",
        "Submit your PIN to the recruitment contact, but do not submit your password to strangers.",
    ],
)
def test_sensitive_data_warning_exception_is_local(text: str) -> None:
    result = baseline.analyze_text(text)
    assert {detail.code for detail in result.indicator_details} == {"SENSITIVE_DATA_REQUEST"}
    assert result.category.value == "HIGH"
    assert result.indicator_details[0].evidence == [text]


# Pengecualian dalam satu klausa tidak boleh menutupi permintaan pembayaran pada klausa lain.
@pytest.mark.parametrize(
    "text",
    [
        "Biaya pelatihan ditanggung perusahaan, tetapi pelamar wajib membayar deposit seragam.",
        "The employer covers relocation costs, but applicants must pay a uniform deposit.",
    ],
)
def test_company_payment_exception_is_local(text: str) -> None:
    result = baseline.analyze_text(text)
    assert {detail.code for detail in result.indicator_details} == {"PAYMENT_REQUEST"}
    assert result.category.value == "HIGH"
    assert result.indicator_details[0].evidence == [text]


# Kategori memakai aturan runtime, termasuk dua LOW berbeda dan indikator berulang yang dihitung sekali.
@pytest.mark.parametrize(
    ("text", "category"),
    [
        ("Tugas meliputi pencatatan stok dan laporan bulanan.", "LOW"),
        ("Gaji sangat tinggi untuk posisi ini.", "LOW"),
        ("Gaji sangat tinggi untuk posisi ini. Rincian tugas menyusul.", "MEDIUM"),
        ("Rincian tugas menyusul. Rincian lokasi menyusul.", "LOW"),
        ("Konfirmasi segera karena kuota terbatas.", "MEDIUM"),
        ("Pelamar wajib membayar deposit seragam.", "HIGH"),
    ],
)
def test_runtime_scoring_is_reused(text: str, category: str) -> None:
    assert baseline.analyze_text(text).category.value == category


# Bukti harus tetap kalimat asli walau PDF membungkus baris atau memuat singkatan dan pemisah ribuan.
def test_sentences_preserve_wrapping_and_abbreviations() -> None:
    evidence = "Pelamar wajib membayar biaya\nadministrasi sebelum bekerja."
    text = "PT. Contoh menawarkan gaji Rp. 10.000.000 per bulan. " + evidence
    result = baseline.analyze_text(text)
    assert result.indicator_details[0].code == "PAYMENT_REQUEST"
    assert result.indicator_details[0].evidence == [evidence]


# Normalisasi untuk deteksi tidak mengganti kutipan asli yang mengandung karakter lebar penuh.
def test_unicode_evidence_is_not_rewritten() -> None:
    text = "Kirimkan ＯＴＰ dan ＰＩＮ kepada petugas rekrutmen."
    result = baseline.analyze_text(text)
    assert result.indicator_details[0].code == "SENSITIVE_DATA_REQUEST"
    assert result.indicator_details[0].evidence == [text]


# Indikator berulang mempertahankan maksimal tiga kutipan unik sesuai kontrak API-08.
def test_repeated_evidence_is_bounded() -> None:
    sentences = [f"Pelamar wajib membayar deposit seragam tahap {number}." for number in range(4)]
    result = baseline.analyze_text(" ".join([sentences[0], *sentences]))
    assert len(result.indicator_details) == 1
    assert result.indicator_details[0].evidence == sentences[:3]


# Input tidak valid ditolak tanpa kategori yang mengesankan pemeriksaan sudah dijalankan.
@pytest.mark.parametrize("text", ["", " \n ", "a" * (MAX_CHARS + 1)])
def test_invalid_text_is_rejected(text: str) -> None:
    with pytest.raises(ValueError):
        baseline.analyze_text(text)


# Membuat manifest/PDF lokal khusus tes; baris test sengaja tidak memiliki berkas untuk mendeteksi akses terlarang.
def _dataset(directory: Path) -> None:
    pdf_dir = directory / "pdf"
    pdf_dir.mkdir(parents=True)
    content = generate_pdfs.render_text_pdf("Pelamar wajib membayar biaya administrasi sebelum mulai bekerja.")
    (pdf_dir / "id-high-01-text.pdf").write_bytes(content)
    with (directory / "manifest.csv").open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerow(
            {
                "id": "id-high-01-text",
                "split": "dev",
                "lang": "id",
                "format": "text",
                "label": "HIGH",
                "indicators": '["PAYMENT_REQUEST"]',
                "file": "pdf/id-high-01-text.pdf",
                "sha256": sha256(content),
            }
        )
        writer.writerow(
            {
                "id": "frozen-unit-test",
                "split": "test",
                "lang": "id",
                "format": "scan",
                "label": "UNUSED",
                "indicators": "UNUSED",
                "file": "frozen-do-not-read.pdf",
                "sha256": "UNUSED",
            }
        )


# Konfigurasi tes tidak memakai kredensial atau provider LLM anggota tim.
@pytest.fixture
def extraction_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(
        app_env="test", internal_api_token="baseline-unit-test-token", llm_provider="openai_compatible", llm_api_key=""
    )
    monkeypatch.setattr(baseline, "get_settings", lambda: settings)


# Mode check benar-benar mengekstrak PDF dev dan tidak membaca, memvalidasi anotasi, atau menulis test set.
def test_dev_check_uses_real_extraction_only_on_dev(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], extraction_settings: None
) -> None:
    _dataset(tmp_path)
    before = {path.relative_to(tmp_path) for path in tmp_path.rglob("*")}
    assert baseline.main(["--split", "dev", "--dataset", str(tmp_path), "--check"]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["processed"] == 1
    assert summary["split"] == "dev"
    assert summary["outputWritten"] is False
    assert {path.relative_to(tmp_path) for path in tmp_path.rglob("*")} == before


# Checksum berbeda harus menggagalkan pemeriksaan sebelum hasil baseline dinyatakan valid.
def test_dev_check_rejects_checksum_drift(tmp_path: Path, extraction_settings: None) -> None:
    _dataset(tmp_path)
    (tmp_path / "pdf" / "id-high-01-text.pdf").write_bytes(b"%PDF-berubah")
    assert baseline.main(["--split", "dev", "--dataset", str(tmp_path), "--check"]) == 1


# CLI dev tidak boleh membaca test set atau menggabungkan check-only dengan ekspor.
@pytest.mark.parametrize("arguments", [["--split", "test", "--check"], ["--check", "--output", "unused"]])
def test_invalid_modes_are_rejected(arguments: list[str]) -> None:
    with pytest.raises(SystemExit) as error:
        baseline.main(arguments)
    assert error.value.code == 2


# Ekspor riil harus bisa dibaca lewat model yang sama untuk konsumen pipeline/metrik tanpa membaca test set.
def test_export_uses_shared_record_contract(tmp_path: Path, extraction_settings: None) -> None:
    dataset, output = tmp_path / "dataset", tmp_path / "run"
    _dataset(dataset)
    assert baseline.main(["--dataset", str(dataset), "--output", str(output)]) == 0
    lines = (output / "raw.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    record = EvaluationRecord.model_validate_json(lines[0])
    assert record.id == "id-high-01-text"
    assert record.variant == "baseline" and record.status == "OK"
    assert record.result is not None and record.result.category.value == "HIGH"
    assert record.extraction is not None and record.extraction.method is ExtractionMethod.TEXT_LAYER
    assert "text" not in json.loads(lines[0])["extraction"]
    config = json.loads((output / "run_config.json").read_text())
    assert config["status"] == "COMPLETE" and config["schemaVersion"] == 1
    assert config["manifestSha256"] == sha256((dataset / "manifest.csv").read_bytes())
    assert config["records"] == 1 and config["counts"] == {"OK": 1}
    assert set(config["settings"]) == {
        "aiMaxPages",
        "aiMaxChars",
        "ocrMinCharsPerPage",
        "ocrDpi",
        "ocrPageTimeoutSeconds",
    }


# Kegagalan input tetap tersimpan sebagai UNAVAILABLE dengan result null, bukan kategori LOW palsu.
def test_export_failure_has_no_category(tmp_path: Path, extraction_settings: None) -> None:
    dataset, output = tmp_path / "dataset", tmp_path / "run"
    _dataset(dataset)
    (dataset / "pdf" / "id-high-01-text.pdf").write_bytes(b"%PDF-berubah")
    assert baseline.main(["--dataset", str(dataset), "--output", str(output)]) == 1
    record = EvaluationRecord.model_validate_json((output / "raw.jsonl").read_text())
    assert record.status == "UNAVAILABLE" and record.result is None
    assert record.error is not None and record.error.code == "CHECKSUM_MISMATCH"
    config = json.loads((output / "run_config.json").read_text())
    assert config["status"] == "COMPLETE" and config["counts"] == {"UNAVAILABLE": 1}


# Run lama tidak ditimpa; output di dalam folder dataset juga harus ditolak sebelum menulis apa pun.
def test_export_rejects_overwrite_and_dataset_output(tmp_path: Path, extraction_settings: None) -> None:
    dataset, output = tmp_path / "dataset", tmp_path / "run"
    _dataset(dataset)
    assert baseline.main(["--dataset", str(dataset), "--output", str(output)]) == 0
    raw = (output / "raw.jsonl").read_bytes()
    assert baseline.main(["--dataset", str(dataset), "--output", str(output)]) == 1
    assert (output / "raw.jsonl").read_bytes() == raw
    assert baseline.main(["--dataset", str(dataset), "--output", str(dataset / "bad")]) == 1
    assert not (dataset / "bad").exists()


# Contoh respons sukses kedua varian mengikuti API-08 yang sama; label referensi tetap di manifest.
def _record(variant: Literal["baseline", "pipeline"] = "baseline") -> dict[str, Any]:
    result = baseline.analyze_text("Pelamar wajib membayar deposit seragam sebelum mulai bekerja.")
    extracted = ExtractionResponse(
        status=ExtractionStatus.OK,
        text="Isi sintetis tidak disalin ke metadata.",
        method=ExtractionMethod.TEXT_LAYER,
        pages_total=1,
        pages_processed=1,
        truncated=False,
        language=None,
    )
    return EvaluationRecord(
        id="unit-example",
        variant=variant,
        status="OK",
        result=result,
        extraction=ExtractionMetadata.from_response(extracted),
        error=None,
        latency_ms=1,
    ).model_dump(mode="json", by_alias=True)


# Pembaca metrik dapat memvalidasi respons baseline maupun pipeline dengan kontrak yang sama.
@pytest.mark.parametrize("variant", ["pipeline", "baseline"])
def test_both_variants_share_response_schema(variant: Literal["baseline", "pipeline"]) -> None:
    assert EvaluationRecord.model_validate(_record(variant)).variant == variant


# Pembaca menolak versi asing, status palsu, kategori bebas, serta penyisipan teks dokumen di metadata.
@pytest.mark.parametrize("defect", ["version", "ok_without_result", "failed_with_result", "category", "text", "status"])
def test_record_invariants_are_enforced(defect: str) -> None:
    record = _record()
    if defect == "version":
        record["schemaVersion"] = 2
    elif defect == "ok_without_result":
        record["result"] = None
    elif defect == "failed_with_result":
        record["status"] = "UNAVAILABLE"
    elif defect == "category":
        record["result"]["category"] = "LOW"
    elif defect == "text":
        record["extraction"]["text"] = "Teks tidak boleh disalin ke metadata."
    else:
        record["status"] = "UNKNOWN"
    with pytest.raises(ValidationError):
        EvaluationRecord.model_validate(record)


# NO_CONTENT tetap menyimpan reason ekstraksi tanpa mengarang hasil analisis.
def test_no_content_is_unavailable(tmp_path: Path, extraction_settings: None, monkeypatch: pytest.MonkeyPatch) -> None:
    _dataset(tmp_path)
    entry = baseline._dev_entries(tmp_path)[0]
    no_content = ExtractionResponse(
        status=ExtractionStatus.NO_CONTENT,
        text=None,
        method=None,
        pages_total=1,
        pages_processed=1,
        truncated=False,
        language=None,
        reason_detail=NoContentReason.NO_EXTRACTABLE_TEXT,
    )
    monkeypatch.setattr(baseline, "extract_document", lambda *_args: no_content)
    record = baseline.evaluate_entry(entry, tmp_path, baseline.get_settings())
    assert record.status == "UNAVAILABLE" and record.result is None
    assert record.error is not None and record.error.code == "EXTRACTION_NO_CONTENT"
    assert record.error.reason_detail is NoContentReason.NO_EXTRACTABLE_TEXT


# Run terputus atau manifest berubah tidak boleh menghasilkan file final berstatus COMPLETE.
@pytest.mark.parametrize("failure", ["interrupt", "manifest_drift"])
def test_incomplete_run_is_not_published(
    tmp_path: Path,
    extraction_settings: None,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failure: str,
) -> None:
    dataset, output = tmp_path / "dataset", tmp_path / "run"
    _dataset(dataset)
    original = baseline.evaluate_entry

    # Menguji kegagalan proses tanpa menulis pesan exception yang bisa mengandung konten sensitif.
    def interrupted(entry: Entry, directory: Path, settings: Settings) -> EvaluationRecord:
        if failure == "interrupt":
            raise RuntimeError("NEVER_PRINT_DOCUMENT_OR_SECRET")
        result = original(entry, directory, settings)
        with (directory / "manifest.csv").open("a", encoding="utf-8") as manifest:
            manifest.write("\n")
        return result

    monkeypatch.setattr(baseline, "evaluate_entry", interrupted)
    assert baseline.main(["--dataset", str(dataset), "--output", str(output)]) == 1
    assert json.loads((output / "run_config.json").read_text())["status"] == "RUNNING"
    assert not (output / "raw.jsonl").exists()
    captured = capsys.readouterr()
    assert "NEVER_PRINT_DOCUMENT_OR_SECRET" not in captured.err + captured.out
