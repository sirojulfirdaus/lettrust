# ai-eval — Evaluasi AI Lettrust

Owner: B (PIC 5) · Status: STUB · Ref: PRD FR-05.12, §10.4; SA §7.8, §7.9

Tooling dataset dan evaluasi pipeline AI. Protokol: [`docs/evaluation/protocol.md`](../docs/evaluation/protocol.md).

| Path | Isi |
| ----- | ----- |
| `templates/` | Templat surat dan variasi (ID/EN, LOW/MEDIUM/HIGH) |
| `dataset/manifest.csv` | `id, split, lang, format, label, indicators, file, sha256` |
| `dataset/pdf/` | PDF dataset (dibuat `generate_pdfs.py` / `make_scans.py`) |
| `scripts/` | `generate_pdfs`, `make_scans`, `freeze_testset`, `baseline`, `run_eval`, `metrics` (semua STUB) |
| `results/<timestamp>/` | `raw.jsonl`, `metrics.json`, `confusion.csv`, `run_config.json` |

Menjalankan (di image `ai-service`, `ai-eval/` dan `fixtures/` ter-mount):

```
python scripts/dev.py eval run_eval --split dev
python scripts/dev.py eval run --split test      # alias run_eval.py
```

Aturan: penyesuaian prompt/ambang hanya pada dev set; test set dibekukan (checksum) dan tidak dipakai untuk tuning; catat model ID, versi prompt, dan output mentah; laporkan hasil aktual termasuk kegagalan. Baseline aturan hanya untuk evaluasi, bukan fallback runtime. Seluruh data sintetis.
