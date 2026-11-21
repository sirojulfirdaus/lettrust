# BAB 2. GAMBARAN UMUM PRODUK

## 2.1 Latar Belakang

Penipuan rekrutmen dapat dilakukan dengan mencatut nama, logo, atau identitas perusahaan, menggunakan surat yang menyerupai dokumen resmi, memakai kontak yang mengatasnamakan HR, serta meminta pembayaran dengan alasan administrasi, pelatihan, transportasi, atau akomodasi.

Ketika meragukan offer letter, pelamar umumnya diarahkan untuk mencari kanal resmi perusahaan dan meminta konfirmasi secara manual. Mekanisme verifikasi dokumen elektronik sudah tersedia di sejumlah organisasi, tetapi penerapannya berbeda-beda. Bukti penerbitan, kecocokan isi berkas, status keberlakuan surat, dan pengenalan indikasi penipuan belum tentu dapat diperiksa melalui satu alur layanan.

Lettrust dikembangkan sebagai layanan verifikasi independen yang diintegrasikan ke job portal mitra. Melalui Lettrust, pelamar dapat memeriksa bukti penerbitan, keutuhan berkas, dan status surat yang dicatat penerbit terverifikasi, serta memperoleh analisis indikasi risiko berbasis AI atas isi surat.

Kondisi As-Is bersifat konseptual untuk perusahaan pemberi kerja secara umum dan disusun dari sumber sekunder serta asumsi terbuka, bukan dari observasi satu perusahaan tertentu.

## 2.2 Permasalahan Produk

Permasalahan berasal dari D1 (subbab 1.1.3 laporan) dan dipertahankan tanpa perubahan identifier.

| ID | Permasalahan | Dampak pada Layanan | Dasar |
| ----- | ----- | ----- | ----- |
| P-01 | Penyalahgunaan identitas perusahaan dalam komunikasi rekrutmen | Pelamar berisiko menerima dokumen yang mengatasnamakan perusahaan tanpa diterbitkan pihak berwenang. | Didukung sumber sekunder |
| P-02 | Ketergantungan pada verifikasi melalui kanal terpisah | Pelamar harus mencari kanal resmi dan meminta konfirmasi secara mandiri. | Didukung sumber sekunder |
| P-03 | Keterbatasan pemeriksaan bukti penerbitan dan integritas dokumen | Tanpa mekanisme verifikasi digital, pelamar sulit memastikan berkas sesuai versi yang diterbitkan. | Potensi gap yang perlu validasi |
| P-04 | Keterbatasan akses terhadap status dokumen | Pelamar tidak dapat mengetahui langsung apakah penawaran masih berlaku atau telah dicabut. | Potensi gap yang perlu validasi |
| P-05 | Kesulitan mengenali indikasi penipuan pada isi dokumen | Pelamar harus mengenali sendiri permintaan pembayaran, kontak tidak resmi, atau informasi tidak konsisten. | Didukung sumber sekunder |

Permasalahan utama bukan ketiadaan teknologi verifikasi dokumen, melainkan belum terintegrasinya pemeriksaan bukti penerbitan, integritas, status, dan indikasi risiko dalam satu alur layanan yang mudah diakses pelamar.

PRD tidak mengklaim bahwa seluruh perusahaan mengalami permasalahan tersebut atau bahwa seluruh kasus penipuan rekrutmen melibatkan offer letter.

## 2.3 Visi Produk

Lettrust menjadi lapisan kepercayaan bagi ekosistem rekrutmen: pelamar dapat memeriksa offer letter sebelum mempercayainya, perusahaan dapat menerbitkan bukti yang dapat diperiksa, dan job portal dapat menawarkan kapabilitas verifikasi tanpa membangun infrastruktur sendiri, tanpa menyatakan suatu penawaran pasti aman atau pasti penipuan.

## 2.4 Tujuan Produk

1. Menyediakan pemeriksaan mandiri atas bukti penerbitan, keutuhan berkas, dan status offer letter melalui portal mitra.
2. Memastikan hanya penerbit terverifikasi dan HR terotorisasi yang dapat mencatat dan mencabut bukti.
3. Menyediakan bukti penerbitan dan riwayat status yang tamper-evident menggunakan blockchain.
4. Membantu pelamar mengenali indikasi penipuan pada isi surat menggunakan AI, termasuk untuk surat yang tidak tercatat.
5. Menyajikan hasil secara terpisah, jujur, dan dapat ditindaklanjuti, termasuk ketika sebagian pemeriksaan gagal atau tidak dijalankan.
6. Membuktikan rancangan D1–D2 melalui prototipe yang dapat diuji dan didemonstrasikan.

## 2.5 Positioning dan Diferensiasi

Lettrust bukan job portal. Lettrust tidak menyediakan posting lowongan, pencarian kerja, CV screening, matching, tes, wawancara, penetapan kandidat, payroll, atau onboarding karyawan.

| Aspek | Job Portal | Lettrust |
| ----- | ----- | ----- |
| Fungsi inti | Publikasi lowongan dan proses lamaran | Verifikasi bukti penerbitan offer letter dan analisis indikasi risiko |
| Posisi dalam proses | Sebelum dan selama seleksi | Setelah kandidat menerima penawaran |
| Hubungan | Pelanggan B2B dan kanal distribusi Lettrust | Penyedia layanan verifikasi melalui API |
| Penerbit surat | Bukan penerbit | Tidak menerbitkan surat; mencatat bukti penerbitan dari HR terotorisasi |
| Kepercayaan penerbit | Tidak menjadi validator legalitas | Administrator independen memverifikasi penerbit sebelum penerbit dapat mencatat bukti |

Perusahaan tidak otomatis dipercaya karena membayar atau terdaftar di job portal. Kepercayaan penerbit berasal dari verifikasi administrator dan otorisasi HR.

## 2.6 Model Bisnis

Model bisnis mengikuti BMC To-Be D1 dan bersifat hipotesis perancangan.

| Elemen | Ketentuan |
| ----- | ----- |
| Model | API-based Integration Partnership (B2B2C). |
| Pelanggan B2B | Job portal yang mengintegrasikan Lettrust melalui REST API. |
| Pengguna manfaat | Perusahaan/HR (penerbit) dan pelamar (pemeriksa). |
| Pendapatan (hipotesis) | Lisensi berlangganan dan kuota penggunaan API yang dibayarkan job portal; biaya kelebihan kuota sesuai kontrak. |
| Biaya pengguna | Perusahaan/HR dan pelamar tidak dikenai biaya penggunaan langsung. |
| Implementasi pada D3 | Tidak ada billing, pembayaran, harga, atau manajemen kuota komersial. Portal mitra disimulasikan. |

Skema lama yang membebankan biaya kepada perusahaan (subscription atau pay-per-issuance) tidak digunakan.

## 2.7 Proposisi Nilai

| Segmen | Nilai |
| ----- | ----- |
| Job portal mitra | Kapabilitas verifikasi offer letter dan analisis risiko yang dapat ditambahkan melalui satu API tanpa membangun infrastruktur sendiri. |
| Perusahaan/HR | Pencatatan bukti penerbitan offer letter resmi tanpa biaya langsung, serta kendali pencabutan status apabila penawaran dibatalkan. |
| Pelamar | Pemeriksaan mandiri tanpa akun atas bukti penerbitan dan penerbitnya, status surat, keutuhan berkas, serta indikasi risiko isi surat, disertai panduan tindak lanjut. |

## 2.8 Kapabilitas Utama Produk

| Kapabilitas | Deskripsi | FR |
| ----- | ----- | ----- |
| Issuer Onboarding & Authorization | Registrasi perusahaan, verifikasi oleh administrator, dan otorisasi akun HR. | FR-01 |
| Partner Verification Interface | Fitur pemeriksaan pada portal mitra dengan Mode Dengan Kode dan Mode Tanpa Kode. | FR-02 |
| Proof Issuance & Integrity Check | Pencatatan hash dan status bukti ke blockchain serta pembandingan hash berkas pelamar. | FR-03 |
| Proof Revocation | Pencabutan bukti oleh HR berwenang dan penyajian status terkini. | FR-04 |
| AI Fraud Risk Analysis | Ekstraksi teks/OCR dan analisis indikator risiko berbasis taksonomi. | FR-05 |
| Result Separation & Exception Handling | Penyajian hasil terpisah dan pembedaan kondisi tidak tercatat, gangguan, serta pemeriksaan yang tidak dijalankan. | FR-06 |

Kapabilitas tersebut tersedia melalui tiga area antarmuka:

1. **Portal Karier Mitra (Simulasi)** untuk pelamar, sebagai client API terpisah.
2. **Lettrust Console — area Perusahaan/HR** untuk registrasi, status, penerbitan, dan pencabutan bukti.
3. **Lettrust Console — area Administrator** untuk verifikasi penerbit dan otorisasi HR.

## 2.9 Peran Teknologi

### 2.9.1 Peran Blockchain

| Fungsi | Ketentuan |
| ----- | ----- |
| Yang dicatat | `proofId`, `documentHash`, referensi penerbit, status lifecycle, serta waktu penerbitan dan pencabutan. |
| Yang tidak dicatat | Isi offer letter, berkas, `referenceCode`, data pribadi pelamar, maupun data kontak. |
| Nilai | Catatan bukti dan riwayat status bersifat append-only dan tamper-evident. Status REVOKED tidak menghapus riwayat penerbitan, dan perubahan tidak dapat dilakukan secara diam-diam oleh pengelola basis data. |
| Batas kepercayaan | Prototipe menggunakan satu signer milik layanan. Otorisasi penerbit dilakukan off-chain oleh administrator sebelum transaksi diizinkan. Operator layanan tetap merupakan pihak yang dipercaya; blockchain tidak menghilangkan kepercayaan tersebut. |
| Jaringan | Jaringan pengembangan lokal yang nyata (bukan simulasi basis data). |

Hash membuktikan bahwa berkas yang diperiksa identik byte demi byte dengan berkas yang dicatat. Hash tidak membuktikan identitas hukum perusahaan, keaslian isi, atau keamanan penawaran.

### 2.9.2 Peran AI

| Fungsi | Ketentuan |
| ----- | ----- |
| Input | Teks hasil ekstraksi PDF atau OCR, bukan berkas mentah dan bukan kode referensi. |
| Model | Model bahasa pra-latih yang sudah tersedia, diakses melalui layanan inferensi free tier. Tidak ada pelatihan, fine-tuning, atau penggunaan GPU lokal. |
| Proses | Model mendeteksi indikator berdasarkan taksonomi yang ditetapkan (BR-04). Setiap indikator wajib memiliki kutipan bukti yang benar-benar terdapat pada teks surat. Kategori risiko ditentukan oleh aturan skoring yang transparan. |
| Output | Kategori LOW/MEDIUM/HIGH, daftar indikator beserta kutipan bukti, penjelasan, dan rekomendasi tindak lanjut dalam bahasa Indonesia. |
| Evaluasi | Dataset offer letter sintetis berlabel (Indonesia/Inggris, PDF teks/scan) dengan test set terpisah, dibandingkan dengan baseline berbasis aturan. |
| Batas | Hasil AI bersifat indikatif, bukan putusan hukum, bukan penentu keaslian dokumen, dan tidak menggantikan konfirmasi kanal resmi. |

AI tidak memiliki akses tulis ke blockchain dan tidak terlibat dalam verifikasi penerbit, otorisasi, penerbitan, maupun pencabutan. Blockchain tidak melakukan analisis teks.

### 2.9.3 Saling Melengkapi

Bukti yang tercatat dan aktif belum tentu berarti isi surat bebas risiko. Surat yang tidak tercatat belum tentu palsu. Karena itu, kedua jenis pemeriksaan disajikan terpisah dan dibaca bersama sebagai bahan pertimbangan pelamar.

## 2.10 Prinsip Produk

| Prinsip | Ketentuan |
| ----- | ----- |
| Honest Results | Sistem tidak menyajikan hasil yang tidak benar-benar diperiksa dan tidak mengarang status, kategori, atau bukti. |
| Separated Outcomes | Bukti penerbitan, integritas berkas, dan analisis AI disajikan sebagai hasil yang berbeda. |
| No Single Verdict | Tidak ada label tunggal "asli/palsu" atau "aman/penipuan". |
| Upstream Trust | Kepercayaan penerbit ditetapkan melalui verifikasi administrator dan otorisasi HR sebelum pencatatan. |
| Privacy by Design | Berkas tidak disimpan permanen; data pribadi dan isi surat tidak dicatat on-chain. |
| Applicant Without Account | Pelamar memeriksa surat tanpa registrasi atau login. |
| Partner as Client | Job portal adalah client API; token partner tidak pernah sampai ke browser pelamar. |
| Fail Honestly | Kegagalan komponen dinyatakan sebagai gangguan, bukan sebagai hasil bisnis. |
| Evidence over Claims | Kemampuan dinyatakan berdasarkan bukti pengujian, bukan asumsi. |
| Official Channel First | Pelamar selalu diarahkan untuk mengonfirmasi melalui kanal resmi perusahaan apabila ragu. |

## 2.11 Batasan Produk

Lettrust merupakan alat bantu pengambilan keputusan pelamar, bukan pengganti verifikasi legal, kanal resmi perusahaan, atau penegak hukum.

Lettrust tidak menjamin bahwa surat dengan bukti ACTIVE dan MATCH bebas dari risiko, dan tidak menyatakan bahwa surat yang tidak tercatat atau berkategori HIGH merupakan penipuan.

Prototipe D3 menggunakan entitas perusahaan, akun, dan dokumen sintetis, berjalan secara lokal, dan belum merepresentasikan kapasitas produksi maupun integrasi komersial dengan job portal nyata.
