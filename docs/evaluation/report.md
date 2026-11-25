# Laporan Evaluasi AI Lettrust

Owner: B (PIC 5) · Status: PARTIAL — draf, evaluasi test set belum dijalankan · Ref: PLAN T5-09; PRD §10.4, §10.4.4; ACC-06

## Status dan sumber bukti

Dokumen ini memuat hasil pengembangan pada dev set dan metode yang sudah diimplementasikan. MET-09–MET-15 final belum tersedia: test set belum dibekukan, `metrics.py` T4-07 masih STUB, dan run final pipeline/baseline T5-08 belum dilakukan. ACC-06 dan T5-09 belum dinyatakan selesai. Hasil dev tidak digunakan sebagai angka test set laporan.

Prosedur, provenance, checksum sumber, parameter, dan rincian seluruh run berada di [protokol](protocol.md). Model bantu yang dilaporkan untuk sumber ID adalah `gemini-4-neon-medium`, dengan beberapa klarifikasi dibantu GPT-6 (Codex); EN ditulis Pash dengan bantuan GPT-6 (Codex) pada format/metadata dan anotasi kutipan. Pengguna mengonfirmasi review manusia Pash atas ID dan Van atas EN selesai pada 26 November 2026. Catatan konfirmasi serta batas pembuktiannya dijelaskan pada protokol §1–§2.

## Data dan metode

T5-05 menghasilkan 72 PDF sintetis dari 36 surat, mencakup ID/EN, LOW/MEDIUM/HIGH, dan teks/scan. Split terdiri atas 24 PDF dev dan 48 PDF test. Pasangan teks/scan satu surat berada pada split yang sama; dokumen berpasangan tetap berkorelasi, sehingga 72 PDF tidak mewakili 72 surat independen.

Pipeline memakai fungsi ekstraksi dan analisis runtime: text layer atau Tesseract `ind+eng` pada CPU, LLM pralatih melalui API OpenAI-compatible, validasi taksonomi/kutipan, skoring deterministik, dan rekomendasi templat. Tidak ada training/fine-tuning. Konfigurasi dev saat ini: prompt v1, temperature 0, JSON mode, output maksimum 900 token, reasoning default provider, OCR minimum 25 karakter/halaman pada 300 DPI, dan fuzzy 90 hanya OCR/MIXED. Kandidat adalah `openai/gpt-oss-120b` dan `qwen/qwen3.8-27b` melalui Groq.

Baseline `rules-v1` mendeteksi pola ID/EN dan pengecualian per klausa, lalu memakai validator/skoring/komposisi runtime. Baseline hanya varian evaluasi eksplisit. Output kedua varian mengikuti `EvaluationRecord` v1; prediksi hanya berasal dari teks ekstraksi, tanpa label referensi, ID, atau nama berkas sebagai input detektor.

## Hasil dev yang tersedia

Pada dev ID awal tanggal 25 November (12 PDF), kategori kedua kandidat cocok dengan anotasi pada 12/12 PDF. Himpunan indikator cocok pada GPT-OSS 12/12 dan Qwen 10/12. Dua output GPT-OSS terpotong dan berhasil pada retry runtime tunggal. Ini bukti awal ID saja, dengan format artefak historis yang tetap dipertahankan.

Pada dev ID/EN tanggal 26 November, Qwen dan baseline melalui runner baru masing-masing menyelesaikan 24/24 dokumen dengan record OK dan konfigurasi COMPLETE. Status OK berarti pemrosesan berhasil, bukan bukti bahwa semua kategori/indikator benar. Keduanya memakai daftar dev, checksum manifest, fingerprint sumber, dan parameter ekstraksi yang sama.

| Diagnostik dev | Qwen 3.8 27B | Baseline rules-v1 |
| --- | --- | --- |
| Kategori sesuai anotasi | 24/24 | 12/24 |
| Himpunan indikator persis sesuai anotasi | 20/24 | 6/24 |
| Median latensi ekstraksi + analisis | 1429,5 ms | 607,5 ms |
| P95 latensi ekstraksi + analisis | 2538 ms | 1800 ms |

P95 memakai nearest rank, nilai ke-23 dari 24. Qwen menambah `URGENCY_PRESSURE` pada pasangan EN-HIGH-01 dan `UNOFFICIAL_CONTACT` pada pasangan ID-MEDIUM-03; kategori tetap sesuai. Baseline antara lain mendeteksi `PAYMENT_REQUEST` pada ID-LOW-02/03 yang berlabel LOW dan melewatkan indikator pada EN-HIGH-05 serta beberapa surat MEDIUM. Temuan baseline diteruskan ke Sat; aturan tidak diubah oleh B. Kedua varian tidak membuang indikator pada run ini. Artefak: `ai-eval/results/t5-07-20261126-qwen38-id-en-dev-900/` dan `ai-eval/results/t5-08-20261126-baseline-id-en-dev/`.

Run GPT-OSS baru mencoba empat dokumen: tiga berhasil, kemudian `en-high-05-text` gagal dengan `AI_PROVIDER_ERROR`. Run dihentikan tanpa retry provider atau fallback; konfigurasi tetap RUNNING dan tujuh record yang benar-benar dicoba (empat pipeline, tiga baseline) tersimpan di `tmp/`. Artefak ini tidak memenuhi syarat konsumsi metrics sebagai run lengkap: `ai-eval/results/t5-07-20261126-gptoss120b-id-en-dev-900/`. Penyebab HTTP/provider lebih rinci tidak direkam dan tidak ditebak dari kode umum tersebut.

Usulan terbaru adalah Qwen berdasarkan keberhasilan menyelesaikan cakupan dev ID/EN, dengan parameter tetap; penggantian default masih menunggu persetujuan Dws. Default layanan tetap GPT-OSS dan tidak ada fallback otomatis. GPT-OSS parsial tidak dibandingkan sebagai akurasi satu run lengkap; bukti ini tidak cukup untuk menyimpulkan Qwen lebih akurat atau selalu lebih stabil. Risiko preview Qwen dan keterbatasan anotasi tetap dicatat pada protokol §7.4. Tidak ada penggantian nilai gagal menjadi LOW atau pengisian prediksi/latensi untuk dokumen yang belum dicoba.

## Interpretasi dan pekerjaan yang belum selesai

Kategori dihitung dari indikator tervalidasi dengan aturan tetap. Metrik klasifikasi terutama mengukur kemampuan mendeteksi indikator dan mempertahankan kutipan bukti, bukan kemampuan klasifikasi yang independen dari skoring. Data sintetis kecil, cakupan bahasa/format terbatas, dan korelasi pasangan membatasi generalisasi; hasil tidak membuktikan kemampuan pada surat dunia nyata.

Bagian hasil final menunggu metrics T4-07 dan eksekusi T5-08 pada test set yang dibekukan. Hasil yang diperlukan adalah precision/recall/F1 per kategori, macro F1, accuracy, confusion matrix (MET-09); precision/recall per indikator (MET-10); selisih terhadap baseline (MET-11); rincian bahasa/format (MET-12); keberhasilan ekstraksi (MET-13); indikator yang dibuang validator (MET-14); serta reliabilitas dan alasan UNAVAILABLE (MET-15). Kegagalan dan coverage harus tetap dilaporkan; target numerik kualitas tidak ditetapkan dan tidak diklaim tercapai.
