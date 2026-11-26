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
| `scripts/baseline.py`, `scripts/_eval_schema.py` | COMPLETE: baseline regex ID/EN dan kontrak hasil evaluasi v1; CLI pengembangan hanya memproses dev |
| `scripts/run_eval.py`, `scripts/_eval_records.py` | COMPLETE: pemilihan model T5-07 hanya pada dev; format terdahulu belum mengikuti kontrak bersama §6 |
| `scripts/freeze_testset.py` | STUB: pembekuan checksum test set belum tersedia |
| `scripts/metrics.py` | COMPLETE: menghasilkan `metrics.json` dan `confusion.csv`; 9 test sintetis lulus. Belum ada metrik final dari test set. |
| `results/<timestamp>/` | `raw.jsonl`, `metrics.json`, `confusion.csv`, `run_config.json` |

Menjalankan tooling yang tersedia dari root repository (di image `ai-service`, `ai-eval/` dan `fixtures/` ter-mount):

```
python scripts/dev.py eval generate_pdfs --languages id
python scripts/dev.py eval make_scans --languages id
python scripts/dev.py eval test_dataset
python scripts/dev.py eval generate_fixtures
python scripts/dev.py eval generate_fixtures --check
python scripts/dev.py eval generate_fixtures --test
python scripts/dev.py eval baseline --split dev --check
python scripts/dev.py eval baseline --split dev
python scripts/dev.py eval metrics /ai-eval/results/<nama-run> --dataset-dir /ai-eval/dataset
python scripts/dev.py eval metrics --test
```

Cara memakai fixture, checksum, test validator backend, dan hasil skenario yang diharapkan dijelaskan di [fixtures/README.md](../fixtures/README.md). FX-01–FX-10 dibuat mandiri dan bukan tambahan dev/test set.

**T5-05 masih parsial:** tersedia 36 PDF Indonesia (18 teks/18 scan; 12 dev/24 test) dari target 72. Identitas model bantu Indonesia sudah dicatat dari metadata Van di [protocol.md §2](../docs/evaluation/protocol.md#2-label-dan-pembuatan-data). Dataset belum final: tinjauan manusia per surat oleh Pash serta data Inggris dan provenance model bantunya masih menunggu.

Sebelum seluruh prasyarat tersebut selesai, jangan menjalankan `freeze_testset`, menyatakan T5-05 selesai, atau menggunakan hasil test split sebagai metrik laporan. Jika tinjauan manusia mengubah sumber surat, tinjau dan regenerasi pasangan PDF serta baris manifest yang terdampak sebelum freeze. Penambahan fixture T5-06 tidak menutup prasyarat tersebut.

Aturan evaluasi berikut berlaku setelah prasyarat dipenuhi: penyesuaian prompt/ambang hanya pada dev set; test set dibekukan (checksum) sebelum penyesuaian final dan tidak dipakai untuk tuning; catat model ID, versi prompt, dan output mentah; laporkan hasil aktual termasuk kegagalan. Baseline aturan hanya untuk evaluasi, bukan fallback runtime. Seluruh data sintetis. `run` merupakan alias `run_eval.py` pada launcher, bukan implementasi evaluasi terpisah.

## Baseline T6-05 dan format hasil bersama

Baseline mendeteksi tujuh indikator melalui pola ID/EN dengan pengecualian per klausa, mengambil evidence dari kalimat asli, lalu memakai validator, skoring, dan komposisi API-08 yang sama dengan runtime. Ini baseline kata kunci; angka gaji tidak dipakai untuk menyimpulkan kewajaran dan nama perusahaan tidak dibandingkan secara semantik. `analyze_text(text)` dapat dipakai B dari `run_eval.py` setelah ekstraksi, tanpa memanggil LLM.

`--check` menjalankan ekstraksi/OCR asli pada PDF dev dan memvalidasi checksum, tanpa menulis hasil. Tanpa flag itu, `--output <direktori-baru>` memilih lokasi run; default `results/<UTC>-baseline/`. Hasilnya `raw.jsonl` dan `run_config.json`, bukan metrik. Direktori lama dan output di dalam dataset ditolak. Kegagalan dokumen tetap dicatat sebagai UNAVAILABLE dengan result null dan exit code 1. PDF test tidak dibuka; CLI menolak `--split test` selama pengembangan.

Kontrak yang harus dipakai **B (T5-07/T5-08), Pash (T4-07), dan Sat (T6-05)** ada di [protocol.md §6](../docs/evaluation/protocol.md#6-kontrak-output-evaluasi-v1), dengan model bersama `scripts/_eval_schema.py`. Baseline sudah memakai kontrak tersebut. `metrics.py` (T4-07) COMPLETE dan memiliki adapter untuk output legacy T5-07 serta kontrak v1, termasuk validasi subset ID/checksum dan lifecycle run. Runner T5-07 saat ini masih mengeluarkan format legacy dan hanya menjalankan dev; B perlu menyelaraskannya sebelum evaluasi final gabungan. Protokol berstatus DRAF, dengan hasil dev dan keputusan sementara di [§7](../docs/evaluation/protocol.md#7-hasil-aktual-dan-keputusan). Bukti T5-07 dipertahankan dalam format asal. Belum ada hasil evaluasi final atau klaim kinerja test set.

Jika user non-root di image tidak dapat menulis bind mount Linux, jalankan container dengan UID/GID pemilik workspace, tanpa mengubah launcher/file bersama atau permission seluruh repository:

```bash
docker compose run --rm --no-deps -T --user "$(id -u):$(id -g)" -v "$PWD/ai-eval:/ai-eval" -v "$PWD/fixtures:/fixtures" ai-service python /ai-eval/scripts/baseline.py --split dev
docker compose run --rm --no-deps -T -v "$PWD/ai-eval:/ai-eval:ro" ai-service python -m pytest -q -p no:cacheprovider --tb=no /ai-eval/scripts/test_baseline.py
```
