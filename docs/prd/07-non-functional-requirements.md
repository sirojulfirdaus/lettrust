# BAB 7. NON-FUNCTIONAL REQUIREMENTS

## 7.1 Gambaran Umum

Non-Functional Requirements (NFR) menetapkan standar kualitas Lettrust yang proporsional untuk prototipe lokal D3: keamanan, privasi, performa, keandalan, reprodusibilitas, kegunaan, kualitas output AI, kemudahan pemeliharaan, dan keterlacakan.

Seluruh NFR P0 wajib diverifikasi sebelum prototipe dinyatakan siap dikumpulkan. Target yang berstatus *Proposed* diukur dan dilaporkan apa adanya; target tersebut bukan janji performa produksi.

## 7.2 NFR-01 — Security

| ID | Requirement | Prioritas |
| ----- | ----- | ----- |
| NFR-01.01 | Password akun disimpan menggunakan algoritma hash password yang sesuai (bukan hash umum tanpa salt) dan tidak pernah dikembalikan atau dicatat. | P0 |
| NFR-01.02 | Token sesi ditandatangani, memiliki masa berlaku terbatas, dan divalidasi pada setiap endpoint terlindungi. | P0 |
| NFR-01.03 | Autentikasi, role, status penerbit, status otorisasi HR, dan kepemilikan resource diperiksa di backend pada setiap operasi terlindungi. | P0 |
| NFR-01.04 | Token partner disimpan sebagai hash di Lettrust, hanya tersedia sebagai secret di server portal, dan tidak pernah dikirim ke browser. | P0 |
| NFR-01.05 | Endpoint `/internal/v1/*` hanya dapat dipanggil oleh backend Lettrust menggunakan token internal dan tidak diekspos sebagai API publik. | P0 |
| NFR-01.06 | Kunci privat signer registry, kunci API penyedia model, token internal, dan secret JWT hanya tersedia melalui konfigurasi environment, tidak di-commit, tidak dicatat di log, dan tidak dikembalikan oleh API. | P0 |
| NFR-01.07 | Input divalidasi di backend, termasuk tipe dan ukuran berkas, format kode referensi, field wajib, dan enum yang diizinkan. | P0 |
| NFR-01.08 | Isi dokumen diperlakukan sebagai data tidak tepercaya dan tidak dapat mengubah instruksi analisis AI, aturan skoring, atau otorisasi. | P0 |
| NFR-01.09 | Antarmuka tidak merender konten dari dokumen atau output model sebagai HTML atau skrip yang dapat dieksekusi. | P0 |
| NFR-01.10 | CORS backend hanya mengizinkan origin Lettrust Console pada environment lokal. Portal mitra memanggil backend dari sisi server. | P0 |
| NFR-01.11 | Kegagalan pemeriksaan otorisasi menghasilkan penolakan, bukan pemberian akses berdasarkan asumsi. | P0 |
| NFR-01.12 | Registry hanya menerima transaksi tulis dari signer Lettrust. Contract menolak pencatatan ulang `proofId` dan pencabutan lintas penerbit. | P0 |
| NFR-01.13 | Kunci signer yang digunakan adalah kunci pengembangan lokal yang tidak memiliki nilai di jaringan publik dan diberi label demikian. | P0 |
| NFR-01.14 | Komunikasi lokal menggunakan HTTP pada localhost sebagai deviasi terdokumentasi dari desain HTTPS D2 (DLT-10). Deviasi ini dinyatakan pada laporan D3. | P0 |

**Verifikasi:** Uji otorisasi negatif (SCN-14), pemeriksaan bundle dan lalu lintas browser portal (SCN-19), uji prompt injection (SCN-18), uji contract, pemeriksaan repository terhadap secret, dan code review.

## 7.3 NFR-02 — Privacy & Data Minimization

| ID | Requirement | Prioritas |
| ----- | ----- | ----- |
| NFR-02.01 | Berkas yang diunggah HR maupun pelamar tidak disimpan permanen. Berkas hanya berada di memori atau penyimpanan sementara selama permintaan diproses. | P0 |
| NFR-02.02 | Teks hasil ekstraksi tidak disimpan setelah permintaan selesai. | P0 |
| NFR-02.03 | Registry blockchain tidak menyimpan isi dokumen, kode referensi, data pribadi, nama perusahaan, maupun kontak. | P0 |
| NFR-02.04 | Data yang dikirim ke penyedia model AI dibatasi pada teks hasil ekstraksi. | P0 |
| NFR-02.05 | Log aplikasi tidak memuat isi berkas, teks dokumen, respons mentah model, password, token, atau kunci. | P0 |
| NFR-02.06 | Pelamar tidak diminta memberikan data pribadi dan tidak memiliki akun. | P0 |
| NFR-02.07 | Seluruh data pengujian, seed, dataset evaluasi, dan demo merupakan data sintetis. | P0 |
| NFR-02.08 | Penggunaan layanan AI pihak ketiga hanya dengan data sintetis, termasuk layanan yang ketentuannya mengizinkan penggunaan data untuk peningkatan produk. | P0 |

**Verifikasi:** Inspeksi penyimpanan dan basis data setelah skenario uji, inspeksi log, inspeksi data on-chain, dan peninjauan dataset.

## 7.4 NFR-03 — Performance & Responsiveness

| ID | Requirement | Prioritas |
| ----- | ----- | ----- |
| NFR-03.01 | Waktu respons API-07 diukur terpisah untuk kode saja, kode dengan berkas, analisis AI pada PDF teks, dan analisis AI pada PDF scan. | P0 |
| NFR-03.02 | Waktu penerbitan dan pencabutan bukti (termasuk konfirmasi transaksi) diukur. | P0 |
| NFR-03.03 | Antarmuka menampilkan indikator pemrosesan untuk operasi yang memerlukan waktu, termasuk penerbitan, pencabutan, dan verifikasi. | P0 |
| NFR-03.04 | Batas waktu pemrosesan AI, batas waktu registry, dan batas waktu server portal dapat dikonfigurasi, dan batas waktu server portal lebih besar daripada batas waktu pemrosesan Lettrust. | P0 |
| NFR-03.05 | Pemrosesan permintaan tidak memblokir pemrosesan permintaan lain pada skala demo (beberapa pengguna bersamaan). | P1 |

### Target Performa Awal

Diukur pada laptop pengembangan dengan seluruh layanan berjalan lokal.

| Metrik | Target / Baseline | Status |
| ----- | ----- | ----- |
| API-07 kode saja | P95 ≤ 2 detik | Proposed |
| API-07 kode dan berkas tanpa AI | P95 ≤ 3 detik untuk berkas ≤ 5 MB | Proposed |
| API-04 penerbitan (termasuk konfirmasi transaksi lokal) | P95 ≤ 5 detik | Proposed |
| API-07 dengan AI, PDF teks | Diukur dan dilaporkan | Open |
| API-07 dengan AI, PDF scan | Diukur dan dilaporkan | Open |
| Batas waktu pemrosesan AI | Dapat dikonfigurasi; default ditetapkan di SYSTEM_ARCHITECTURE | Open |

Latensi AI bergantung pada layanan inferensi eksternal dan OCR berbasis CPU. Nilai aktual dilaporkan tanpa dinyatakan sebagai SLA.

**Verifikasi:** Pengukuran durasi pada skenario uji dan skrip evaluasi AI (MET-16, MET-17).

## 7.5 NFR-04 — Reliability & Consistency

| ID | Requirement | Prioritas |
| ----- | ----- | ----- |
| NFR-04.01 | Status ACTIVE atau REVOKED hanya dinyatakan setelah transaksi registry terkonfirmasi. | P0 |
| NFR-04.02 | Pengulangan permintaan penerbitan dan pencabutan dengan `Idempotency-Key` yang sama tidak menghasilkan transaksi ganda. | P0 |
| NFR-04.03 | Transaksi penerbitan dan pencabutan dikirim secara berurutan oleh signer sehingga tidak terjadi konflik nonce pada permintaan bersamaan. | P0 |
| NFR-04.04 | Kegagalan registry atau AI pada verifikasi menghasilkan hasil parsial yang benar sesuai FR-06.04. | P0 |
| NFR-04.05 | State registry blockchain lokal bertahan ketika layanan dihentikan dan dijalankan kembali secara normal. | P0 |
| NFR-04.06 | Proses reset selalu mereset basis data dan registry secara bersamaan sehingga pemetaan kode tidak menunjuk bukti yang tidak ada. | P0 |
| NFR-04.07 | Setiap layanan menyediakan health check yang membedakan layanan aktif dan dependensi yang tidak tersedia. | P0 |
| NFR-04.08 | Batas waktu diterapkan pada panggilan ke registry, layanan AI internal, dan penyedia model; tidak ada panggilan yang menunggu tanpa batas. | P0 |
| NFR-04.09 | Pengulangan otomatis terhadap penyedia model dibatasi (maksimal satu kali untuk output tidak valid) dan tidak dilakukan berulang saat kuota habis. | P0 |

**Verifikasi:** SCN-07, SCN-15, SCN-17, SCN-20, dan uji restart layanan.

## 7.6 NFR-05 — Reproducibility & Local Deployment

| ID | Requirement | Prioritas |
| ----- | ----- | ----- |
| NFR-05.01 | Seluruh layanan dapat dijalankan dengan satu perintah lintas OS. Apabila Docker tersedia dan aktif, perintah tersebut menjalankan seluruh layanan melalui Docker Compose secara otomatis. | P0 |
| NFR-05.02 | Apabila Docker tidak tersedia, perintah memberikan pesan yang jelas dan langkah native yang terdokumentasi. | P0 |
| NFR-05.03 | Penyiapan otomatis mencakup jaringan blockchain lokal, deployment contract, pembuatan skema basis data, dan seed data sintetis. | P0 |
| NFR-05.04 | Lingkungan didukung pada Windows (Docker Desktop dengan WSL2), macOS (termasuk Apple Silicon), dan Linux. | P0 |
| NFR-05.05 | Konfigurasi menggunakan berkas environment lokal yang tidak di-commit, dengan contoh konfigurasi tanpa nilai rahasia di repository. | P0 |
| NFR-05.06 | Konfigurasi divalidasi saat layanan dijalankan; konfigurasi wajib yang hilang menghasilkan pesan yang jelas dan layanan tidak berjalan dengan perilaku fiktif. | P0 |
| NFR-05.07 | Anggota dapat menjalankan sebagian layanan secara native untuk pengembangan sementara layanan lain berjalan di Docker. | P1 |
| NFR-05.08 | Versi dependency dikunci melalui lock file atau versi eksplisit. | P0 |

**Verifikasi:** SCN-21 (clone baru hingga layanan berjalan pada minimal dua OS berbeda) dan README.

## 7.7 NFR-06 — Usability & Accessibility

| ID | Requirement | Prioritas |
| ----- | ----- | ----- |
| NFR-06.01 | Antarmuka menggunakan bahasa Indonesia yang jelas. Istilah teknis disertai penjelasan untuk pelamar. | P0 |
| NFR-06.02 | Status hasil tidak dibedakan hanya dengan warna; setiap status memiliki teks dan ikon. | P0 |
| NFR-06.03 | Formulir utama (login, registrasi, penerbitan, verifikasi) dapat digunakan melalui keyboard dengan label yang terhubung ke field. | P0 |
| NFR-06.04 | Portal mitra dapat digunakan pada desktop dan browser mobile. Lettrust Console dioptimalkan untuk desktop. | P0 |
| NFR-06.05 | Loading, empty, success, error, disabled, dan confirmation states tersedia dan konsisten. | P0 |
| NFR-06.06 | Tindakan destruktif (pencabutan, keputusan verifikasi) memerlukan konfirmasi. | P0 |
| NFR-06.07 | Kontras dan focus state mengacu pada WCAG 2.2 Level AA. | P1 |

**Verifikasi:** Pengujian manual antarmuka, navigasi keyboard, dan tampilan responsif.

## 7.8 NFR-07 — AI Output Quality & Integrity

| ID | Requirement | Prioritas |
| ----- | ----- | ----- |
| NFR-07.01 | Setiap indikator yang disajikan memiliki kutipan bukti yang tervalidasi terhadap teks dokumen. | P0 |
| NFR-07.02 | Kategori risiko diturunkan secara deterministik dari indikator tervalidasi. | P0 |
| NFR-07.03 | Output model divalidasi terhadap skema sebelum digunakan. | P0 |
| NFR-07.04 | Parameter inferensi dibuat sedeterministik mungkin dan identitas model dicatat pada setiap evaluasi. | P0 |
| NFR-07.05 | Evaluasi menggunakan test set terpisah dan dibandingkan dengan baseline; evaluasi tidak hanya mengandalkan penilaian model terhadap outputnya sendiri. | P0 |
| NFR-07.06 | Keterbatasan data sintetis, ukuran dataset, dan kemungkinan bias pembuat data dinyatakan pada laporan evaluasi. | P0 |
| NFR-07.07 | Kegagalan AI tidak menghasilkan kategori pengganti. | P0 |

**Verifikasi:** Protokol dan laporan evaluasi (MET-09–MET-15), SCN-18, dan unit test validator.

## 7.9 NFR-08 — Maintainability & Testability

| ID | Requirement | Prioritas |
| ----- | ----- | ----- |
| NFR-08.01 | Antarmuka, logika aplikasi, orkestrasi verifikasi, adapter registry, dan layanan AI memiliki batas tanggung jawab yang terpisah sesuai SYSTEM_ARCHITECTURE. | P0 |
| NFR-08.02 | Kontrak API dihasilkan dari backend sebagai OpenAPI dan menjadi sumber kebenaran bagi frontend. | P0 |
| NFR-08.03 | Setiap modul memiliki automated test untuk logika utamanya; contract blockchain memiliki unit test untuk seluruh fungsi dan penolakan. | P0 |
| NFR-08.04 | Adapter registry dan provider AI dapat diganti mock pada unit test tanpa credential, dan mock tidak dapat aktif pada konfigurasi demo. | P0 |
| NFR-08.05 | Struktur repository, perintah setup, dan prosedur pengujian terdokumentasi di README. | P0 |
| NFR-08.06 | Fungsi dan kelas yang ditulis memiliki komentar atau docstring singkat berbahasa Indonesia; identifier menggunakan bahasa Inggris. | P0 |
| NFR-08.07 | Perubahan tidak merusak fungsi yang sebelumnya lulus pengujian; regresi diperiksa sebelum merge. | P0 |

**Verifikasi:** Code review, automated test, dan peninjauan dokumentasi.

## 7.10 NFR-09 — Observability & Auditability

| ID | Requirement | Prioritas |
| ----- | ----- | ----- |
| NFR-09.01 | Setiap permintaan memiliki `requestId` yang dicatat di log dan dikembalikan pada respons kesalahan. | P0 |
| NFR-09.02 | Log terstruktur memuat waktu, layanan, kategori kejadian, status, dan durasi tanpa konten sensitif. | P0 |
| NFR-09.03 | Keputusan verifikasi penerbit dan otorisasi HR dicatat beserta aktor dan waktunya. | P0 |
| NFR-09.04 | Penerbitan dan pencabutan menyimpan hash transaksi dan nomor blok sebagai bukti yang dapat dicocokkan dengan registry. | P0 |
| NFR-09.05 | Kategori kegagalan registry dan AI dapat dibedakan pada log (unavailable, timeout, quota, output invalid, transaction failed). | P0 |
| NFR-09.06 | Hasil pengujian dan evaluasi disimpan sebagai berkas bukti yang dapat ditelusuri ke SCN dan TC. | P0 |

**Verifikasi:** Inspeksi log pada skenario kegagalan dan dokumentasi pengujian.

## 7.11 Ketentuan Penerimaan NFR

Prototipe memenuhi standar kualitas apabila:

1. Seluruh NFR P0 telah diverifikasi dengan bukti.
2. Tidak terdapat secret di repository maupun di bundle frontend.
3. Otorisasi berlaku pada seluruh jalur operasi terlindungi.
4. Kegagalan komponen menghasilkan status yang benar tanpa hasil fiktif.
5. Prototipe dapat dijalankan ulang dari clone baru menggunakan prosedur terdokumentasi.
6. Hasil performa dan evaluasi AI dilaporkan berdasarkan pengukuran aktual.

Target berstatus *Proposed* atau *Open* tidak boleh dinyatakan tercapai tanpa pengukuran.
