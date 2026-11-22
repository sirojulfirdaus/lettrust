# Format Templat Surat

Owner: B (PIC 5) · Status: COMPLETE · Ref: PRD bagian 10.4.1, 10.4.2, 8.4, 8.5; SA bagian 7.9; PLAN T5-01

Format ini menjadi masukan bersama untuk penulis templat T2-04 (Van), T4-03 (Pash), dan generator PDF T5-05 (B). Seluruh surat, identitas, perusahaan, alamat, dan kontak harus sintetis. Format ini tidak mengubah kontrak API Lettrust.

## Berkas dan Struktur JSON

Simpan JSON UTF-8 tanpa komentar atau trailing comma. Setiap berkas berisi satu array dengan enam objek surat lengkap, bukan potongan kalimat atau teks dengan placeholder yang belum diisi.

| Berkas | Penulis · Peninjau | Bahasa (`lang`) | Kategori (`label`) |
| --- | --- | --- | --- |
| `id-low.json` | Van · Pash | `id` | `LOW` |
| `id-medium.json` | Van · Pash | `id` | `MEDIUM` |
| `id-high.json` | Van · Pash | `id` | `HIGH` |
| `en-low.json` | Pash · Van | `en` | `LOW` |
| `en-medium.json` | Pash · Van | `en` | `MEDIUM` |
| `en-high.json` | Pash · Van | `en` | `HIGH` |

Enam berkas tersebut menghasilkan 36 surat sumber; T5-05 merender setiap surat menjadi PDF teks dan PDF scan sehingga target awalnya 72 dokumen. Jumlah final dan pembagian dev/test dicatat dalam `docs/evaluation/protocol.md` (OI-02); dokumen ini tidak menutup OI-02.

Setiap objek memiliki tepat enam field berikut; nama field menggunakan huruf kecil agar konsisten dengan kolom manifest dataset.

| Field | Tipe | Ketentuan |
| --- | --- | --- |
| `id` | string | Unik di seluruh berkas; pola `<lang>-<kategori huruf kecil>-<01..06>`, misalnya `id-low-01`. |
| `lang` | string | Hanya `id` (Indonesia) atau `en` (Inggris), sesuai nama berkas dan bahasa surat. |
| `label` | string | Hanya `LOW`, `MEDIUM`, atau `HIGH`, sesuai nama berkas dan aturan skoring di bawah. |
| `indicators` | array string | Kode indikator referensi yang memang ada dalam teks; tidak boleh duplikat atau memakai kode di luar taksonomi. Array kosong `[]` sah untuk LOW. |
| `text` | string | Isi surat final, tidak kosong. Gunakan `\n` untuk baris baru dalam string JSON. Hanya field ini yang dirender menjadi isi surat dan diteruskan ke pipeline analisis. |
| `notes` | string | Catatan tidak kosong: alasan label/indikator dan pola pengecoh, penulis, peninjau serta status tinjauan. Bila dibantu model bahasa, catat identitas model bantu agar dapat diperiksa terhadap kandidat model evaluasi. |

`label`, `indicators`, dan `notes` adalah anotasi referensi, tidak boleh dicetak ke PDF atau dimasukkan ke prompt analisis. `split`, `format`, `file`, dan `sha256` ditetapkan oleh tooling dataset, bukan oleh penulis templat. Pasangan PDF teks/scan dari surat sumber yang sama harus tetap dalam split yang sama agar isi surat tidak bocor dari dev ke test.

## Label dan Taksonomi

Acuan label adalah PRD bagian 8.4 dan 8.5 (BR-04.06). Kode dihitung satu kali, meskipun muncul berkali-kali dalam surat.

| Kode | Tingkat | Pola yang dilabeli |
| --- | --- | --- |
| `PAYMENT_REQUEST` | HIGH | Pelamar diminta membayar biaya sebelum bekerja. Biaya yang ditanggung perusahaan bukan indikator ini. |
| `SENSITIVE_DATA_REQUEST` | HIGH | Permintaan OTP, PIN, password, akses rekening, atau data sensitif sejenis. |
| `UNOFFICIAL_CONTACT` | MEDIUM | Komunikasi hanya melalui kanal pribadi atau email layanan gratis yang mengatasnamakan HR. |
| `URGENCY_PRESSURE` | MEDIUM | Tenggat sangat singkat atau ancaman kehilangan posisi. |
| `IDENTITY_INCONSISTENCY` | MEDIUM | Nama perusahaan, alamat, posisi, atau penanda tangan saling bertentangan dalam surat. |
| `UNREALISTIC_COMPENSATION` | LOW | Kompensasi jauh melebihi kewajaran posisi. |
| `VAGUE_JOB_DETAILS` | LOW | Rincian pekerjaan tidak memadai. |

- **HIGH:** minimal satu kode bertingkat HIGH.
- **MEDIUM:** tanpa HIGH, tetapi ada minimal satu MEDIUM atau dua kode LOW yang berbeda.
- **LOW:** selain kondisi di atas, termasuk tanpa indikator atau hanya satu kode LOW.

Kategori merupakan label indikasi risiko isi surat, bukan vonis asli/palsu atau aman/penipuan. Seluruh kode taksonomi perlu tercakup pada sejumlah surat MEDIUM/HIGH dalam kumpulan akhir. Surat LOW juga harus memuat pola wajar yang mirip indikator, misalnya biaya relokasi ditanggung perusahaan, untuk menguji false positive.

## Contoh Lengkap per Kategori

Setiap blok berikut berisi satu objek lengkap untuk menunjukkan format, bukan berkas penyerahan enam surat. Contoh dibuat dengan bantuan coding agent pada T5-01 dan belum ditinjau manusia. Contoh dokumentasi ini tidak termasuk dataset evaluasi; jangan menyalinnya ke dataset sebelum tinjauan manual dan pencatatan identitas model bantu sesuai PRD bagian 10.4.2.

### LOW — Bahasa Indonesia

```json
{
  "id": "id-low-01",
  "lang": "id",
  "label": "LOW",
  "indicators": [],
  "text": "Bandung, 2 November 2026\nPerihal: Penawaran Kerja Staf Administrasi\n\nYth. Nara Contoh,\nPT Awan Kertas Contoh menawarkan posisi Staf Administrasi mulai 1 Desember 2026. Tugas Anda meliputi pencatatan surat masuk, pengarsipan dokumen, dan penyusunan laporan administrasi mingguan di bawah koordinasi Kepala Administrasi, Rima Contoh. Lokasi kerja di Jalan Simulasi Nomor 12, Bandung, dengan jadwal Senin sampai Jumat pukul 08.00–17.00 WIB dan waktu istirahat satu jam.\n\nGaji pokok sebesar Rp5.500.000 per bulan, ditambah tunjangan makan Rp500.000 per bulan. Biaya relokasi dan pemeriksaan kesehatan ditanggung langsung oleh perusahaan; pelamar tidak diminta membayar. Silakan menyampaikan tanggapan paling lambat 16 November 2026 melalui hr@awan-kertas.test. Pertanyaan mengenai penawaran dapat disampaikan melalui kontak perusahaan pada situs https://awan-kertas.test.\n\nHormat kami,\nRima Contoh\nKepala Administrasi, PT Awan Kertas Contoh",
  "notes": "Tidak ada indikator referensi. Penyebutan biaya relokasi dan pemeriksaan kesehatan merupakan pengecoh yang wajar karena dibayar perusahaan. Penulis: coding agent sesi T5-01; peninjau manusia: belum ada; status: contoh dokumentasi, bukan dataset evaluasi."
}
```

### MEDIUM — Bahasa Inggris

```json
{
  "id": "en-medium-01",
  "lang": "en",
  "label": "MEDIUM",
  "indicators": ["URGENCY_PRESSURE"],
  "text": "Bandung, 2 November 2026\nSubject: Employment Offer for Inventory Clerk\n\nDear Lila Sample,\nPT Blue Paper Example offers you the position of Inventory Clerk starting on 1 December 2026. Your duties are to record stock movements, reconcile weekly inventory reports, and assist warehouse audits under the supervision of Warehouse Manager, Damar Sample. The workplace is 20 Example Street, Bandung. Working hours are Monday to Friday, 08:00 to 17:00 WIB, including a one-hour break.\n\nThe monthly base salary is IDR 5,500,000, with a monthly meal allowance of IDR 500,000. No recruitment payment is required. You must accept within 30 minutes of receiving this letter, or this offer will be withdrawn permanently. Send your confirmation to hr@blue-paper.test. Company contact information is available at https://blue-paper.test.\n\nSincerely,\nDamar Sample\nWarehouse Manager, PT Blue Paper Example",
  "notes": "URGENCY_PRESSURE: kutipan 'You must accept within 30 minutes of receiving this letter, or this offer will be withdrawn permanently.' menunjukkan tenggat sangat singkat dengan ancaman. Satu MEDIUM tanpa HIGH menghasilkan MEDIUM. Penulis: coding agent sesi T5-01; peninjau manusia: belum ada; status: contoh dokumentasi, bukan dataset evaluasi."
}
```

### HIGH — Bahasa Indonesia

```json
{
  "id": "id-high-01",
  "lang": "id",
  "label": "HIGH",
  "indicators": ["PAYMENT_REQUEST", "UNOFFICIAL_CONTACT"],
  "text": "Bandung, 2 November 2026\nPerihal: Penawaran Kerja Staf Arsip\n\nYth. Bima Contoh,\nPT Lentera Dokumen Contoh menawarkan posisi Staf Arsip mulai 1 Desember 2026. Tugas Anda adalah mengelompokkan dokumen, memperbarui katalog arsip, dan membuat laporan penyimpanan bulanan di bawah arahan Kepala Arsip, Sari Contoh. Tempat kerja berada di Jalan Fiktif Nomor 8, Bandung. Jadwal kerja Senin sampai Jumat pukul 08.00–17.00 WIB dengan istirahat satu jam. Gaji pokok sebesar Rp5.500.000 per bulan dan tunjangan makan Rp500.000 per bulan.\n\nSebelum mulai bekerja, Anda wajib membayar biaya administrasi rekrutmen sebesar Rp1.500.000 kepada petugas penerimaan. Seluruh komunikasi rekrutmen hanya melalui pesan WhatsApp pribadi petugas yang mengirim surat ini; jangan menghubungi kanal perusahaan. Rincian pembayaran akan disampaikan melalui percakapan pribadi tersebut.\n\nHormat kami,\nSari Contoh\nKepala Arsip, PT Lentera Dokumen Contoh",
  "notes": "PAYMENT_REQUEST: 'Anda wajib membayar biaya administrasi rekrutmen sebesar Rp1.500.000'; UNOFFICIAL_CONTACT: 'Seluruh komunikasi rekrutmen hanya melalui pesan WhatsApp pribadi petugas'. Minimal satu HIGH menghasilkan HIGH. Penulis: coding agent sesi T5-01; peninjau manusia: belum ada; status: contoh dokumentasi, bukan dataset evaluasi."
}
```

## Pemeriksaan Sebelum Serah Terima

Untuk T2-04 dan T4-03, penulis dan peninjau memeriksa hal berikut secara manual dan menyebutkan hasilnya di PR:

1. JSON dapat di-parse; setiap berkas merupakan array berisi enam objek dengan tepat enam field di atas. Semua `id` unik, mengikuti pola, dan sesuai nama berkas, `lang`, serta `label`.
2. Seluruh tipe field benar; `text` dan `notes` tidak kosong; `indicators` hanya memakai kode yang diizinkan tanpa duplikat. Kategori cocok dengan skoring indikator referensi.
3. Surat utuh dalam bahasa yang ditetapkan, seluruh data fiktif, dan tidak ada placeholder tersisa. Setiap indikator referensi memiliki dasar pada teks; catat kutipan pendukung dalam `notes` agar dapat ditinjau.
4. Peninjau membaca isi setiap surat, termasuk pengecualian biaya ditanggung perusahaan dan kemungkinan indikator tambahan yang belum dilabeli. Templat ID ditinjau Pash; templat EN ditinjau Van, sehingga penulis/peninjau berbeda dari pengembang prompt.
5. `notes` mencatat penulis, peninjau, dan status tinjauan yang sebenarnya. Bila menggunakan model bantu, identitasnya dicatat dan harus berbeda dari setiap model yang dievaluasi; pemeriksaan ini diulang saat memilih kandidat T5-07. Jangan mengklaim tinjauan telah dilakukan sebelum ada pelaksanaannya.
6. Serahkan enam surat per kategori/bahasa kepada B untuk T5-05. Hanya isi `text` menjadi surat; anotasi referensi tetap di luar PDF dan input model. Penetapan split, checksum, dan pembekuan test set dilakukan pada tugas dataset/evaluasi, bukan pada penulisan templat.
