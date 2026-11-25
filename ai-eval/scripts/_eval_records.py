# Owner: B (PIC 5) | Status: COMPLETE | Ref: PLAN T5-07; PRD §10.4.3; SA §7.9
"""Membaca hanya berkas dev dan menyimpan record evaluasi tanpa secret atau akses PDF test."""

import csv
import json
from pathlib import Path
from typing import Any, TextIO
from urllib.parse import urlsplit

from _dataset import FIELDS, SOURCE_ID, Entry, pdf_path, sha256, validate_labels

from app.core.config import Settings


# Memvalidasi manifest dan checksum hanya dokumen dev; baris test tidak dibuka atau dipakai sebagai input model.
def load_dev_entries(directory: Path, limit: int | None = None) -> list[Entry]:
    if limit is not None and limit < 1:
        raise ValueError("Limit harus positif.")
    with (directory / "manifest.csv").open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(FIELDS):
            raise ValueError("Header manifest tidak sesuai SA §7.9.")
        entries = []
        identifiers = set()
        pairs = {}
        for row in reader:
            if row.get("split") != "dev":
                continue
            if set(row) != set(FIELDS) or any(not isinstance(value, str) for value in row.values()):
                raise ValueError("Baris dev tidak lengkap.")
            entry = Entry(**row)
            source_id, _, file_format = entry.id.rpartition("-")
            if not SOURCE_ID.fullmatch(source_id) or file_format not in {"text", "scan"}:
                raise ValueError("ID dokumen dev tidak valid.")
            if entry.id in identifiers or entry.format != file_format:
                raise ValueError("ID duplikat atau format dev tidak konsisten.")
            if entry.lang != source_id.split("-")[0] or entry.label != source_id.split("-")[1].upper():
                raise ValueError("Bahasa/kategori dev tidak sesuai ID sumber.")
            validate_labels(json.loads(entry.indicators), entry.label)
            metadata = (entry.lang, entry.label, entry.indicators)
            if source_id in pairs and pairs[source_id] != metadata:
                raise ValueError("Anotasi pasangan dev tidak konsisten.")
            pairs[source_id] = metadata
            path = pdf_path(directory, entry)
            if not path.is_file() or sha256(path.read_bytes()) != entry.sha256:
                raise ValueError(f"PDF dev hilang atau checksum berubah: {entry.id}.")
            identifiers.add(entry.id)
            entries.append(entry)
    if not entries:
        raise ValueError("Manifest tidak mempunyai dokumen dev.")
    return sorted(entries, key=lambda entry: entry.id)[:limit]


# Mengizinkan URL provider tanpa kredensial/query agar konfigurasi atau bukti tidak membocorkan secret.
def safe_base_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname:
        raise ValueError("Base URL provider tidak valid.")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Base URL harus tanpa kredensial, query, atau fragment.")
    return value.rstrip("/")


# Menyimpan hanya konfigurasi yang diizinkan, tidak pernah model_dump Settings atau nilai token/API key.
def public_settings(settings: Settings) -> dict[str, Any]:
    return {
        "provider": settings.llm_provider,
        "baseUrl": safe_base_url(settings.llm_base_url),
        "model": settings.llm_model,
        "promptVersion": settings.prompt_version,
        "temperature": 0,
        "responseFormat": {"type": "json_object"},
        "maxOutputTokens": settings.llm_max_output_tokens,
        "reasoningEffort": settings.llm_reasoning_effort or None,
        "requestTimeoutSeconds": settings.llm_request_timeout_seconds,
        "outputInvalidRetries": 1,
        "providerRetries": 0,
        "maxUploadBytes": settings.max_upload_bytes,
        "aiMaxPages": settings.ai_max_pages,
        "aiMaxChars": settings.ai_max_chars,
        "ocrMinCharsPerPage": settings.ocr_min_chars_per_page,
        "ocrDpi": settings.ocr_dpi,
        "ocrPageTimeoutSeconds": settings.ocr_page_timeout_seconds,
        "evidenceFuzzyThreshold": settings.evidence_fuzzy_threshold,
    }


# Menulis JSON sintetis hanya ke artefak evaluasi; stdout/log aplikasi tidak menerima isi dokumen/model.
def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


# Menyimpan setiap record seketika agar kegagalan atau interupsi tetap meninggalkan bukti run yang telah terjadi.
def append_record(stream: TextIO, data: dict[str, Any]) -> None:
    stream.write(json.dumps(data, ensure_ascii=False) + "\n")
    stream.flush()
