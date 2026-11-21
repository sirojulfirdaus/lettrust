# BAB 3. CAKUPAN PRODUK

## 3.1 Cakupan Prototipe D3

Prototipe D3 mencakup layanan Lettrust yang berjalan secara lokal dengan tiga area antarmuka dan empat layanan logis hasil desain SoaML D2.

| Area / Layanan | Peran |
| ----- | ----- |
| Portal Karier Mitra (Simulasi) | Client API yang menyediakan fitur pemeriksaan offer letter bagi pelamar tanpa akun. |
| Lettrust Console — Perusahaan/HR | Registrasi perusahaan, status penerbit, penerbitan bukti, daftar bukti, dan pencabutan. |
| Lettrust Console — Administrator | Peninjauan penerbit, keputusan verifikasi, dan otorisasi HR. |
| SVC-01 Issuer Onboarding & Authorization | API-01, API-02, API-03. |
| SVC-02 Offer Proof Issuance & Lifecycle | API-04, API-05, API-06 dan registry blockchain. |
| SVC-03 Offer Verification | API-07. |
| SVC-04 AI Fraud Risk Analysis | API-08 (internal) serta ekstraksi dan OCR (internal pendukung). |

Penyelesaian prototipe tidak berarti persetujuan penggunaan produksi.

## 3.2 In-Scope

| Area | Cakupan Fungsional | Prioritas | FR |
| ----- | ----- | ----- | ----- |
| Akun dan Autentikasi | Registrasi akun HR/perwakilan perusahaan, login, logout, sesi; akun Administrator melalui seed. | P0 | FR-01 |
| Onboarding Penerbit | Registrasi perusahaan (PENDING), keputusan VERIFIED/REJECTED oleh Administrator, otorisasi HR. | P0 | FR-01 |
| Penerbitan Bukti | Unggah PDF final, SHA-256, `proofId` dan `referenceCode`, pencatatan ACTIVE di blockchain, idempotensi. | P0 | FR-03 |
| Pengelolaan Bukti HR | Daftar dan detail bukti milik penerbit beserta referensi transaksi. | P0 | FR-03, FR-04 |
| Pencabutan Bukti | Pencabutan dengan alasan, pencatatan REVOKED tanpa menghapus riwayat. | P0 | FR-04 |
| Verifikasi melalui Portal | Mode Dengan Kode (kode, berkas opsional, AI opsional) dan Mode Tanpa Kode (berkas, AI). | P0 | FR-02 |
| Pemeriksaan Bukti dan Integritas | Resolusi kode, pembacaan status dari registry, perbandingan hash. | P0 | FR-03 |
| Analisis AI | Ekstraksi teks PDF, OCR PDF scan, deteksi indikator dengan kutipan bukti, kategori berbasis aturan, penjelasan, dan rekomendasi. | P0 | FR-05 |
| Evaluasi AI | Dataset sintetis berlabel, baseline aturan, metrik, dan laporan hasil aktual. | P0 | FR-05 |
| Pemisahan Hasil dan Pengecualian | Tiga komponen hasil, NOT_FOUND vs UNAVAILABLE, NOT_REQUESTED/NOT_CHECKED, hasil parsial, validasi input. | P0 | FR-06 |
| Deployment Lokal | Satu perintah menjalankan seluruh layanan melalui Docker apabila tersedia; reset dan seed data sintetis. | P0 | NFR-05 |
| Pengujian dan Bukti | Eksekusi SCN-01–SCN-07 dan skenario D3, dokumentasi hasil aktual dan bukti. | P0 | Bab 12 |
| Penolakan dokumen aktif duplikat | Mencegah pencatatan berkas identik yang masih ACTIVE pada penerbit yang sama. | P1 | FR-03 |
| Pembatasan laju partner | Rate limit teknis sederhana untuk API-07 (429). | P1 | FR-06 |
| Log verifikasi minimal | Pencatatan enum hasil verifikasi tanpa isi untuk bukti dan metrik. | P1 | FR-06 |

## 3.3 Out-of-Scope

| Area | Batasan |
| ----- | ----- |
| Fungsi job portal | Posting lowongan, pencarian kerja, CV screening, matching, tes, wawancara, penetapan kandidat, payroll, onboarding karyawan. |
| Pembuatan surat | Editor atau generator offer letter, tanda tangan elektronik, pengiriman surat oleh sistem. |
| Integrasi komersial | Integrasi dengan job portal nyata (LinkedIn, JobStreet, Indeed, dan sejenisnya). |
| Billing | Harga, pembayaran, invoice, payment gateway, kuota komersial. |
| KYC nyata | Verifikasi legalitas perusahaan terhadap registri pemerintah atau PSrE. |
| Akun pelamar | Registrasi, login, riwayat pemeriksaan, atau profil pelamar. |
| Pengelolaan tim HR | Undangan atau penambahan HR lain melalui antarmuka; pencabutan otorisasi HR. |
| Pengelolaan partner | Pendaftaran partner dan rotasi token melalui antarmuka. Partner disiapkan melalui seed. |
| Pencarian berdasarkan berkas | Pencarian bukti dari hash berkas tanpa kode referensi (reverse lookup). |
| Tautan atau QR verifikasi | Penyisipan kode, tautan, atau QR ke dalam berkas. |
| Format lain | Gambar (JPG/PNG) sebagai input terpisah, DOCX, dan format selain PDF. |
| Bahasa lain | Dokumen selain bahasa Indonesia dan Inggris. |
| Reaktivasi bukti | Mengubah REVOKED menjadi ACTIVE. |
| Pelatihan model | Training atau fine-tuning model AI; model lokal berbasis GPU. |
| Deployment online | Hosting publik, domain, HTTPS publik, public testnet sebagai keharusan. |
| Signer per penerbit | Wallet atau kunci per penerbit/HR. |
| Penentuan hukum | Penetapan bahwa suatu surat atau perusahaan merupakan penipuan. |

Item out-of-scope yang relevan dicatat sebagai rencana pengembangan (P2) pada laporan D3.

## 3.4 Batasan Fungsional dan Operasional

1. Pelamar tidak memerlukan akun; pemeriksaan dilakukan melalui portal mitra.
2. Portal mitra hanya mengonsumsi API-07. Portal tidak memanggil API-05 maupun API-08.
3. Hanya akun HR terotorisasi dari penerbit berstatus VERIFIED yang dapat mencatat dan mencabut bukti.
4. Administrator tidak dapat menerbitkan atau mencabut bukti dan tidak dapat menjadi anggota penerbit.
5. Satu akun HR hanya berafiliasi dengan satu penerbit.
6. Input berkas hanya PDF. Batas ukuran default prototipe adalah 5 MB per berkas.
7. Analisis AI memproses maksimal 5 halaman pertama secara default. Pemrosesan sebagian dinyatakan secara eksplisit.
8. Analisis AI hanya dijalankan apabila diminta, berkas tersedia, dan persetujuan pemrosesan diberikan.
9. Hash integritas selalu dihitung atas byte berkas asli, tidak pernah atas teks hasil ekstraksi atau OCR.
10. Berkas dan teks hasil ekstraksi tidak disimpan permanen.
11. Seluruh identitas, perusahaan, dan dokumen yang digunakan adalah data sintetis.
12. Kegagalan komponen tidak boleh menghasilkan status atau kategori fiktif.
13. Prototipe dijalankan secara lokal. Ketersediaan internet diperlukan untuk analisis AI karena model diakses melalui layanan inferensi eksternal.

Nilai batas default dapat disesuaikan melalui konfigurasi. Nilai final dan cara konfigurasi ditetapkan di SYSTEM_ARCHITECTURE.

## 3.5 Asumsi

| ID | Asumsi |
| ----- | ----- |
| ASM-01 | Administrator verifikasi adalah pihak independen dari penerbit. Pada prototipe, proses verifikasi identitas disimulasikan menggunakan data sintetis dan referensi bukti (`evidenceRef`). |
| ASM-02 | HR mengunggah berkas final yang sama persis dengan berkas yang dikirimkan kepada pelamar. Perubahan satu byte menghasilkan MISMATCH. |
| ASM-03 | HR mendistribusikan berkas dan kode referensi melalui kanal perusahaan sendiri (TB-07). Lettrust tidak mengirimkan surat. |
| ASM-04 | Portal mitra telah memperoleh persetujuan pelamar sebelum mengirim `includeRisk=true` ke API-07. |
| ASM-05 | Layanan inferensi AI free tier tersedia dengan kuota yang memadai untuk pengembangan, evaluasi, dan demo apabila penggunaannya direncanakan. |
| ASM-06 | Setiap anggota memiliki akses ke perangkat yang mampu menjalankan Docker. Apabila tidak, jalur native terdokumentasi tersedia. |
| ASM-07 | Smart contract pada jaringan pengembangan lokal memenuhi rencana D2 yang mengizinkan local atau public testnet. |
| ASM-08 | Jadwal pengumpulan D3 mengikuti guideline (27 November 2026, 23.59 WIB) dengan soft deadline internal 26 November 2026, 23.59 WIB. |

## 3.6 Status Validasi

Status per 21 November 2026, sebelum implementasi dimulai.

| Aspek | Status |
| ----- | ----- |
| Desain layanan dan proses (D1–D2) | Diserahkan sebagai baseline |
| Kontrak REST API-01–API-08 (D2) | Baseline desain dengan delta D3 |
| Registrasi, verifikasi, dan otorisasi penerbit | Not Implemented |
| Pencatatan bukti pada blockchain | Not Implemented |
| Pencabutan bukti | Not Implemented |
| Verifikasi melalui portal (Mode Dengan Kode) | Not Implemented |
| Mode Tanpa Kode (AI-only) | Not Implemented |
| Ekstraksi teks dan OCR | Not Implemented |
| Analisis risiko AI | Not Implemented |
| Evaluasi AI | Not Implemented |
| Penanganan pengecualian dan hasil parsial | Not Implemented |
| Deployment lokal otomatis | Not Implemented |

Status diperbarui pada dokumentasi pengujian dan tabel Implementation Traceability SYSTEM_ARCHITECTURE berdasarkan bukti aktual. Tabel ini tidak boleh diperbarui tanpa bukti.

## 3.7 Batas Pengembangan dan Penggunaan

### Pengembangan

Pengembangan dilakukan pada environment lokal dengan:

* Jaringan blockchain pengembangan lokal yang nyata.
* Layanan inferensi AI melalui free tier dengan data sintetis.
* Mock AI dan mock registry hanya untuk unit test.
* Data sintetis untuk seluruh identitas dan dokumen.

### Demonstrasi dan Pengujian D3

Seluruh skenario uji dan demonstrasi wajib menggunakan registry blockchain dan layanan AI yang sesungguhnya. Mock tidak boleh digunakan sebagai pengganti pada demo maupun sebagai bukti skenario.

### Produksi

Penggunaan dengan data nyata berada di luar cakupan tugas dan berstatus NO-GO. Penggunaan nyata memerlukan, antara lain, verifikasi legal penerbit, signer per penerbit, kebijakan pemrosesan data oleh penyedia AI, HTTPS, hosting, dan pengujian keamanan menyeluruh.
