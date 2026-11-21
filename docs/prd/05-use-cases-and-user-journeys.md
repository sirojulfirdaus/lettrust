# BAB 5. USE CASES DAN USER JOURNEYS

## 5.1 Gambaran Umum

Use case mendefinisikan tujuan interaksi aktor dengan Lettrust. User journey mendefinisikan urutan aktivitas untuk mencapai tujuan tersebut dan dipetakan ke Service Blueprint (D1) serta BPMN To-Be (D2).

Aktor utama:

* Pelamar: memeriksa offer letter melalui portal mitra tanpa akun.
* Partner: meneruskan permintaan pemeriksaan ke API-07.
* HR: mendaftarkan perusahaan, menerbitkan, dan mencabut bukti.
* Administrator: memverifikasi penerbit dan mengotorisasi HR.

Aktivitas manusia di luar sistem dipertahankan sebagai bagian alur sosio-teknis tanpa endpoint: HR menyiapkan surat final (TB-05), HR mengirim surat dan kode kepada pelamar (TB-07), dan pelamar menentukan tindak lanjut (TB-16).

## 5.2 Use Case Catalog

### 5.2.1 Perusahaan/HR dan Administrator

| ID | Use Case | Aktor | Deskripsi | FR | BPMN | Blueprint |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| UC-01 | Registrasi Akun | HR | Membuat akun HR/perwakilan perusahaan. | FR-01 | TB-01 (pendukung) | H1 |
| UC-02 | Login dan Logout | HR, Admin | Mengakses dan mengakhiri sesi Console. | FR-01 | — | H1–H3 |
| UC-03 | Registrasi Perusahaan | HR | Mengajukan data perusahaan; status PENDING. | FR-01 | TB-01 | H1 |
| UC-04 | Verifikasi Penerbit | Admin | Meninjau dan menetapkan VERIFIED atau REJECTED. | FR-01 | TB-02, TB-03 | H2 |
| UC-05 | Otorisasi HR | Admin | Mengotorisasi akun HR terafiliasi pada penerbit VERIFIED. | FR-01 | TB-04 | H3 |
| UC-06 | Penerbitan Bukti | HR | Mengunggah PDF final dan memperoleh bukti ACTIVE serta kode referensi. | FR-03 | TB-05, TB-06 | H4, H5 |
| UC-07 | Pengelolaan Bukti | HR | Melihat daftar dan detail bukti beserta status dan referensi transaksi. | FR-03, FR-04 | TB-11 (API-05) | H5–H7 |
| UC-08 | Pencabutan Bukti | HR | Mencabut bukti ACTIVE dengan alasan. | FR-04 | TB-17 | H7 |

### 5.2.2 Pelamar dan Partner

| ID | Use Case | Aktor | Deskripsi | FR | BPMN | Blueprint |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| UC-09 | Verifikasi Dengan Kode | Pelamar, Partner | Memeriksa bukti dan status menggunakan kode; berkas dan AI opsional. | FR-02, FR-03, FR-06 | TB-08–TB-12, TB-14, TB-15 | T2–T4, T6 |
| UC-10 | Verifikasi Kode dan Berkas dengan AI | Pelamar, Partner | Memeriksa bukti, integritas, dan indikasi risiko dalam satu permintaan. | FR-02, FR-03, FR-05, FR-06 | TB-08–TB-15 | T2–T6 |
| UC-11 | Analisis AI Tanpa Kode | Pelamar, Partner | Menganalisis isi surat tanpa pemeriksaan bukti. | FR-02, FR-05, FR-06 | TB-08–TB-10, TB-13–TB-15 (DLT-01) | T2, T3, T5, T6 |
| UC-12 | Membaca Hasil dan Tindak Lanjut | Pelamar | Memahami hasil terpisah dan memilih langkah berikutnya. | FR-02, FR-06 | TB-15, TB-16 | T6, T7 |
| UC-13 | Integrasi Partner | Partner | Mengirim permintaan ke API-07 dari server dan menangani respons serta kesalahan. | FR-02, FR-06 | TB-10, TB-14 | T3, T6 |

## 5.3 User Journeys

### 5.3.1 UJ-01 — Onboarding Perusahaan

**Aktor:** HR.
**Prasyarat:** Tidak ada.
**Keterlacakan:** H1, TB-01; UC-01, UC-03.

**Alur utama:**

1. HR membuka Lettrust Console dan memilih "Daftarkan Perusahaan".
2. HR membuat akun dengan nama, email, dan password.
3. HR masuk menggunakan akun tersebut.
4. HR mengisi nama perusahaan, nomor registrasi, dan email kontak (data sintetis).
5. Sistem mencatat penerbit berstatus PENDING dan mengafiliasikan akun HR sebagai NOT_AUTHORIZED.
6. Console menampilkan status "Menunggu verifikasi administrator" dan menjelaskan bahwa penerbitan belum tersedia.

**Hasil:** Penerbit tercatat PENDING; akun HR terafiliasi tetapi belum dapat menerbitkan.

### 5.3.2 UJ-02 — Verifikasi Penerbit dan Otorisasi HR

**Aktor:** Administrator.
**Prasyarat:** Terdapat penerbit PENDING.
**Keterlacakan:** H2, H3, TB-02–TB-04; UC-04, UC-05.

**Alur utama:**

1. Administrator masuk dan membuka daftar penerbit berstatus PENDING.
2. Administrator membuka detail penerbit dan memeriksa data pengajuan.
3. Administrator menetapkan VERIFIED dengan referensi bukti verifikasi.
4. Sistem mencatat keputusan, peninjau, dan waktu.
5. Administrator memilih akun HR terafiliasi dan mengotorisasinya.
6. Sistem mencatat status AUTHORIZED.

**Hasil:** HR dapat menerbitkan bukti atas nama penerbit.

**Alternatif:** Administrator menetapkan REJECTED (AF-03). Penerbit tidak dapat menerbitkan bukti.

### 5.3.3 UJ-03 — Penerbitan Bukti Offer Letter

**Aktor:** HR terotorisasi.
**Prasyarat:** Penerbit VERIFIED, HR AUTHORIZED, berkas PDF final tersedia.
**Keterlacakan:** H4, H5, H6, TB-05–TB-07; UC-06.

**Alur utama:**

1. HR menyiapkan offer letter final di luar sistem (TB-05).
2. HR membuka "Terbitkan Bukti" dan mengunggah PDF.
3. HR mengonfirmasi bahwa berkas adalah versi final yang akan dikirim kepada pelamar.
4. Sistem memvalidasi otorisasi dan berkas, menghitung SHA-256, serta membuat `proofId` dan `referenceCode`.
5. Sistem mencatat bukti ACTIVE pada registry blockchain dan menunggu konfirmasi transaksi.
6. Setelah transaksi terkonfirmasi, Console menampilkan kode referensi, hash, status ACTIVE, dan referensi transaksi.
7. HR menyalin kode dan mengirim surat beserta kode kepada pelamar melalui kanal perusahaan (TB-07).

**Hasil:** Bukti ACTIVE tercatat dan kode siap dibagikan.

**Alternatif:** Transaksi gagal (AF-07); permintaan diulang dengan kunci idempotensi yang sama (AF-08).

### 5.3.4 UJ-04 — Pencabutan Bukti

**Aktor:** HR terotorisasi.
**Prasyarat:** Bukti ACTIVE milik penerbit.
**Keterlacakan:** H7, TB-17; UC-07, UC-08.

**Alur utama:**

1. HR membuka daftar bukti dan memilih bukti ACTIVE.
2. HR memilih "Cabut Bukti" dan menentukan alasan.
3. Console menampilkan konfirmasi bahwa pencabutan tidak dapat dibatalkan.
4. Sistem memvalidasi kewenangan dan status, lalu mencatat REVOKED pada registry.
5. Setelah transaksi terkonfirmasi, Console menampilkan status REVOKED, alasan, waktu, dan referensi transaksi pencabutan. Referensi penerbitan tetap ditampilkan.

**Hasil:** Pemeriksaan berikutnya terhadap kode tersebut menampilkan FOUND dan REVOKED.

### 5.3.5 UJ-05 — Verifikasi Dengan Kode, Berkas, dan AI

**Aktor:** Pelamar, Partner.
**Prasyarat:** Pelamar memiliki surat dan kode referensi.
**Keterlacakan:** T1–T7, TB-08–TB-16; UC-09, UC-10, UC-12.

**Alur utama:**

1. Pelamar membuka fitur "Cek Offer Letter" pada Portal Karier Mitra (TB-08).
2. Pelamar memilih "Saya punya kode referensi".
3. Pelamar memasukkan kode, mengunggah PDF, mencentang analisis AI, dan memberikan persetujuan (TB-09).
4. Server portal meneruskan permintaan ke API-07 dengan token partner (TB-10).
5. Lettrust memvalidasi permintaan, membaca bukti dari registry, membandingkan hash, dan menjalankan analisis AI secara independen (TB-11–TB-13).
6. Lettrust mengembalikan hasil terstruktur (TB-14).
7. Portal menampilkan tiga panel hasil dan panduan tindak lanjut (TB-15).
8. Pelamar menentukan tindak lanjut, termasuk konfirmasi ke kanal resmi bila perlu (TB-16).

**Hasil:** Pelamar memperoleh informasi bukti dan penerbit, status, integritas, serta indikasi risiko secara terpisah.

**Variasi:** Kode saja tanpa berkas (integritas NOT_CHECKED, AI NOT_REQUESTED); berkas tanpa AI.

### 5.3.6 UJ-06 — Analisis AI Tanpa Kode

**Aktor:** Pelamar, Partner.
**Prasyarat:** Pelamar memiliki berkas PDF tetapi tidak memiliki kode referensi.
**Keterlacakan:** T2, T3, T5, T6, T7; TB-08–TB-10, TB-13–TB-16; DLT-01; UC-11.

**Alur utama:**

1. Pelamar memilih "Saya tidak punya kode — analisis isi surat dengan AI".
2. Portal menampilkan penjelasan bahwa bukti penerbitan dan keutuhan berkas tidak diperiksa dalam mode ini.
3. Pelamar mengunggah PDF dan memberikan persetujuan.
4. Server portal meneruskan permintaan ke API-07 tanpa kode dan dengan `includeRisk=true`.
5. Lettrust tidak memanggil registry, mengekstraksi teks (dengan OCR bila diperlukan), dan menjalankan analisis AI.
6. Portal menampilkan panel AI serta panel bukti dan integritas berstatus "Tidak diperiksa".

**Hasil:** Pelamar memperoleh indikasi risiko tanpa klaim apa pun tentang bukti penerbitan.

### 5.3.7 UJ-07 — Pemeriksaan dengan Gangguan Komponen

**Aktor:** Pelamar, Partner.
**Prasyarat:** Registry atau layanan AI tidak tersedia.
**Keterlacakan:** SCN-07, FR-06.

**Alur utama:**

1. Pelamar mengirim pemeriksaan seperti pada UJ-05.
2. Salah satu komponen gagal.
3. Lettrust mengembalikan hasil dengan komponen yang gagal berstatus UNAVAILABLE dan komponen lain tetap disajikan apabila berhasil.
4. Portal menampilkan bahwa pemeriksaan tertentu sedang tidak dapat dilakukan, bukan bahwa surat tidak tercatat atau berisiko rendah.

**Hasil:** Pelamar memahami bagian mana yang berhasil dan bagian mana yang perlu diulang.

## 5.4 Alternative Flows dan Exception Handling

| ID | Kondisi | Perilaku Sistem | FR |
| ----- | ----- | ----- | ----- |
| AF-01 | Email akun sudah terdaftar. | Menolak registrasi dengan pesan yang sesuai. | FR-01.01 |
| AF-02 | Kredensial login salah. | Menolak login dengan pesan umum tanpa menyebut bagian yang salah. | FR-01.02 |
| AF-03 | Administrator menetapkan REJECTED. | Penerbit tidak dapat menerbitkan; HR melihat status ditolak. | FR-01.05 |
| AF-04 | Keputusan verifikasi pada penerbit yang sudah diputuskan. | Menolak sebagai konflik status. | FR-01.05 |
| AF-05 | Otorisasi HR pada penerbit yang belum VERIFIED atau HR tidak terafiliasi. | Menolak otorisasi. | FR-01.06 |
| AF-06 | HR tanpa otorisasi mencoba menerbitkan atau mencabut. | Menolak tanpa mencatat transaksi. | FR-01.07 |
| AF-07 | Registry tidak tersedia atau transaksi gagal saat penerbitan/pencabutan. | Mengembalikan kegagalan; tidak menyatakan ACTIVE/REVOKED; status tetap seperti sebelumnya. | FR-03.04, FR-04.05 |
| AF-08 | Permintaan penerbitan diulang dengan Idempotency-Key yang sama. | Mengembalikan bukti yang sama tanpa transaksi kedua. | FR-03.05 |
| AF-09 | Pencabutan bukti yang sudah REVOKED. | Menolak sebagai konflik status. | FR-04.04 |
| AF-10 | HR mencoba mengakses atau mencabut bukti penerbit lain. | Menolak tanpa mengungkap detail bukti. | FR-04.03 |
| AF-11 | Kode referensi tidak terdaftar. | NOT_FOUND; integritas NOT_CHECKED; AI tetap berjalan bila diminta dan berkas tersedia. | FR-03.10, FR-06.02 |
| AF-12 | Format kode referensi tidak valid. | Menolak permintaan dengan pesan perbaikan input. | FR-06.05 |
| AF-13 | Tanpa kode dan tanpa berkas, atau tanpa kode tanpa permintaan AI. | Menolak sebagai kombinasi input tidak valid. | FR-06.05 |
| AF-14 | Berkas bukan PDF atau melebihi batas ukuran. | Menolak dengan alasan yang sesuai. | FR-06.06 |
| AF-15 | Teks PDF tidak dapat diekstraksi dan OCR tidak menghasilkan teks. | AI NOT_PERFORMED dengan alasan konten tidak tersedia; tidak ada kategori. | FR-05.04 |
| AF-16 | Layanan AI gagal, timeout, atau kuota habis. | AI UNAVAILABLE dengan alasan; hasil bukti dan integritas tetap disajikan. | FR-05.09 |
| AF-17 | Registry gagal saat verifikasi. | Lookup UNAVAILABLE (bukan NOT_FOUND); integritas NOT_CHECKED; AI tetap berjalan bila diminta. | FR-06.02 |
| AF-18 | Registry dan AI gagal bersamaan. | Kedua komponen UNAVAILABLE; respons tetap terstruktur. | FR-06.04 |
| AF-19 | Token partner tidak valid. | Menolak permintaan API-07 sebagai tidak terautentikasi; portal menampilkan gangguan layanan. | FR-02.07 |
| AF-20 | Backend Lettrust tidak dapat dihubungi portal. | Portal menampilkan bahwa layanan pemeriksaan sedang tidak tersedia dan mempertahankan input. | FR-02.11 |
| AF-21 | Isi surat memuat instruksi yang mencoba memengaruhi analisis. | Instruksi diperlakukan sebagai data; aturan analisis tidak berubah. | FR-05.08 |
| AF-22 | Batas laju partner terlampaui (P1). | Menolak dengan status pembatasan laju; portal menyarankan mencoba kembali. | FR-06.10 |

## 5.5 Referensi Desain

Tidak terdapat desain Figma. Struktur halaman, state antarmuka, label hasil, dan aturan panduan tindak lanjut ditetapkan pada Bab 9. Detail perilaku dan acceptance criteria ditetapkan pada Bab 6.
