# ai-eval — Evaluasi AI Lettrust

Owner: B (PIC 5) · Status: COMPLETE (dokumentasi; evaluasi belum lengkap) · Ref: PRD FR-05.12, §10.4; SA §7.8, §7.9

Tooling dataset dan evaluasi pipeline AI. Protokol: [`docs/evaluation/protocol.md`](../docs/evaluation/protocol.md).

| Path | Isi |
| ----- | ----- |
| `templates/` | 36 surat sintetis LOW/MEDIUM/HIGH: 18 Indonesia dan 18 Inggris |
| `dataset/manifest.csv` | `id, split, lang, format, label, indicators, file, sha256` |
| `dataset/pdf/` | 72 PDF: 36 teks dan 36 scan; 24 dev/48 test |
| `scripts/generate_pdfs.py`, `scripts/make_scans.py` | COMPLETE: generator PDF teks/scan deterministik; mode parsial memakai `--languages id` |
| `scripts/generate_fixtures.py` | COMPLETE: entry point T5-06 yang memanggil `../fixtures/fixture_builder.py` dengan renderer T5-05; mendukung `--check` dan `--test` |
| `scripts/baseline.py`, `scripts/_eval_schema.py` | COMPLETE: baseline regex ID/EN dan kontrak hasil evaluasi v1; CLI pengembangan hanya memproses dev |
| `scripts/run_eval.py`, `scripts/_eval_records.py` | COMPLETE: runner dev pipeline/baseline dengan kontrak hasil v1, pemeriksaan split, dan artefak atomik |
| `scripts/freeze_testset.py` | COMPLETE: tooling checksum dan pemeriksaan prasyarat; freeze aktual belum dilakukan |
| `scripts/metrics.py` | STUB: menunggu implementasi T4-07 oleh Pash sesuai PLAN |
| `results/<timestamp>/` | Run lengkap: `raw.jsonl`, `model_outputs.jsonl`, `run_config.json`; `metrics.json`/`confusion.csv` final belum tersedia |

Menjalankan tooling yang tersedia dari root repository (di image `ai-service`, `ai-eval/` dan `fixtures/` ter-mount):

```
python scripts/dev.py eval generate_pdfs
python scripts/dev.py eval make_scans
python scripts/dev.py eval test_dataset
python scripts/dev.py eval generate_fixtures
python scripts/dev.py eval generate_fixtures --check
python scripts/dev.py eval generate_fixtures --test
python scripts/dev.py eval baseline --split dev --check
python scripts/dev.py eval baseline --split dev
python scripts/dev.py eval run_eval --test
python scripts/dev.py eval run_eval --split dev --variants pipeline baseline --dry-run
python scripts/dev.py eval run_eval --split dev --variants baseline
python scripts/dev.py eval freeze_testset --check
```

Cara memakai fixture, checksum, test validator backend, dan hasil skenario yang diharapkan dijelaskan di [fixtures/README.md](../fixtures/README.md). FX-01–FX-10 dibuat mandiri dan bukan tambahan dev/test set.

**T5-05 lengkap:** tersedia 72 PDF dari 36 surat ID/EN, dengan manifest delapan kolom dan pasangan teks/scan pada split yang sama. Pengguna mengonfirmasi pada 26 November 2026 bahwa review manusia seluruh 18 surat ID oleh Pash dan 18 surat EN oleh Van sudah selesai. Identitas snapshot sumber, konfirmasi review, dan provenance model bantu dicatat di [protocol.md §1–§2](../docs/evaluation/protocol.md#1-dataset). Notes lama pada templat milik Van/Pash tidak diubah; konfirmasi ini bukan klaim bahwa coding agent melakukan review manusia.

**T5-08/T5-09 belum final:** dataset belum dibekukan dan belum ada run LLM pada test split. Preflight dengan konfirmasi review/checksum menyisakan `T4_07_NOT_AVAILABLE`; `--check` hanya memeriksa metadata/prasyarat, tanpa membuka PDF atau membuat snapshot. Tunggu metrics Pash, persetujuan pilihan model, dan verifikasi integrasi sebelum freeze/run final. Hasil dev tidak digunakan sebagai metrik laporan test set. Jika sumber surat berubah, tinjau dan regenerasi pasangan PDF serta baris manifest yang terdampak sebelum freeze.

Aturan evaluasi berikut berlaku setelah prasyarat dipenuhi: penyesuaian prompt/ambang hanya pada dev set; test set dibekukan (checksum) sebelum penyesuaian final dan tidak dipakai untuk tuning; catat model ID, versi prompt, dan output mentah; laporkan hasil aktual termasuk kegagalan. Baseline aturan hanya untuk evaluasi, bukan fallback runtime. Seluruh data sintetis. `run` merupakan alias `run_eval.py` pada launcher, bukan implementasi evaluasi terpisah.

## Baseline T6-05 dan format hasil bersama

Baseline mendeteksi tujuh indikator melalui pola ID/EN dengan pengecualian per klausa, mengambil evidence dari kalimat asli, lalu memakai validator, skoring, dan komposisi API-08 yang sama dengan runtime. Ini baseline kata kunci; angka gaji tidak dipakai untuk menyimpulkan kewajaran dan nama perusahaan tidak dibandingkan secara semantik. `analyze_text(text)` dapat dipakai B dari `run_eval.py` setelah ekstraksi, tanpa memanggil LLM.

`--check` menjalankan ekstraksi/OCR asli pada PDF dev dan memvalidasi checksum, tanpa menulis hasil. Tanpa flag itu, `--output <direktori-baru>` memilih lokasi run; default `results/<UTC>-baseline/`. Hasilnya `raw.jsonl` dan `run_config.json`, bukan metrik. Direktori lama dan output di dalam dataset ditolak. Kegagalan dokumen tetap dicatat sebagai UNAVAILABLE dengan result null dan exit code 1. PDF test tidak dibuka; CLI menolak `--split test` selama pengembangan.

Kontrak yang harus dipakai **B (T5-07/T5-08), Pash (T4-07), dan Sat (T6-05)** ada di [protocol.md §6](../docs/evaluation/protocol.md#6-kontrak-output-evaluasi-v1), dengan model bersama `scripts/_eval_schema.py`. Runner dan baseline sudah memakai `schemaVersion, id, variant, status, result, extraction, error, latencyMs`. Hasil sukses berstatus `OK` dengan respons API-08 lengkap; kegagalan `UNAVAILABLE` memiliki `result=null` dan error terstruktur. Kode indikator dibaca dari `result.indicatorDetails`, bukan teks tampilan `result.indicators`. `metrics.py` masih menunggu Pash. Bukti T5-07 awal dipertahankan dalam format historisnya; tidak dimigrasikan atau diperlakukan sebagai record v1.

## Runner dev dan hasil terkini

`run_eval --variants pipeline baseline` menjalankan kedua varian secara eksplisit, masing-masing melalui ekstraksi runtime dengan pengaturan sama. Baseline tidak membangun provider atau memanggil LLM. `--output-dir <direktori-baru>` menentukan lokasi run; direktori yang sudah ada atau berada di dalam dataset ditolak. `--split test` tetap ditolak. `--dry-run` memeriksa pemilihan dev tanpa panggilan LLM atau menulis hasil run.

Contoh run nyata berikut memakai key B yang sudah tersedia di environment container; jangan mengirim key ke percakapan atau menaruhnya di argumen perintah:

```sh
python scripts/dev.py eval run_eval --split dev --variants pipeline baseline --interval-seconds 25
```

Konfigurasi berstatus `RUNNING` selama proses. Raw dan output model disimpan di `tmp/` sampai seluruh dokumen/varian dicoba dan checksum manifest tetap sama; lalu berkas diterbitkan atomik dan konfigurasi menjadi `COMPLETE`. COMPLETE dapat mencakup kegagalan dokumen yang tercatat. Error kuota/provider/timeout menghentikan run, mempertahankan bukti parsial di `tmp/` dan status RUNNING; pembaca metrics harus menolaknya. Tidak ada record atau latensi fiktif bagi dokumen yang belum dicoba, retry provider, atau fallback otomatis. Output model mentah hanya disimpan sebagai artefak data sintetis, bukan log aplikasi.

Folder `results/**/tmp/` diabaikan Git. Bukti run GPT-OSS yang terhenti telah disalin identik byte ke `partial_raw.jsonl` dan `partial_model_outputs.jsonl` pada direktori run yang sama; checksum dan konteks tersedia di [protocol.md §7.5](../docs/evaluation/protocol.md#75-koreksi-bukti-parsial-dan-review-t5-07-26-november). Salinan ini terlihat oleh Git untuk audit, tetapi bukan `raw.jsonl` run lengkap dan tidak boleh dipakai sebagai input metrics final. `RUNNING` disertai `stopReason`/`stoppedAt` menandai run tidak lengkap yang sudah berhenti; enum lifecycle bersama tetap mengikuti protokol §6.

Hasil dev ID/EN tanggal 26 November ada di [protocol.md §7.4](../docs/evaluation/protocol.md#74-dev-iden-lengkap-dan-usulan-pilihan-model-26-november): Qwen menyelesaikan 24/24 PDF, kategori sesuai 24/24 dan himpunan indikator sesuai 20/24; baseline 24/24 berhasil diproses, kategori sesuai 12/24 dan himpunan indikator 6/24. GPT-OSS berhenti pada dokumen keempat dengan `AI_PROVIDER_ERROR`, sehingga tidak dibandingkan sebagai run lengkap. Ini diagnostik dev, bukan metrik test final atau bukti bahwa satu model selalu lebih baik.

Dws menyetujui Qwen melalui konfirmasi pengguna pada 26 November 2026. Default `LLM_MODEL` pada `.env.example`, konfigurasi ai-service, dan fallback Compose kini konsisten `qwen/qwen3.8-27b`, tetap melalui Groq. Nilai `LLM_MODEL` yang sudah ditetapkan operator mengalahkan default tersebut; operator perlu memperbaruinya sendiri dan membuat ulang container ai-service bila ingin menerapkan pilihan baru. `.env` tidak diakses oleh agent. Override eksperimen `--model` tidak mengganti konfigurasi layanan dan tidak ada fallback otomatis. Pengguna juga mengonfirmasi pada 26 November bahwa pilihan terbaru sudah diumumkan B ke tim; kriteria implementasi T5-07 lengkap. Draf laporan berada di [report.md](../docs/evaluation/report.md) dan belum menyatakan MET-09–MET-15 final.

Jika user non-root di image tidak dapat menulis bind mount Linux, jalankan container dengan UID/GID pemilik workspace, tanpa mengubah launcher/file bersama atau permission seluruh repository:

```bash
docker compose run --rm --no-deps -T --user "$(id -u):$(id -g)" -v "$PWD/ai-eval:/ai-eval" -v "$PWD/fixtures:/fixtures" ai-service python /ai-eval/scripts/baseline.py --split dev
docker compose run --rm --no-deps -T -v "$PWD/ai-eval:/ai-eval:ro" ai-service python -m pytest -q -p no:cacheprovider --tb=no /ai-eval/scripts/test_baseline.py
```
