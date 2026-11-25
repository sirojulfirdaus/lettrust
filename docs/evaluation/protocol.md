# Protokol Evaluasi AI Lettrust (STUB)

Owner: B (PIC 5) · Status: STUB · Ref: PRD §10.4, FR-05.12, BR-04.13, BR-04.14; SA §7.9

> Bagian 1–5 masih kerangka yang wajib dilengkapi B sebelum evaluasi final. Bagian 6 menetapkan kontrak output v1 atas arahan Sat pada T6-05 (25 November 2026). Tidak ada angka hasil yang boleh ditulis tanpa pengukuran nyata.

## 1. Dataset

TODO: komposisi final (kategori × bahasa × format), jumlah per kelas, pembagian dev/test (OI-02), dan batasan dataset. Target awal PRD: 72 dokumen (≈24 dev, ≈48 test).

## 2. Label dan Pembuatan Data

TODO: sumber dan cara pembuatan data, skema label, label indikator referensi, peninjau label (anggota selain pengembang prompt), cara pembuatan PDF scan, dan pernyataan identitas fiktif.

## 3. Prosedur

TODO: langkah tuning pada dev set, pembekuan test set (checksum), satu kali run pipeline AI dan baseline pada test set, parameter yang dicatat (model ID, tanggal, parameter, `PROMPT_VERSION`), lokasi output mentah, dan perhitungan metrik oleh skrip.

## 4. Interpretasi

TODO: nyatakan bahwa kategori diturunkan dari indikator melalui aturan sehingga metrik klasifikasi terutama mencerminkan deteksi indikator dan validasi kutipan; analisis kualitatif kesalahan klasifikasi.

## 5. Log Perubahan Ambang dan Prompt

TODO: setiap perubahan ambang skoring, `EVIDENCE_FUZZY_THRESHOLD`, OCR, atau prompt beserta alasan dan bukti dari dev set.

## 6. Kontrak output evaluasi v1

Kontrak ini berlaku bagi `baseline.py` (Sat, T6-05), `run_eval.py` (B, T5-07/T5-08), dan `metrics.py` (Pash, T4-07). Format bersama ditetapkan di T6-05 karena producer pipeline dan pembaca metrik masih STUB. B/Pash harus memakai kontrak ini ketika mengimplementasikan keduanya. Kontrak ini bukan perubahan API publik dan tidak menyelesaikan keputusan dataset, pemilihan model, freeze, atau metrik yang masih terbuka di bagian 1–5.

Sumber skema yang dapat dieksekusi: `ai-eval/scripts/_eval_schema.py`, kelas `EvaluationRecord`. Serialisasi memakai `model_dump_json(by_alias=True)`; pembaca memakai `EvaluationRecord.model_validate_json(line)`. Kunci JSON memakai camelCase. Satu baris UTF-8 dalam `raw.jsonl` adalah satu objek lengkap, tanpa baris kosong. Pasangan `(variant, id)` harus unik dalam satu run. Kandidat model pipeline yang berbeda disimpan pada direktori run yang berbeda.

| Field | Ketentuan |
| ----- | ----- |
| `schemaVersion` | Integer `1`; pembaca menolak versi yang tidak didukung. |
| `id` | ID dokumen yang tepat sama dengan `manifest.csv`; join referensi kategori/indikator, bahasa, dan format memakai ID ini. |
| `variant` | `baseline` atau `pipeline`; metrik kedua varian tidak boleh tercampur. |
| `status` | `OK` atau `UNAVAILABLE`. |
| `result` | Respons `RiskAnalysisResponse` API-08 lengkap bila OK, atau `null` bila gagal. `category` tetap dihitung dari indikator memakai `scoring.py`. |
| `extraction` | Metadata I-01 **tanpa field `text`**: `status`, `method`, `pagesTotal`, `pagesProcessed`, `truncated`, `language`, `reasonDetail`; `null` bila gagal sebelum metadata tersedia. |
| `error` | `null` bila OK; bila gagal, `{stage, code, reasonDetail}`. `stage` adalah `INPUT`, `EXTRACTION`, atau `ANALYSIS`; kode stabil, tanpa pesan exception/provider atau payload mentah. |
| `latencyMs` | Integer ≥ 0: waktu total per dokumen, mulai pembacaan/checksum PDF sampai ekstraksi dan analisis selesai. `result.meta.latencyMs` tetap latency tahap analisis menurut implementasi masing-masing. |

Untuk metrik, kategori berada di `result.category`; kode indikator berada di `result.indicatorDetails[].code`. `result.indicators[]` berisi teks tampilan, bukan daftar kode. Model/versi prompt tersedia di `result.meta.model` dan `result.meta.promptVersion`. Baseline memakai model `rule-based-baseline` dan versi aturan `rules-v1`.

`OK` memerlukan ekstraksi OK, `result` lengkap, dan `error=null`. `UNAVAILABLE` memerlukan `result=null` dan error terstruktur; jangan mengubah kegagalan menjadi LOW atau membuang record kegagalan. Pembaca harus melaporkan jumlah gagal/coverage secara terpisah; definisi penyebut metrik final tetap disepakati B/Pash di protokol. Label/indikator referensi tidak disalin ke input detektor atau dipakai untuk menentukan prediksi.

Kode baseline: `DOCUMENT_READ_ERROR`/`CHECKSUM_MISMATCH` pada INPUT; `EXTRACTION_FAILED`/`EXTRACTION_NO_CONTENT` pada EXTRACTION; `ANALYSIS_INVALID` pada ANALYSIS. `reasonDetail` memakai enum I-01 bila tersedia (`PDF_UNREADABLE` atau `NO_EXTRACTABLE_TEXT`). Producer pipeline dapat memakai kode `AI_*` yang sudah didefinisikan ai-service pada tahap ANALYSIS.

Contoh kegagalan sintetis berikut hanya menjelaskan format, bukan hasil evaluasi:

```json
{"schemaVersion":1,"id":"example-only","variant":"baseline","status":"UNAVAILABLE","result":null,"extraction":null,"error":{"stage":"INPUT","code":"CHECKSUM_MISMATCH","reasonDetail":null},"latencyMs":1}
```

Setiap direktori run memuat `raw.jsonl` dan `run_config.json`. Konfigurasi memuat `schemaVersion`, `status` (`RUNNING`/`COMPLETE`), `variants`, `split`, `startedAt`, `finishedAt`, `manifestSha256`, `languages`, `formats`, whitelist parameter non-rahasia dalam `settings`, serta jumlah `records` dan `counts` saat selesai. Baseline juga merekam `baselineVersion`, `model`, dan checksum kode `baseline`, `scoring`, `taxonomy` dalam `sourceSha256`. B menambahkan identitas model/prompt dan parameter pipeline yang diperlukan tanpa menyalin token, API key, atau seluruh objek Settings.

Producer tidak menimpa run lama dan memastikan manifest tidak berubah selama pemrosesan. File sementara berada di subfolder `tmp/`; `raw.jsonl` dipindahkan atomik setelah semua dokumen dicoba, kemudian konfigurasi ditandai COMPLETE. COMPLETE berarti seluruh dokumen sudah dicoba, termasuk record UNAVAILABLE. Pembaca menolak run belum COMPLETE, jumlah record yang tidak sesuai, duplikat `(variant,id)`, atau checksum manifest yang berbeda. CLI baseline keluar 1 bila ada dokumen gagal, tetapi tetap menyimpan seluruh record kegagalannya.

Evidence sintetis boleh disimpan dalam artefak hasil evaluasi; teks dokumen lengkap tidak digandakan dalam metadata. Output console hanya ringkasan jumlah dan lokasi run, tanpa teks surat, kutipan, token, atau keluaran provider mentah. Jika audit T5-08 membutuhkan completion provider mentah, B menyimpannya terpisah dalam artefak run dengan aturan data sintetis dan tanpa secret, bukan pada stdout/log aplikasi.

CLI baseline hanya menerima dev selama pengembangan. Untuk run final T5-08 setelah freeze, B dapat memanggil `baseline.analyze_text(extracted.text)` dan membungkus responsnya dengan `EvaluationRecord(variant="baseline", ...)`. Jangan mengaktifkan baseline sebagai fallback runtime. Perubahan kontrak harus memperbarui skema, contoh/tes sintetis, dan dokumentasi ini serta dikoordinasikan ke ketiga owner.
