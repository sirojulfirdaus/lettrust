# ai-eval — Evaluasi AI Lettrust

Owner: B (PIC 5) · Status: COMPLETE (dokumentasi; evaluasi belum lengkap) · Ref: PRD FR-05.12, §10.4; SA §7.8, §7.9

Tooling dataset dan evaluasi pipeline AI. Protokol: [`docs/evaluation/protocol.md`](../docs/evaluation/protocol.md).

| Path | Isi |
| ----- | ----- |
| `templates/` | Format surat LOW/MEDIUM/HIGH; 18 surat Indonesia tersedia, bagian Inggris menunggu T4-03 |
| `dataset/manifest.csv` | `id, split, lang, format, label, indicators, file, sha256` |
| `dataset/pdf/` | PDF dataset (dibuat `generate_pdfs.py` / `make_scans.py`) |
| `scripts/generate_pdfs.py`, `scripts/make_scans.py` | COMPLETE: generator PDF teks/scan deterministik; mode parsial memakai `--languages id` |
| `scripts/generate_fixtures.py` | COMPLETE: entry point T5-06 yang memanggil `../fixtures/fixture_builder.py` dengan renderer T5-05; mendukung `--check` dan `--test` |
| `scripts/freeze_testset.py`, `baseline.py`, `run_eval.py`, `metrics.py` | STUB: tooling evaluasi lanjutan, belum boleh dipakai untuk menyatakan hasil test set |
| `results/<timestamp>/` | `raw.jsonl`, `metrics.json`, `confusion.csv`, `run_config.json` |

Menjalankan tooling yang tersedia dari root repository (di image `ai-service`, `ai-eval/` dan `fixtures/` ter-mount):

```
python scripts/dev.py eval generate_pdfs --languages id
python scripts/dev.py eval make_scans --languages id
python scripts/dev.py eval test_dataset
python scripts/dev.py eval generate_fixtures
python scripts/dev.py eval generate_fixtures --check
python scripts/dev.py eval generate_fixtures --test
```

Cara memakai fixture, checksum, test validator backend, dan hasil skenario yang diharapkan dijelaskan di [fixtures/README.md](../fixtures/README.md). FX-01–FX-10 dibuat mandiri dan bukan tambahan dev/test set.

**T5-05 masih parsial:** tersedia 36 PDF Indonesia (18 teks/18 scan; 12 dev/24 test) dari target 72. Dataset belum final: menunggu tinjauan manusia per surat oleh Pash, identitas model bantu yang dapat diverifikasi, dan bagian Inggris T4-03. Nama “Gemini Neon” yang dicatat saat ini belum merupakan ID model yang dapat diperiksa.

Sebelum ketiga prasyarat tersebut selesai, jangan menjalankan `freeze_testset`, menyatakan T5-05 selesai, atau menggunakan hasil test split sebagai metrik laporan. Jika tinjauan manusia mengubah sumber surat, tinjau dan regenerasi pasangan PDF serta baris manifest yang terdampak sebelum freeze. Penambahan fixture T5-06 tidak menutup prasyarat tersebut.

Aturan evaluasi berikut berlaku setelah prasyarat dipenuhi: penyesuaian prompt/ambang hanya pada dev set; test set dibekukan (checksum) sebelum penyesuaian final dan tidak dipakai untuk tuning; catat model ID, versi prompt, dan output mentah; laporkan hasil aktual termasuk kegagalan. Baseline aturan hanya untuk evaluasi, bukan fallback runtime. Seluruh data sintetis. `run` merupakan alias `run_eval.py` pada launcher, bukan implementasi evaluasi terpisah.
