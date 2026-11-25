# Protokol Evaluasi AI Lettrust

Owner: B (PIC 5) · Status: T5-05 lengkap; hasil dev T5-07 tersedia; final T5-08 menunggu T4-07 · Reviewer: Dws · Ref: PRD §10.4, FR-05.12, BR-04.13, BR-04.14; SA §7.4.1, §7.9

Dokumen ini menetapkan prosedur uji dev T5-07 dan format artefak bersama B, Sat (baseline T6-05), dan Pash (metrics T4-07). Hasil awal bukan metrik test set atau penutupan OI-01/OI-02. Freeze dan evaluasi final T5-08 belum diizinkan.

Bagian 6 menetapkan kontrak output bersama v1 dari T6-05; bagian 7 mempertahankan hasil nyata T5-07. Artefak run awal tetap memakai format historis §3.3. Runner baru mengikuti §6, sedangkan integrasi metrics masih menunggu T4-07. Tidak ada angka hasil yang boleh ditulis tanpa pengukuran nyata.

## 1. Dataset

Pada run awal T5-07 tersedia 18 surat Indonesia dalam 36 PDF (12 dev/24 test). Setelah T4-03 merge, pelengkapan T5-05 tanggal 26 November 2026 menghasilkan 72 PDF dari 36 surat ID/EN: 36 teks dan 36 scan, terbagi 24 dev/48 test secara seimbang per bahasa, kategori, dan format. Manifest memuat delapan kolom SA §7.9; pasangan teks/scan dari surat yang sama selalu satu split. Jumlah ini sesuai target awal PRD §10.4.1 dan PLAN; OI-02 tidak ditutup sepihak oleh agent.

Runner T5-07 hanya menerima `--split dev`. Ia memvalidasi ID dan split seluruh metadata manifest terlebih dahulu; pasangan teks/scan dari satu ID surat dengan split berbeda ditolak sebelum PDF apa pun diakses, termasuk saat memakai `--limit`. Setelah metadata lolos, ia memeriksa path dan SHA-256 PDF dev saja. Runner tidak membuka PDF test atau mengirimkannya ke LLM. QA generator seluruh PDF dijelaskan terpisah di §7.3 dan tidak dipakai untuk tuning. `--limit` hanya untuk smoke test dan selalu dicatat melalui daftar dokumen pada `run_config.json`.

Dataset belum dibekukan dan hasil dev tidak menjadi metrik test set laporan. Pengguna mengonfirmasi pada 26 November 2026 bahwa review manusia seluruh 18 surat ID oleh Pash dan 18 surat EN oleh Van sudah selesai. Data EN dan provenance yang dilaporkan penulis kini tersedia. Catatan lama “belum dikonfirmasi/menunggu tinjauan” masih ada pada berkas templat milik Van/Pash; konfirmasi pengguna ini dicatat terpisah, tanpa mengubah berkas mereka atau mengklaim agent melakukan review manusia. Freeze dan evaluasi final tetap menunggu metrics T4-07 serta verifikasi integrasi T5-08.

Konfirmasi tersebut berlaku untuk snapshot sumber berikut; perubahan teks/anotasi sesudahnya memerlukan review dan regenerasi pasangan terkait:

| Templat | SHA-256 berkas |
| --- | --- |
| `en-high.json` | `d79db73cc3d5688f3e4c4ff43b13d4876a773a8a27fe764c456711e174dd8492` |
| `en-low.json` | `1ec8a6974eae7bddae49c78806574822a07d0fdce9267605275ccc2c1482242b` |
| `en-medium.json` | `cac9a55ffa7f8c1e6f4f1cd5a6ee05387050fd237b0478edba52792ade451649` |
| `id-high.json` | `a81c6d00aa850b95c0fe13ae1d6610911415c971e2787e0bc6d9985aa07bc87a` |
| `id-low.json` | `1446be55bbd0b65983b6e7e8f61f55c358633dd4067417374ba7636bbf662c65` |
| `id-medium.json` | `bc2cf570820671e5a53d17df0b1ad12f30bf444f8b68c860385f85af82cf0a97` |

Checksum manifest 72 PDF: `e7cb70b0e2a0e99a06be30c064903c2eff5baf79f3c8741357423c8edb7f86fb`. Pencatatan ini merupakan identitas data T5-05, bukan snapshot freeze T5-08.

## 2. Label dan Pembuatan Data

Penulis surat Indonesia: Van (T2-04), peninjau manusia yang ditetapkan: Pash. Seluruh identitas dan kontak dikonfirmasi pengguna sebagai data sintetis. Label kategori dan daftar kode indikator berasal dari manifest dan harus sesuai PRD §8.4–§8.5; kategori bukan vonis asli/palsu. Anotasi referensi dan notes tidak masuk prompt.

Provenance model bantu berdasarkan cuplikan metadata tersanitasi yang disampaikan Van melalui pengguna:

- Model executor penulis `id-low.json`, `id-medium.json`, `id-high.json`: `gemini-4-neon-medium` (Google Gemini 4 Neon, thinking level Medium).
- Parent: `87006406-f64c-40b3-8aa7-7429b0aa0d2b`, spawn `2026-11-22T15:11:12Z` (22:11:12 WIB).
- Executor T2-04: `f7da1ac1-0a0f-4915-ac29-648b082c855c`, aktif `2026-11-22T15:11:41Z` sampai `2026-11-22T15:17:46Z`.
- Metadata penulisan tiga berkas: `write_file`, step 6, `2026-11-22T15:12:22Z`; `models_used` executor hanya `gemini-4-neon-medium`.
- Sumber: cuplikan `transcript.jsonl`, field `model` dan ringkasan executor. Log lokal penuh tidak tersedia di repository dan tidak diklaim telah diperiksa langsung oleh B.

Tiga surat ID (MEDIUM-03, MEDIUM-06, HIGH-05) kemudian diperjelas dengan bantuan Codex (keluarga GPT-6) setelah koordinasi Van. Konfirmasi review Pash pada §1 mencakup versi ini. Untuk EN, notes T4-03 mencatat penulis Pash, peninjau Van, dan bantuan OpenAI GPT-6 (Codex) untuk koreksi format/metadata LOW serta anotasi kutipan MEDIUM/HIGH. Identitas itu dicatat sesuai laporan penulis, tanpa mengarang ID varian tambahan. Model bantu yang dilaporkan berbeda dari kedua kandidat evaluasi (`openai/gpt-oss-120b`, `qwen/qwen3.8-27b`); pemeriksaan ini diulang bila kandidat berubah.

PDF teks memakai ReportLab dengan font Unicode bawaan; scan memakai PDFium dan Pillow, seed 20261121, render 200 DPI, rotasi kecil dan derau ringan, tanpa text layer. Generator tidak menyisipkan label/notes dalam PDF. SHA-256 dihitung dari byte PDF asli. Fixture FX-01–FX-10 terpisah dari dataset ini dan tidak dipakai untuk memilih model.

## 3. Prosedur

### 3.1 Kandidat dan parameter awal

Dua kandidat awal SA §7.4.1: `openai/gpt-oss-120b` dan `qwen/qwen3.8-27b` melalui Groq. Endpoint daftar model telah diperiksa dari container: keduanya tersedia untuk akun yang digunakan. Ketersediaan gratis/kuota mengikuti akun B; tidak memakai akun atau key anggota lain. Tidak ada pergantian provider/model otomatis saat gagal.

Kedua model mendukung JSON mode menurut [dokumentasi Groq](https://console.groq.com/docs/models); [Qwen 3.8 27B](https://console.groq.com/docs/model/qwen/qwen3.8-27b) berstatus preview. Base URL tetap konfigurasi layanan. Parameter awal: temperature 0, JSON object mode, max output 900, reasoning effort tidak dikirim (default provider), prompt v1, timeout 40 detik. Pemeriksaan `finish_reason=length` diperlukan karena budget output juga dapat habis oleh reasoning. Dukungan reasoning dan parameter diperiksa pada [referensi API Groq](https://console.groq.com/docs/api-reference).

Ambang awal runtime dipertahankan sebelum ada bukti dev: OCR minimum 25 karakter per halaman, 300 DPI, timeout halaman 20 detik; total minimum 40 karakter; maksimal lima halaman/12000 karakter; fuzzy 90 hanya OCR/MIXED, TEXT_LAYER memakai substring ketat. Perubahan eksperimen disimpan per run, bukan langsung ditulis ke konfigurasi layanan.

### 3.2 Urutan pemilihan dan guard

1. Jalankan unit test dan `--dry-run` tanpa panggilan model.
2. Smoke test satu PDF dev dengan konfigurasi awal untuk setiap kandidat. Bila hasil terpotong/invalid, catat semua attempt dan event length, lalu tetapkan revisi parameter secara eksplisit berdasarkan bukti dev.
3. Bandingkan kedua kandidat pada daftar PDF dev, urutan, prompt, ambang OCR/fuzzy, dan parameter yang sama. Jangan memilih dokumen berdasarkan hasil kandidat.
4. Prioritaskan kelengkapan run/JSON valid, ketepatan kategori dan indikator dev, lalu latensi serta ketersediaan provider. Jangan menyembunyikan kegagalan atau menghitung model gagal sebagai LOW. Keputusan tetap sementara selama dataset belum lengkap/ditinjau.
5. SDK tidak me-retry provider; pipeline runtime mengulang hanya output tidak valid sekali. Pada kuota, timeout, unconfigured, atau provider error, runner menghentikan panggilan berikutnya dan mencatat sisa dokumen NOT_PERFORMED. Tidak ada loop pada kuota atau fallback ke baseline/mock.
6. T6-05 menyediakan baseline; T4-07 menyediakan metrics. Keduanya masih STUB pada awal T5-07. Baseline kini COMPLETE beserta kontrak §6. Runner baru mendukung varian pipeline/baseline pada dev; metrics masih STUB, sehingga integrasi pembaca metrik dan hasil final belum diklaim.
7. Setelah seluruh prasyarat selesai, T5-08 menambahkan verifikasi freeze dan eksekusi sekali untuk pipeline serta baseline pada test set yang sama. Runner T5-07 saat ini sengaja menolak `--split test` sebelum membaca PDF atau konfigurasi.

### 3.3 Format terdahulu artefak T5-07

Bagian ini mendokumentasikan keluaran runner T5-07 dan artefak hasil aktual di §7. Format tersebut belum mengikuti `EvaluationRecord` pada §6; angka `schemaVersion=1` pada konfigurasi lama tidak membuktikan kesesuaian dengan kontrak bersama v1.

Setiap run memakai direktori baru `ai-eval/results/<run>/`; direktori bukti yang sudah ada tidak ditimpa. Runner T5-07 mencatat `schemaVersion=1` dan `method=llm` pada `run_config.json`. Baseline T6-05 memakai direktori terpisah dan format §6.

`raw.jsonl` berisi satu objek per ID manifest:

| Field | Ketentuan |
| --- | --- |
| `id` | ID dokumen persis seperti manifest |
| `status` | `COMPLETED`, `NOT_PERFORMED`, atau `UNAVAILABLE` |
| `result` | Respons API-08 lengkap dan camelCase, termasuk `indicatorDetails` dan `meta`; null kecuali COMPLETED |
| `extraction` | Metadata I-01 tanpa `text`: status, method, pagesTotal, pagesProcessed, truncated, language, reasonDetail; null bila belum dilakukan |
| `error` | null atau `{stage, code}`; stage `input`, `extraction`, `analysis`, atau `run`; pesan SDK tidak disimpan |
| `latencyMs` | Durasi total baca/ekstraksi/analisis termasuk retry output runtime, tanpa jeda antardokumen; null bila dokumen belum dijalankan |

NO_CONTENT menjadi NOT_PERFORMED dengan kode alasan ekstraksi. Error model menjadi UNAVAILABLE dengan kode API-08 sebenarnya. Kode lokal artefak: FILE_IO_ERROR, DATASET_CHECKSUM_CHANGED, EXTRACTION_FAILED, RUN_ABORTED; bukan penambahan kode kontrak API. Penyebab penghentian run tercatat pada `run_config.stopReason`. Hasil gagal tetap menjadi record dan dilaporkan sebagai coverage/kegagalan oleh metrics, bukan dihapus dari denominator secara diam-diam.

`result.meta.latencyMs` tetap memiliki makna runtime: waktu panggilan model, termasuk retry output. Jangan menyamakannya dengan `raw.latencyMs` end-to-end. Perhitungan per kode indikator memakai `result.indicatorDetails[].code`; `result.indicators[]` adalah string tampilan, bukan daftar enum kode. Baseline harus menandai identitas aturan secara jujur dan tidak mengarang metadata LLM.

`model_outputs.jsonl` menyimpan `{id, attempts}` dengan konten mentah model sintetis, nomor attempt, durasi provider, kode error, dan jumlah event length per attempt. Ini artefak evaluasi, bukan log aplikasi. Input dokumen mentah tidak dicetak atau disalin ke log. Tidak ada key, token, password, atau seluruh Settings pada artefak.

`run_config.json` mencatat timestamp UTC, status run, model/provider, prompt version, parameter, ambang, daftar ID/SHA-256 dev, checksum manifest, fingerprint kode runtime/runner, jumlah status, alasan penghentian, dan event length. Field `settings.baseUrl` pada runner setelah perbaikan review hanya menyimpan origin (`scheme://host[:port]`); seluruh path dihilangkan karena dapat memuat kredensial. URL dengan userinfo, query, atau fragment ditolak. URL lengkap dalam Settings runtime tidak diubah. Tidak ada nilai API key/internal token. `state=interrupted` berarti bukti belum lengkap dan tidak boleh dinyatakan run penuh.

### 3.4 Perintah dan penggantian model

```sh
python scripts/dev.py eval run_eval --test
python scripts/dev.py eval run_eval --split dev --dry-run
python scripts/dev.py eval run_eval --split dev --model openai/gpt-oss-120b --limit 1
python scripts/dev.py eval run_eval --split dev --model qwen/qwen3.8-27b --limit 1
python scripts/dev.py eval run_eval --split dev --model openai/gpt-oss-120b --interval-seconds 25 --output-dir /ai-eval/results/t5-07-20261125-gptoss120b-dev-900
python scripts/dev.py eval run_eval --split dev --model qwen/qwen3.8-27b --interval-seconds 25 --output-dir /ai-eval/results/t5-07-20261125-qwen38-dev-900
```

Tanpa `--limit`, runner memakai seluruh dev. `--output-dir` menetapkan direktori baru; default membuat nama timestamp unik. Dua perintah run lengkap di atas memakai nama artefak aktual; saat mereproduksi, ganti nama direktori agar bukti lama tetap utuh. `--interval-seconds` default 10, sedangkan run lengkap ini memakai jeda 25 detik. Eksperimen dapat mengubah `--max-output-tokens`, `--reasoning-effort`, `--ocr-dpi`, `--ocr-min-chars`, dan `--fuzzy-threshold`. Seluruh nilai efektif dicatat per run. Kuota berlaku per organisasi dan berbagai jendela waktu; ikuti [batas akun Groq](https://console.groq.com/docs/rate-limits), jangan mengulang otomatis setelah 429.

Untuk pergantian model layanan setelah keputusan disetujui: human mengatur environment lokal sendiri, lalu membuat ulang container dan memeriksa health serta panggilan nyata. Jangan membagikan atau mencetak key. Perubahan default `.env.example`, `core/config.py`, atau `compose.yaml` disiapkan hanya bila diperlukan dan memerlukan persetujuan Dws untuk file bersama. Implementasi T5-07 tidak mengubah file tersebut secara otomatis.

## 4. Interpretasi

Kategori diturunkan dari indikator tervalidasi dengan skoring deterministik, bukan label kategori keluaran langsung model. Karena itu, klasifikasi mengukur kemampuan menemukan indikator dan mempertahankan kutipan bukti. Catat indikator yang dibuang, kegagalan parsing, pemotongan, serta salah positif/negatif secara terpisah.

Dataset dev lengkap mencakup ID/EN, tetapi tetap kecil dan mempunyai pasangan teks/scan yang berkorelasi. Run awal pada §7 hanya mencakup Indonesia; hasil awal tersebut tidak membuktikan kemampuan bahasa Inggris atau generalisasi ke surat nyata. Tinjauan coding agent tidak menggantikan review manusia yang dikonfirmasi pada §1. Angka dev hanya untuk keputusan eksperimen, bukan MET-09–MET-15 test set final.

## 5. Log Perubahan Ambang dan Prompt

| Tahap | Parameter | Alasan/status |
| --- | --- | --- |
| Awal T5-07 | Prompt v1; max output 900; reasoning effort default; OCR 25/300 DPI/20 detik; fuzzy 90 | Acuan konfigurasi runtime sebelum uji nyata. Tidak ada perubahan skoring atau prompt. |
| Setelah perbandingan dev 25/11/2026 | Parameter awal dipertahankan; Groq / `openai/gpt-oss-120b` dipilih sementara | Kategori dan himpunan indikator sesuai anotasi dev pada 12/12 PDF; dua output terpotong dipulihkan retry runtime. Ambang belum dikalibrasi untuk variasi scan yang lebih luas. |

## 6. Kontrak output evaluasi v1

Kontrak ini berlaku bagi `baseline.py` (Sat, T6-05), `run_eval.py` (B, T5-07/T5-08), dan `metrics.py` (Pash, T4-07). Format bersama ditetapkan di T6-05. Runner B kini memakai `EvaluationRecord` yang sama dengan baseline, termasuk varian, status, dan lifecycle konfigurasi; bukti run awal tetap memakai format historis §3.3. Pembaca metrik masih STUB dan integrasi dengannya belum teruji. Kontrak ini tidak mengubah API publik atau menyelesaikan freeze/evaluasi final.

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

Penyelarasan runner tanggal 26 November mengganti `COMPLETED` menjadi `OK`, menambahkan `schemaVersion`/`variant`, memakai stage error huruf besar, serta mengganti lifecycle `state` dengan `status`. NO_CONTENT tercatat UNAVAILABLE dengan `EXTRACTION_NO_CONTENT` dan `reasonDetail` asli, tanpa kategori. Bila quota/timeout/provider error menghentikan pemrosesan, hanya dokumen yang benar-benar dicoba disimpan di `tmp/raw.jsonl`; konfigurasi tetap RUNNING dengan `stopReason`, `stoppedAt`, jumlah aktual dan `plannedRecords`. Dokumen yang belum dicoba tidak mendapat kategori, status prediksi, atau latensi fiktif. `raw.jsonl` diterbitkan atomik dan status menjadi COMPLETE hanya setelah seluruh dokumen/varian dicoba dan checksum manifest masih sesuai.

`--variants pipeline baseline` menjalankan kedua detector secara eksplisit pada PDF dev yang sama, masing-masing melalui ekstraksi runtime dengan pengaturan identik. Baseline tidak membuat provider atau memerlukan key; `--variants baseline` hanya merekam parameter ekstraksi. Setiap record divalidasi melalui skema bersama sebelum ditulis. Sebelum final, B/Pash tetap harus memverifikasi pembacaan hasil oleh metrics. Keempat direktori bukti T5-07 awal pada §7 dipertahankan utuh dan tidak dimigrasikan.

## 7. Hasil Aktual dan Keputusan

Saat run pemilihan model awal: unit test runner 19 passed; suite ai-service 254 passed. Dry run memvalidasi 12 dokumen dev tanpa panggilan LLM. Endpoint daftar model mengonfirmasi kedua kandidat tersedia.

Smoke test satu dokumen yang sama (`id-high-03-scan`) berhasil pada kedua kandidat dengan 900 token dan reasoning default. Keduanya menghasilkan kategori HIGH serta PAYMENT_REQUEST, UNOFFICIAL_CONTACT, dan URGENCY_PRESSURE sesuai label dev. Tidak ada event length atau retry output pada kedua smoke test. Latensi total terukur: GPT-OSS 120B 4804 ms, Qwen 3.8 27B 3194 ms. Ini hanya pemeriksaan teknis awal satu dokumen, bukan dasar tunggal pemilihan model.

Artefak smoke test:

- `ai-eval/results/t5-07-20261125-gptoss120b-smoke-900/`
- `ai-eval/results/t5-07-20261125-qwen38-smoke-900/`

### 7.1 Perbandingan dev ID awal (25 November)

Run nyata tanggal 25 November 2026 memakai 12 PDF dev yang sama dalam urutan yang sama (enam surat, masing-masing teks dan scan). Baseline repository saat eksekusi adalah commit `b646387`; runner/helper T5-07 masih berupa perubahan working tree, dengan fingerprint tersimpan pada artefak. Kedua `run_config.json` cocok dalam daftar ID/SHA-256, checksum manifest, fingerprint kode, dan seluruh parameter selain model. Prompt v1, 900 token, reasoning default provider, serta jeda antardokumen 25 detik. Tidak ada error kuota, timeout, atau penghentian run.

| Ukuran diagnostik dev | GPT-OSS 120B | Qwen 3.8 27B |
| --- | --- | --- |
| Dokumen COMPLETED | 12/12 | 12/12 |
| Kategori sesuai anotasi | 12/12 | 12/12 |
| Himpunan kode indikator persis sesuai anotasi | 12/12 | 10/12 |
| Total attempt model (termasuk retry output) | 14 | 12 |
| Event `finish_reason=length` | 2 | 0 |
| Indikator dibuang validator | 0 | 0 |
| Median latensi model, termasuk retry | 2284 ms | 808,5 ms |
| P95 latensi model, termasuk retry | 6585 ms | 1803 ms |
| Median latensi total ekstraksi + analisis | 2903 ms | 1600,5 ms |
| P95 latensi total ekstraksi + analisis | 6630 ms | 3339 ms |

P95 memakai nearest rank, indeks `ceil(0,95 × n)` pada nilai terurut. Dengan n=12, nilainya sama dengan maksimum. Ini satu run per model pada data draft berpasangan, bukan pengukuran MET-09–MET-15 test set atau MET-16 skenario.

Qwen menambah `UNOFFICIAL_CONTACT` pada `id-medium-03-scan` dan `id-medium-03-text`, sedangkan anotasi keduanya hanya `IDENTITY_INCONSISTENCY`. Kategori tetap MEDIUM. Ini dua PDF dari satu surat yang sama, bukan dua kesalahan independen. Ketidaksesuaian dihitung terhadap anotasi sementara; penilaian semantik final tetap memerlukan tinjauan Pash.

Dua event length GPT-OSS terjadi pada attempt pertama `id-high-06-scan` dan `id-high-06-text`. Keduanya gagal validasi output awal lalu berhasil pada retry runtime tunggal. Output setiap attempt tersimpan; tidak ada kegagalan yang dihapus dari artefak. Budget 900 masih berisiko membutuhkan retry atau berakhir AI_OUTPUT_INVALID pada dokumen lain. T5-07 ini tidak mengubah budget atau reasoning effort berdasarkan test set.

Artefak run lengkap (masing-masing berisi `raw.jsonl`, `model_outputs.jsonl`, `run_config.json`):

- `ai-eval/results/t5-07-20261125-gptoss120b-dev-900/`
- `ai-eval/results/t5-07-20261125-qwen38-dev-900/`

### 7.2 Keputusan awal dan ambang sementara (25 November)

Pilihan sementara B: **Groq / `openai/gpt-oss-120b`**, prompt v1 dan parameter awal. Prioritas kualitas indikator pada prosedur §3.2 menjadi pembeda: GPT-OSS sesuai anotasi pada seluruh 12 PDF. Qwen memiliki latensi lebih rendah dan tidak memerlukan retry pada run ini; status preview dan ketersediaannya tetap perlu dipantau bila dipertimbangkan lagi. Tidak ada fallback otomatis antar kandidat.

Base URL dan model terpilih sama dengan default repository, sehingga `.env.example`, `app/core/config.py`, dan fallback `compose.yaml` tidak memerlukan perubahan. Pengumuman ke tim dilakukan B; agent tidak mengirim pesan eksternal. Teks yang dapat diteruskan: “T5-07: pilihan sementara tetap Groq / openai/gpt-oss-120b, prompt v1, OCR 25 karakter/halaman pada 300 DPI, fuzzy 90 khusus OCR/MIXED. Kedua model sudah diuji pada 12 PDF dev ID; hasil dan keterbatasan tersedia di docs/evaluation/protocol.md. Test set belum dievaluasi atau dibekukan.”

OCR minimum 25 karakter/halaman, 300 DPI, timeout 20 detik, dan fuzzy 90 dipertahankan. Pada kedua run, enam scan berhasil memakai OCR dan enam PDF teks memakai TEXT_LAYER, tanpa pemotongan ekstraksi. Pemeriksaan ulang terhadap ekstraksi dev menemukan 25/25 kutipan GPT-OSS dan 42/42 kutipan Qwen cocok substring ternormalisasi; tidak ada yang hanya lolos karena fuzzy. Ini mendukung mempertahankan konfigurasi awal untuk data ini, tetapi belum membuktikan ambang fuzzy optimal atau ketahanan terhadap scan buruk. TOI-06/TOI-07 tetap memiliki batas bukti tersebut; OI/TOI tidak ditutup sepihak.

Model bantu yang dicatat di §2 berbeda dari model terpilih. Saat run ID awal, dataset EN dan review manusia belum lengkap. Kondisi tersebut diperbarui pada §1 dan §7.3 tanggal 26 November; keputusan di bagian ini tetap merupakan keputusan dari run ID awal. Bukti lama tersedia untuk Sat/Pash dalam format historis §3.3. Runner baru sudah diselaraskan ke §6, sedangkan metrics dan evaluasi final masih menunggu T4-07.

Audit 12 berkas artefak dari dua smoke test dan dua run dev lengkap tidak menemukan nilai API key atau internal token yang dikonfigurasi. Pemeriksaan memakai environment container dan hanya mencetak jumlah temuan, tanpa membuka `.env` atau menampilkan secret.

Perbaikan review PR #49 memperketat validasi metadata split dan penyimpanan origin provider. Keempat artefak run di atas tetap merupakan bukti eksekusi sebelum perbaikan, dengan `baseUrl` lama yang mencakup path `/openai/v1` dan fingerprint kode saat itu. Artefak tersebut tidak ditulis ulang; seluruh ID yang dijalankan sudah dikonfirmasi berada di dev tanpa pasangan lintas split. Perbaikan ini diverifikasi dengan test sintetis dan dry run, tanpa mengulang evaluasi LLM.

Verifikasi setelah perbaikan review (container Python 3.12): `python scripts/dev.py eval run_eval --test` 31 passed (19 test sebelumnya dan 12 kasus regresi); `python scripts/dev.py eval test_dataset` 18 passed; `python scripts/dev.py test ai-service` 254 passed. Dry run tetap memilih 12 PDF dev dengan nol panggilan LLM. Ruff check dan format check dengan konfigurasi proyek lulus. Dua belas kasus regresi gagal sebelum perbaikan; kasus split mencakup kedua arah pasangan, urutan baris, dan penggunaan limit, sedangkan kasus URL memeriksa artefak yang ditulis dengan path sintetis, path terenkode, port, dan IPv6. Warning pytest tentang rewrite modul anyio yang sudah diimpor tetap muncul pada test runner.

### 7.3 Pelengkapan T5-05 dan integrasi runner (26 November)

Perintah aktual `python scripts/dev.py eval generate_pdfs` menghasilkan 36 PDF teks ID/EN; `python scripts/dev.py eval make_scans` menghasilkan 36 scan. Manifest lengkap berisi 72 baris, 24 dev/48 test, dan setiap bahasa/format memiliki 18 PDF. Diff manifest menambah 36 baris EN tanpa mengubah baris ID; PDF ID lama tidak berubah. Tidak ada perubahan teks/anotasi templat milik Van/Pash. Review manusia telah dikonfirmasi pengguna sebagaimana §1.

QA generator memakai ekstraksi runtime nyata pada seluruh PDF, tanpa panggilan LLM atau perhitungan metrik prediksi test set:

| Kelompok | Berhasil / jumlah | Metode | Kemiripan minimum ke teks sumber |
| --- | --- | --- | --- |
| EN teks | 18/18 | TEXT_LAYER | 1,000000 |
| EN scan | 18/18 | OCR | 0,994746 |
| ID teks | 18/18 | TEXT_LAYER | 1,000000 |
| ID scan | 18/18 | OCR | 0,997739 |

Kemiripan dihitung dengan `rapidfuzz.fuzz.ratio` atas normalisasi runtime, hanya untuk QA isi hasil generator. Tidak ada ekstraksi gagal/terpotong atau pasangan lintas split. Hasil QA ini tidak digunakan untuk menyesuaikan prompt/ambang dari test set; seluruh parameter runtime tetap sebagaimana run awal. Ketiga kriteria implementasi T5-05 terpenuhi: 72 PDF, manifest/split seimbang, dan eksekusi melalui launcher.

Migrasi runner lulus `python scripts/dev.py eval run_eval --test` (36 passed) dan suite generator `python scripts/dev.py eval test_dataset` (18 passed). Test runner menggunakan MockLLMProvider bersama dan baseline asli pada PDF unit sintetis, memvalidasi format melalui `EvaluationRecord`, hasil gagal tetap tercatat, penghentian kuota tidak membuat latensi fiktif, dan perubahan manifest mencegah penerbitan raw. Hasil test ini bukan bukti evaluasi model nyata atau hasil final.

Perintah pengembangan baru:

```sh
python scripts/dev.py eval run_eval --split dev --variants pipeline baseline --dry-run
python scripts/dev.py eval run_eval --split dev --variants baseline
python scripts/dev.py eval run_eval --split dev --variants pipeline baseline --interval-seconds 25
```

T5-08 belum selesai: runner tetap menolak test split, metrics masih STUB, dan belum ada freeze/run test set aktual. T5-09 tidak dapat menyatakan metrik final sebelum dependensi itu selesai.

Pemeriksaan metadata `freeze_testset --check` dengan konfirmasi review pengguna dan checksum manifest §1 menyisakan satu prasyarat eksternal: `T4_07_NOT_AVAILABLE`. Perintah keluar 1 dengan `ready=false`, `pdfsOpened=0`; tidak ada snapshot freeze yang dibuat. Integrasi dan run test final tetap belum dijalankan.

Verifikasi tambahan T5-06 tanggal 26 November: `generate_fixtures --check` mengonfirmasi byte/checksum kesepuluh fixture tetap sesuai README; test manual `fixtures/test_upload_validation.py` melalui image backend lulus 11 test. FX-09 berukuran 5.244.158 byte, masih melampaui konfigurasi backend aktual `MAX_UPLOAD_BYTES=5.242.880`. Fixture tidak diubah. Kategori fixture tetap target skenario sampai TB-04 dengan LLM/Anvil nyata; test validator ini tidak menjadi bukti skenario tersebut. Suite `python scripts/dev.py test ai-service` lulus 254 test.

### 7.4 Dev ID/EN lengkap dan usulan pilihan model (26 November)

Ketiga run berikut memakai manifest §1, daftar 24 PDF dev beserta SHA-256 yang identik, dan fingerprint sumber yang sama. Run pipeline menggunakan pengaturan yang sama selain model: prompt v1, 900 token, reasoning default, temperature 0, timeout 40 detik, dan jeda 25 detik antardokumen. OCR/fuzzy tetap sebagaimana §3.1. Baseline tidak memanggil LLM dan memakai parameter ekstraksi yang sama. Seluruh angka di bagian ini diagnostik dev, bukan MET-09–MET-15 test set.

| Ukuran dev | GPT-OSS 120B | Qwen 3.8 27B | Baseline rules-v1 |
| --- | --- | --- | --- |
| Dokumen pipeline/baseline dicoba | 4/24 | 24/24 | 24/24 |
| Status OK | 3/4 | 24/24 | 24/24 |
| Lifecycle run | RUNNING, dihentikan | COMPLETE | COMPLETE |
| Kategori sesuai anotasi | Tidak dibandingkan sebagai run lengkap | 24/24 | 12/24 |
| Himpunan kode indikator persis sesuai anotasi | Tidak dibandingkan sebagai run lengkap | 20/24 | 6/24 |
| Event length | 0 | 0 | Tidak berlaku |
| Median latensi ekstraksi + analisis | Tidak dibandingkan sebagai run lengkap | 1429,5 ms | 607,5 ms |
| P95 latensi ekstraksi + analisis | Tidak dibandingkan sebagai run lengkap | 2538 ms | 1800 ms |

P95 memakai nearest rank `ceil(0,95 × 24)`, yaitu nilai ke-23 setelah diurutkan. Jeda antardokumen tidak masuk latensi. Baseline dan pipeline masing-masing menjalankan ekstraksi sehingga latensi mencerminkan alur lengkap tiap varian, bukan waktu detektor saja.

GPT-OSS semula dijalankan bersama baseline, dengan target 48 record. Sesudah tiga pasangan varian berhasil, pipeline pada `en-high-05-text` menghasilkan `AI_PROVIDER_ERROR`; run langsung berhenti. Bukti parsial berisi tujuh record aktual (tiga pipeline OK, tiga baseline OK, satu pipeline UNAVAILABLE), dengan `finishedAt=null`, `stopReason=AI_PROVIDER_ERROR`, dan raw di `tmp/`. Tidak ada retry provider, perpindahan model otomatis, atau record untuk dokumen yang belum dicoba. Penyebab HTTP lebih rinci tidak diketahui; tidak ada event length pada run ini sehingga kegagalan tidak diklaim akibat pemotongan output. Bukti ini tidak boleh dibaca metrics sebagai run lengkap.

Qwen menyelesaikan seluruh 24 PDF tanpa UNAVAILABLE; kategori sesuai 24/24 dan tidak ada indikator yang dibuang validator. Empat ketidaksesuaian himpunan indikator berupa tambahan: `URGENCY_PRESSURE` pada pasangan `en-high-01`, serta `UNOFFICIAL_CONTACT` pada pasangan `id-medium-03`. Tidak ada kode referensi yang hilang pada run ini. Empat PDF tersebut hanya dua surat sumber; jangan menghitungnya sebagai empat kasus independen atau mengubah anotasi berdasarkan prediksi.

Baseline menyelesaikan 24/24 tetapi cocok kategori pada 12/24 dan himpunan indikator pada 6/24. Contoh keterbatasan dev: pasangan `id-low-02` dan `id-low-03` mendapat `PAYMENT_REQUEST` meskipun anotasi LOW; pola biaya/negasi perlu ditinjau Sat. Pasangan `en-high-05`, `en-medium-02`, `id-medium-03`, dan `id-medium-04` menjadi LOW karena indikator referensi tidak terdeteksi. Ini temuan untuk owner baseline, bukan perubahan aturan oleh B. Tidak ada baseline yang dipakai sebagai fallback runtime.

Usulan B berdasarkan cakupan eksekusi dev terbaru: **Groq / `qwen/qwen3.8-27b`**, dengan prompt/OCR/fuzzy dan budget tetap. Pilihan ini memprioritaskan run lengkap yang tersedia, bukan klaim bahwa Qwen lebih akurat secara umum: GPT-OSS belum menyelesaikan pembandingan ID/EN yang berpasangan dan hasil awal ID-nya tetap tercatat di §7.1. Qwen masih memiliki tambahan indikator pada dua surat sumber dan berstatus preview menurut dokumentasi provider di §3.1. Satu run ini tidak membuktikan kestabilan jangka panjang.

Usulan penggantian default **menunggu persetujuan Dws**. `.env.example`, `app/core/config.py`, dan fallback `compose.yaml` masih memakai pilihan awal GPT-OSS; `.env` tidak dibaca atau diubah. Override `--model` pada eksperimen tidak mengganti konfigurasi layanan. T5-07 kriteria pembaruan default/pengumuman belum dinyatakan terpenuhi untuk usulan baru. Setelah persetujuan, ketiga default harus konsisten, operator memperbarui `LLM_MODEL` sendiri bila perlu, lalu memuat ulang konfigurasi layanan. Tidak ada fallback otomatis. T5-08 tetap menunggu metrics T4-07 serta verifikasi integrasinya sebelum freeze/run final; T5-09 masih draf.

Perintah nyata dan lokasi artefak:

```sh
python scripts/dev.py eval run_eval --split dev --model openai/gpt-oss-120b --variants pipeline baseline --interval-seconds 25 --output-dir /ai-eval/results/t5-07-20261126-gptoss120b-id-en-dev-900
python scripts/dev.py eval run_eval --split dev --model qwen/qwen3.8-27b --interval-seconds 25 --output-dir /ai-eval/results/t5-07-20261126-qwen38-id-en-dev-900
python scripts/dev.py eval run_eval --split dev --variants baseline --output-dir /ai-eval/results/t5-08-20261126-baseline-id-en-dev
```

Run pertama keluar 1 karena error provider, dua run berikut keluar 0. Nama direktori baseline menyatakan konteks integrasi T5-08, tetapi `split=dev` dan `datasetStatus=not-frozen`; direktori itu bukan bukti run final. Artefak lama tetap utuh dan artefak baru tidak ditulis ulang setelah eksekusi.

Audit offline memvalidasi seluruh 55 record baru melalui `EvaluationRecord` v1. Kutipan diterima cocok substring ternormalisasi: sembilan pada run parsial GPT-OSS (termasuk baseline), 64 pada Qwen, dan 14 pada baseline lengkap; tidak ada kutipan yang hanya lolos fuzzy. Qwen memakai 24 attempt untuk 24 dokumen, tanpa retry output; GPT-OSS memakai empat attempt termasuk satu yang gagal provider. Pemeriksaan 22 berkas artefak lama/baru tidak menemukan nilai API key atau internal token yang dikonfigurasi. Audit memakai environment container, tidak membuka `.env`, tidak menampilkan secret/isi surat, dan tidak memanggil LLM.

Pemeriksaan akhir mengulang suite runner (36 passed, satu warning rewrite anyio) serta Ruff check/format untuk runner, test runner, dan generator (lulus). `git diff --check` bersih. `python scripts/dev.py status` keluar 1: container ai-service lama berstatus Exited dan endpoint health backend tidak dapat dihubungi. Test dan evaluasi di atas berjalan melalui container sementara; kesehatan enam layanan, Anvil, dan SCN nyata tidak diklaim terverifikasi pada sesi ini.
