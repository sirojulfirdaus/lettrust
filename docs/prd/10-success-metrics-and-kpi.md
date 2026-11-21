# BAB 10. SUCCESS METRICS & EVALUATION

## 10.1 Gambaran Umum

Metrik pada bab ini mengukur keberhasilan prototipe D3: pemenuhan fungsi, kebenaran semantik hasil, kualitas komponen AI, performa terukur, keamanan dasar, dan reprodusibilitas. KPI adopsi dan bisnis tidak diukur karena prototipe menggunakan data sintetis dan tidak memiliki pengguna nyata; hipotesis model bisnis dinyatakan sebagai keterbatasan pada laporan.

Prinsip pengukuran:

1. Setiap metrik memiliki definisi, metode, dan sumber bukti.
2. Metrik tanpa target numerik yang disepakati dilaporkan sebagai hasil aktual, tidak dinilai lulus atau gagal terhadap angka yang dikarang.
3. Kegagalan pengumpulan data dibedakan dari nilai nol.
4. Hasil mock tidak digunakan sebagai data metrik.

## 10.2 Aspek Keberhasilan

| Aspek | Tujuan |
| ----- | ----- |
| Functional Completeness | Seluruh requirement P0 berfungsi sesuai acceptance criteria. |
| Semantic Correctness | Hasil verifikasi tidak pernah menyatakan sesuatu yang tidak diperiksa atau salah menafsirkan gangguan. |
| AI Quality | Kemampuan aktual komponen AI terukur secara empiris dan dibandingkan dengan baseline. |
| Technology Visibility | Peran blockchain dan AI terbukti melalui transaksi nyata, inferensi nyata, dan bukti yang dapat diperiksa. |
| Security & Privacy | Otorisasi berlaku, secret tidak bocor, dan data minimal. |
| Reproducibility | Prototipe dapat dijalankan ulang oleh anggota lain dan saat demo. |

## 10.3 Metrik

### 10.3.1 Fungsi dan Pengujian

| ID | Metrik | Definisi | Target | Status Target |
| ----- | ----- | ----- | ----- | ----- |
| MET-01 | P0 Acceptance Pass Rate | Persentase acceptance criteria P0 yang terverifikasi lulus dengan bukti. | 100% | Mandatory |
| MET-02 | Scenario Pass Rate | Persentase skenario P0 (SCN-01–SCN-22) yang dieksekusi dan lulus. | 100% | Mandatory |
| MET-03 | Evidence Completeness | Persentase test case yang dieksekusi dan memiliki hasil aktual, status, dan bukti. | 100% | Mandatory |
| MET-04 | Open Defect | Jumlah defect Critical atau High yang masih terbuka saat pengumpulan. | 0 | Mandatory |

### 10.3.2 Kebenaran Semantik dan Keamanan

| ID | Metrik | Definisi | Target | Status Target |
| ----- | ----- | ----- | ----- | ----- |
| MET-05 | Semantic Violation | Jumlah kasus pada pengujian di mana gangguan registry ditampilkan sebagai NOT_FOUND, pemeriksaan yang tidak dijalankan menampilkan hasil, atau kegagalan AI menghasilkan kategori. | 0 | Mandatory |
| MET-06 | Authorization Bypass | Jumlah operasi terlindungi yang berhasil dijalankan oleh pihak tanpa hak pada SCN-14. | 0 | Mandatory |
| MET-07 | Secret Exposure | Jumlah secret yang ditemukan pada repository, bundle frontend portal, respons API, atau log. | 0 | Mandatory |
| MET-08 | On-Chain Data Minimization | Jumlah field on-chain yang memuat isi dokumen, kode referensi, atau data pribadi. | 0 | Mandatory |

### 10.3.3 Kualitas AI

| ID | Metrik | Definisi | Target | Status Target |
| ----- | ----- | ----- | ----- | ----- |
| MET-09 | Category Classification | Precision, recall, dan F1 per kelas (LOW, MEDIUM, HIGH), macro F1, accuracy, dan confusion matrix pada test set. | Dilaporkan | Open |
| MET-10 | Indicator Detection | Precision dan recall per kode indikator terhadap label indikator referensi pada test set. | Dilaporkan | Open |
| MET-11 | Baseline Comparison | Selisih MET-09 dan MET-10 antara pipeline AI dan baseline berbasis aturan pada test set yang sama. | Dilaporkan | Open |
| MET-12 | Breakdown per Bahasa dan Format | MET-09 yang dipisahkan untuk bahasa Indonesia/Inggris dan PDF teks/scan. | Dilaporkan | Open |
| MET-13 | Content Extraction Success | Persentase dokumen test set yang menghasilkan teks yang dapat dianalisis, dipisahkan untuk PDF teks dan scan. | Dilaporkan | Open |
| MET-14 | Evidence Validation Drop Rate | Persentase indikator dari model yang dibuang karena kutipan bukti tidak tervalidasi. | Dilaporkan | Open |
| MET-15 | AI Reliability | Persentase permintaan evaluasi yang selesai tanpa UNAVAILABLE, beserta rincian alasan kegagalan. | Dilaporkan | Open |

Target numerik kualitas AI tidak ditetapkan karena dataset bersifat sintetis dan kecil. Kelompok tidak boleh menyatakan target tercapai atau mengklaim akurasi pada data nyata.

### 10.3.4 Performa

| ID | Metrik | Definisi | Target | Status Target |
| ----- | ----- | ----- | ----- | ----- |
| MET-16 | Verification Latency | Median dan P95 durasi API-07 untuk: kode saja; kode dan berkas; AI pada PDF teks; AI pada PDF scan. | Sesuai NFR-03 | Proposed / Open |
| MET-17 | Issuance and Revocation Latency | Median dan P95 durasi API-04 dan API-06 termasuk konfirmasi transaksi. | P95 ≤ 5 detik | Proposed |

### 10.3.5 Reprodusibilitas dan Demo

| ID | Metrik | Definisi | Target | Status Target |
| ----- | ----- | ----- | ----- | ----- |
| MET-18 | Fresh Setup Success | Keberhasilan menjalankan seluruh layanan dari clone baru dengan satu perintah pada minimal dua OS berbeda. | Berhasil pada ≥ 2 OS | Mandatory |
| MET-19 | Restart Persistence | Bukti yang diterbitkan sebelum restart tetap ditemukan dengan status yang sama setelah restart normal. | 100% | Mandatory |
| MET-20 | Demo Flow Duration | Durasi alur demo utama (penerbitan, verifikasi, pencabutan, verifikasi ulang, AI-only) tanpa jeda. | ≤ 5 menit | Proposed |

## 10.4 Protokol Evaluasi AI

Protokol lengkap disimpan di `docs/evaluation/` dan wajib memuat ketentuan berikut.

### 10.4.1 Dataset

| Dimensi | Variasi |
| ----- | ----- |
| Kategori | LOW, MEDIUM, HIGH |
| Bahasa | Indonesia, Inggris |
| Format | PDF berbasis teks, PDF hasil scan |
| Indikator | Seluruh kode taksonomi muncul minimal pada beberapa dokumen MEDIUM/HIGH; dokumen LOW memuat pola wajar yang mirip (misalnya biaya ditanggung perusahaan) untuk menguji false positive |

Komposisi target awal adalah 72 dokumen (3 kategori × 2 bahasa × 2 format × 6 dokumen), dibagi menjadi sekitar 24 dokumen dev set dan 48 dokumen test set dengan proporsi seimbang. Komposisi final ditetapkan pada protokol evaluasi (OI-02).

### 10.4.2 Label dan Pembuatan Data

1. Setiap dokumen memiliki label kategori dan daftar kode indikator referensi.
2. Label kategori konsisten dengan aturan skoring BR-04.06 terhadap indikator referensi.
3. Dokumen dibuat dari template dan variasi yang ditulis atau ditinjau anggota selain pengembang prompt.
4. Apabila model bahasa digunakan untuk membantu membuat variasi, model tersebut berbeda dari model yang dievaluasi, dan setiap dokumen ditinjau manual.
5. PDF scan dibuat dengan merender PDF teks menjadi gambar dengan derau ringan, lalu disimpan sebagai PDF tanpa lapisan teks.
6. Seluruh identitas dalam dokumen adalah fiktif.

### 10.4.3 Prosedur

1. Penyesuaian prompt, normalisasi, dan ambang skoring hanya menggunakan dev set.
2. Test set dibekukan (dicatat checksum-nya) sebelum penyesuaian final.
3. Pipeline AI dan baseline aturan dijalankan sekali pada test set yang sama menggunakan skrip.
4. Identitas model, tanggal, parameter, versi prompt, dan output mentah per dokumen disimpan.
5. Metrik dihitung oleh skrip dari output tersimpan.
6. Kesalahan klasifikasi dianalisis secara kualitatif pada laporan.

### 10.4.4 Interpretasi

Karena kategori diturunkan dari indikator melalui aturan, metrik klasifikasi terutama mencerminkan kemampuan model mendeteksi indikator dan memvalidasi kutipan bukti. Hal ini dinyatakan secara eksplisit pada laporan.

## 10.5 Sumber Data Pengukuran

| Sumber | Metrik |
| ----- | ----- |
| Dokumentasi pengujian (`docs/testing/`) | MET-01–MET-06, MET-19 |
| Pemeriksaan repository, bundle, dan log | MET-07 |
| Pembacaan registry langsung | MET-08 |
| Skrip dan output evaluasi (`docs/evaluation/`) | MET-09–MET-15 |
| Pengukuran durasi pada pengujian | MET-16, MET-17 |
| Uji setup dari clone baru | MET-18 |
| Gladi demo | MET-20 |

## 10.6 Tahapan Evaluasi

| Tahap | Fokus | Output |
| ----- | ----- | ----- |
| Unit & Contract Testing | Logika modul, contract, validator, skoring. | Hasil automated test. |
| Integration Testing | Backend dengan registry dan layanan AI nyata. | Hasil pengujian integrasi dan bukti transaksi. |
| Scenario Testing | SCN-01–SCN-22 secara end-to-end melalui antarmuka atau API. | Test report dengan hasil aktual dan bukti. |
| AI Evaluation | Dataset dan test set beku. | Laporan evaluasi AI. |
| Reproducibility Check | Clone baru pada OS berbeda. | Catatan setup dan bukti. |
| Demo Rehearsal | Alur demo utama. | Durasi dan catatan perbaikan. |

Hasil pengukuran digunakan untuk perbaikan sebelum pengumpulan dan untuk bagian keterbatasan serta rencana pengembangan pada laporan D3.
