# BAB 1. INFORMASI DOKUMEN

## 1.1 Identitas Dokumen

| Atribut | Keterangan |
| ----- | ----- |
| Nama Produk | Lettrust |
| Deskripsi Produk | Layanan verifikasi offer letter dan analisis indikasi penipuan rekrutmen yang diintegrasikan ke job portal mitra melalui REST API |
| Judul Proyek Akademik | Deteksi Penipuan Proses Rekrutmen Berbasis Blockchain dan AI |
| Konteks | Tugas Besar II3120 Layanan Sistem & Teknologi Informasi (LaSTI), Institut Teknologi Bandung, 2026 — Kelompok 04 |
| Nama Dokumen | Product Requirements Document (PRD) |
| Versi | 1.2 |
| Tanggal | 21 November 2026 |
| Status | D3 Implementation Baseline |
| Jenis Produk | Verification-as-a-Service, model B2B2C (prototipe akademik) |
| Platform | Web application dan REST API, dijalankan secara lokal |
| Target Pengguna | Pelamar kerja (tanpa akun), perusahaan/HR penerbit, administrator verifikasi, job portal mitra (simulasi) |
| Tahap Pengembangan | Prototipe Deliverable 3 (D3) berbasis desain D1–D2 |
| Development Decision | GO — prototipe lokal dengan data sintetis |
| Production Readiness | Not Ready — penggunaan produksi berada di luar cakupan tugas |
| Referensi Utama | Laporan D1–D2 Kelompok 04, Guideline Tugas Besar II3120, SYSTEM_ARCHITECTURE.md, AGENTS.md, PLAN.md |

## 1.2 Tujuan Dokumen

PRD merupakan acuan utama pengembangan Lettrust. Dokumen ini mendefinisikan kebutuhan produk, cakupan fitur, perilaku sistem, batasan, serta kriteria penerimaan prototipe D3.

Dokumen ini bertujuan untuk:

1. Menetapkan cakupan dan prioritas pengembangan prototipe D3.
2. Mendefinisikan Functional Requirements (FR) beserta business rules dan acceptance criteria yang dapat diverifikasi.
3. Menetapkan Non-Functional Requirements (NFR) yang proporsional untuk prototipe lokal.
4. Menjaga keterlacakan antara kebutuhan D1, desain D2, keputusan D3, implementasi, dan pengujian.
5. Menjadi dasar penyusunan test case, evaluasi AI, demonstrasi, dan bagian D3 laporan.

PRD berfokus pada kebutuhan dan perilaku produk. Rancangan teknis, struktur repository, skema data, kontrak API rinci, konfigurasi, dan deployment dijelaskan dalam `docs/SYSTEM_ARCHITECTURE.md`. Pembagian tugas, tenggat, dan dependensi pekerjaan dijelaskan dalam `docs/PLAN.md`.

## 1.3 Audiens Dokumen

| Audiens | Penggunaan Dokumen |
| ----- | ----- |
| Anggota Kelompok 04 (Product/Project) | Validasi kebutuhan, cakupan, prioritas, dan keterlacakan ke D1/D2. |
| Frontend Engineer | Implementasi halaman, alur, state antarmuka, dan label hasil sesuai FR, Bab 9, dan acceptance criteria. |
| Backend Engineer | Implementasi endpoint, otorisasi, validasi, dan orkestrasi sesuai FR dan business rules. |
| Blockchain Engineer | Implementasi pencatatan, pembacaan, dan pencabutan bukti sesuai FR-03, FR-04, dan BR-02. |
| AI Engineer | Implementasi ekstraksi, OCR, analisis risiko, dan evaluasi sesuai FR-05 dan BR-04. |
| Penguji (seluruh anggota) | Penyusunan test case dan bukti pengujian berdasarkan acceptance criteria dan Bab 12. |
| AI Coding Agent | Referensi implementasi, perubahan kode, pengujian, dan validasi requirement. |

PRD menjadi sumber acuan utama kebutuhan produk. Perubahan perilaku sistem yang tidak tercakup dalam PRD harus melalui pengelolaan perubahan (§1.8), bukan diputuskan sepihak saat implementasi.

## 1.4 Panduan Membaca untuk Anggota dan AI Coding Agent

PRD dipecah per bab agar pembaca cukup membuka bagian yang relevan setelah memahami konteks awal.

| Kebutuhan | Bab yang Dibaca |
| ----- | ----- |
| Memahami produk pertama kali | Bab 1, 2, 3, lalu ringkasan Bab 4 dan 6.2 |
| Implementasi fitur | Bab 6 pada FR terkait, Bab 8 untuk business rules terkait, Bab 9 untuk tampilan |
| Otorisasi dan role | Bab 4 dan BR-01 pada Bab 8 |
| Semantik hasil verifikasi (FOUND, MATCH, dll.) | BR-03 pada Bab 8 dan §9.6 pada Bab 9 |
| Komponen AI | FR-05 pada Bab 6, BR-04 pada Bab 8, Bab 10 |
| Kualitas sistem | Bab 7 |
| Risiko dan keputusan terbuka | Bab 11 |
| Pengujian, demo, dan pengumpulan | Bab 12 |

Bab 1 memuat konvensi identifier dan hierarki dokumen. Pembaca yang telah memahami Bab 1 tidak perlu membacanya ulang pada setiap tugas.

## 1.5 Konvensi Penulisan Kebutuhan

### 1.5.1 Identifikasi Kebutuhan dan Artefak

Seluruh identifier dipertahankan selama kebutuhan atau artefak masih berlaku. Identifier dari D1 dan D2 tidak diubah.

| Elemen | Format | Asal | Keterangan |
| ----- | ----- | ----- | ----- |
| Problem | P-01 | D1 | Permasalahan proses eksisting (P-01–P-05). |
| Blueprint Stage | A1, H1, T1 | D1 | Tahap Service Blueprint As-Is (A1–A6), HR To-Be (H1–H7), Pelamar To-Be (T1–T7). |
| BPMN Activity | AS-01, TB-01 | D2 | Aktivitas BPMN As-Is (AS-01–AS-10) dan To-Be (TB-01–TB-17). |
| Service Interface | SVC-01 | D2 | Layanan SoaML (SVC-01–SVC-04). |
| API Operation | API-01 | D2 | Endpoint bisnis REST (API-01–API-08). |
| MVP Feature | MVP-01 | D2 | Fitur minimum prototipe (MVP-01–MVP-06). |
| Functional Requirement | FR-01 | D2 | Kelompok kebutuhan fungsional (FR-01–FR-06). |
| Detailed Functional Requirement | FR-01.01 | D3 | Kebutuhan spesifik dalam kelompok FR. |
| Acceptance Criteria | AC-01 | D3 | Kriteria penerimaan per detailed FR. |
| Business Rule | BR-01.01 | D3 | Aturan bisnis berkelompok (menggantikan penomoran usulan BR-01–BR-16 pada konteks master; pemetaan di Bab 8). |
| Non-Functional Requirement | NFR-01.01 | D3 | Kebutuhan kualitas sistem. |
| Use Case | UC-01 | D3 | Skenario penggunaan. |
| User Journey | UJ-01 | D3 | Alur interaksi pengguna. |
| Alternative Flow | AF-01 | D3 | Alur alternatif dan pengecualian. |
| Assumption | ASM-01 | D3 | Asumsi yang diterima. |
| D3 Delta | DLT-01 | D3 | Perubahan atau klarifikasi D3 terhadap desain D2. |
| Scenario | SCN-01 | D2/D3 | Skenario uji dan demonstrasi (SCN-01–SCN-07 dari D2; SCN-08 dan seterusnya ditambahkan pada D3). |
| Test Case | TC-001 | D3 | Test case rinci pada dokumentasi pengujian (`docs/testing/`). |
| Metric | MET-01 | D3 | Metrik keberhasilan dan evaluasi. |
| Dependency | DEP-01 | D3 | Ketergantungan pengembangan. |
| Open Issue | OI-01 | D3 | Keputusan atau validasi yang belum selesai. |
| Risk | R-01 | D3 | Risiko pengembangan dan demonstrasi. |
| Acceptance Gate | ACC-01 | D3 | Kriteria penerimaan pengumpulan dan demo D3. |

Penomoran acceptance criteria dimulai kembali dari AC-01 pada setiap detailed functional requirement. Referensi terhadap acceptance criteria wajib menyertakan identifier requirement, misalnya `FR-03.11/AC-02`.

Namespace dipisahkan secara tegas. `BR-0x.yy` adalah business rule PRD, `AD-xx` dan `TOI-xx` adalah keputusan dan isu teknis pada SYSTEM_ARCHITECTURE, `TB-xx` (tugas bersama) dan `T<PIC>-xx` (tugas individu, misalnya `T3-02` = tugas kedua PIC 3) adalah tugas pada PLAN.md, dan `TC-xxx` adalah test case pada dokumentasi pengujian.

### 1.5.2 Prioritas Kebutuhan

| Prioritas | Klasifikasi | Ketentuan | Pemetaan MoSCoW D2 |
| ----- | ----- | ----- | ----- |
| P0 | Critical | Wajib dipenuhi sebelum prototipe D3 dinyatakan siap dikumpulkan dan didemonstrasikan. | Must Have; MVP-05 dinaikkan dari Should Have menjadi P0 pada D3 (DLT-03). |
| P1 | High | Dikerjakan setelah seluruh P0 terpenuhi apabila waktu memungkinkan. Tidak menjadi blocker pengumpulan. | Should Have |
| P2 | Future Consideration | Rencana pengembangan lanjutan; dicatat pada bab penutup laporan. Tidak diimplementasikan pada D3. | Could Have / Won't Have |

Prioritas tidak menentukan status keberhasilan implementasi. Suatu kebutuhan hanya dinyatakan terpenuhi setelah acceptance criteria yang relevan berhasil diverifikasi dengan bukti.

### 1.5.3 Struktur Detailed Functional Requirement

Setiap detailed functional requirement memuat:

* Identifier dan nama requirement.
* Prioritas.
* Deskripsi kebutuhan.
* Business rules terkait, apabila relevan.
* Acceptance criteria yang dapat diverifikasi.
* Dependency, batasan, atau catatan delta D3, apabila relevan.

Setiap kelompok FR memuat keterlacakan ke P, Blueprint, BPMN, SVC, API, MVP, dan SCN.

Requirement harus dapat diverifikasi dan tidak boleh bertentangan dengan requirement lain. Apabila ditemukan konflik, konflik dicatat sebagai Open Issue (Bab 11) dan diselesaikan melalui perubahan spesifikasi yang terdokumentasi.

### 1.5.4 Label Status

| Label | Makna |
| ----- | ----- |
| Not Implemented | Belum ada implementasi. |
| Implemented | Kode tersedia, tetapi belum diverifikasi. |
| Verified (Automated) | Diverifikasi melalui automated test. |
| Verified (Manual) | Diverifikasi melalui pengujian manual dengan bukti. |
| Partial | Sebagian acceptance criteria terpenuhi. |
| Deferred | Ditunda ke pengembangan lanjutan (P2). |
| Blocked | Terhambat dependency atau isu yang belum selesai. |

Status tidak boleh dinaikkan tanpa bukti. Hasil mock tidak dapat digunakan sebagai bukti verifikasi integrasi aktual.

## 1.6 Referensi dan Pengelolaan Dokumentasi

### 1.6.1 Hierarki Rujukan

Apabila terdapat ketidaksesuaian antarsumber, gunakan urutan berikut:

1. Guideline resmi Tugas Besar II3120 (deskripsi dan instruksi tugas, 21 Oktober 2026) untuk syarat penilaian dan artefak wajib.
2. Keputusan produk D3 yang tercatat pada PRD ini, khususnya Delta Register (§1.7).
3. Laporan D1–D2 terbaru Kelompok 04 sebagai baseline desain. Bagian 2.3 laporan adalah acuan kontrak REST, kecuali yang diubah melalui delta D3.
4. Presentasi D1–D2 sebagai representasi ringkas. Apabila berbeda dengan laporan, laporan yang berlaku.
5. Dokumen historis sebagai arsip, bukan kontrak implementasi.

### 1.6.2 Dokumen Proyek

| Referensi | Fungsi |
| ----- | ----- |
| `docs/prd/` (dokumen ini) | Kebutuhan, cakupan, perilaku produk, business rules, dan acceptance criteria. |
| `docs/SYSTEM_ARCHITECTURE.md` | Rancangan teknis, komponen, kontrak API rinci, data, konfigurasi, deployment, dan keputusan arsitektur. |
| `docs/PLAN.md` | Tugas, pemilik, dependensi, tenggat, dan kriteria selesai. |
| `docs/testing/` | Test case, hasil aktual, status, dan bukti pengujian D3. |
| `docs/evaluation/` | Dataset, protokol, dan hasil evaluasi AI. |
| `AGENTS.md` | Instruksi kerja AI coding agent dalam repository. |
| `contracts/openapi.json` | Kontrak API aktual yang dihasilkan backend. |
| Laporan dan presentasi D1–D2 | Baseline desain layanan, proses, SoaML, dan REST API. |

### 1.6.3 Ketentuan Penggunaan Dokumentasi

1. PRD menjadi acuan kebutuhan dan perilaku produk.
2. SYSTEM_ARCHITECTURE menjadi acuan keputusan teknis dan implementasi.
3. PLAN.md menjadi acuan pembagian dan urutan pekerjaan.
4. Dokumentasi pengujian dan evaluasi menjadi acuan kemampuan yang telah dibuktikan.
5. AGENTS.md mengatur prosedur kerja coding agent tanpa menggantikan PRD maupun arsitektur.
6. Ketidaksesuaian antardokumen diselesaikan melalui perubahan spesifikasi yang terdokumentasi, bukan melalui asumsi implementasi.
7. Kemampuan yang belum diuji tidak boleh dianggap telah tervalidasi, baik di dokumen, kode, laporan, maupun presentasi.

## 1.7 Baseline Pengembangan dan Delta D3

### 1.7.1 Baseline

PRD v1.0 disusun berdasarkan desain D1–D2 yang telah diserahkan serta keputusan produk dan teknis D3 yang disepakati Kelompok 04 pada 21 November 2026.

Baseline pengembangan menetapkan:

1. Lettrust adalah layanan verifikasi independen yang diintegrasikan ke job portal mitra melalui REST API, bukan job portal.
2. Model bisnis B2B2C: job portal sebagai pelanggan B2B dan kanal distribusi; perusahaan/HR dan pelamar sebagai pengguna tanpa biaya langsung. Model ini bersifat hipotesis dan tidak diimplementasikan sebagai billing.
3. Blockchain mencatat bukti penerbitan (hash, referensi penerbit, status ACTIVE/REVOKED) pada smart contract yang berjalan di jaringan pengembangan lokal.
4. AI menganalisis indikasi penipuan pada isi offer letter menggunakan model bahasa pra-latih yang sudah tersedia, tanpa pelatihan atau fine-tuning, dan dievaluasi secara empiris pada dataset sintetis berlabel berskala kecil.
5. Hasil bukti penerbitan, integritas berkas, dan analisis AI disajikan terpisah tanpa vonis tunggal "asli/palsu" atau "aman/penipuan".
6. Pelamar tidak memerlukan akun. Job portal mitra adalah client API terautentikasi.
7. Prototipe dijalankan secara lokal menggunakan data sintetis.

### 1.7.2 Delta Register D3

Delta berikut mengubah atau mengklarifikasi desain D2. Setiap delta wajib tercermin pada laporan D3 dan tidak boleh mengubah isi D1/D2 yang telah diserahkan secara diam-diam.

| ID | Delta | Jenis | Artefak D1/D2 Terdampak |
| ----- | ----- | ----- | ----- |
| DLT-01 | Mode analisis AI tanpa kode referensi: pelamar dapat mengunggah PDF tanpa `referenceCode` untuk analisis AI saja. Tidak ada pemanggilan registry dan bukan pencarian hash terbalik. | Perubahan perilaku | T3–T5, TB-09, TB-11, SVC-03, API-07, FR-02, FR-05, FR-06, MVP-03, MVP-04, MVP-06, SCN-06 |
| DLT-02 | Representasi eksplisit pemeriksaan yang tidak dijalankan: `proofCheck.lookup = NOT_REQUESTED` serta field `reason` pada setiap komponen hasil. | Perluasan kontrak (aditif) | API-07, FR-06, Tabel status D2 |
| DLT-03 | Pencabutan bukti (MVP-05) dinaikkan dari Should Have menjadi P0. | Perubahan prioritas | MVP-05, FR-04, SCN-03 |
| DLT-04 | Input dokumen dibatasi pada PDF berbasis teks dan PDF hasil scan (dengan OCR) berbahasa Indonesia dan Inggris. Format gambar terpisah dan DOCX tidak didukung. | Klarifikasi cakupan | API-04, API-07, FR-05, MVP-04 |
| DLT-05 | Pendekatan AI ditetapkan: model bahasa pra-latih melalui layanan inferensi free tier, deteksi indikator berbasis taksonomi dengan kutipan bukti, kategori ditentukan aturan skoring, serta evaluasi empiris terhadap baseline aturan. | Penetapan desain | SVC-04, API-08, FR-05, MVP-04 |
| DLT-06 | Ekstraksi teks dan OCR disediakan sebagai endpoint internal pendukung pada layanan AI. API-08 tetap menerima teks sesuai D2. | Penetapan desain | API-08, TB-13, 2.4.4 laporan D2 |
| DLT-07 | Hasil `proofCheck` menyertakan identitas penerbit (nama perusahaan), waktu penerbitan, dan waktu pencabutan apabila REVOKED agar pelamar dapat mencocokkan penerbit dengan surat. | Perluasan kontrak (aditif) | API-07, FR-02, FR-03 |
| DLT-08 | Hasil `riskAnalysis` menyertakan rincian indikator (kode, tingkat, kutipan bukti), alasan status, dan metode ekstraksi. | Perluasan kontrak (aditif) | API-07, API-08, FR-05 |
| DLT-09 | Koreksi D2: portal tidak memanggil API-05 (deskripsi MVP-03); SCN-05 menyertakan `includeRisk` eksplisit; SCN-06 dilengkapi input sesuai mode; SCN-07 dipecah menjadi dua subkasus; koreksi kutipan JSON contoh API-07. | Koreksi | MVP-03, Tabel 2.23, contoh API-07 |
| DLT-10 | Deployment lokal dengan Docker Compose otomatis apabila Docker tersedia. Komunikasi lokal menggunakan HTTP pada localhost sebagai deviasi terdokumentasi dari desain HTTPS D2. | Penetapan desain | 2.3 laporan D2 (konvensi komunikasi), arsitektur 2.4.4 |
| DLT-11 | Onboarding disederhanakan: akun yang mendaftarkan perusahaan otomatis tercatat sebagai akun HR terafiliasi. Penambahan HR lain melalui antarmuka berada di luar cakupan D3; skenario multi-issuer disiapkan melalui seed data. Endpoint pendukung akun (registrasi akun, login) ditambahkan. | Penetapan desain | H1–H3, TB-01–TB-04, SVC-01, API-01–API-03 |
| DLT-12 | Validasi kombinasi input API-07: tanpa kode dan tanpa berkas ditolak; tanpa kode dengan `includeRisk` tidak bernilai `true` ditolak; format kode tidak valid ditolak. | Penetapan kontrak | API-07, FR-06 |
| DLT-13 | HR mengunggah offer letter final; tidak ada editor atau pembuatan surat di dalam sistem. | Klarifikasi | Lampiran C H4 laporan D2 |
| DLT-14 | API-07 mengembalikan 200 untuk setiap permintaan valid yang diproses, termasuk ketika registry atau AI tidak tersedia (dinyatakan melalui status komponen). 503 hanya digunakan apabila layanan tidak dapat memproses permintaan sama sekali. | Klarifikasi kontrak | API-07, Tabel 2.18 laporan D2 |
| DLT-15 | Pelamar memasukkan kode referensi secara manual. Tautan atau QR verifikasi berada di luar cakupan D3. | Klarifikasi cakupan | Lampiran B/C (kode/tautan) |
| DLT-16 | Nama produk ditetapkan "Lettrust". Portal simulasi menggunakan nama generik "Portal Karier Mitra (Simulasi)". | Penetapan | Seluruh artefak antarmuka |

Detail kontrak teknis untuk DLT-01, DLT-02, DLT-07, DLT-08, DLT-12, dan DLT-14 ditetapkan di SYSTEM_ARCHITECTURE.

## 1.8 Pengelolaan Perubahan

1. Perubahan kebutuhan atau perilaku produk diperbarui dalam PRD dan dicatat pada Riwayat Revisi.
2. Perubahan teknis diperbarui dalam SYSTEM_ARCHITECTURE.
3. Perubahan yang memengaruhi desain D2 dicatat sebagai delta baru (DLT-xx).
4. Perubahan identifier atau acceptance criteria harus terdokumentasi beserta alasannya.
5. Perubahan cakupan P0 memerlukan persetujuan koordinator proyek (PIC 1).
6. Coding agent tidak boleh mengubah requirement, menutup open issue, atau memperluas cakupan berdasarkan asumsi sendiri.

## 1.9 Glosarium

| Istilah | Definisi |
| ----- | ----- |
| Offer letter | Surat penawaran kerja yang disampaikan perusahaan kepada kandidat setelah keputusan menawarkan pekerjaan. |
| Penerbit (issuer) | Perusahaan yang terdaftar di Lettrust dan berhak mencatat bukti setelah diverifikasi administrator. |
| HR terotorisasi | Akun HR yang berafiliasi dengan penerbit berstatus VERIFIED dan telah diotorisasi administrator. |
| Bukti penerbitan (proof) | Catatan pada registry blockchain yang memuat hash berkas, referensi penerbit, dan status lifecycle. |
| `proofId` | Identitas internal bukti. Tidak ditampilkan sebagai input bagi pelamar. |
| `referenceCode` | Kode yang dibagikan HR kepada pelamar untuk memeriksa bukti. Dipetakan secara internal ke `proofId`. |
| `issuerId` | Identitas penerbit pada Lettrust. |
| `documentHash` | Hash SHA-256 atas byte berkas offer letter final. |
| `lifecycleStatus` | Status bukti pada registry: ACTIVE atau REVOKED. |
| Registry | Smart contract blockchain yang menyimpan bukti penerbitan. |
| Verifikasi | Permintaan pemeriksaan oleh pelamar melalui portal mitra (API-07). |
| Mode Dengan Kode | Verifikasi menggunakan `referenceCode`, dengan berkas dan analisis AI opsional. |
| Mode Tanpa Kode (AI-only) | Verifikasi tanpa `referenceCode`; hanya analisis AI terhadap berkas. |
| Integritas berkas | Kesamaan byte berkas yang diperiksa dengan berkas yang tercatat, dinyatakan MATCH atau MISMATCH. |
| Indikator risiko | Pola pada isi surat yang perlu diwaspadai, misalnya permintaan pembayaran. |
| Kategori risiko | LOW, MEDIUM, atau HIGH. Merupakan indikasi, bukan putusan hukum atau penentu keaslian. |
| Job portal mitra / partner | Platform rekrutmen yang mengintegrasikan Lettrust melalui API-07. Pada prototipe disimulasikan oleh Portal Karier Mitra (Simulasi). |
| BFF | Backend-for-Frontend: bagian server portal mitra yang menyimpan token partner dan meneruskan permintaan ke API-07. |
| Data sintetis | Identitas, perusahaan, dan dokumen buatan untuk pengujian, bukan data nyata. |

## 1.10 Riwayat Revisi

| Versi | Tanggal | Deskripsi Perubahan |
| ----- | ----- | ----- |
| 1.0 | 21 November 2026 | PRD awal D3 berdasarkan desain D1–D2, keputusan produk D3, dan keputusan teknis yang disepakati Kelompok 04. |
| 1.1 | 21 November 2026 | Jadwal dipercepat: soft deadline (feature freeze) Selasa 24 November 2026 23.59 WIB (ASM-08, DEP-10, R-01, §11.6); skema ID tugas PLAN menjadi `TB-xx`/`T<PIC>-xx`; OI-06 diperbarui sesuai perangkat tim (Windows dan Linux). Tidak ada perubahan kebutuhan fungsional. |
| 1.2 | 21 November 2026 | Rincian M2 diselaraskan dengan PLAN.md: modul mandiri pukul 12.00; pemilihan model (OI-01) dan pembekuan test set pukul 23.59 pada hari yang sama. OI-01 mencakup pemilihan provider, tidak hanya model. |
