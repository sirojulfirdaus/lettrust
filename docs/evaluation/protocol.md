# Protokol Evaluasi AI Lettrust

Owner: B (PIC 5) · Status: DRAF T5-07 (run dev selesai; keputusan sementara) · Reviewer: Dws · Ref: PRD §10.4, FR-05.12, BR-04.13, BR-04.14; SA §7.4.1, §7.9

Dokumen ini menetapkan prosedur uji dev T5-07 dan format artefak bersama B, Sat (baseline T6-05), dan Pash (metrics T4-07). Hasil awal bukan metrik test set atau penutupan OI-01/OI-02. Freeze dan evaluasi final T5-08 belum diizinkan.

## 1. Dataset

Saat penyusunan T5-07 tersedia 18 surat Indonesia dalam 36 PDF: 18 teks dan 18 scan. Manifest memuat delapan kolom SA §7.9. Pembagian sementara 12 dev dan 24 test; pasangan teks/scan dari surat yang sama selalu satu split. Target lengkap tetap 72 PDF (ID/EN × LOW/MEDIUM/HIGH × teks/scan × enam), sekitar 24 dev/48 test. Bagian Inggris menunggu T4-03; komposisi final OI-02 belum ditetapkan.

Runner T5-07 hanya menerima `--split dev`. Ia memvalidasi ID dan split seluruh metadata manifest terlebih dahulu; pasangan teks/scan dari satu ID surat dengan split berbeda ditolak sebelum PDF apa pun diakses, termasuk saat memakai `--limit`. Setelah metadata lolos, ia memeriksa path dan SHA-256 PDF dev saja. PDF test tidak dibuka, dikirim ke LLM, atau dipakai untuk tuning. `--limit` hanya untuk smoke test dan selalu dicatat melalui daftar dokumen pada `run_config.json`.

Semua run pada tahap ini berstatus `draft-not-frozen` dan pemilihan model bersifat sementara. Dokumen test tidak boleh dipakai sebagai metrik laporan. Jangan menjalankan `freeze_testset` atau menyatakan T5-05 selesai sampai tinjauan manusia Pash, identitas model bantu, serta data Inggris lengkap. Identitas model ID kini telah dikonfirmasi melalui cuplikan metadata Van di bawah; tinjauan Pash dan EN masih menunggu.

## 2. Label dan Pembuatan Data

Penulis surat Indonesia: Van (T2-04), peninjau manusia yang ditetapkan: Pash. Seluruh identitas dan kontak dikonfirmasi pengguna sebagai data sintetis. Label kategori dan daftar kode indikator berasal dari manifest dan harus sesuai PRD §8.4–§8.5; kategori bukan vonis asli/palsu. Anotasi referensi dan notes tidak masuk prompt.

Provenance model bantu berdasarkan cuplikan metadata tersanitasi yang disampaikan Van melalui pengguna:

- Model executor penulis `id-low.json`, `id-medium.json`, `id-high.json`: `gemini-4-neon-medium` (Google Gemini 4 Neon, thinking level Medium).
- Parent: `87006406-f64c-40b3-8aa7-7429b0aa0d2b`, spawn `2026-11-22T15:11:12Z` (22:11:12 WIB).
- Executor T2-04: `f7da1ac1-0a0f-4915-ac29-648b082c855c`, aktif `2026-11-22T15:11:41Z` sampai `2026-11-22T15:17:46Z`.
- Metadata penulisan tiga berkas: `write_file`, step 6, `2026-11-22T15:12:22Z`; `models_used` executor hanya `gemini-4-neon-medium`.
- Sumber: cuplikan `transcript.jsonl`, field `model` dan ringkasan executor. Log lokal penuh tidak tersedia di repository dan tidak diklaim telah diperiksa langsung oleh B.

Tiga surat ID (MEDIUM-03, MEDIUM-06, HIGH-05) kemudian diperjelas dengan bantuan Codex (keluarga GPT-6) setelah koordinasi Van. Revisi tersebut ikut memerlukan tinjauan Pash. Kandidat T5-07 di bawah berbeda dari keluarga/model bantu yang dilaporkan; pemeriksaan ini diulang bila kandidat berubah. Provenance model EN harus dilengkapi saat T4-03 tersedia.

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
6. T6-05 menyediakan baseline; T4-07 menyediakan metrics. Keduanya masih STUB pada awal T5-07, sehingga runner ini belum menjalankan baseline atau mengklaim keluaran metrics final.
7. Setelah seluruh prasyarat selesai, T5-08 menambahkan verifikasi freeze dan eksekusi sekali untuk pipeline serta baseline pada test set yang sama. Runner T5-07 saat ini sengaja menolak `--split test` sebelum membaca PDF atau konfigurasi.

### 3.3 Format artefak versi 1

Setiap run memakai direktori baru `ai-eval/results/<run>/`; direktori bukti yang sudah ada tidak ditimpa. LLM dan baseline memakai direktori terpisah. Metadata umum `schemaVersion=1` dan `method=llm|baseline` ada pada `run_config.json`; runner ini menghasilkan `method=llm` saja.

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

Dataset dev saat ini hanya Indonesia, berukuran kecil dan mempunyai pasangan teks/scan yang berkorelasi. Hasil tidak membuktikan kemampuan bahasa Inggris atau generalisasi ke surat nyata. Tinjauan coding agent tidak menggantikan tinjauan manusia Pash. Angka dev hanya untuk keputusan eksperimen, bukan MET-09–MET-15 test set final.

## 5. Log Perubahan Ambang dan Prompt

| Tahap | Parameter | Alasan/status |
| --- | --- | --- |
| Awal T5-07 | Prompt v1; max output 900; reasoning effort default; OCR 25/300 DPI/20 detik; fuzzy 90 | Acuan konfigurasi runtime sebelum uji nyata. Tidak ada perubahan skoring atau prompt. |
| Setelah perbandingan dev 25/11/2026 | Parameter awal dipertahankan; Groq / `openai/gpt-oss-120b` dipilih sementara | Kategori dan himpunan indikator sesuai anotasi dev pada 12/12 PDF; dua output terpotong dipulihkan retry runtime. Ambang belum dikalibrasi untuk variasi scan yang lebih luas. |

## 6. Hasil Aktual dan Keputusan

Saat run pemilihan model awal: unit test runner 19 passed; suite ai-service 254 passed. Dry run memvalidasi 12 dokumen dev tanpa panggilan LLM. Endpoint daftar model mengonfirmasi kedua kandidat tersedia.

Smoke test satu dokumen yang sama (`id-high-03-scan`) berhasil pada kedua kandidat dengan 900 token dan reasoning default. Keduanya menghasilkan kategori HIGH serta PAYMENT_REQUEST, UNOFFICIAL_CONTACT, dan URGENCY_PRESSURE sesuai label dev. Tidak ada event length atau retry output pada kedua smoke test. Latensi total terukur: GPT-OSS 120B 4804 ms, Qwen 3.8 27B 3194 ms. Ini hanya pemeriksaan teknis awal satu dokumen, bukan dasar tunggal pemilihan model.

Artefak smoke test:

- `ai-eval/results/t5-07-20261125-gptoss120b-smoke-900/`
- `ai-eval/results/t5-07-20261125-qwen38-smoke-900/`

### 6.1 Perbandingan seluruh dev

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

### 6.2 Keputusan dan ambang sementara

Pilihan sementara B: **Groq / `openai/gpt-oss-120b`**, prompt v1 dan parameter awal. Prioritas kualitas indikator pada prosedur §3.2 menjadi pembeda: GPT-OSS sesuai anotasi pada seluruh 12 PDF. Qwen memiliki latensi lebih rendah dan tidak memerlukan retry pada run ini; status preview dan ketersediaannya tetap perlu dipantau bila dipertimbangkan lagi. Tidak ada fallback otomatis antar kandidat.

Base URL dan model terpilih sama dengan default repository, sehingga `.env.example`, `app/core/config.py`, dan fallback `compose.yaml` tidak memerlukan perubahan. Pengumuman ke tim dilakukan B; agent tidak mengirim pesan eksternal. Teks yang dapat diteruskan: “T5-07: pilihan sementara tetap Groq / openai/gpt-oss-120b, prompt v1, OCR 25 karakter/halaman pada 300 DPI, fuzzy 90 khusus OCR/MIXED. Kedua model sudah diuji pada 12 PDF dev ID; hasil dan keterbatasan tersedia di docs/evaluation/protocol.md. Test set belum dievaluasi atau dibekukan.”

OCR minimum 25 karakter/halaman, 300 DPI, timeout 20 detik, dan fuzzy 90 dipertahankan. Pada kedua run, enam scan berhasil memakai OCR dan enam PDF teks memakai TEXT_LAYER, tanpa pemotongan ekstraksi. Pemeriksaan ulang terhadap ekstraksi dev menemukan 25/25 kutipan GPT-OSS dan 42/42 kutipan Qwen cocok substring ternormalisasi; tidak ada yang hanya lolos karena fuzzy. Ini mendukung mempertahankan konfigurasi awal untuk data ini, tetapi belum membuktikan ambang fuzzy optimal atau ketahanan terhadap scan buruk. TOI-06/TOI-07 tetap memiliki batas bukti tersebut; OI/TOI tidak ditutup sepihak.

Model bantu ID yang dicatat di §2 berbeda dari model terpilih. Keputusan akhir OI-01/OI-02 dan evaluasi final tetap menunggu dataset ID/EN lengkap serta tinjauan Pash. T5-05 belum dinyatakan selesai dan T5-08 tidak dijalankan. Format artefak versi 1 siap diserahkan kepada Sat/Pash; integrasi baseline dan metrics masih pekerjaan pemilik masing-masing.

Audit 12 berkas artefak dari dua smoke test dan dua run dev lengkap tidak menemukan nilai API key atau internal token yang dikonfigurasi. Pemeriksaan memakai environment container dan hanya mencetak jumlah temuan, tanpa membuka `.env` atau menampilkan secret.

Perbaikan review PR #49 memperketat validasi metadata split dan penyimpanan origin provider. Keempat artefak run di atas tetap merupakan bukti eksekusi sebelum perbaikan, dengan `baseUrl` lama yang mencakup path `/openai/v1` dan fingerprint kode saat itu. Artefak tersebut tidak ditulis ulang; seluruh ID yang dijalankan sudah dikonfirmasi berada di dev tanpa pasangan lintas split. Perbaikan ini diverifikasi dengan test sintetis dan dry run, tanpa mengulang evaluasi LLM.

Verifikasi setelah perbaikan review (container Python 3.12): `python scripts/dev.py eval run_eval --test` 31 passed (19 test sebelumnya dan 12 kasus regresi); `python scripts/dev.py eval test_dataset` 18 passed; `python scripts/dev.py test ai-service` 254 passed. Dry run tetap memilih 12 PDF dev dengan nol panggilan LLM. Ruff check dan format check dengan konfigurasi proyek lulus. Dua belas kasus regresi gagal sebelum perbaikan; kasus split mencakup kedua arah pasangan, urutan baris, dan penggunaan limit, sedangkan kasus URL memeriksa artefak yang ditulis dengan path sintetis, path terenkode, port, dan IPv6. Warning pytest tentang rewrite modul anyio yang sudah diimpor tetap muncul pada test runner.
