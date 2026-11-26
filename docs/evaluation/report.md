# Laporan Evaluasi AI Lettrust

Owner: B (PIC 5) · Status: COMPLETE — isi T5-09 lengkap; review manusia hasil dan approval mengikuti proses tim · Reviewer: Dws · Ref: PLAN T5-09; PRD §10.4, §10.4.4; FR-05.12; ACC-06

## 1. Status dan bukti

Evaluasi test set beku telah dijalankan dengan LLM nyata dan baseline aturan melalui ekstraksi runtime. Pipeline Qwen menghasilkan 47 respons sukses dari 48 PDF pada percobaan pertama; seluruh 47 kategori sesuai referensi. Satu dokumen gagal dengan AI_PROVIDER_ERROR, kemudian berhasil pada satu retry yang diizinkan pengguna. Baseline menyelesaikan 48/48 dokumen dengan 26 kategori sesuai. Semua metrik utama memakai observasi pertama; retry disimpan terpisah tanpa mengganti kegagalan awal.

Accuracy dan macro F1 pipeline adalah 1,0000 **pada 47 respons sukses**, dengan completion rate first-pass 47/48 (97,9167%). Ini tidak berarti seluruh indikator benar: ada 12 false positive indikator pada 12 PDF dari enam surat. PRD tidak menetapkan target numerik kualitas AI; laporan tidak mengklaim akurasi surat nyata atau menutup OI-01/OI-02.

T5-08 telah merge melalui PR #57 pada `c746bbf`. Laporan ini melengkapi isi T5-09. Review manusia atas respons model masih PENDING pada artefak; kelengkapan dokumen tidak berarti approval reviewer atau penerimaan ACC-06 oleh tim. Riwayat rinci ada di [protokol §8](protocol.md#8-freeze-dan-evaluasi-final-t5-08-26-november).

Sumber pengukuran adalah run `t5-08-20261126-final-qwen38`:

| Bukti | Isi |
| --- | --- |
| [raw.jsonl](../../ai-eval/results/t5-08-20261126-final-qwen38/raw.jsonl) | 96 observasi pertama: 48 pipeline dan 48 baseline |
| [metrics.json](../../ai-eval/results/t5-08-20261126-final-qwen38/metrics.json) | Metrik presisi penuh, breakdown, dan denominator |
| [confusion.csv](../../ai-eval/results/t5-08-20261126-final-qwen38/confusion.csv) | Confusion matrix kedua varian |
| [run_config.json](../../ai-eval/results/t5-08-20261126-final-qwen38/run_config.json) | Model, tanggal, parameter, profil dev, dan fingerprint kode |
| [model_outputs.jsonl](../../ai-eval/results/t5-08-20261126-final-qwen38/model_outputs.jsonl) | Keluaran asli tiap attempt provider untuk 48 percobaan pertama |
| [snapshot freeze](../../ai-eval/results/t5-08-20261126-freeze/testset.freeze.json) | Checksum 48 PDF test sebelum prediksi |
| [hasil retry](../../ai-eval/results/t5-08-20261126-final-qwen38/retry_raw.jsonl) dan [riwayat attempt](../../ai-eval/results/t5-08-20261126-final-qwen38/retry_attempts.jsonl) | Satu retry di luar metrik utama |
| [checksum artefak](../../ai-eval/results/t5-08-20261126-final-qwen38/final_checksums.json) | SHA-256 19 berkas hasil dan identitas manifest/snapshot |
| [indeks review manusia](../../ai-eval/results/t5-08-20261126-final-qwen38/human_review_index.json) | Navigasi 48 respons sukses setelah pemulihan; review PENDING |

Identitas SHA-256:

- Manifest: `e7cb70b0e2a0e99a06be30c064903c2eff5baf79f3c8741357423c8edb7f86fb`.
- Snapshot: `2500f7c7544417aa3800bd5dbe7e86dc7f86971dd7350f00437077b8fa1ecb34`.
- Raw utama: `6273275531c5112e5b03e7662e8409d66e13ea1910e63fa7cd807b932b926d96`.
- Metrics: `bede10b51a01f6b28eb3338f9e759db92020156367b5c8a98bcb10ca3ceb228a`.

## 2. Data, provenance, dan metode

T5-05 menyediakan 72 PDF dari 36 surat sintetis: 18 Indonesia dan 18 Inggris, masing-masing versi teks/scan. Split terdiri atas 24 PDF dev dari 12 surat dan 48 PDF test dari 24 surat. Test seimbang: 16 PDF per kategori, 24 per bahasa, 24 per format, serta empat PDF per sel bahasa × kategori × format. Pasangan teks/scan satu surat selalu satu split; 48 PDF test bukan 48 surat independen.

Penulis ID adalah Van dengan model bantu yang dilaporkan metadata sesi sebagai `gemini-4-neon-medium`; penulis EN adalah Pash, dibantu GPT-6 (Codex) pada format/metadata dan anotasi kutipan. Klarifikasi beberapa templat ID juga dibantu coding agent B. Keluarga model bantu berbeda dari Qwen yang dievaluasi. Provenance didasarkan pada konfirmasi/cuplik metadata anggota yang disampaikan pengguna, bukan audit independen terhadap layanan penyedia model bantu.

Pengguna mengonfirmasi pada 26 November bahwa review manusia 18 surat ID oleh Pash dan 18 surat EN oleh Van selesai, serta identitas/kontak sintetis. Konfirmasi diikat ke checksum sumber pada [protokol §1–§2](protocol.md#1-dataset); notes historis templat yang masih menyebut review tertunda tidak diubah oleh B. Review label sumber ini berbeda dari review hasil model yang masih menunggu.

Label berasal dari manifest; prediksi hanya berasal dari teks ekstraksi, tanpa label, ID, atau nama berkas sebagai input detektor. Setelah freeze tidak ada perubahan data, label, prompt, ambang, atau kode detektor berdasarkan hasil test. Pipeline memakai ekstraksi text layer atau OCR Tesseract `ind+eng` CPU, LLM pralatih, validator kode/kutipan, skoring deterministik, dan rekomendasi templat. Tidak ada training/fine-tuning.

Baseline `rules-v1` memakai pola ID/EN dengan pengecualian per klausa dan validator/skoring/komposisi runtime yang sama. Baseline hanya pembanding evaluasi eksplisit, bukan fallback runtime.

| Parameter final | Nilai |
| --- | --- |
| Provider/model | Groq; `qwen/qwen3.8-27b` |
| Prompt/output | `v1`; temperature 0; `json_object`; maksimum 900 token; reasoning default provider |
| Timeout/retry runtime | Timeout provider 40 detik; satu retry maksimum untuk output invalid; retry error provider 0 |
| Batas ekstraksi | Unggahan 5 MiB; maksimum 5 halaman dan 12.000 karakter |
| OCR | Minimum 25 karakter/halaman; 300 DPI; timeout 20 detik/halaman |
| Kutipan | Substring ketat TEXT_LAYER; fuzzy 90 hanya OCR/MIXED |
| Jeda | 25 detik antardokumen, di luar latensi per dokumen |
| Freeze | 26 November 2026, 15:17:21 UTC, sebelum prediksi pertama |
| Mulai / selesai first-pass | 26 November 2026, 15:18:25 / 15:57:01 UTC (22:18:25 / 22:57:01 WIB) |
| Selesai retry tambahan | 26 November 2026, 15:57:08 UTC |

Parameter publik sama dengan profil dev Qwen lengkap T5-07. Fingerprint kode disimpan pada konfigurasi. Environment operator saat evaluasi masih memilih GPT-OSS, sehingga CLI memberi override Qwen eksplisit tanpa membuka/mengubah `.env`. Run test beserta pemulihannya melakukan 49 attempt provider: 48 percobaan pertama dan satu retry tambahan, tanpa event length atau retry output invalid.

## 3. Pemilihan model pada dev

Pada dev ID awal 25 November (12 PDF), GPT-OSS dan Qwen masing-masing menghasilkan 12/12 kategori sesuai; himpunan indikator persis sesuai pada GPT-OSS 12/12 dan Qwen 10/12. GPT-OSS mengalami dua output terpotong yang berhasil pada retry runtime. Ini bukti historis dev, bukan angka test.

Pada dev ID/EN lengkap 26 November, Qwen menyelesaikan 24/24 PDF: kategori sesuai 24/24 dan himpunan indikator sesuai 20/24. Baseline menghasilkan kategori sesuai 12/24 dan himpunan indikator sesuai 6/24. GPT-OSS berhenti pada dokumen keempat setelah tiga respons sukses dan satu AI_PROVIDER_ERROR; bukti parsial tersimpan. Karena cakupan tidak setara, ini tidak membuktikan Qwen lebih akurat atau selalu lebih stabil daripada GPT-OSS.

Dws menyetujui Qwen dan pengguna mengonfirmasi pengumumannya ke tim. Dasar operasionalnya adalah penyelesaian cakupan dev ID/EN dengan parameter tetap. Riwayat dan keterbatasan kandidat preview/provider ada pada [protokol §7.4–§7.5](protocol.md#74-dev-iden-lengkap-dan-usulan-pilihan-model-26-november). Angka dev tidak digabungkan ke metrik test berikut.

## 4. Konvensi penghitungan

Tabel memakai observasi pertama dalam raw utama, dibulatkan empat desimal; metrics menyimpan presisi penuh. P/R/F1 adalah rasio 0–1.

- Kategori dihitung hanya pada respons sukses: Qwen n=47, baseline n=48. Kegagalan dilaporkan lewat coverage/reliabilitas, bukan diberi kategori. Accuracy = kategori benar / respons berkategori; macro F1 adalah rata-rata F1 tiga kelas.
- Indikator dihitung pada seluruh 48 dokumen per varian dari `result.indicatorDetails`. Record gagal mempunyai himpunan prediksi kosong, sehingga indikator referensinya menjadi FN. TP/FP/FN dihitung per pasangan dokumen–kode, bukan per kutipan.
- MET-11 memakai 47 ID yang sukses pada kedua varian, termasuk saat membandingkan indikator. Delta = pipeline dikurangi baseline; denominator ini berbeda dari MET-10 seluruh test.
- Precision/F1 dengan denominator nol diberi 0; recall tanpa support bernilai null. Semua kode indikator mempunyai support pada test ini.
- Ekstraksi memakai seluruh dokumen tiap format. Evidence drop memakai indikator dipertahankan + dibuang pada respons sukses yang mempunyai metadata, bukan seluruh attempt provider.
- Latensi mencakup ekstraksi, analisis, dan retry output runtime bila terjadi. Jeda 25 detik, pemulihan manusia, portal/backend, serta registry dikecualikan. P95 memakai nearest rank. Failure awal tetap dihitung; retry tambahan tidak masuk latensi utama.

## 5. MET-09 — Klasifikasi kategori

| Varian | Diklasifikasi / test | Kategori benar | Accuracy | Macro F1 |
| --- | ---: | ---: | ---: | ---: |
| Qwen | 47/48 | 47/47 | 1,0000 | 1,0000 |
| Baseline | 48/48 | 26/48 | 0,5417 | 0,5183 |

| Kategori | Support Qwen | P Qwen | R Qwen | F1 Qwen | Support baseline | P baseline | R baseline | F1 baseline |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| LOW | 16 | 1,0000 | 1,0000 | 1,0000 | 16 | 0,4375 | 0,8750 | 0,5833 |
| MEDIUM | 15 | 1,0000 | 1,0000 | 1,0000 | 16 | 1,0000 | 0,2500 | 0,4000 |
| HIGH | 16 | 1,0000 | 1,0000 | 1,0000 | 16 | 0,6667 | 0,5000 | 0,5714 |

Confusion matrix berikut memakai baris referensi dan kolom prediksi. Satu MEDIUM pipeline UNAVAILABLE tidak masuk matriks, tetapi tetap dilaporkan pada MET-15.

| Varian | Referensi | Prediksi LOW | Prediksi MEDIUM | Prediksi HIGH |
| --- | --- | ---: | ---: | ---: |
| Qwen | LOW | 16 | 0 | 0 |
| Qwen | MEDIUM | 0 | 15 | 0 |
| Qwen | HIGH | 0 | 0 | 16 |
| Baseline | LOW | 14 | 0 | 2 |
| Baseline | MEDIUM | 10 | 4 | 2 |
| Baseline | HIGH | 8 | 0 | 8 |

## 6. MET-10 — Deteksi indikator

Support adalah jumlah PDF yang mempunyai kode referensi. Dua FN pipeline berasal dari dokumen provider gagal; label referensi beku tidak diubah untuk menyesuaikan prediksi.

| Kode | Support | TP/FP/FN Qwen | P Qwen | R Qwen | TP/FP/FN baseline | P baseline | R baseline |
| --- | ---: | --- | ---: | ---: | --- | ---: | ---: |
| PAYMENT_REQUEST | 10 | 10/0/0 | 1,0000 | 1,0000 | 4/4/6 | 0,5000 | 0,4000 |
| SENSITIVE_DATA_REQUEST | 6 | 6/0/0 | 1,0000 | 1,0000 | 4/0/2 | 1,0000 | 0,6667 |
| UNOFFICIAL_CONTACT | 12 | 11/2/1 | 0,8462 | 0,9167 | 8/0/4 | 1,0000 | 0,6667 |
| URGENCY_PRESSURE | 4 | 3/8/1 | 0,2727 | 0,7500 | 2/0/2 | 1,0000 | 0,5000 |
| IDENTITY_INCONSISTENCY | 10 | 10/0/0 | 1,0000 | 1,0000 | 0/0/10 | 0,0000 | 0,0000 |
| UNREALISTIC_COMPENSATION | 6 | 6/0/0 | 1,0000 | 1,0000 | 0/0/6 | 0,0000 | 0,0000 |
| VAGUE_JOB_DETAILS | 6 | 6/2/0 | 0,7500 | 1,0000 | 0/0/6 | 0,0000 | 0,0000 |

Sebagai diagnostik tambahan, himpunan indikator persis sesuai pada 35/47 respons sukses Qwen (35/48 seluruh test), dibanding 20/48 baseline. Agregat Qwen adalah TP=52, FP=12, FN=2; baseline TP=18, FP=4, FN=36. Accuracy kategori 1,0000 tidak menghapus kesalahan indikator ini.

## 7. MET-11 — Perbandingan pasangan yang sama

MET-11 memakai 47 dokumen yang sukses pada kedua varian. `id-medium-05-scan` dikeluarkan dari kedua sisi karena observasi pertama pipeline gagal. Pada pasangan ini baseline mempunyai accuracy 26/47 = 0,5532 dan macro F1 0,5323; pipeline masing-masing 1,0000. Delta accuracy = +0,4468 dan macro F1 = +0,4677. Ini perbandingan deskriptif, bukan uji signifikansi atau klaim keunggulan umum.

| Kategori | Delta precision | Delta recall | Delta F1 |
| --- | ---: | ---: | ---: |
| LOW | +0,5625 | +0,1250 | +0,4167 |
| MEDIUM | +0,0000 | +0,7333 | +0,5789 |
| HIGH | +0,2727 | +0,5000 | +0,4074 |

| Kode | Delta precision | Delta recall |
| --- | ---: | ---: |
| PAYMENT_REQUEST | +0,4286 | +0,6000 |
| SENSITIVE_DATA_REQUEST | +0,0000 | +0,3333 |
| UNOFFICIAL_CONTACT | −0,1538 | +0,3636 |
| URGENCY_PRESSURE | −0,7273 | +0,6667 |
| IDENTITY_INCONSISTENCY | +1,0000 | +1,0000 |
| UNREALISTIC_COMPENSATION | +1,0000 | +1,0000 |
| VAGUE_JOB_DETAILS | +0,7500 | +1,0000 |

Recall pipeline meningkat, tetapi precision UNOFFICIAL_CONTACT dan URGENCY_PRESSURE lebih rendah dari baseline pada pasangan ini. Delta tidak sama dengan pengurangan tabel MET-10 karena tabel itu memakai seluruh 48 dokumen.

## 8. MET-12 — Bahasa dan format

Setiap kelompok berisi 24 PDF. Satu kegagalan pipeline berada pada kelompok Indonesia dan scan; keduanya mempunyai 23 respons berkategori. Kelompok bahasa/format saling tumpang tindih dan tidak boleh dijumlahkan sebagai observasi independen.

| Kelompok | Qwen diklasifikasi | Accuracy Qwen | Macro F1 Qwen | Baseline diklasifikasi | Accuracy baseline | Macro F1 baseline |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Indonesia | 23/24 | 1,0000 | 1,0000 | 24/24 | 0,5833 | 0,5556 |
| Inggris | 24/24 | 1,0000 | 1,0000 | 24/24 | 0,5000 | 0,4571 |
| PDF teks | 24/24 | 1,0000 | 1,0000 | 24/24 | 0,5417 | 0,5183 |
| PDF scan | 23/24 | 1,0000 | 1,0000 | 24/24 | 0,5417 | 0,5183 |

Rincian kelas memakai urutan P/R/F1. Support baseline setiap kelas adalah 8; Qwen juga 8 kecuali MEDIUM Indonesia/scan masing-masing 7. Baris teks/scan diringkas bersama karena nilai P/R/F1 identik, bukan karena dokumennya digabung saat penghitungan.

| Kelompok | Kategori | P/R/F1 Qwen | P/R/F1 baseline |
| --- | --- | --- | --- |
| Indonesia | LOW | 1,0000 / 1,0000 / 1,0000 | 0,5000 / 0,7500 / 0,6000 |
| Indonesia | MEDIUM | 1,0000 / 1,0000 / 1,0000 | 1,0000 / 0,2500 / 0,4000 |
| Indonesia | HIGH | 1,0000 / 1,0000 / 1,0000 | 0,6000 / 0,7500 / 0,6667 |
| Inggris | LOW | 1,0000 / 1,0000 / 1,0000 | 0,4000 / 1,0000 / 0,5714 |
| Inggris | MEDIUM | 1,0000 / 1,0000 / 1,0000 | 1,0000 / 0,2500 / 0,4000 |
| Inggris | HIGH | 1,0000 / 1,0000 / 1,0000 | 1,0000 / 0,2500 / 0,4000 |
| Teks; scan (masing-masing) | LOW | 1,0000 / 1,0000 / 1,0000 | 0,4375 / 0,8750 / 0,5833 |
| Teks; scan (masing-masing) | MEDIUM | 1,0000 / 1,0000 / 1,0000 | 1,0000 / 0,2500 / 0,4000 |
| Teks; scan (masing-masing) | HIGH | 1,0000 / 1,0000 / 1,0000 | 0,6667 / 0,5000 / 0,5714 |

Confusion matrix tiap kelompok tersimpan di `variants.<variant>.classificationByLang.{id,en}.confusion` dan `classificationByFormat.{text,scan}.confusion` pada [metrics.json](../../ai-eval/results/t5-08-20261126-final-qwen38/metrics.json). Hasil format pada sampel ini tidak membuktikan ketahanan terhadap scan berkualitas rendah di luar generator.

## 9. MET-13–MET-15 dan latensi

### MET-13 — Ekstraksi

| Varian | PDF teks | PDF scan | Metadata tidak tersedia |
| --- | --- | --- | ---: |
| Qwen | 24/24 (100%) | 24/24 (100%) | 0 |
| Baseline | 24/24 (100%) | 24/24 (100%) | 0 |

Semua PDF test menghasilkan konten yang dapat dianalisis. Record gagal provider tetap mempunyai ekstraksi OK, sehingga bukan kegagalan OCR. Persentase ini mengukur ketersediaan konten, bukan akurasi karakter OCR atau ketepatan analisis semantik.

### MET-14 — Evidence validation drop

| Varian | Dipertahankan | Dibuang | Kandidat teramati | Drop rate |
| --- | ---: | ---: | ---: | ---: |
| Qwen | 64 | 0 | 64 | 0% |
| Baseline | 22 | 0 | 22 | 0% |

Metadata mencakup 47 respons sukses Qwen dan 48 baseline; respons provider gagal tidak mempunyai kandidat yang dapat dinilai. Drop rate 0% tidak membuktikan interpretasi kode benar. Validator memeriksa kode dan keberadaan kutipan, tetapi 12 indikator pipeline tetap FP terhadap referensi.

### MET-15 — Reliabilitas dan pemulihan

| Varian | Permintaan dokumen first-pass | Selesai | UNAVAILABLE | Completion rate | Alasan |
| --- | ---: | ---: | ---: | ---: | --- |
| Qwen | 48 | 47 | 1 | 97,9167% | ANALYSIS / AI_PROVIDER_ERROR |
| Baseline | 48 | 48 | 0 | 100% | Tidak ada |

Run berhenti pada `id-medium-05-scan`, 26 November pukul 15:39:18 UTC, setelah 44 pipeline sukses. Error terjadi pada satu attempt; penyebab HTTP tidak direkam sehingga tidak disimpulkan sebagai key salah, kuota, timeout, atau truncation. Empat baseline yang belum dicoba diselesaikan tanpa LLM. Pengguna mengizinkan penyelesaian tiga pipeline yang belum dicoba dan pengulangan kegagalan. Ketiga dokumen baru berhasil pada percobaan pertama; dokumen gagal berhasil pada satu retry, sehingga seluruh 48 PDF mempunyai respons sukses setelah pemulihan.

Satu retry ini adalah pengecualian prosedur sekali pada PRD §10.4.3 dan tetap harus dinyatakan saat review. Sebanyak 44 dokumen yang sudah berhasil tidak diulang. Model, parameter, dan snapshot sama, tanpa fallback. [Instruksi pemulihan](../../ai-eval/results/t5-08-20261126-final-qwen38/completion_authorization.json), hasil awal, konfigurasi parsial, serta retry tersimpan terpisah. Raw utama tetap UNAVAILABLE untuk observasi awal; completion rate first-pass tidak dinaikkan menjadi 100%. Konfigurasi COMPLETE berarti semua pasangan telah dicoba, termasuk kegagalan. Merge PR #57 tidak ditafsirkan sebagai perubahan aturan PRD atau bukti isi approval yang tidak diperiksa.

### Latensi offline tambahan

| Varian | Observasi | Median | P95 | Minimum | Maksimum |
| --- | ---: | ---: | ---: | ---: | ---: |
| Qwen | 48 | 1749,5 ms | 4401 ms | 411 ms | 20916 ms |
| Baseline | 48 | 552,5 ms | 3648 ms | 26 ms | 3991 ms |

Failure pertama masuk 48 observasi Qwen; retry dan waktu menunggu kelanjutan dikecualikan. Latensi ekstraksi+analisis offline ini bukan MET-16/API-07 dan tidak membuktikan target performa skenario terintegrasi.

## 10. Analisis kualitatif kesalahan

Analisis ini dilakukan coding agent terhadap artefak dan sumber sintetis; bukan pengganti tinjauan manusia. FP/FN selalu relatif terhadap anotasi beku. Kategori dihitung dari indikator tervalidasi melalui skoring tetap PRD §8.5, bukan label kategori langsung model. Karena itu, salah indikator dapat tidak mengubah kategori.

### Pipeline: kategori benar, indikator tambahan keliru

Seluruh 12 PDF dengan indikator tambahan berada pada HIGH. Indikator HIGH yang benar sudah cukup mempertahankan kategori, sehingga tambahan MEDIUM/LOW tidak mengubah hasil kategori. Kesalahan muncul pada kedua format dari enam surat berikut:

| ID surat (masing-masing teks dan scan) | Kode tambahan | Jumlah FP | Interpretasi |
| --- | --- | ---: | --- |
| en-high-02, en-high-04, id-high-01, id-high-04 | URGENCY_PRESSURE | 8 | Model memperluas tekanan waktu dari prasyarat, tenggat, atau penundaan proses; referensi tidak memberi kode tekanan waktu |
| id-high-02 | UNOFFICIAL_CONTACT | 2 | Permintaan data sensitif memakai domain perusahaan sintetis; bahaya isi tidak otomatis menjadikan kanal tidak resmi |
| id-high-05 | VAGUE_JOB_DETAILS | 2 | Identitas/posisi/lokasi bertentangan, tetapi tugas dan atasan disebut; inkonsistensi bukan otomatis ketiadaan rincian |

Ada batas anotasi yang perlu ditinjau manusia. EN-HIGH-02, misalnya, memuat desakan agar tidak menunda, sehingga pembaca dapat memperdebatkan apakah cukup untuk URGENCY_PRESSURE walau referensi hanya SENSITIVE_DATA_REQUEST. Laporan menghitung FP sesuai referensi beku tanpa mengklaim semua perbedaan semantik telah diputuskan manusia. Koreksi label, bila dibutuhkan, menjadi versi dataset/evaluasi baru; snapshot dan hasil sekarang tidak diubah retrospektif.

Himpunan indikator sesuai pada 35/47 respons sukses. Tidak ada kode referensi hilang pada respons sukses pipeline; dua FN berasal dari ketiadaan respons provider untuk ID-MEDIUM-05 scan. Ini membedakan kegagalan teknis dari salah tafsir kode.

### Baseline: keterbatasan pola dan negasi

Baseline menghasilkan 22 salah kategori: delapan HIGH menjadi LOW, sepuluh MEDIUM menjadi LOW, dua LOW menjadi HIGH, dan dua MEDIUM menjadi HIGH. Semuanya berpasangan dari 11 surat, sehingga bukan 22 kesalahan independen.

- ID-LOW-04 memuat penggantian transportasi wawancara oleh perusahaan serta keterangan tanpa pungutan rekrutmen. Variasi frasa biaya/negasi tidak tertangkap memadai, memicu PAYMENT_REQUEST dan LOW menjadi HIGH. Pada ID-MEDIUM-05, keterangan tanpa pungutan rekrutmen juga memicu pembayaran palsu dan MEDIUM menjadi HIGH. Kedua pasangan menghasilkan empat FP pembayaran.
- EN-HIGH-03 meminta pembayaran kursus sebelum bekerja, tetapi rumusan biaya kursus tidak tercakup memadai oleh pola pembayaran; kedua format menjadi LOW. EN-HIGH-02 kehilangan SENSITIVE_DATA_REQUEST. Aturan istilah/jarak kata rentan terhadap variasi bahasa.
- Baseline tidak mendeteksi IDENTITY_INCONSISTENCY pada seluruh 10 PDF referensinya. Ketidaksesuaian dapat tersirat lewat nama, peran, dan lokasi tanpa frasa eksplisit bahwa semuanya tidak konsisten. EN-MEDIUM-03 menjadi contoh kategori MEDIUM turun menjadi LOW.
- Recall UNREALISTIC_COMPENSATION dan VAGUE_JOB_DETAILS juga 0 pada sampel ini. Pola mengandalkan frasa eksplisit dan tidak menyimpulkan kewajaran gaji atau kelengkapan rincian. Pada ID-LOW-05/06 kategori tetap LOW walau indikator LOW referensi hilang; kategori benar tidak menjamin indikator benar.

Tidak ada perubahan kode baseline milik Sat, prompt, atau label setelah analisis ini. Perbaikan berikutnya harus memakai dev set dan versi eksperimen baru.

### FX-03 dari integrasi, di luar test set

Dws melaporkan TB-02 pada dev `cb67c3c` berhasil, termasuk pengujian ulang 5c dengan Qwen: COMPLETED/HIGH serta tiga indikator, termasuk URGENCY_PRESSURE. FX-03 di repo menargetkan PAYMENT_REQUEST dan UNOFFICIAL_CONTACT. Surat bertanggal 20 November memberi batas konfirmasi 30 November tanpa ancaman kehilangan posisi atau kuota terbatas. Berdasarkan isi fixture dan PRD §8.4, tambahan itu dinilai false positive; HIGH tetap konsisten dengan pembayaran.

Pada konfirmasi lanjutan yang disampaikan pengguna, Dws mengidentifikasi respons Qwen dengan request ID `req_CFA22FCF636DDB0C`. URGENCY_PRESSURE muncul kembali seperti pada pengujian sebelumnya, dengan satu-satunya kutipan pendukung: “Konfirmasi paling lambat 30 November 2026”. Dws mengonfirmasi ini sebagai false positive. Kutipan tenggat biasa tersebut tidak menunjukkan tenggat sangat singkat, ancaman kehilangan posisi, atau kuota terbatas sesuai PRD §8.4; label referensi dua indikator dan kategori HIGH tetap dipertahankan.

Request ID, kutipan, dan pengulangan hasil di atas bersumber dari konfirmasi Dws melalui pengguna, bukan pengujian ulang oleh penyusun laporan. JSON respons lengkap belum diinspeksi sebagai artefak lokal pada T5-09; bukti lengkap tetap perlu disimpan pada TB-04. Konfirmasi manusia untuk kasus FX-03 ini tidak berarti review seluruh 48 respons evaluasi telah selesai. Laporan tidak mengisi PASS skenario atau mengklaim audit respons lengkap tersebut.

FX-03 terpisah dari dataset 48 PDF, sehingga tidak ditambahkan ke denominator MET-09–MET-15, tidak diubah labelnya, dan tidak dipakai untuk tuning setelah test.

## 11. Keterbatasan dan tindak lanjut

Dataset hanya mempunyai 24 surat test independen dengan scan sintetis berpasangan. Support beberapa indikator hanya empat atau enam PDF; satu surat dapat mengubah metrik secara besar. Tidak dilakukan uji signifikansi, interval kepercayaan, evaluasi dokumen nyata, variasi scan lapangan, atau pengukuran lintas provider berulang. Kelas seimbang buatan tidak mencerminkan prevalensi produksi.

Penulis/model bantu berbeda dari model evaluasi dan review label manusia telah dikonfirmasi pengguna, tetapi interpretasi label tetap dapat ambigu. Metadata model bantu dilaporkan anggota; review manusia atas output terbaru masih PENDING. Validasi keberadaan kutipan tidak membuktikan kode semantik benar, sehingga drop rate 0% dapat berdampingan dengan FP.

Konfirmasi Dws pada FX-03 (`req_CFA22FCF636DDB0C`) memperlihatkan kesalahan semantik itu berulang: kutipan tenggat konfirmasi yang ada dalam surat tetap dipetakan ke URGENCY_PRESSURE tanpa tekanan yang memenuhi definisi referensi. Keluaran berulang tidak menjamin ketepatan indikator. Pengujian fixture yang dilaporkan tersebut bukan pengukuran frekuensi kesalahan secara umum dan tidak digabungkan dengan metrik test beku.

Kategori mengikuti skoring tetap. Angka kategori tinggi terutama mencerminkan indikator dominan pada data sintetis, bukan vonis keaslian atau keamanan surat. Failure tidak masuk denominator kategori tetapi tetap masuk indikator/reliabilitas; accuracy 1,0000 wajib disertai coverage 47/48. Hasil retry adalah bukti pemulihan teknis, bukan pengganti observasi pertama.

Provider gratis/preview dapat berubah perilaku, ketersediaan, dan latensi. Satu run tidak membuktikan keluaran LLM akan identik meskipun temperature 0 dan fingerprint sama. Budget 900 token serta dua event length GPT-OSS pada dev menunjukkan risiko truncation di dokumen lain; run test Qwen ini tidak mengalami event length. Perbandingan kandidat dev ID/EN tidak setara karena GPT-OSS berhenti lebih awal.

Tindak lanjut manusia adalah review 48 respons melalui indeks, penilaian perbedaan anotasi yang ambigu, dan penyimpanan bukti FX-03 pada TB-04. Dws mereview laporan dan pengecualian retry melalui proses tim. Usulan peningkatan negasi, batas URGENCY_PRESSURE, dan pemisahan inkonsistensi dari ketidakjelasan rincian hanya untuk versi berikutnya pada dev set; test beku dan hasil ini dipertahankan.

## 12. Verifikasi dan keterlacakan

T5-09 memverifikasi offline 96 record terhadap skema bersama, penghitungan ulang `metrics.py`, checksum 19 artefak, serta snapshot/PDF dengan `verify_freeze`. Metrik hasil penghitungan ulang identik dengan metrics tersimpan. Analisis himpunan indikator dan salah kategori memakai raw yang sama. Tidak ada panggilan LLM baru, akses `.env`, perubahan data/kode/artefak, atau klaim kesehatan stack/Anvil baru pada tugas dokumentasi ini.

Penghitungan ulang tanpa menimpa hasil dilakukan di image ai-service dengan mount `ai-eval:/ai-eval:ro`: muat `load_manifest`, `load_run`, lalu bandingkan hasil `calculate_metrics(config, records, entries)` dengan `metrics.json`. Fungsi-fungsi berasal dari `ai-eval/scripts/metrics.py`. Validasi snapshot memakai `freeze_testset.verify_freeze`; checksum dibandingkan dengan `final_checksums.json`. Tidak perlu menjalankan ulang perintah LLM final.

`python scripts/dev.py eval metrics --test` dijalankan pada T5-09: **9 passed**. Unit test memakai data sintetis sementara dan bukan bukti kinerja model. Pemeriksaan laporan juga memvalidasi 15 tautan lokal, tabel terhadap artefak, serta diagnostik 35/47 himpunan indikator pipeline sesuai dan 22/48 salah kategori baseline. `git diff --check` bersih. Riwayat uji implementasi T5-08 ada pada protokol §8.2 dan §8.5; suite seluruh layanan tidak diulang karena perubahan T5-09 hanya dokumentasi.

| Keluaran wajib PLAN T5-09 | Lokasi |
| --- | --- |
| MET-09 klasifikasi kategori | §5 |
| MET-10 indikator | §6 |
| MET-11 pembandingan baseline | §7 |
| MET-12 bahasa/format | §8 |
| MET-13 ekstraksi, MET-14 evidence, MET-15 reliabilitas | §9 |
| Analisis kualitatif kesalahan dan kegagalan | §9–§10 |
| Interpretasi PRD §10.4.4 dan keterbatasan | §4, §10–§11 |

Isi laporan dan bukti pengukuran ACC-06 tersedia; penerimaan akhir mengikuti review manusia. Tidak ada klaim bahwa approval, review hasil, seluruh SCN, atau target kualitas numerik yang tidak ditetapkan sudah selesai.
