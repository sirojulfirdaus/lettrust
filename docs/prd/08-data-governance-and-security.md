# BAB 8. BUSINESS RULES & DATA GOVERNANCE

## 8.1 Gambaran Umum

Bab ini menetapkan aturan bisnis, semantik hasil verifikasi, aturan pemrosesan AI, batas akses informasi, dan kebijakan pengelolaan data Lettrust. Ketentuan berlaku pada Portal Karier Mitra (Simulasi), Lettrust Console, backend, registry blockchain, dan layanan AI.

Business rules dikelompokkan sebagai berikut:

| Kelompok | Cakupan |
| ----- | ----- |
| BR-01 | Identitas, akun, penerbit, dan otorisasi |
| BR-02 | Lifecycle bukti dan blockchain |
| BR-03 | Verifikasi dan semantik hasil |
| BR-04 | Pemrosesan dan evaluasi AI |
| BR-05 | Data, privasi, dan secret |

## 8.2 Business Rules Catalog

### 8.2.1 BR-01 — Identity, Issuer & Authorization

| ID | Business Rule |
| ----- | ----- |
| BR-01.01 | Akun yang dibuat melalui registrasi selalu ber-role HR. Role tidak dapat dipilih atau dikirim oleh client. |
| BR-01.02 | Email akun bersifat unik. Password disimpan dalam bentuk hash. |
| BR-01.03 | Identitas, role, dan afiliasi pengguna ditentukan backend dari token sesi yang valid. Token memiliki masa berlaku terbatas. |
| BR-01.04 | Registrasi perusahaan menghasilkan penerbit berstatus PENDING dan tidak memberikan hak penerbitan. |
| BR-01.05 | Satu akun HR hanya dapat berafiliasi dengan satu penerbit. Akun yang mendaftarkan perusahaan otomatis berafiliasi dengan status NOT_AUTHORIZED. |
| BR-01.06 | Nomor registrasi perusahaan bersifat unik di Lettrust. |
| BR-01.07 | Hanya Administrator yang dapat memutuskan verifikasi penerbit. Perusahaan atau HR tidak dapat memverifikasi dirinya sendiri. Administrator tidak dapat menjadi anggota penerbit. |
| BR-01.08 | Keputusan verifikasi hanya diberikan pada penerbit PENDING, wajib menyertakan `evidenceRef`, dan bersifat final pada D3 (VERIFIED atau REJECTED). |
| BR-01.09 | Otorisasi HR hanya diberikan oleh Administrator kepada akun yang terafiliasi dengan penerbit VERIFIED. |
| BR-01.10 | Otorisasi HR dicatat beserta Administrator pelaksana dan waktunya. Pencabutan otorisasi HR berada di luar cakupan D3 dan berbeda dari status bukti REVOKED. |
| BR-01.11 | Penerbitan dan pencabutan bukti hanya dapat dilakukan oleh HR AUTHORIZED pada penerbit VERIFIED. |
| BR-01.12 | Bukti dimiliki oleh penerbit. Penerbit untuk operasi ditentukan dari afiliasi akun di backend, bukan dari nilai yang dikirim client. |
| BR-01.13 | Akun Administrator dan client partner hanya dibuat melalui seed atau konfigurasi dan menggunakan identitas sintetis. |
| BR-01.14 | Token partner hanya berlaku untuk API-07, disimpan sebagai hash di Lettrust, dan tidak pernah dikirim ke browser pelamar. |
| BR-01.15 | Endpoint internal hanya dapat dipanggil oleh backend Lettrust. Pelamar, partner, HR, dan Administrator tidak dapat memanggilnya. |

### 8.2.2 BR-02 — Proof Lifecycle & Blockchain

| ID | Business Rule |
| ----- | ----- |
| BR-02.01 | HR mengunggah offer letter final. Lettrust tidak membuat, mengedit, atau mengirim surat. |
| BR-02.02 | Berkas yang diterima hanya PDF yang divalidasi berdasarkan tanda tangan berkas, tidak kosong, dan tidak melebihi batas ukuran. |
| BR-02.03 | `documentHash` dihitung dengan SHA-256 atas byte berkas asli. Algoritma yang sama digunakan saat verifikasi. Hash tidak pernah dihitung atas teks hasil ekstraksi atau OCR. |
| BR-02.04 | `proofId` dan `referenceCode` dibuat acak, unik, dan tidak berurutan. `referenceCode` tidak dapat diturunkan dari identitas lain dan tidak memuat informasi pribadi. |
| BR-02.05 | `referenceCode` dan pemetaannya ke `proofId` disimpan off-chain. |
| BR-02.06 | Registry hanya menyimpan `proofId`, `documentHash`, referensi penerbit, status lifecycle, waktu penerbitan, dan waktu pencabutan. |
| BR-02.07 | Transaksi tulis ke registry hanya dikirim oleh signer Lettrust setelah otorisasi off-chain (BR-01.11) terpenuhi. |
| BR-02.08 | ACTIVE, REVOKED, dan keberhasilan operasi hanya dinyatakan setelah transaksi terkonfirmasi. Kegagalan tidak boleh dinyatakan sebagai keberhasilan dan tidak boleh menghasilkan kode yang berlaku. |
| BR-02.09 | Operasi mutasi (penerbitan dan pencabutan) mendukung idempotensi agar pengulangan tidak menghasilkan transaksi ganda. |
| BR-02.10 | Registry adalah sumber kebenaran status dan hash. Salinan off-chain hanya untuk tampilan dan tidak digunakan sebagai dasar verifikasi. |
| BR-02.11 | Pencabutan hanya mengubah status ACTIVE menjadi REVOKED dan wajib menyertakan `reasonCode` dari daftar: `OFFER_WITHDRAWN`, `ISSUED_IN_ERROR`, `DOCUMENT_REPLACED`, `OTHER`. |
| BR-02.12 | Alasan pencabutan disimpan off-chain, ditampilkan kepada HR penerbit, dan tidak ditampilkan kepada pelamar. |
| BR-02.13 | REVOKED adalah status final. Tidak ada reaktivasi. Pencabutan ulang ditolak sebagai konflik status. |
| BR-02.14 | Pencabutan tidak menghapus bukti maupun riwayat penerbitan. Peristiwa penerbitan dan pencabutan tercatat terpisah. |
| BR-02.15 | Pencabutan lintas penerbit dilarang dan ditegakkan pada backend maupun contract. |
| BR-02.16 | Bukti yang sudah tercatat tidak dapat ditimpa. |

### 8.2.3 BR-03 — Verification & Result Semantics

| ID | Business Rule |
| ----- | ----- |
| BR-03.01 | Hasil verifikasi terdiri atas tiga komponen terpisah: bukti penerbitan dan status, integritas berkas, dan analisis AI. Tidak ada vonis tunggal "asli/palsu" atau "aman/penipuan". |
| BR-03.02 | Setiap nilai hasil memiliki makna terbatas sebagaimana §8.3 dan tidak boleh ditafsirkan melebihi makna tersebut. |
| BR-03.03 | `referenceCode` dipetakan ke bukti secara internal di Lettrust. Portal tidak menangani `proofId` sebagai dasar pencarian. |
| BR-03.04 | NOT_FOUND hanya digunakan setelah registry berhasil diperiksa. NOT_FOUND berarti tidak tercatat dalam cakupan Lettrust dan tidak otomatis berarti palsu. |
| BR-03.05 | Status bukti dibaca dari registry pada saat verifikasi sehingga pencabutan langsung terlihat. |
| BR-03.06 | Kegagalan registry dinyatakan UNAVAILABLE, bukan NOT_FOUND. |
| BR-03.07 | MATCH berarti byte berkas identik dengan berkas yang tercatat, bukan bahwa isi surat aman. MISMATCH berarti berkas berbeda, bukan otomatis penipuan. |
| BR-03.08 | Pemeriksaan dengan kode saja membuktikan keberadaan catatan, penerbit, dan status, tetapi tidak membuktikan bahwa berkas yang dimiliki pelamar sama dengan berkas yang tercatat. |
| BR-03.09 | Tanpa kode referensi, hanya analisis AI yang dilakukan. Registry tidak dipanggil dan tidak ada status bukti yang disajikan, termasuk NOT_FOUND. |
| BR-03.10 | Label antarmuka diturunkan dari enum API secara konsisten sesuai §9.6. Label naratif diagram tidak menggantikan enum API. |
| BR-03.11 | Panduan tindak lanjut selalu menyertakan anjuran konfirmasi melalui kanal resmi perusahaan apabila ragu dan anjuran tidak melakukan pembayaran dalam proses rekrutmen. |
| BR-03.12 | Kegagalan suatu komponen dinyatakan sebagai gangguan dan tidak menghilangkan hasil komponen lain yang berhasil. Tidak ada hasil fiktif sebagai pengganti. |
| BR-03.13 | Kombinasi input yang tidak bermakna ditolak sebagai input tidak valid, bukan diproses sebagai verifikasi. |
| BR-03.14 | Informasi penerbit yang disajikan kepada pelamar dibatasi pada identitas penerbit, nama perusahaan, status verifikasi penerbit, serta waktu penerbitan dan pencabutan. |

### 8.2.4 BR-04 — AI Processing & Evaluation

| ID | Business Rule |
| ----- | ----- |
| BR-04.01 | Analisis AI hanya dijalankan apabila diminta, berkas tersedia, dan persetujuan diberikan. Analisis berjalan independen dari hasil bukti dan integritas, dan hasil bukti tidak menjadi input analisis. |
| BR-04.02 | Input analisis adalah teks hasil ekstraksi. Halaman tanpa lapisan teks memadai diproses OCR (bahasa Indonesia dan Inggris). Pemrosesan dibatasi jumlah halaman dan panjang teks yang dikonfigurasi; pemrosesan sebagian dinyatakan secara eksplisit. |
| BR-04.03 | Indikator yang dapat dihasilkan terbatas pada taksonomi §8.4. |
| BR-04.04 | Setiap indikator wajib memiliki kutipan bukti yang ditemukan pada teks dokumen setelah normalisasi. Indikator tanpa bukti yang tervalidasi dibuang. |
| BR-04.05 | Model yang digunakan adalah model bahasa pra-latih yang sudah tersedia. Tidak ada pelatihan atau fine-tuning. Parameter inferensi dibuat sedeterministik mungkin, dan identitas model dicatat. |
| BR-04.06 | Kategori risiko ditentukan oleh aturan skoring §8.5 dari indikator tervalidasi, bukan ditentukan bebas oleh model. |
| BR-04.07 | Penjelasan dan rekomendasi ditulis dalam bahasa Indonesia dan merujuk pada indikator yang terdeteksi. |
| BR-04.08 | Hasil AI bersifat indikatif. LOW tidak menjamin aman, HIGH tidak membuktikan kejahatan, dan hasil AI tidak menentukan keaslian dokumen. |
| BR-04.09 | Tanpa konten yang dapat diperoleh, tidak ada kategori, indikator, penjelasan, atau rekomendasi yang dibuat. |
| BR-04.10 | Hanya teks hasil ekstraksi yang dikirim ke penyedia model. Pemrosesan memerlukan persetujuan yang diperoleh portal. |
| BR-04.11 | Isi dokumen diperlakukan sebagai data tidak tepercaya dan tidak dapat mengubah instruksi, taksonomi, skema output, atau aturan skoring. |
| BR-04.12 | Kegagalan AI dinyatakan UNAVAILABLE dengan alasan. Tidak ada peralihan otomatis ke provider lain, mock, atau baseline aturan sebagai pengganti hasil. Mock provider hanya untuk unit test. |
| BR-04.13 | Evaluasi menggunakan dev set untuk penyesuaian dan test set yang dibekukan sebelum penyesuaian final. Test set tidak digunakan untuk penyesuaian. |
| BR-04.14 | Hasil evaluasi dilaporkan apa adanya, termasuk kesalahan dan keterbatasan, tanpa klaim performa pada data dunia nyata. |
| BR-04.15 | Komponen AI tidak memiliki akses tulis ke registry dan tidak terlibat dalam verifikasi penerbit, otorisasi, penerbitan, atau pencabutan. |

### 8.2.5 BR-05 — Data, Privacy & Secrets

| ID | Business Rule |
| ----- | ----- |
| BR-05.01 | Pelamar tidak memerlukan akun dan tidak diminta data pribadi. |
| BR-05.02 | Isi dokumen, kode referensi, dan data pribadi tidak disimpan on-chain. |
| BR-05.03 | Berkas dan teks hasil ekstraksi diproses sementara dan tidak disimpan permanen. |
| BR-05.04 | Persetujuan pemrosesan AI diperoleh sebelum isi surat dikirim ke penyedia model. |
| BR-05.05 | Log tidak memuat isi berkas, teks dokumen, respons mentah model, kode referensi utuh, data pribadi, password, token, atau kunci. Log verifikasi hanya memuat enum hasil dan metadata teknis. |
| BR-05.06 | Seluruh identitas, perusahaan, dan dokumen yang digunakan adalah data sintetis. |
| BR-05.07 | Secret tidak di-commit ke repository, tidak dikirim ke frontend, dan tidak muncul pada respons atau pesan kesalahan. |
| BR-05.08 | Layanan AI pihak ketiga hanya digunakan dengan data sintetis sesuai §8.9. |

## 8.3 Semantik Hasil Verifikasi

Tabel berikut menjadi acuan makna nilai pada API-07. Skema field rinci ditetapkan di SYSTEM_ARCHITECTURE; label antarmuka ditetapkan di §9.6.

### 8.3.1 `proofCheck`

| `lookup` | `lifecycleStatus` | `reason` | Makna | Bukan Berarti |
| ----- | ----- | ----- | ----- | ----- |
| FOUND | ACTIVE | — | Kode merujuk bukti yang dicatat penerbit terverifikasi dan masih berlaku menurut registry. | Isi surat aman atau penawaran pasti sah. |
| FOUND | REVOKED | — | Bukti pernah dicatat dan telah dicabut penerbit. | Surat palsu. |
| NOT_FOUND | null | — | Registry berhasil diperiksa dan kode tidak merujuk bukti yang tercatat. | Surat palsu. |
| UNAVAILABLE | null | `REGISTRY_UNAVAILABLE` | Pemeriksaan bukti tidak dapat dilakukan karena gangguan. | Kode tidak terdaftar. |
| NOT_REQUESTED | null | `NO_REFERENCE_CODE` | Pemeriksaan bukti tidak dilakukan karena tidak ada kode (Mode Tanpa Kode). | Kode tidak ditemukan. |

`issuerVerified` bernilai `true` apabila penerbit bukti berstatus VERIFIED saat pemeriksaan, `false` apabila tidak, dan `null` apabila bukti tidak ditemukan atau tidak diperiksa.

### 8.3.2 `integrityCheck`

| `result` | `reason` | Makna |
| ----- | ----- | ----- |
| MATCH | — | Byte berkas identik dengan berkas yang tercatat pada bukti. |
| MISMATCH | — | Berkas berbeda dari berkas yang tercatat, misalnya karena diubah, disimpan ulang, atau dikompresi. |
| NOT_CHECKED | `NO_FILE` | Bukti diperiksa tetapi berkas tidak diunggah. |
| NOT_CHECKED | `PROOF_NOT_FOUND` | Tidak ada hash rujukan karena bukti tidak ditemukan. |
| NOT_CHECKED | `REGISTRY_UNAVAILABLE` | Hash rujukan tidak dapat dibaca karena gangguan registry. |
| NOT_CHECKED | `NO_REFERENCE_CODE` | Mode Tanpa Kode; tidak ada bukti rujukan. |

### 8.3.3 `riskAnalysis`

| `state` | `reason` | `category` | Makna |
| ----- | ----- | ----- | ----- |
| COMPLETED | — | LOW / MEDIUM / HIGH | Analisis selesai pada konten yang tersedia. |
| NOT_REQUESTED | — | null | Analisis tidak diminta. |
| NOT_PERFORMED | `DOCUMENT_CONTENT_UNAVAILABLE` | null | Analisis diminta tetapi konten tidak tersedia (tanpa berkas, tanpa teks, OCR gagal, berkas terenkripsi atau rusak). |
| UNAVAILABLE | `AI_SERVICE_UNAVAILABLE` | null | Layanan AI internal tidak dapat dihubungi. |
| UNAVAILABLE | `AI_TIMEOUT` | null | Pemrosesan melebihi batas waktu. |
| UNAVAILABLE | `AI_QUOTA_EXCEEDED` | null | Kuota atau rate limit penyedia model terlampaui. |
| UNAVAILABLE | `AI_OUTPUT_INVALID` | null | Output model tidak valid setelah satu kali pengulangan. |

### 8.3.4 Kombinasi Penting

| Kombinasi | Interpretasi |
| ----- | ----- |
| FOUND + ACTIVE + MATCH | Surat yang diperiksa identik dengan surat yang dicatat penerbit terverifikasi dan bukti masih berlaku. Isi surat tetap perlu dibaca dengan waspada. |
| FOUND + ACTIVE + NOT_CHECKED (`NO_FILE`) | Kode valid dan aktif, tetapi belum dipastikan bahwa surat yang dimiliki pelamar adalah surat tersebut. Kode dapat saja disalin dari surat lain. |
| FOUND + ACTIVE + MISMATCH | Kode valid, tetapi berkas berbeda dari yang dicatat. Pelamar perlu meminta salinan asli melalui kanal resmi. |
| FOUND + REVOKED | Penerbit telah mencabut bukti. Pelamar perlu mengonfirmasi status penawaran melalui kanal resmi. |
| NOT_FOUND + AI COMPLETED | Surat tidak tercatat di Lettrust; analisis isi tetap tersedia sebagai bahan pertimbangan. |
| NOT_REQUESTED + AI COMPLETED | Mode Tanpa Kode; hanya indikasi risiko isi yang tersedia. |

## 8.4 Taksonomi Indikator Risiko

| Kode | Indikator | Tingkat | Contoh Pola |
| ----- | ----- | ----- | ----- |
| `PAYMENT_REQUEST` | Permintaan pembayaran dari pelamar | HIGH | Biaya administrasi, pelatihan, seragam, medical check-up, tiket, akomodasi, atau deposit yang dibayarkan pelamar sebelum bekerja. |
| `SENSITIVE_DATA_REQUEST` | Permintaan data atau akses sensitif | HIGH | OTP, PIN, password, foto kartu ATM, akses rekening, atau data kartu kredit. |
| `UNOFFICIAL_CONTACT` | Kontak hanya melalui kanal tidak resmi | MEDIUM | Komunikasi hanya melalui nomor pesan pribadi atau email layanan gratis yang mengatasnamakan HR perusahaan. |
| `URGENCY_PRESSURE` | Tekanan waktu atau ancaman | MEDIUM | Tenggat konfirmasi sangat singkat, ancaman kehilangan posisi, kuota terbatas. |
| `IDENTITY_INCONSISTENCY` | Inkonsistensi identitas perusahaan atau penawaran | MEDIUM | Nama perusahaan, alamat, posisi, atau penanda tangan yang tidak saling konsisten. |
| `UNREALISTIC_COMPENSATION` | Kompensasi tidak wajar | LOW | Gaji atau fasilitas yang jauh melebihi kewajaran untuk posisi yang disebutkan. |
| `VAGUE_JOB_DETAILS` | Rincian pekerjaan tidak jelas | LOW | Tanpa rincian tanggung jawab, lokasi, atau atasan; salam tidak spesifik. |

Ketentuan taksonomi:

1. Model hanya boleh menghasilkan kode di atas.
2. Penyebutan biaya yang ditanggung perusahaan (misalnya biaya relokasi dibayar perusahaan) bukan `PAYMENT_REQUEST`.
3. Satu indikator dapat memiliki lebih dari satu kutipan bukti. Kode yang sama dihitung satu kali dalam skoring.
4. Perubahan taksonomi memerlukan pembaruan PRD dan evaluasi ulang.

## 8.5 Aturan Skoring Kategori Risiko

| Kategori | Ketentuan |
| ----- | ----- |
| HIGH | Terdapat minimal satu indikator tervalidasi bertingkat HIGH. |
| MEDIUM | Tidak terdapat indikator HIGH, dan terdapat minimal satu indikator MEDIUM atau minimal dua indikator LOW yang berbeda. |
| LOW | Selain kondisi di atas, termasuk tanpa indikator. |

Ketentuan skoring:

1. Skoring hanya menggunakan indikator yang lolos validasi kutipan bukti.
2. Ambang skoring hanya boleh disesuaikan berdasarkan dev set. Setiap perubahan dicatat pada protokol evaluasi beserta alasannya.
3. Satu indikator MEDIUM (misalnya kontak tidak resmi) menghasilkan MEDIUM, bukan HIGH, sehingga kontak nonkorporat tidak otomatis dianggap penipuan.

## 8.6 Klasifikasi Data dan Kepemilikan Informasi

| Kategori Data | Lokasi | Pemilik / Otoritas | Pengelolaan |
| ----- | ----- | ----- | ----- |
| Akun pengguna (nama, email, hash password, role) | Basis data off-chain | Lettrust | Akses oleh pemilik akun; identitas dasar HR terlihat oleh Administrator. |
| Data penerbit | Basis data off-chain | Penerbit; dikelola Lettrust | HR terafiliasi dan Administrator. |
| Keputusan verifikasi dan otorisasi | Basis data off-chain | Administrator | Dicatat dengan aktor dan waktu. |
| Bukti on-chain | Registry blockchain | Penerbit; ditulis signer Lettrust | Minimal, tanpa data pribadi, tidak dapat ditimpa. |
| Pemetaan kode dan metadata bukti | Basis data off-chain | Penerbit; dikelola Lettrust | HR penerbit; pembacaan internal untuk verifikasi. |
| Berkas yang diunggah | Memori/penyimpanan sementara | Pengunggah | Tidak disimpan permanen. |
| Teks hasil ekstraksi | Memori; dikirim ke penyedia model | Pengunggah | Tidak disimpan; tidak dicatat di log. |
| Log verifikasi (P1) | Basis data off-chain | Lettrust | Enum hasil dan metadata teknis saja. |
| Dataset evaluasi | Repository | Kelompok 04 | Data sintetis; tidak memuat data nyata. |
| Secret (kunci signer, kunci API model, token, secret JWT) | Environment lokal | Pengelola teknis | Tidak di-commit; tidak dikirim ke frontend. |

## 8.7 Kebijakan Retensi Prototipe

| Jenis Data | Retensi pada Prototipe |
| ----- | ----- |
| Berkas yang diunggah HR | Tidak disimpan setelah hash dihitung. |
| Berkas yang diunggah pelamar | Tidak disimpan setelah permintaan selesai. |
| Teks hasil ekstraksi | Tidak disimpan setelah permintaan selesai. |
| Akun, penerbit, metadata bukti, log | Disimpan sampai environment direset. |
| Catatan registry | Disimpan pada state jaringan lokal sampai environment direset. |
| Output mentah evaluasi AI | Disimpan sebagai bukti evaluasi di repository (data sintetis). |

Prototipe tidak mengklaim penghapusan data pada penyedia model pihak ketiga. Ketentuan retensi penyedia mengikuti kebijakan penyedia tersebut, dan karena itu hanya data sintetis yang dikirim (BR-05.08).

## 8.8 Audit dan Keterlacakan

| Aktivitas | Informasi Minimum |
| ----- | ----- |
| Registrasi perusahaan | Akun pendaftar, waktu, `issuerId`. |
| Keputusan verifikasi | Administrator, keputusan, `evidenceRef`, waktu. |
| Otorisasi HR | Administrator, akun HR, penerbit, waktu. |
| Penerbitan bukti | HR, penerbit, `proofId`, hash transaksi, nomor blok, waktu. |
| Pencabutan bukti | HR, penerbit, `proofId`, `reasonCode`, hash transaksi, nomor blok, waktu. |
| Verifikasi (P1) | `verificationId`, partner, mode, enum hasil, durasi, waktu. |
| Kegagalan registry atau AI | `requestId`, kategori kegagalan, waktu. |

Catatan audit tidak memuat password, token, kunci, isi dokumen, atau teks dokumen.

## 8.9 Kebijakan Penggunaan Layanan AI Eksternal

| Aspek | Ketentuan |
| ----- | ----- |
| Layanan utama | Layanan inferensi model open-weight melalui free tier dengan API yang kompatibel OpenAI. Pilihan model final ditetapkan melalui pengujian pada dev set (OI-01). |
| Layanan cadangan | Layanan inferensi lain melalui konfigurasi, hanya dengan data sintetis. |
| Data | Hanya teks hasil ekstraksi dari dokumen sintetis. |
| Kredensial | Setiap anggota menggunakan kunci API dari akun miliknya sendiri. Kunci tidak dibagikan di kanal kelompok dan tidak di-commit. |
| Kuota | Penggunaan direncanakan agar evaluasi dan demo tidak melebihi kuota; kegagalan kuota dinyatakan `AI_QUOTA_EXCEEDED`. |
| Pergantian provider | Hanya melalui perubahan konfigurasi yang disengaja; tidak ada peralihan otomatis saat runtime. |
| Penggunaan nyata | Pemrosesan data nyata memerlukan evaluasi kebijakan data penyedia dan berada di luar cakupan D3. |

## 8.10 Pemetaan Business Rules Usulan Sebelumnya

Konteks master proyek sebelumnya memuat usulan BR-01–BR-16 yang bukan ID resmi D1/D2. Pemetaan ke ID PRD:

| ID Usulan | Aturan | ID PRD |
| ----- | ----- | ----- |
| BR-01 | Perusahaan tidak boleh memverifikasi dirinya sendiri | BR-01.07 |
| BR-02 | Penerbitan hanya oleh penerbit VERIFIED dan HR AUTHORIZED | BR-01.11 |
| BR-03 | SHA-256 atas byte berkas; tidak menggunakan teks OCR | BR-02.03 |
| BR-04 | ACTIVE hanya setelah transaksi terkonfirmasi | BR-02.08 |
| BR-05 | Pencabutan hanya oleh HR berhak; lintas penerbit dilarang | BR-01.11, BR-02.15 |
| BR-06 | REVOKED mempertahankan riwayat; tanpa reaktivasi | BR-02.13, BR-02.14 |
| BR-07 | Dokumen dan PII tidak on-chain; persetujuan AI | BR-02.06, BR-05.02, BR-05.04 |
| BR-08 | Kode saja tidak membuktikan kesamaan berkas | BR-03.08 |
| BR-09 | AI hanya jika diminta dan konten tersedia | BR-04.01, BR-04.09 |
| BR-10 | AI independen dari hasil bukti | BR-04.01 |
| BR-11 | Tidak ada satu vonis | BR-03.01 |
| BR-12 | Registry gagal = UNAVAILABLE | BR-03.06 |
| BR-13 | AI gagal tidak menghilangkan hasil blockchain | BR-03.12, BR-04.12 |
| BR-14 | Tanpa kode hanya AI; tanpa status bukti fiktif | BR-03.09 |
| BR-15 | Pelamar tanpa login; token partner tidak ke browser | BR-05.01, BR-01.14 |
| BR-16 | PDF scan memakai OCR; kegagalan OCR tidak mengubah hash | BR-04.02, BR-02.03 |

## 8.11 Ketentuan Validasi Data Governance

Sebelum pengumpulan D3, prototipe harus memenuhi:

1. Otorisasi penerbit, HR, partner, dan endpoint internal tervalidasi (SCN-14, SCN-19).
2. Registry tidak memuat data pribadi atau isi dokumen (inspeksi data on-chain).
3. Berkas dan teks tidak tersimpan setelah permintaan (inspeksi penyimpanan dan basis data).
4. Log tidak memuat konten sensitif atau secret (inspeksi log).
5. Repository dan bundle frontend tidak memuat secret.
6. Seluruh data yang digunakan bersifat sintetis.
