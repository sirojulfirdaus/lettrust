# BAB 12. D3 ACCEPTANCE, TESTING & SUBMISSION

## 12.1 Gambaran Umum

Bab ini menetapkan kriteria penerimaan prototipe Lettrust untuk Deliverable 3, katalog skenario uji, ketentuan test case dan bukti, kesiapan demo, serta kelengkapan pengumpulan sesuai guideline Tugas Besar II3120.

Ketentuan D3 pada guideline:

1. Prototipe dibangun berdasarkan D1 dan D2 dengan lingkup yang disesuaikan dengan waktu, sumber daya, dan prioritas kebutuhan layanan.
2. Kedua teknologi terpilih (blockchain dan AI) harus terlihat perannya pada solusi.
3. Pengujian fungsi didokumentasikan: skenario, langkah/input, hasil yang diharapkan, hasil aktual, status pengujian, dan bukti pengujian.
4. Alur layanan utama, interaksi layanan/API, dan kontribusi teknologi didemonstrasikan.
5. Keterbatasan prototipe dan rencana pengembangan dijelaskan.
6. Satu laporan PDF dan satu presentasi memuat D1, D2, dan D3, dengan tabel penugasan anggota di awal.

Keputusan siap kumpul didasarkan pada bukti pengujian, bukan pada penyelesaian kode semata.

## 12.2 D3 Acceptance Gates

| ID | Gate | Kriteria | Metrik |
| ----- | ----- | ----- | ----- |
| ACC-01 | Functional Completeness | Seluruh requirement P0 diimplementasikan dan acceptance criteria-nya terverifikasi lulus. | MET-01 |
| ACC-02 | Technology Visibility | Penerbitan dan pencabutan menghasilkan transaksi nyata pada registry lokal yang dapat dibaca langsung; analisis AI menggunakan inferensi model nyata dengan identitas model tercatat. | MET-08, MET-15 |
| ACC-03 | Scenario Execution | Seluruh SCN-01–SCN-22 dieksekusi; skenario P0 lulus. | MET-02 |
| ACC-04 | Test Documentation | Setiap test case memuat field §12.5 dan bukti. | MET-03 |
| ACC-05 | Semantic & Security Correctness | Tidak ada pelanggaran semantik, bypass otorisasi, kebocoran secret, atau data pribadi on-chain. | MET-05–MET-08 |
| ACC-06 | AI Evaluation | Evaluasi pada test set beku selesai dan laporan memuat hasil aktual serta keterbatasan. | MET-09–MET-15 |
| ACC-07 | Reproducibility | Prototipe berjalan dari clone baru dengan satu perintah pada minimal dua OS; state bertahan setelah restart. | MET-18, MET-19 |
| ACC-08 | Demo Readiness | Alur demo §12.7 berhasil pada mesin demo dan tersedia rekaman cadangan. | MET-20 |
| ACC-09 | Traceability | Laporan D3 memetakan implementasi dan pengujian ke P, FR, MVP, SVC, API, BPMN, dan Blueprint, serta menyajikan delta DLT-01–DLT-16. | — |
| ACC-10 | Submission Completeness | Laporan PDF dan presentasi gabungan D1–D3 memenuhi struktur §12.8. | — |

## 12.3 Functional Acceptance

| Kelompok FR | Kriteria | Skenario Utama |
| ----- | ----- | ----- |
| FR-01 | Registrasi, verifikasi, dan otorisasi berjalan; hak penerbitan ditegakkan di backend. | SCN-13, SCN-14 |
| FR-02 | Portal tanpa akun, dua mode, persetujuan AI, BFF tanpa kebocoran token, hasil tiga panel, dan panduan. | SCN-01, SCN-08, SCN-19 |
| FR-03 | Penerbitan tercatat on-chain setelah konfirmasi, idempotensi, pembacaan status dari registry, integritas MATCH/MISMATCH. | SCN-01, SCN-02, SCN-15, SCN-20 |
| FR-04 | Pencabutan oleh HR berwenang, riwayat tetap, status REVOKED langsung terlihat, transisi tidak valid ditolak. | SCN-03, SCN-14, SCN-16 |
| FR-05 | Ekstraksi, OCR, deteksi indikator dengan kutipan tervalidasi, skoring, mode tanpa kode, ketahanan injection, dan evaluasi. | SCN-06, SCN-08, SCN-09, SCN-12, SCN-18, SCN-22 |
| FR-06 | Tiga komponen hasil, NOT_FOUND vs UNAVAILABLE, NOT_REQUESTED/NOT_CHECKED, hasil parsial, dan validasi input. | SCN-04, SCN-05, SCN-07, SCN-10, SCN-11, SCN-17 |

Ketentuan:

1. Seluruh acceptance criteria P0 wajib lulus.
2. Requirement P1 tidak menjadi blocker kecuali ditetapkan sebaliknya oleh koordinator proyek.
3. Setiap requirement memiliki hasil pengujian yang dapat ditelusuri.
4. Requirement yang belum diuji tidak dinyatakan lulus.
5. Hasil mock tidak menggantikan pengujian integrasi.

## 12.4 Katalog Skenario Uji

SCN-01–SCN-07 berasal dari Tabel 2.23 laporan D2 dengan koreksi DLT-09. SCN-08 dan seterusnya ditambahkan pada D3. Seluruh skenario berprioritas P0.

### 12.4.1 Fixture Minimum

| ID | Fixture | Kegunaan |
| ----- | ----- | ----- |
| FX-01 | Offer letter sintetis wajar, bahasa Indonesia, PDF teks | Penerbitan, SCN-01, SCN-03, SCN-05 |
| FX-02 | Salinan FX-01 dengan perubahan isi (misalnya nominal gaji atau nomor rekening) | SCN-02 |
| FX-03 | Offer letter sintetis berisiko tinggi (biaya administrasi, kontak tidak resmi), bahasa Indonesia, PDF teks | SCN-06, SCN-08 |
| FX-04 | Offer letter sintetis berisiko tinggi, bahasa Inggris, PDF scan | SCN-09 |
| FX-05 | Offer letter sintetis berisiko sedang (tekanan waktu, kontak tidak resmi) | Demo dan pemeriksaan kategori MEDIUM |
| FX-06 | Offer letter sintetis berisi instruksi prompt injection dan permintaan pembayaran | SCN-18 |
| FX-07 | PDF tanpa teks yang dapat dikenali (halaman kosong) | SCN-12 |
| FX-08 | Berkas bukan PDF dengan ekstensi `.pdf` | SCN-11 |
| FX-09 | PDF berukuran di atas batas | SCN-11 |
| FX-10 | Berkas dengan header PDF tetapi rusak | SCN-11 |

Fixture disimpan di repository dan seluruh isinya adalah data sintetis.

### 12.4.2 Skenario D2 (Dikoreksi)

| ID | Skenario | Input / Langkah | Expected Output | FR |
| ----- | ----- | ----- | ----- | ----- |
| SCN-01 | Verifikasi surat sah dan utuh | HR terotorisasi menerbitkan FX-01. Pelamar memeriksa dengan kode tersebut, FX-01, dan `includeRisk=true`. | HTTP 200; `mode=REFERENCE_CHECK`; FOUND; penerbit dan `issuerVerified=true`; ACTIVE; MATCH; panel AI terpisah dengan `state=COMPLETED`. | FR-02, FR-03, FR-05, FR-06 |
| SCN-02 | Deteksi perubahan isi dokumen | Kode bukti FX-01 dengan FX-02. | FOUND; ACTIVE; MISMATCH; peringatan berkas berbeda (G-04). | FR-03.11 |
| SCN-03 | Pemeriksaan surat yang dicabut | HR mencabut bukti FX-01 melalui Console/API-06; pelamar memeriksa ulang kode (dengan FX-01). | API-06 HTTP 201 dengan referensi transaksi; verifikasi FOUND, REVOKED, `revokedAt`, MATCH; panduan G-03; riwayat penerbitan tetap terlihat di Console. | FR-04 |
| SCN-04 | Referensi tidak ditemukan | (a) Kode berformat valid yang tidak terdaftar tanpa berkas. (b) Kode yang sama dengan FX-03 dan `includeRisk=true`. | (a) NOT_FOUND; NOT_CHECKED (`PROOF_NOT_FOUND`); AI NOT_REQUESTED; tidak ada label palsu. (b) NOT_FOUND; NOT_CHECKED (`PROOF_NOT_FOUND`); AI COMPLETED. | FR-03.10, FR-05.01, FR-06.02 |
| SCN-05 | Pemeriksaan dengan kode saja | (a) Kode bukti ACTIVE tanpa berkas, `includeRisk=false`. (b) Kode yang sama tanpa berkas, `includeRisk=true` melalui API. | (a) FOUND; ACTIVE; NOT_CHECKED (`NO_FILE`); AI NOT_REQUESTED; panduan G-05. (b) AI NOT_PERFORMED (`DOCUMENT_CONTENT_UNAVAILABLE`), `category=null`. | FR-03.11, FR-05.01, FR-06.03 |
| SCN-06 | Deteksi indikasi risiko tinggi | FX-03 dengan Mode Tanpa Kode dan persetujuan AI. | AI COMPLETED; indikator `PAYMENT_REQUEST` dan `UNOFFICIAL_CONTACT` dengan kutipan bukti yang terdapat pada teks; kategori HIGH; rekomendasi tidak membayar dan konfirmasi kanal resmi. Lulus hanya apabila keluaran model aktual memenuhi; kegagalan dicatat apa adanya. | FR-05.05–FR-05.07 |
| SCN-07a | Gangguan layanan AI | Layanan AI dihentikan; kode bukti ACTIVE dengan FX-01 dan `includeRisk=true`. | HTTP 200; FOUND; ACTIVE; MATCH; AI UNAVAILABLE (`AI_SERVICE_UNAVAILABLE`), `category=null`. | FR-05.09, FR-06.04 |
| SCN-07b | Gangguan registry | Jaringan blockchain lokal dihentikan; kode bukti ACTIVE dengan FX-01 dan `includeRisk=true`. | HTTP 200; `lookup=UNAVAILABLE` (bukan NOT_FOUND); NOT_CHECKED (`REGISTRY_UNAVAILABLE`); AI COMPLETED. | FR-06.02, FR-06.04 |

### 12.4.3 Skenario Tambahan D3

| ID | Skenario | Input / Langkah | Expected Output | FR |
| ----- | ----- | ----- | ----- | ----- |
| SCN-08 | Mode Tanpa Kode, PDF teks | FX-03 tanpa kode dengan persetujuan AI. | `mode=AI_ONLY`; `lookup=NOT_REQUESTED` (`NO_REFERENCE_CODE`); NOT_CHECKED (`NO_REFERENCE_CODE`); AI COMPLETED; metode `TEXT_LAYER`; log menunjukkan registry tidak dipanggil. | FR-02.04, FR-05.10, FR-06.03 |
| SCN-09 | Mode Tanpa Kode, PDF scan | FX-04 tanpa kode dengan persetujuan AI. | AI COMPLETED; metode `OCR`; indikator memiliki kutipan dari teks OCR. | FR-05.03 |
| SCN-10 | Kombinasi input tidak valid | (a) Tanpa kode dan tanpa berkas. (b) Tanpa kode, dengan berkas, `includeRisk=false`. (c) Kode berformat tidak valid. | (a) 400 `INVALID_INPUT_COMBINATION`. (b) 400 `AI_ONLY_REQUIRES_INCLUDE_RISK`. (c) 400 `INVALID_REFERENCE_CODE_FORMAT`. Registry dan AI tidak dipanggil. | FR-06.05 |
| SCN-11 | Berkas tidak valid | (a) FX-08. (b) FX-09. (c) Berkas kosong. (d) FX-10 dengan kode bukti ACTIVE dan `includeRisk=true`. | (a) 415. (b) 413. (c) 400. (d) HTTP 200; integritas dihitung atas byte (MISMATCH); AI NOT_PERFORMED. | FR-06.06, FR-05.04 |
| SCN-12 | Konten tidak dapat dibaca | FX-07 pada Mode Tanpa Kode. | AI NOT_PERFORMED (`DOCUMENT_CONTENT_UNAVAILABLE`); tanpa kategori atau indikator. | FR-05.04 |
| SCN-13 | Onboarding end-to-end | Registrasi akun → registrasi perusahaan → percobaan penerbitan → keputusan VERIFIED → otorisasi HR → penerbitan. | PENDING tercatat; penerbitan sebelum verifikasi dan otorisasi ditolak (403); setelah VERIFIED dan AUTHORIZED, penerbitan berhasil (201). | FR-01 |
| SCN-14 | Otorisasi negatif | (a) HR penerbit PENDING menerbitkan. (b) HR penerbit REJECTED menerbitkan. (c) HR NOT_AUTHORIZED menerbitkan. (d) HR penerbit A mencabut bukti penerbit B melalui API. (e) Pencabutan lintas penerbit langsung pada contract. (f) Administrator menerbitkan. (g) HR memanggil API-02 dan API-03. (h) Token partner pada API-04. (i) Tanpa token atau token tidak valid. (j) Endpoint internal dipanggil tanpa token internal. (k) Keputusan verifikasi kedua kali. | (a)–(c), (f), (g) 403; (d) ditolak tanpa mengungkap bukti; (e) transaksi ditolak contract; (h) 401/403; (i) 401; (j) ditolak; (k) 409. Tidak ada transaksi registry yang terjadi. | FR-01.05–FR-01.07, FR-04.03 |
| SCN-15 | Idempotensi dan kegagalan registry saat penerbitan | (a) Penerbitan diulang dengan `Idempotency-Key` dan berkas sama. (b) Kunci sama dengan berkas berbeda. (c) Registry dihentikan lalu penerbitan dicoba; registry dijalankan lagi lalu penerbitan diulang. | (a) Bukti sama; hanya satu peristiwa penerbitan di registry. (b) 409 `IDEMPOTENCY_KEY_CONFLICT`. (c) 503 `REGISTRY_UNAVAILABLE` tanpa kode berlaku; setelah registry kembali, penerbitan berhasil. | FR-03.04, FR-03.05 |
| SCN-16 | Pencabutan tidak valid dan kegagalan | (a) Mencabut bukti REVOKED. (b) Memeriksa ketiadaan operasi reaktivasi. (c) Registry dihentikan saat pencabutan. | (a) 409 `PROOF_ALREADY_REVOKED`. (b) Tidak ada endpoint atau fungsi contract reaktivasi. (c) Kegagalan dilaporkan; status tetap ACTIVE di registry. | FR-04.04, FR-04.05 |
| SCN-17 | Gangguan ganda | Registry dan layanan AI dihentikan; kode bukti dengan FX-01 dan `includeRisk=true`. | HTTP 200; `lookup=UNAVAILABLE`; NOT_CHECKED (`REGISTRY_UNAVAILABLE`); AI UNAVAILABLE. | FR-06.04 |
| SCN-18 | Ketahanan prompt injection | FX-06 pada Mode Tanpa Kode. | `PAYMENT_REQUEST` terdeteksi dengan kutipan; kategori sesuai aturan (HIGH); instruksi dalam dokumen tidak menurunkan kategori. Kegagalan dicatat apa adanya. | FR-05.08 |
| SCN-19 | Token partner tidak terekspos | Inspeksi lalu lintas jaringan browser dan bundle JavaScript portal; pemanggilan API-07 dari browser tanpa token. | Token tidak ditemukan; browser hanya memanggil route server portal; pemanggilan langsung tanpa token ditolak 401. | FR-02.07 |
| SCN-20 | Persistensi setelah restart | Menerbitkan dan mencabut bukti, menghentikan seluruh layanan secara normal, menjalankan kembali, lalu memverifikasi. | Bukti ACTIVE dan REVOKED tetap ditemukan dengan status yang sama. | FR-03.03, NFR-04.05 |
| SCN-21 | Reprodusibilitas setup | Clone baru, salin contoh konfigurasi, jalankan satu perintah pada minimal dua OS berbeda. | Seluruh layanan sehat, contract ter-deploy, seed tersedia, portal dan Console dapat diakses. | NFR-05 |
| SCN-22 | Eksekusi evaluasi AI | Skrip evaluasi dijalankan pada test set beku untuk pipeline AI dan baseline. | Metrik MET-09–MET-15, output mentah, identitas model, dan laporan evaluasi dihasilkan. | FR-05.12 |

## 12.5 Ketentuan Test Case dan Bukti

Test case rinci disusun di `docs/testing/` dengan identifier `TC-xxx`. Satu skenario dapat memiliki beberapa test case.

Setiap test case wajib memiliki:

| Field | Keterangan |
| ----- | ----- |
| Test case ID | `TC-xxx` |
| Referensi | SCN, FR/AC, dan MVP terkait |
| Tujuan | Hal yang dibuktikan |
| Prasyarat | Kondisi awal, data seed, dan state layanan |
| Data uji | Fixture dan nilai input |
| Langkah / input | Urutan langkah yang dapat diulang |
| Expected result | Sesuai PRD |
| Actual result | Diisi setelah eksekusi nyata |
| Status | Pass, Fail, Blocked, atau Not Run |
| Bukti | Screenshot, respons JSON, log, referensi transaksi, atau output skrip |
| Penguji dan waktu | Nama anggota dan waktu eksekusi |
| Catatan defect | Defect, perbaikan, dan hasil retest apabila ada |

Ketentuan bukti:

1. Kolom actual result dan status hanya diisi setelah pengujian benar-benar dijalankan.
2. Bukti disimpan di `docs/testing/evidence/<TC-ID>/` atau dirujuk dengan lokasi yang jelas.
3. Bukti tidak memuat secret, token, atau kunci.
4. Bukti integrasi mencantumkan referensi transaksi registry dan, untuk AI, identitas model yang digunakan.
5. Test case yang gagal tetap dilaporkan beserta analisis dan tindak lanjutnya.

## 12.6 Defect Policy

| Severity | Definisi | Ketentuan Pengumpulan |
| ----- | ----- | ----- |
| Critical | Bypass otorisasi, kebocoran secret, data pribadi on-chain, hasil fiktif, NOT_FOUND pada gangguan registry, atau alur utama tidak berjalan. | Wajib diselesaikan. |
| High | Gangguan signifikan pada requirement P0 tanpa workaround layak. | Wajib diselesaikan. |
| Medium | Gangguan terbatas dengan workaround dan tidak melanggar requirement P0. | Dapat ditunda dengan pencatatan sebagai keterbatasan. |
| Low | Masalah minor yang tidak memengaruhi fungsi utama. | Dapat ditunda. |

Defect yang ditunda dicatat beserta dampak dan rencana tindak lanjut pada laporan.

## 12.7 Kesiapan Demo

### 12.7.1 Alur Demo Utama

Durasi target alur demo adalah lima menit atau kurang dari total presentasi 10–15 menit.

| Urutan | Langkah | Teknologi yang Terlihat |
| ----- | ----- | ----- |
| 1 | Administrator memverifikasi penerbit dan mengotorisasi HR (dapat memakai data seed untuk mempersingkat). | Kontrol penerbit hulu |
| 2 | HR menerbitkan bukti FX-01; tampil kode, hash, hash transaksi, dan nomor blok. | Blockchain |
| 3 | Pelamar memeriksa kode, FX-01, dan AI: FOUND, ACTIVE, MATCH, dan panel AI. | Blockchain dan AI terpisah |
| 4 | Pelamar memeriksa kode yang sama dengan FX-02: MISMATCH. | Hash integritas |
| 5 | HR mencabut bukti; pelamar memeriksa ulang: REVOKED. | Lifecycle on-chain |
| 6 | Pelamar memakai Mode Tanpa Kode dengan FX-04 (scan): OCR dan HIGH dengan kutipan. | AI dan OCR |
| 7 | Opsional: layanan AI dihentikan untuk menunjukkan hasil parsial. | Penanganan pengecualian |

### 12.7.2 Persiapan

1. Mesin demo telah menjalankan SCN-21 dan alur demo secara penuh minimal satu kali sebelum presentasi.
2. Data seed dan fixture siap; kunci API dengan kuota yang belum terpakai pada hari demo.
3. Rekaman video alur demo lengkap tersedia sebagai cadangan.
4. Koneksi internet cadangan tersedia untuk analisis AI.

## 12.8 Kelengkapan Pengumpulan

### 12.8.1 Laporan PDF Gabungan

| Bagian | Isi Minimum |
| ----- | ----- |
| Cover | Judul dan identitas kelompok dengan nama lengkap dan NIM seluruh anggota. |
| Pembagian tugas dan kontribusi | Tabel penugasan D1, D2, dan D3 untuk setiap anggota. |
| Pendahuluan | Ringkasan studi kasus, ruang lingkup, dan teknologi pilihan. |
| Deliverable 1 | Hasil D1 dengan perbaikan inkonsistensi yang dicatat (OI-12). |
| Deliverable 2 | Hasil D2 dengan koreksi DLT-09. |
| Deliverable 3 | Ringkasan prototipe dan delta D3 (DLT); arsitektur dan implementasi; peran blockchain dengan bukti transaksi; peran AI dan hasil evaluasi; pengujian fungsi (tabel skenario dan test case dengan hasil aktual dan bukti); demonstrasi alur dan interaksi API; keterbatasan. |
| Penutup | Kesimpulan dan rencana pengembangan (termasuk item P2 dan Accepted Limitation). |
| Referensi | Sumber D1 dan referensi teknis yang digunakan. |
| Lampiran | Blueprint, bukti pengujian tambahan, dan protokol evaluasi. |

### 12.8.2 Presentasi Gabungan

1. Memuat D1, D2, dan D3 dalam satu deck.
2. Memperbaiki inkonsistensi deck D1 yang tercatat pada OI-12.
3. Menyajikan delta D3, demo, peran dua teknologi, hasil pengujian, hasil evaluasi AI, dan keterbatasan.
4. Sesuai durasi presentasi 10–15 menit.

## 12.9 Keputusan Kesiapan

| Area | Keputusan Saat Ini | Kondisi Perubahan |
| ----- | ----- | ----- |
| Pengembangan prototipe | GO | — |
| Demo D3 | Pending | GO apabila ACC-01–ACC-08 terpenuhi. |
| Pengumpulan D3 | Pending | GO apabila ACC-01–ACC-10 terpenuhi atau keterbatasan yang tersisa terdokumentasi tanpa defect Critical/High. |
| Penggunaan produksi | NO-GO | Di luar cakupan tugas. |

## 12.10 Definition of Done — Prototipe D3

Prototipe Lettrust D3 dinyatakan selesai ketika:

* Seluruh requirement P0 telah diimplementasikan dan acceptance criteria-nya terverifikasi dengan bukti.
* Seluruh SCN-01–SCN-22 telah dieksekusi dan didokumentasikan.
* Penerbitan, pencabutan, dan verifikasi menggunakan registry blockchain yang sesungguhnya.
* Analisis AI menggunakan model yang sesungguhnya dan evaluasi telah dilaporkan dengan hasil aktual.
* Tidak ada defect Critical atau High yang terbuka.
* Prototipe dapat dijalankan ulang dari clone baru menggunakan prosedur terdokumentasi.
* Dokumentasi pengujian, tabel Implementation Traceability, dan laporan evaluasi sesuai kondisi aktual.
* Laporan PDF dan presentasi gabungan D1–D3 siap dikumpulkan.
