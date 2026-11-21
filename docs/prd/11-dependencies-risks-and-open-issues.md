# BAB 11. DEPENDENCIES, RISKS & OPEN ISSUES

## 11.1 Gambaran Umum

Bab ini merupakan register utama ketergantungan, keputusan terbuka, dan risiko pengembangan prototipe Lettrust D3. Status per 21 November 2026.

| Status | Keterangan |
| ----- | ----- |
| Resolved | Keputusan telah ditetapkan dan didokumentasikan. |
| Partially Resolved | Sebagian keputusan telah ditetapkan; validasi atau nilai final masih diperlukan. |
| Open | Keputusan atau validasi belum diselesaikan. |
| Accepted Limitation | Keterbatasan yang diterima secara sadar untuk prototipe dan dinyatakan pada laporan. |
| Deferred | Ditunda ke pengembangan lanjutan (P2) atau setelah P0 selesai (P1). |

Status keputusan tidak menggantikan hasil pengujian.

## 11.2 Dependency Catalog

| ID | Dependency | Kebutuhan | Status |
| ----- | ----- | ----- | ----- |
| DEP-01 | Layanan inferensi AI free tier (utama) | Inferensi model bahasa pra-latih untuk FR-05; akun dan kunci API per anggota. | Required |
| DEP-02 | Layanan inferensi AI cadangan | Alternatif melalui konfigurasi apabila kuota utama habis; hanya data sintetis. | Optional |
| DEP-03 | Docker Desktop / Docker Engine dan Docker Compose | Menjalankan seluruh layanan secara otomatis lintas OS (Windows memerlukan WSL2). | Required |
| DEP-04 | Jaringan blockchain lokal dan tooling smart contract | Menjalankan, menguji, dan men-deploy registry dengan state persisten. | Required |
| DEP-05 | OCR engine dengan data bahasa Indonesia dan Inggris | OCR PDF scan pada CPU. | Required |
| DEP-06 | Ekosistem Python dan Node.js | Backend, layanan AI, dan frontend. | Required |
| DEP-07 | Repository GitHub | Kolaborasi enam anggota. Commit, push, dan merge dilakukan oleh manusia. | Required |
| DEP-08 | Laporan D1–D2 dan guideline II3120 | Baseline desain dan syarat penilaian. | Available |
| DEP-09 | Koneksi internet | Analisis AI melalui layanan eksternal dan pengunduhan dependency/image. | Required |
| DEP-10 | Ketersediaan seluruh anggota | Enam workstream paralel hingga soft deadline 26 November 2026. | Required |

## 11.3 Open Issues Register

| ID | Open Issue | Keputusan / Validasi Diperlukan | Pemilik | Target | Status |
| ----- | ----- | ----- | ----- | ----- | ----- |
| OI-01 | Pemilihan final model LLM | Membandingkan dua kandidat model pada dev set dan membekukan pilihan beserta identitas model. | AI Engineer | Milestone M2 | Open |
| OI-02 | Ukuran dan komposisi final dataset evaluasi | Menetapkan jumlah final, pembagian dev/test, dan peninjau label. Target awal 72 dokumen. | AI Engineer | Milestone M2 | Open |
| OI-03 | Nilai batas operasional | Mengonfirmasi batas ukuran berkas (default 5 MB), halaman AI (default 5), panjang teks, dan batas waktu berdasarkan pengukuran. | Technical Lead | Milestone M3 | Partially Resolved |
| OI-04 | Penerimaan delta D3 oleh dosen | Menyampaikan DLT-01–DLT-16 secara eksplisit pada laporan dan presentasi D3 beserta alasannya. | Project Coordinator | Pengumpulan D3 | Open |
| OI-05 | Kecukupan kuota free tier | Memantau kuota selama pengembangan, evaluasi, dan demo; menyiapkan kunci cadangan dari akun anggota lain. | AI Engineer | Berkelanjutan | Open |
| OI-06 | Kompatibilitas Docker lintas OS | Memvalidasi seluruh image pada Windows (WSL2) dan macOS Apple Silicon. | Technical Lead | Milestone M1 | Open |
| OI-07 | Pembatasan laju partner | Mengimplementasikan FR-06.10 apabila waktu memungkinkan. | Technical Lead | Setelah P0 | Deferred |
| OI-08 | Format final `referenceCode` dan representasi hash | Ditetapkan di SYSTEM_ARCHITECTURE. | Technical Lead, Blockchain Engineer | Milestone M1 | Partially Resolved |
| OI-09 | Pemakaian ulang kode referensi | Pemeriksaan kode saja dapat menampilkan FOUND ACTIVE untuk surat palsu yang menyalin kode asli. Mitigasi: menampilkan nama penerbit dan waktu terbit, serta mendorong unggah berkas (MATCH mengikat bukti ke berkas). | Product | — | Accepted Limitation |
| OI-10 | Kepercayaan pada satu signer | Operator layanan tetap pihak yang dipercaya. Signer per penerbit menjadi rencana pengembangan. | Blockchain Engineer | — | Accepted Limitation |
| OI-11 | Surat melebihi batas halaman AI | Analisis sebagian dinyatakan secara eksplisit. | AI Engineer | — | Accepted Limitation |
| OI-12 | Perbaikan artefak D1–D2 untuk laporan dan deck gabungan | Memperbaiki inkonsistensi deck D1 (positioning, model pendapatan lama, teks berbahasa Melayu, label Blueprint), identitas pada cover, dan koreksi DLT-09. | Project Coordinator | Pengumpulan D3 | Open |
| OI-13 | Verifikasi legal penerbit dunia nyata | Disimulasikan dengan data sintetis dan `evidenceRef`. | Product | — | Accepted Limitation |

### OI-09 — Pemakaian Ulang Kode Referensi

**Uraian:** Kode referensi tidak terikat pada berkas apabila pelamar hanya memasukkan kode. Pihak tidak bertanggung jawab dapat menyalin kode dari surat asli ke surat palsu.

**Mitigasi pada D3:**

1. Hasil FOUND menampilkan nama penerbit dan waktu terbit agar pelamar dapat mencocokkannya dengan surat.
2. Panduan G-05 mendorong pelamar mengunggah berkas.
3. MATCH hanya terjadi apabila berkas identik dengan berkas yang tercatat.

**Rencana lanjutan (P2):** Pengikatan kode dengan identitas penerima tanpa menyimpan data pribadi on-chain, atau mewajibkan berkas untuk pemeriksaan.

### OI-10 — Kepercayaan pada Satu Signer

**Uraian:** Seluruh transaksi registry dikirim oleh satu signer milik Lettrust setelah otorisasi off-chain.

**Nilai yang tetap diperoleh:** Catatan bukti dan riwayat status bersifat append-only dan tamper-evident; perubahan oleh pengelola basis data dapat dideteksi terhadap registry.

**Keterbatasan:** Registry tidak membuktikan secara kriptografis bahwa transaksi berasal dari penerbit tertentu.

**Rencana lanjutan (P2):** Signer atau wallet per penerbit dengan allowlist on-chain.

## 11.4 Risk Register

| ID | Risiko | Severity | Kemungkinan | Mitigasi | Pemilik |
| ----- | ----- | ----- | ----- | ----- | ----- |
| R-01 | Waktu pengembangan tidak cukup untuk seluruh P0 dan bukti pengujian. | Critical | Tinggi | Milestone harian, kontrak dibekukan lebih awal, jalur kritis dipantau, urutan pemangkasan P1 terlebih dahulu, soft deadline 26 November. | Project Coordinator |
| R-02 | Integrasi antarmodul terlambat sehingga pengujian end-to-end tertunda. | High | Sedang | Kontrak OpenAPI dan contoh respons dibekukan pada M1; frontend memakai fixture kontrak selama backend belum siap; integrasi bertahap M2–M3. | Technical Lead |
| R-03 | Kuota free tier habis saat evaluasi atau demo. | High | Sedang | Kunci API per akun anggota, prompt ringkas, evaluasi terjadwal, kunci cadangan, video demo cadangan. | AI Engineer |
| R-04 | Docker atau dependency gagal berjalan pada OS tertentu. | High | Sedang | Validasi image lintas OS pada M1, jalur native terdokumentasi, satu mesin demo yang telah diuji. | Technical Lead |
| R-05 | Hasil model bervariasi antar-eksekusi. | Medium | Sedang | Parameter deterministik, kategori berbasis aturan, validasi kutipan, test set dijalankan sekali dengan output tersimpan. | AI Engineer |
| R-06 | Kualitas OCR rendah pada PDF scan. | Medium | Sedang | Render resolusi memadai, data bahasa Indonesia dan Inggris, metrik terpisah per format, keterbatasan dilaporkan. | AI Engineer |
| R-07 | Scope creep atau perubahan desain di tengah implementasi. | Medium | Sedang | Perubahan melalui PRD/SYSTEM_ARCHITECTURE; coding agent dilarang memperluas cakupan. | Project Coordinator |
| R-08 | Konflik merge pada file bersama. | Medium | Tinggi | Ownership modul, perubahan kontrak bersama hanya melalui Technical Lead, file bersama diubah atas koordinasi. | Technical Lead |
| R-09 | Secret ter-commit atau terekspos ke browser. | High | Sedang | `.gitignore`, contoh konfigurasi tanpa nilai, pemeriksaan sebelum merge, SCN-19. | Seluruh anggota |
| R-10 | Bias evaluasi karena pembuat data dan penyetel prompt adalah orang yang sama. | Medium | Tinggi | Peninjau label lain, test set beku, baseline pembanding, keterbatasan dilaporkan. | AI Engineer |
| R-11 | Anggota berhalangan pada jalur kritis. | High | Sedang | Dokumentasi modul, status dikomunikasikan rutin di grup tim, pasangan cadangan per workstream. | Project Coordinator |
| R-12 | Koneksi internet bermasalah saat presentasi. | Medium | Sedang | Hotspot cadangan, video demo cadangan, skenario non-AI tetap dapat didemonstrasikan. | Project Coordinator |
| R-13 | State registry dan basis data tidak konsisten setelah reset atau restart. | Medium | Sedang | State registry persisten, reset gabungan, SCN-20. | Blockchain Engineer |
| R-14 | Audiens menafsirkan hasil sebagai vonis keaslian. | Medium | Sedang | Label dan disclaimer §9.6, panduan §9.7, penjelasan pada presentasi. | Frontend Engineer (Portal) |
| R-15 | Dosen mempertanyakan perubahan terhadap D2 (misalnya mode tanpa kode). | Medium | Rendah | Delta register DLT, alasan setiap perubahan, keterlacakan ke D1/D2. | Project Coordinator |

Severity merupakan penilaian awal terhadap dampak pada pengumpulan dan demo D3.

## 11.5 Decision Management

Setiap open issue diselesaikan melalui:

1. Identifikasi keputusan yang diperlukan.
2. Penentuan informasi atau pengujian yang dibutuhkan.
3. Validasi teknis atau produk.
4. Persetujuan pemilik issue dan, untuk perubahan P0, koordinator proyek.
5. Dokumentasi keputusan pada PRD, SYSTEM_ARCHITECTURE, atau protokol evaluasi.

Coding agent tidak boleh menutup open issue berdasarkan asumsi sendiri.

## 11.6 Milestone dan Dependensi Pengumpulan

| Milestone | Target | Ketentuan |
| ----- | ----- | ----- |
| M0 | Sabtu, 21 November 2026 | PRD, SYSTEM_ARCHITECTURE, AGENTS.md, dan PLAN.md tersedia. |
| M1 | Minggu, 22 November 2026 | Repository dan Docker berjalan; kontrak OpenAPI dibekukan; kerangka seluruh modul tersedia. |
| M2 | Selasa, 24 November 2026 | Penerbitan dan pencabutan melalui API tercatat di registry; API-08 berfungsi; Console terhubung ke API. |
| M3 | Rabu, 25 November 2026 | API-07 end-to-end untuk seluruh mode; evaluasi AI dijalankan. |
| M4 (soft deadline) | Kamis, 26 November 2026, 23.59 WIB | Seluruh SCN dan test case dieksekusi dengan bukti; bagian D3 laporan selesai. |
| M5 (deadline) | Jumat, 27 November 2026, 23.59 WIB | Laporan PDF dan presentasi gabungan D1–D3 dikumpulkan. |

Rincian tugas, pemilik, dan dependensi berada di `docs/PLAN.md`.

## 11.7 Urutan Pemangkasan Cakupan

Apabila jadwal terancam, cakupan dipangkas dengan urutan:

1. Seluruh requirement P1 (FR-03.06, FR-06.08, FR-06.10, NFR-03.05, NFR-05.07, NFR-06.07).
2. Polesan visual yang tidak memengaruhi acceptance criteria.
3. Optimasi OCR di luar kebutuhan dasar FR-05.03.
4. Jalur Docker dialihkan ke jalur native apabila Docker menghambat seluruh tim, dengan pencatatan sebagai deviasi.

Yang tidak boleh dipangkas:

* Registry blockchain dan layanan AI yang sesungguhnya.
* Semantik pemisahan hasil dan penanganan pengecualian (FR-06).
* Mode Tanpa Kode (DLT-01).
* Pencabutan bukti (MVP-05).
* Evaluasi AI dengan hasil aktual.
* Bukti pengujian.
