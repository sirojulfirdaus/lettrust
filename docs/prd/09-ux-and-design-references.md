# BAB 9. UX & DESIGN REFERENCES

## 9.1 Gambaran Umum

Tidak terdapat desain Figma untuk Lettrust. Bab ini menjadi acuan perilaku dan struktur antarmuka: peta halaman, state, label hasil, aturan panduan tindak lanjut, pesan kesalahan, dan baseline visual.

PRD menjadi acuan perilaku. Detail implementasi komponen dan route teknis mengacu pada SYSTEM_ARCHITECTURE. Penyesuaian visual minor diperbolehkan selama tidak mengubah perilaku, label, dan state yang ditetapkan pada bab ini.

## 9.2 Area Antarmuka

| Area | Pengguna | Karakter |
| ----- | ----- | ----- |
| Portal Karier Mitra (Simulasi) | Pelamar | Aplikasi terpisah yang tampil sebagai job portal pihak ketiga. Fitur "Cek Offer Letter" menampilkan keterangan "Didukung Lettrust". |
| Lettrust Console — Perusahaan/HR | HR | Aplikasi Lettrust untuk penerbit. |
| Lettrust Console — Administrator | Administrator | Area dalam aplikasi yang sama dengan navigasi khusus Administrator. |

Portal dan Console sengaja dibuat sebagai dua aplikasi berbeda dengan identitas visual berbeda untuk menegaskan bahwa portal adalah client API terpisah, bukan bagian dari Lettrust.

## 9.3 Peta Halaman

### 9.3.1 Lettrust Console

| Halaman | Fungsi | Akses | FR |
| ----- | ----- | ----- | ----- |
| Login | Masuk dengan email dan password. | Publik | FR-01.02 |
| Registrasi Akun | Membuat akun HR. | Publik | FR-01.01 |
| Registrasi Perusahaan | Mengisi data perusahaan setelah login. | HR tidak terafiliasi | FR-01.03 |
| Beranda HR | Kartu status penerbit dan otorisasi; ringkasan bukti; tombol Terbitkan Bukti apabila berwenang. | HR | FR-01.04 |
| Terbitkan Bukti | Unggah PDF final, konfirmasi, proses, dan hasil penerbitan. | HR AUTHORIZED | FR-03.01–FR-03.07 |
| Daftar Bukti | Daftar bukti milik penerbit. | HR AUTHORIZED | FR-03.08 |
| Detail Bukti | Status dari registry, hash, referensi transaksi, riwayat, dan tindakan Cabut Bukti. | HR AUTHORIZED | FR-03.08, FR-04.01–FR-04.07 |
| Daftar Penerbit | Daftar penerbit dengan filter status. | Administrator | FR-01.05 |
| Detail Penerbit | Data pengajuan, keputusan verifikasi, daftar HR terafiliasi, dan tindakan Otorisasi. | Administrator | FR-01.05, FR-01.06 |

### 9.3.2 Portal Karier Mitra (Simulasi)

| Halaman | Fungsi | FR |
| ----- | ----- | ----- |
| Beranda Portal | Halaman sederhana yang menampilkan identitas portal simulasi dan akses ke fitur Cek Offer Letter. | FR-02.01 |
| Cek Offer Letter | Pemilihan mode, input, persetujuan, status pemrosesan, hasil tiga panel, dan panduan tindak lanjut. | FR-02.02–FR-02.11 |

Portal tidak menampilkan daftar lowongan nyata, merek job portal nyata, atau data lowongan yang menyerupai platform tertentu.

## 9.4 Struktur Halaman Cek Offer Letter

```
┌─────────────────────────────────────────────────────────────┐
│ Portal Karier Mitra (Simulasi)           Didukung Lettrust   │
├─────────────────────────────────────────────────────────────┤
│ Cek Offer Letter                                             │
│ Penjelasan singkat: apa yang diperiksa dan batas hasilnya    │
│                                                              │
│ (•) Saya punya kode referensi                                │
│ ( ) Saya tidak punya kode — analisis isi surat dengan AI     │
│                                                              │
│ [Mode Dengan Kode]                                           │
│   Kode referensi*      [LTR-____-____-____]                  │
│   Berkas PDF (opsional)[Pilih berkas]  "untuk cek keutuhan"  │
│   [ ] Analisis isi surat dengan AI (perlu berkas)            │
│   [ ] Saya menyetujui pemrosesan AI ... (muncul bila AI)     │
│                                                              │
│ [Mode Tanpa Kode]                                            │
│   ⓘ Bukti penerbitan & keutuhan berkas tidak diperiksa       │
│   Berkas PDF*          [Pilih berkas]                        │
│   [ ] Saya menyetujui pemrosesan AI ...*                     │
│                                                              │
│                                   [ Periksa Surat ]          │
├─────────────────────────────────────────────────────────────┤
│ Hasil                                                        │
│ ┌ Bukti Penerbitan & Status ┐ ┌ Keutuhan Berkas ┐            │
│ └───────────────────────────┘ └─────────────────┘            │
│ ┌ Indikasi Risiko (AI) ─────────────────────────┐            │
│ │ kategori · indikator + kutipan · penjelasan   │            │
│ │ rekomendasi · disclaimer                      │            │
│ └───────────────────────────────────────────────┘            │
│ ┌ Langkah yang Disarankan ──────────────────────┐            │
│ └───────────────────────────────────────────────┘            │
│                                 [ Periksa surat lain ]       │
└─────────────────────────────────────────────────────────────┘
```

Format contoh kode pada sketsa bersifat ilustratif; format final mengikuti SYSTEM_ARCHITECTURE.

## 9.5 Interaction States

| State | Perilaku | Contoh Penerapan |
| ----- | ----- | ----- |
| Default | Menampilkan kondisi normal dan tindakan yang tersedia. | Formulir kosong. |
| Hover / Focus | Indikator interaksi yang terlihat, termasuk outline fokus keyboard. | Semua kontrol. |
| Loading | Indikator pemuatan data halaman. | Daftar penerbit, daftar bukti. |
| Processing | Indikator operasi berjalan; tombol terkait nonaktif. | Penerbitan, pencabutan, verifikasi, keputusan Administrator. |
| Success | Konfirmasi operasi berhasil dengan informasi hasil. | Bukti diterbitkan, bukti dicabut, keputusan tersimpan. |
| Error | Pesan kegagalan yang dapat dipahami dan tindakan pemulihan. | Validasi gagal, layanan tidak tersedia. |
| Empty | Penjelasan kondisi tanpa data dan tindakan berikutnya. | Belum ada bukti, tidak ada penerbit PENDING. |
| Disabled | Tindakan tidak tersedia beserta alasannya. | Terbitkan Bukti saat penerbit PENDING; AI tanpa berkas. |
| Confirmation | Konfirmasi sebelum tindakan destruktif atau final. | Cabut Bukti, keputusan VERIFIED/REJECTED, unggah berkas final. |
| Partial Result | Sebagian komponen berhasil dan sebagian tidak tersedia. | Registry atau AI UNAVAILABLE pada verifikasi. |
| Not Checked | Komponen sengaja tidak dijalankan beserta alasannya. | Mode Tanpa Kode; tanpa berkas. |

Status antarmuka harus berasal dari kondisi aktual backend.

## 9.6 Label dan Penjelasan Hasil Verifikasi

Label berikut wajib digunakan pada portal. Ikon bersifat ilustratif; setiap status harus memiliki teks dan ikon, tidak hanya warna.

### 9.6.1 Panel Bukti Penerbitan & Status

| Kondisi API | Ikon | Nada | Judul | Penjelasan |
| ----- | ----- | ----- | ----- | ----- |
| FOUND + ACTIVE | ✓ | Positif terbatas | Tercatat dan aktif | Surat dengan kode ini dicatat oleh **{companyName}** (penerbit terverifikasi) pada {issuedAt}, dan statusnya masih aktif. Pastikan nama perusahaan sesuai dengan surat Anda. Status ini tidak menjamin isi surat aman. |
| FOUND + REVOKED | ⊘ | Peringatan | Tercatat, tetapi telah dicabut | Surat dengan kode ini pernah dicatat oleh **{companyName}**, tetapi telah dicabut oleh penerbit pada {revokedAt}. Konfirmasikan status penawaran kepada perusahaan melalui kanal resminya. |
| NOT_FOUND | ? | Netral-waspada | Tidak ditemukan di Lettrust | Kode ini tidak tercatat dalam registry Lettrust. Ini tidak berarti surat palsu: perusahaan mungkin tidak menggunakan Lettrust atau kode salah ketik. Periksa kembali kode dan konfirmasikan melalui kanal resmi perusahaan. |
| UNAVAILABLE | ⚠ | Gangguan | Pemeriksaan bukti sedang tidak dapat dilakukan | Terjadi gangguan saat memeriksa registry. Ini bukan berarti kode tidak terdaftar. Coba lagi beberapa saat lagi. |
| NOT_REQUESTED | — | Netral | Tidak diperiksa | Bukti penerbitan tidak diperiksa karena Anda tidak memasukkan kode referensi. |

Apabila `issuerVerified` bernilai `false`, label penerbit menyatakan "penerbit belum/tidak berstatus terverifikasi" dan tidak menggunakan kata "terverifikasi".

### 9.6.2 Panel Keutuhan Berkas

| Kondisi API | Ikon | Nada | Judul | Penjelasan |
| ----- | ----- | ----- | ----- | ----- |
| MATCH | ✓ | Positif terbatas | Berkas identik dengan yang dicatat | Berkas Anda sama persis dengan berkas yang dicatat penerbit. Ini tidak menilai apakah isi surat aman. |
| MISMATCH | ✕ | Peringatan | Berkas berbeda dari yang dicatat | Berkas Anda tidak sama dengan berkas yang dicatat penerbit untuk kode ini. Berkas mungkin telah diubah atau disimpan ulang. Mintalah salinan asli melalui kanal resmi perusahaan. |
| NOT_CHECKED / `NO_FILE` | — | Netral | Tidak diperiksa | Unggah berkas PDF surat Anda untuk memastikan berkas sama dengan yang dicatat penerbit. |
| NOT_CHECKED / `PROOF_NOT_FOUND` | — | Netral | Tidak dapat diperiksa | Tidak ada catatan rujukan karena kode tidak ditemukan. |
| NOT_CHECKED / `REGISTRY_UNAVAILABLE` | — | Gangguan | Tidak dapat diperiksa saat ini | Catatan rujukan tidak dapat dibaca karena gangguan. Coba lagi beberapa saat lagi. |
| NOT_CHECKED / `NO_REFERENCE_CODE` | — | Netral | Tidak diperiksa | Keutuhan berkas hanya dapat diperiksa dengan kode referensi. |

### 9.6.3 Panel Indikasi Risiko (AI)

| Kondisi API | Ikon | Nada | Judul | Penjelasan |
| ----- | ----- | ----- | ----- | ----- |
| COMPLETED / HIGH | ▲ | Bahaya | Indikasi risiko tinggi | Ditemukan pola yang sering muncul pada penipuan rekrutmen. Lihat indikator dan kutipan di bawah. |
| COMPLETED / MEDIUM | ◆ | Peringatan | Indikasi risiko sedang | Ditemukan hal yang perlu diperiksa lebih lanjut. |
| COMPLETED / LOW | ● | Netral | Indikasi risiko rendah | Tidak ditemukan pola yang termasuk dalam daftar indikator. Risiko rendah tidak menjamin surat aman. |
| NOT_REQUESTED | — | Netral | Tidak diminta | Analisis isi surat tidak dipilih. |
| NOT_PERFORMED | — | Netral | Tidak dapat dianalisis | Isi surat tidak dapat dibaca dari berkas (misalnya berkas tidak memuat teks yang dapat dikenali). |
| UNAVAILABLE / `AI_SERVICE_UNAVAILABLE`, `AI_TIMEOUT`, `AI_OUTPUT_INVALID` | ⚠ | Gangguan | Analisis sedang tidak tersedia | Analisis AI gagal dijalankan. Ini bukan berarti risiko rendah. Coba lagi beberapa saat lagi. |
| UNAVAILABLE / `AI_QUOTA_EXCEEDED` | ⚠ | Gangguan | Analisis sedang tidak tersedia | Kapasitas layanan analisis sedang habis. Ini bukan berarti risiko rendah. Coba lagi nanti. |

Apabila COMPLETED, panel menampilkan:

1. Daftar indikator dengan label bahasa Indonesia dan tingkatnya.
2. Kutipan bukti untuk setiap indikator, ditampilkan sebagai teks biasa (bukan HTML).
3. Penjelasan dan rekomendasi.
4. Metode pembacaan isi (teks atau OCR) dan keterangan apabila hanya sebagian halaman yang dianalisis.
5. Disclaimer tetap: "Hasil analisis AI bersifat indikatif dan bukan penentu keaslian surat atau putusan hukum."

| Kode Indikator | Label |
| ----- | ----- |
| `PAYMENT_REQUEST` | Permintaan pembayaran kepada pelamar |
| `SENSITIVE_DATA_REQUEST` | Permintaan data atau akses sensitif |
| `UNOFFICIAL_CONTACT` | Kontak melalui kanal tidak resmi |
| `URGENCY_PRESSURE` | Tekanan waktu atau ancaman |
| `IDENTITY_INCONSISTENCY` | Informasi perusahaan atau penawaran tidak konsisten |
| `UNREALISTIC_COMPENSATION` | Kompensasi tidak wajar |
| `VAGUE_JOB_DETAILS` | Rincian pekerjaan tidak jelas |

## 9.7 Aturan Panduan Tindak Lanjut

Panel "Langkah yang Disarankan" disusun dari aturan berikut. Seluruh aturan yang berlaku ditampilkan, diurutkan dari prioritas tertinggi.

| ID | Kondisi | Panduan |
| ----- | ----- | ----- |
| G-01 | Selalu | Jangan melakukan pembayaran atau memberikan data sensitif untuk proses rekrutmen sebelum memastikan melalui kanal resmi perusahaan. |
| G-02 | `riskAnalysis.category = HIGH` | Hentikan proses dan konfirmasi langsung kepada perusahaan melalui situs atau kontak resmi yang Anda cari sendiri, bukan kontak di dalam surat. |
| G-03 | `lifecycleStatus = REVOKED` | Penawaran ini telah dicabut oleh penerbit. Konfirmasikan status penawaran kepada perusahaan sebelum melanjutkan. |
| G-04 | `integrityCheck.result = MISMATCH` | Mintalah salinan asli surat melalui kanal resmi perusahaan dan periksa kembali. |
| G-05 | `lookup = FOUND`, `NOT_CHECKED (NO_FILE)` | Unggah berkas PDF surat Anda untuk memastikan berkas sama dengan yang dicatat, dan pastikan nama penerbit sama dengan nama perusahaan pada surat. |
| G-06 | `lookup = NOT_FOUND` | Periksa kembali penulisan kode. Apabila kode sudah benar, konfirmasikan keaslian surat melalui kanal resmi perusahaan. |
| G-07 | `lookup = UNAVAILABLE` atau `riskAnalysis.state = UNAVAILABLE` | Sebagian pemeriksaan gagal karena gangguan. Coba lagi beberapa saat lagi. |
| G-08 | `mode = AI_ONLY` | Hasil ini hanya menilai isi surat. Apabila perusahaan menyatakan menggunakan Lettrust, mintalah kode referensi untuk memeriksa bukti penerbitan. |
| G-09 | `riskAnalysis.category = MEDIUM` | Periksa hal yang ditandai dan konfirmasikan kepada perusahaan melalui kanal resmi. |
| G-10 | `lookup = FOUND`, ACTIVE, MATCH, dan risiko LOW atau tidak diminta | Bukti tercatat dan berkas identik. Tetap waspada terhadap permintaan yang tidak wajar dan konfirmasikan bila ragu. |

Panduan tidak boleh menyatakan surat asli, palsu, aman, atau penipuan.

## 9.8 Pesan Kesalahan

| Kode / Kondisi | Pesan untuk Pengguna |
| ----- | ----- |
| `INVALID_REFERENCE_CODE_FORMAT` | Format kode referensi tidak valid. Periksa kembali kode pada surat Anda. |
| `INVALID_INPUT_COMBINATION` | Masukkan kode referensi atau unggah berkas PDF untuk dianalisis. |
| `AI_ONLY_REQUIRES_INCLUDE_RISK` | Tanpa kode referensi, pemeriksaan hanya dapat dilakukan dengan analisis AI. Setujui pemrosesan AI untuk melanjutkan. |
| `UNSUPPORTED_MEDIA_TYPE` | Berkas harus berformat PDF. |
| `FILE_TOO_LARGE` | Ukuran berkas melebihi batas yang diizinkan. |
| Berkas kosong | Berkas kosong tidak dapat diproses. |
| `MULTIPLE_FILES` | Hanya satu berkas yang dapat diproses per permintaan. |
| `RATE_LIMITED` | Terlalu banyak permintaan. Coba lagi beberapa saat lagi. |
| Autentikasi partner gagal, 5xx, timeout portal | Layanan pemeriksaan sedang tidak tersedia. Coba lagi beberapa saat lagi. |
| `EMAIL_ALREADY_REGISTERED` | Email sudah terdaftar. Silakan masuk. |
| `INVALID_CREDENTIALS` | Email atau password tidak sesuai. |
| `ACCOUNT_ALREADY_AFFILIATED` | Akun Anda sudah terhubung dengan perusahaan. |
| `REGISTRATION_NUMBER_ALREADY_EXISTS` | Nomor registrasi perusahaan sudah terdaftar. |
| `ISSUER_DECISION_ALREADY_MADE` | Penerbit ini sudah memiliki keputusan verifikasi. |
| `ISSUER_NOT_VERIFIED` | Penerbit belum terverifikasi sehingga HR belum dapat diotorisasi. |
| `HR_NOT_AFFILIATED` | Akun HR tidak terhubung dengan penerbit ini. |
| `HR_ALREADY_AUTHORIZED` | Akun HR ini sudah diotorisasi. |
| `PROOF_ALREADY_REVOKED` | Bukti ini sudah dicabut sebelumnya. |
| `DUPLICATE_ACTIVE_DOCUMENT` | Berkas yang sama sudah memiliki bukti aktif. |
| `IDEMPOTENCY_KEY_CONFLICT` | Permintaan bertentangan dengan permintaan sebelumnya. Mulai ulang proses penerbitan. |
| `REGISTRY_UNAVAILABLE`, `REGISTRY_TRANSACTION_FAILED` | Pencatatan ke registry gagal. Tidak ada perubahan yang tersimpan. Coba lagi. |
| `REGISTRY_UNAVAILABLE` saat membaca detail bukti (Console) | Data bukti dari registry belum dapat dimuat. Coba lagi beberapa saat lagi. |
| 401 pada Console | Sesi Anda telah berakhir. Silakan masuk kembali. |
| 403 pada Console | Anda tidak memiliki izin untuk tindakan ini. |

Pesan tidak menampilkan stack trace, nama tabel, path internal, token, atau detail teknis sensitif.

## 9.9 Baseline Visual (Usulan)

Nilai berikut adalah baseline yang dapat disesuaikan frontend engineer selama konsisten di seluruh halaman area masing-masing.

### 9.9.1 Lettrust Console

| Elemen | Nilai |
| ----- | ----- |
| Konsep | Tenang, tepercaya, modern |
| Primary | `#1E3A8A` (navy) |
| Accent | `#0D9488` (teal) |
| Teks utama | `#0F172A` |
| Teks sekunder | `#475569` |
| Latar | `#F8FAFC` |
| Permukaan | `#FFFFFF` |
| Font heading | Plus Jakarta Sans |
| Font body | Inter |
| Radius | 8–12 px |
| Spasi | Sistem 4/8 px |

### 9.9.2 Portal Karier Mitra (Simulasi)

| Elemen | Nilai |
| ----- | ----- |
| Konsep | Job portal generik pihak ketiga |
| Primary | `#C2410C` (oranye tua) |
| Latar | `#FFFBF7` |
| Font | Inter |
| Penanda | Label "Simulasi" pada header dan "Didukung Lettrust" pada fitur Cek Offer Letter |

### 9.9.3 Warna Status (Keduanya)

| Nada | Warna | Penggunaan |
| ----- | ----- | ----- |
| Positif terbatas | `#15803D` | ACTIVE, MATCH |
| Peringatan | `#B45309` | REVOKED, MISMATCH, MEDIUM |
| Bahaya | `#B91C1C` | HIGH |
| Gangguan | `#7C3AED` | UNAVAILABLE |
| Netral | `#475569` | NOT_FOUND, NOT_CHECKED, NOT_REQUESTED, NOT_PERFORMED, LOW |

Warna status selalu disertai teks dan ikon (NFR-06.02).

## 9.10 Visibilitas Teknologi pada Antarmuka

Untuk memenuhi ketentuan D3 bahwa peran teknologi harus terlihat, antarmuka menampilkan:

1. Pada hasil penerbitan dan detail bukti: hash dokumen, hash transaksi, nomor blok, dan status yang dibaca dari registry.
2. Pada detail bukti REVOKED: referensi transaksi penerbitan dan pencabutan.
3. Pada hasil verifikasi: sumber status bukti (registry) dan hasil perbandingan hash.
4. Pada panel AI: indikator dengan kutipan bukti, metode pembacaan isi (teks/OCR), dan disclaimer.
5. Penanda "Data sintetis" pada Console dan portal.

## 9.11 Navigasi dan Responsivitas

| Area | Ketentuan |
| ----- | ----- |
| Console | Dioptimalkan untuk desktop (lebar ≥ 1024 px); tetap dapat dibuka pada layar lebih kecil tanpa kehilangan fungsi utama. |
| Portal | Mendukung desktop dan browser mobile; panel hasil disusun vertikal pada layar sempit. |
| Navigasi berbasis role | HR melihat menu HR; Administrator melihat menu Administrator. Penyembunyian menu tidak menggantikan otorisasi backend. |
| Keyboard | Seluruh formulir utama dan tindakan dapat dijalankan melalui keyboard. |

## 9.12 Penerimaan Antarmuka

Antarmuka dianggap memenuhi persyaratan apabila:

1. Seluruh halaman pada §9.3 tersedia dan memenuhi acceptance criteria FR terkait.
2. Label hasil dan panduan mengikuti §9.6 dan §9.7.
3. State pada §9.5 berfungsi sesuai kondisi backend.
4. Tidak ada label vonis tunggal "asli/palsu" atau "aman/penipuan".
5. Status tidak dibedakan hanya dengan warna.
6. Manipulasi antarmuka tidak dapat melewati otorisasi backend.
7. Peran blockchain dan AI terlihat pada antarmuka sesuai §9.10.
