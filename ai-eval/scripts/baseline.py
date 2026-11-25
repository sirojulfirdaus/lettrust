# Owner: Sat (PIC 6) | Status: COMPLETE | Ref: PLAN T6-05; SA §7.8; PRD §8.4–§8.5, BR-04.12
"""Baseline evaluasi ID/EN; --split dev menulis raw.jsonl/run_config.json, --check hanya memvalidasi.

analyze_text() mengembalikan RiskAnalysisResponse yang sama dengan API-08. Baseline tidak memanggil LLM,
tidak menjadi fallback runtime, dan tidak membuat klaim kewajaran numerik gaji atau perbandingan nama perusahaan.
Kontrak hasil bersama pipeline/metrik berada di _eval_schema.py dan docs/evaluation/protocol.md §6.
CLI membatasi pengembangan ke dev; B dapat memakai analyze_text() pada run final setelah test set dibekukan.
"""

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import Counter
from collections.abc import Iterator, Sequence
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Literal

from _dataset import FIELDS, MAX_CHARS, ROOT, Entry, pdf_path, sha256, validate_labels
from _eval_schema import EvaluationError, EvaluationRecord, ExtractionMetadata

from app.analysis import scoring as scoring_module
from app.analysis import taxonomy as taxonomy_module
from app.analysis.compose import compose_result
from app.analysis.scoring import score
from app.analysis.taxonomy import TAXONOMY
from app.analysis.validator import validate_indicators
from app.core.config import Settings, get_settings
from app.extraction.service import extract_document
from app.schemas import AnalysisMeta, ExtractionStatus, RiskAnalysisResponse

BASELINE_VERSION = "rules-v1"


# Mengompilasi pola lintas baris agar pembungkusan baris hasil PDF/OCR tidak memutus frasa.
def _rules(*patterns: str) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(pattern, re.IGNORECASE | re.DOTALL) for pattern in patterns)


PATTERNS = {
    "PAYMENT_REQUEST": _rules(
        r"\bbiaya\s+(?:administrasi|pelatihan|seragam|medical|akomodasi|tiket|rekrutmen)\b",
        r"\b(?:administration|administrative|training|uniform|processing|recruitment)\s+fees?\b",
        r"\b(?:deposit|uang\s+muka|down\s+payment)\b",
        r"\b(?:wajib|harus|diminta|silakan|mohon)\b.{0,35}\b(?:membayar|bayar|transfer|melunasi|menyetor)\b",
        r"\b(?:you|applicants?|candidates?)\b.{0,30}\b(?:must|need\s+to|have\s+to|required\s+to)\s+pay\b",
    ),
    "SENSITIVE_DATA_REQUEST": _rules(
        r"\b(?:kirim(?:kan)?|beri(?:kan)?|bagikan|serahkan|meminta|send|share|provide|submit|request)\b"
        r".{0,85}\b(?:OTP|PIN|password|kata\s+sandi|kartu\s+ATM|akses\s+rekening|credit\s+card|bank\s+access)\b",
        r"\b(?:OTP|PIN|password|kata\s+sandi|data\s+kartu\s+kredit)\b"
        r".{0,40}\b(?:dikirim|diberikan|diserahkan|required)\b",
    ),
    "UNOFFICIAL_CONTACT": _rules(
        r"\b(?:hanya|only|exclusively)\b.{0,45}\b(?:whatsapp|telegram|WA|nomor\s+pribadi|personal\s+number)\b",
        r"\b(?:HR|rekrutmen|recruitment|hubungi|kontak|contact)\b.{0,100}"
        r"[\w.+-]+@(?:gmail|yahoo|hotmail|outlook)\.(?:com|co\.id)\b",
    ),
    "URGENCY_PRESSURE": _rules(
        r"\b(?:konfirmasi|balas|jawab|confirm|accept|respond)\b.{0,35}\b(?:segera|sekarang|immediately|urgently)\b",
        r"\b(?:segera|immediately|urgently)\b.{0,35}\b(?:konfirmasi|balas|jawab|confirm|accept|respond)\b",
        r"\b(?:dalam|within)\s+(?:[1-5]?\d|thirty|fifteen)\s*(?:menit|minutes?)\b",
        r"\b(?:dalam|within)\s+(?:[1-3]|satu|dua|tiga|one|two|three)\s*(?:jam|hours?)\b",
        r"\b(?:kuota\s+terbatas|limited\s+(?:slots|places)|kehilangan\s+posisi|lose\s+(?:your\s+)?(?:place|job))\b",
    ),
    "IDENTITY_INCONSISTENCY": _rules(
        r"\b(?:nama|alamat|posisi|jabatan|perusahaan|penanda\s+tangan|company|address|position|signatory)\b"
        r".{0,100}\b(?:berbeda|bertentangan|tidak\s+(?:sesuai|sama|konsisten)|inconsistent|mismatch|differs)\b",
        r"\b(?:inkonsistensi|ketidaksesuaian|inconsistency|contradiction)\b"
        r".{0,80}\b(?:nama|alamat|perusahaan|penawaran|company|address|offer)\b",
    ),
    "UNREALISTIC_COMPENSATION": _rules(
        r"\b(?:gaji|kompensasi|fasilitas|salary|compensation|benefits)\b"
        r".{0,65}\b(?:tidak\s+wajar|sangat\s+tinggi|jauh\s+melebihi|unrealistic|unusually\s+high|above\s+market)\b",
        r"\b(?:unrealistic|unusually\s+high)\s+(?:salary|compensation|benefits)\b",
    ),
    "VAGUE_JOB_DETAILS": _rules(
        r"\b(?:rincian|tugas|tanggung\s+jawab|lokasi|atasan)\b"
        r".{0,70}\b(?:menyusul|belum\s+(?:jelas|dijelaskan|ditentukan)|tidak\s+(?:dijelaskan|ditentukan))\b",
        r"\b(?:job\s+details|duties|responsibilities|location|supervisor)\b"
        r".{0,70}\b(?:later|not\s+specified|not\s+provided|to\s+be\s+confirmed)\b",
        r"\b(?:yth\.?\s+(?:pelamar|kandidat)|dear\s+(?:applicant|candidate))\b",
    ),
}

EXCLUSIONS = {
    "PAYMENT_REQUEST": _rules(
        r"\b(?:ditanggung|dibayar|dibiayai)\s+(?:sepenuhnya\s+)?(?:oleh\s+)?(?:perusahaan|pemberi\s+kerja)\b",
        r"\b(?:company|employer)\s+(?:fully\s+)?(?:covers|pays|funds|bears)\b",
        r"\b(?:paid|covered|borne)\s+by\s+(?:the\s+)?(?:company|employer)\b",
        r"\b(?:tidak|tanpa)\s+(?:ada\s+)?(?:biaya|pembayaran|deposit)\b",
        r"\b(?:tidak|jangan)\s+(?:pernah\s+)?(?:diminta\s+|perlu\s+|diwajibkan\s+)?(?:membayar|bayar|transfer)\b",
        r"\b(?:do\s+not|don['’]t|never|not\s+required\s+to|no\s+need\s+to|must\s+not)\s+(?:pay|transfer)\b",
        r"\bno\s+(?:administration|administrative|training|processing|recruitment)\s+fees?\b",
    ),
    "SENSITIVE_DATA_REQUEST": _rules(
        r"\b(?:jangan|dilarang|tidak\s+pernah)\b.{0,40}\b(?:kirim|bagikan|berikan|meminta|membagikan)\b",
        r"\b(?:do\s+not|don['’]t|never|must\s+not)\s+(?:share|send|provide|request|ask)\b",
    ),
    "UNOFFICIAL_CONTACT": _rules(r"\b(?:jangan|tidak|do\s+not|never)\b.{0,40}\b(?:hubungi|contact|gunakan|use)\b"),
    "URGENCY_PRESSURE": _rules(r"\b(?:tidak\s+perlu\s+(?:segera|terburu)|no\s+urgency|not\s+urgent)\b"),
    "IDENTITY_INCONSISTENCY": _rules(
        r"\b(?:tidak\s+ada\s+(?:perbedaan|inkonsistensi)|not\s+inconsistent|no\s+inconsistency)\b"
    ),
}


# Mempertahankan potongan asli sebagai evidence, termasuk baris terbungkus dan singkatan umum surat.
def _sentences(text: str) -> Iterator[str]:
    start = 0
    for match in re.finditer(r"[.!?]+(?=\s|$)|\n[ \t]*\n", text):
        if match.group() == "." and re.search(
            r"\b(?:PT|CV|Rp|Mr|Mrs|Ms|Dr|Ltd|Inc)\.$", text[start : match.end()], re.I
        ):
            continue
        sentence = text[start : match.end()].strip()
        if sentence:
            yield sentence
        start = match.end()
    if text[start:].strip():
        yield text[start:].strip()


# Mendeteksi pola tanpa anotasi/ID fixture; negasi berlaku per klausa agar tidak menutupi permintaan lain.
def analyze_text(document_text: str) -> RiskAnalysisResponse:
    if not document_text.strip() or len(document_text) > MAX_CHARS:
        raise ValueError("Baseline memerlukan teks tidak kosong dengan panjang sesuai batas AI.")
    started = perf_counter()
    evidence: dict[str, list[str]] = {code: [] for code in TAXONOMY}
    for sentence in _sentences(document_text):
        clauses = re.split(
            r";|\b(?:but|however|tetapi|namun)\b|\b(?:dan|and)\s+(?=pelamar|kandidat|anda|you|applicants?|candidates?)",
            sentence,
            flags=re.I,
        )
        for code, patterns in PATTERNS.items():
            for clause in clauses:
                normalized = unicodedata.normalize("NFKC", clause)
                if any(pattern.search(normalized) for pattern in patterns) and not any(
                    pattern.search(normalized) for pattern in EXCLUSIONS.get(code, ())
                ):
                    if sentence not in evidence[code] and len(evidence[code]) < 3:
                        evidence[code].append(sentence)
                    break
    indicators, dropped = validate_indicators(
        [{"code": code, "evidence": quotes} for code, quotes in evidence.items() if quotes],
        document_text,
        None,
        90,
    )
    return compose_result(
        indicators,
        score({item.code for item in indicators}),
        None,
        AnalysisMeta(
            model="rule-based-baseline",
            prompt_version=BASELINE_VERSION,
            latency_ms=int((perf_counter() - started) * 1000),
            dropped_indicators=dropped,
        ),
    )


# Memilih dev sebelum membuka PDF atau memeriksa anotasi; test set tidak dibaca untuk pengembangan baseline.
def _dev_entries(directory: Path) -> list[Entry]:
    with (directory / "manifest.csv").open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != list(FIELDS):
            raise ValueError("Header manifest tidak sesuai format dataset.")
        entries = []
        for row in reader:
            if row.get("split") != "dev":
                continue
            if set(row) != set(FIELDS) or any(not isinstance(value, str) for value in row.values()):
                raise ValueError("Baris manifest dev tidak lengkap.")
            entries.append(Entry(**row))
    if not entries or len({entry.id for entry in entries}) != len(entries):
        raise ValueError("Dokumen dev tidak tersedia atau ID dev duplikat.")
    for entry in entries:
        if entry.lang not in {"id", "en"} or entry.format not in {"text", "scan"}:
            raise ValueError("Bahasa atau format dokumen dev tidak didukung.")
        validate_labels(json.loads(entry.indicators), entry.label)
    return entries


# Memeriksa ekstraksi/OCR serta detektor pada dev tanpa memakai label referensi sebagai input analisis.
def check_dev_dataset(directory: Path) -> dict[str, object]:
    entries = _dev_entries(directory)
    settings = get_settings()
    counts: Counter[str] = Counter()
    for entry in entries:
        content = pdf_path(directory, entry).read_bytes()
        if sha256(content) != entry.sha256:
            raise ValueError("Checksum PDF dev tidak sesuai manifest.")
        extracted = extract_document(content, settings)
        if extracted.status is not ExtractionStatus.OK or extracted.text is None:
            raise ValueError("PDF dev tidak menghasilkan teks yang dapat dianalisis.")
        analyze_text(extracted.text)
        counts[entry.lang] += 1
        counts[entry.format] += 1
    return {
        "mode": "check",
        "split": "dev",
        "processed": len(entries),
        "counts": dict(counts),
        "baselineVersion": BASELINE_VERSION,
        "outputWritten": False,
    }


# Mengubah kegagalan dokumen menjadi record tanpa kategori atau pesan exception mentah.
def _failure(
    entry: Entry,
    started: float,
    stage: Literal["INPUT", "EXTRACTION", "ANALYSIS"],
    code: str,
    extraction: ExtractionMetadata | None = None,
) -> EvaluationRecord:
    return EvaluationRecord(
        id=entry.id,
        variant="baseline",
        status="UNAVAILABLE",
        result=None,
        extraction=extraction,
        error=EvaluationError(
            stage=stage, code=code, reason_detail=extraction.reason_detail if extraction is not None else None
        ),
        latency_ms=int((perf_counter() - started) * 1000),
    )


# Mengekstrak PDF nyata lalu menjalankan aturan; label manifest tidak diberikan kepada detektor.
def evaluate_entry(entry: Entry, directory: Path, settings: Settings) -> EvaluationRecord:
    started = perf_counter()
    try:
        content = pdf_path(directory, entry).read_bytes()
    except (OSError, ValueError):
        return _failure(entry, started, "INPUT", "DOCUMENT_READ_ERROR")
    if sha256(content) != entry.sha256:
        return _failure(entry, started, "INPUT", "CHECKSUM_MISMATCH")
    try:
        extracted = extract_document(content, settings)
    except (OSError, ValueError, RuntimeError):
        return _failure(entry, started, "EXTRACTION", "EXTRACTION_FAILED")
    metadata = ExtractionMetadata.from_response(extracted)
    if extracted.status is not ExtractionStatus.OK or extracted.text is None:
        return _failure(entry, started, "EXTRACTION", "EXTRACTION_NO_CONTENT", metadata)
    try:
        result = analyze_text(extracted.text)
    except ValueError:
        return _failure(entry, started, "ANALYSIS", "ANALYSIS_INVALID", metadata)
    return EvaluationRecord(
        id=entry.id,
        variant="baseline",
        status="OK",
        result=result,
        extraction=metadata,
        error=None,
        latency_ms=int((perf_counter() - started) * 1000),
    )


# Menulis konfigurasi atomik agar pembaca menolak run yang terputus sebelum status COMPLETE.
def _write_config(output: Path, config: dict[str, object]) -> None:
    temporary = output / "tmp" / "run_config.json"
    temporary.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(output / "run_config.json")


# Mengekspor hasil dev termasuk kegagalan, tanpa menimpa run lama atau menulis di folder dataset.
def export_dev_dataset(directory: Path, output: Path) -> dict[str, object]:
    manifest_hash = sha256((directory / "manifest.csv").read_bytes())
    entries = _dev_entries(directory)
    settings = get_settings()
    if output.resolve().is_relative_to(directory.resolve()):
        raise ValueError("Output evaluasi tidak boleh berada di dalam dataset.")
    if sha256((directory / "manifest.csv").read_bytes()) != manifest_hash:
        raise ValueError("Manifest berubah saat input evaluasi dibaca.")
    output.mkdir(parents=True, exist_ok=False)
    (output / "tmp").mkdir()
    config: dict[str, object] = {
        "schemaVersion": 1,
        "status": "RUNNING",
        "variants": ["baseline"],
        "split": "dev",
        "startedAt": datetime.now(UTC).isoformat(),
        "finishedAt": None,
        "manifestSha256": manifest_hash,
        "baselineVersion": BASELINE_VERSION,
        "model": "rule-based-baseline",
        "languages": sorted({entry.lang for entry in entries}),
        "formats": sorted({entry.format for entry in entries}),
        "settings": {
            "aiMaxPages": settings.ai_max_pages,
            "aiMaxChars": settings.ai_max_chars,
            "ocrMinCharsPerPage": settings.ocr_min_chars_per_page,
            "ocrDpi": settings.ocr_dpi,
            "ocrPageTimeoutSeconds": settings.ocr_page_timeout_seconds,
        },
        "sourceSha256": {
            "baseline": sha256(Path(__file__).read_bytes()),
            "scoring": sha256(Path(scoring_module.__file__).read_bytes()),
            "taxonomy": sha256(Path(taxonomy_module.__file__).read_bytes()),
        },
    }
    _write_config(output, config)
    counts: Counter[str] = Counter()
    temporary = output / "tmp" / "raw.jsonl"
    with temporary.open("w", encoding="utf-8", newline="\n") as raw:
        for entry in entries:
            record = evaluate_entry(entry, directory, settings)
            raw.write(record.model_dump_json(by_alias=True) + "\n")
            counts[record.status] += 1
    if sha256((directory / "manifest.csv").read_bytes()) != manifest_hash:
        raise ValueError("Manifest berubah selama evaluasi; run tidak difinalisasi.")
    temporary.replace(output / "raw.jsonl")
    config.update(
        status="COMPLETE", finishedAt=datetime.now(UTC).isoformat(), records=len(entries), counts=dict(counts)
    )
    _write_config(output, config)
    return {
        "mode": "export",
        "split": "dev",
        "processed": len(entries),
        "counts": dict(counts),
        "unavailable": counts["UNAVAILABLE"],
        "baselineVersion": BASELINE_VERSION,
        "outputWritten": True,
        "output": str(output),
    }


# Mengekspor dev atau memeriksanya tanpa output; test split hanya dikelola B setelah proses freeze.
def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("dev",), default="dev")
    parser.add_argument("--dataset", type=Path, default=ROOT / "dataset")
    parser.add_argument("--output", type=Path, help="Direktori run baru; direktori yang sudah ada tidak ditimpa.")
    parser.add_argument("--check", action="store_true", help="Validasi dev; tidak menulis raw.jsonl atau metrik.")
    args = parser.parse_args(argv)
    if args.check and args.output is not None:
        parser.error("--check tidak menulis output; jangan gabungkan dengan --output.")
    try:
        if args.check:
            summary = check_dev_dataset(args.dataset)
        else:
            output = args.output or ROOT / "results" / (datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ") + "-baseline")
            summary = export_dev_dataset(args.dataset, output)
    except (OSError, ValueError, RuntimeError):
        print(
            "Baseline gagal memvalidasi input atau output run; run yang belum COMPLETE tidak boleh dipakai.",
            file=sys.stderr,
        )
        return 1
    print(json.dumps(summary, ensure_ascii=False))
    return int(summary.get("unavailable", 0) != 0)


if __name__ == "__main__":
    raise SystemExit(main())
