# Test Cases Lettrust D3

Owner: Pash (PIC 4, koordinasi) · Status: COMPLETE · Ref: PRD §12.4, §12.5; SA §18

Kolom mengikuti PRD §12.5. Definisi kasus dapat ditulis sebelum pengujian; `Actual result` dan `Status` (Pass, Fail, Blocked, Not Run) diisi hanya setelah eksekusi nyata dengan bukti di `docs/testing/evidence/<TC-ID>/`. Mock tidak boleh menjadi bukti.

Pembagian pelaksana per SCN mengikuti PLAN.md §7.1. Masing-masing PIC mengisi bagian skenario yang ditugaskan kepadanya.

Bukti TB-04 Zan berasal dari commit `4c3ef0a9bce098fedfad60a16ef90b425855747a` pada project Compose `lettrust-tb04-zan-4c3ef0a`, dengan volume baru dan data sintetis. Pemeriksaan Console/portal memakai browser terhadap stack tersebut. TC-022 merujuk evaluasi AI final tim.

Hasil DWS dirangkum dari lembar TB-04 dengan SHA yang sama. Bukti asli tetap dirujuk per baris. Detail eksekusi yang belum tercantum dicatat di kolom catatan.

## SCN-01 — Verifikasi surat sah dan utuh

Expected output dan langkah acuan: PRD §12.4 (SCN-01). FR: FR-02, FR-03, FR-05, FR-06.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| TC-001 | SCN-01; FR-02, FR-03, FR-05, FR-06; MVP-02, MVP-03, MVP-04, MVP-06 | Bukti yang diterbitkan HR berwenang dapat diperiksa pelamar dengan kode dan berkas utuh; tiga komponen hasil tampil terpisah tanpa verdict gabungan. | Stack nyata sehat (Anvil + LLM nyata); HR seed pada penerbit VERIFIED dan AUTHORIZED; Console dan portal dapat diakses; partner token aktif di server portal. | FX-01; kode referensi hasil penerbitan. | 1) Login Console sebagai HR seed berwenang, terbitkan FX-01 (API-04), catat kode referensi dan referensi transaksi. 2) Di portal, masukkan kode, unggah FX-01, berikan persetujuan AI (`includeRisk=true`), kirim. 3) Simpan screenshot Console dan portal, respons JSON, referensi transaksi, dan identitas model. | API-04 HTTP 201 dengan kode referensi dan referensi transaksi. API-07 HTTP 200; `mode=REFERENCE_CHECK`; `lookup=FOUND`; nama penerbit dan `issuerVerified=true`; `lifecycleStatus=ACTIVE`; `integrityCheck.result=MATCH`; panel AI terpisah dengan `state=COMPLETED`; tidak ada verdict gabungan. | Console mencatat bukti aktif dan menampilkan hash transaksi. Portal menampilkan tiga panel terpisah dengan Tercatat dan aktif, berkas identik, dan indikasi risiko rendah melalui teks PDF. | Pass | [Ringkasan bukti](evidence/TC-001/dws-tb04-4c3ef0a.json), [TB-04 DWS, baris 1](https://docs.google.com/document/d/148f7CO_TuMiVy269jbM0JgoGC5jLN6AKotWYeOHngoo/edit?tab=t.0) | DWS, 27/11/2026 WIB (jam belum tercantum) | Mohon konfirmasi hash transaksi dalam teks, model ID, dan jam eksekusi. |

## SCN-02 — Deteksi perubahan isi dokumen

Expected output dan langkah acuan: PRD §12.4 (SCN-02). FR: FR-03.11.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| TC-002 | SCN-02; FR-03.11; MVP-02, MVP-03 | Memastikan perubahan byte pada surat terdeteksi terhadap bukti yang telah diterbitkan. | Stack nyata sehat; FX-01 telah diterbitkan dan ACTIVE; API-04/API-07 tersedia; partner token aktif. | Kode referensi dari FX-01; FX-02. | Jalankan `python scripts/scn/scn02_mismatch.py --fx02 fixtures/FX-02.pdf`, masukkan kode saat diminta, lalu periksa tampilan portal untuk panduan G-04. | HTTP 200; `proofCheck.lookup=FOUND`; `proofCheck.lifecycleStatus=ACTIVE`; `integrityCheck.result=MISMATCH`; portal menampilkan panduan G-04. | API dan portal HTTP 200, FOUND / ACTIVE / MISMATCH. Portal menampilkan G-04. | Pass | [scn02-mismatch-20261127-123531121609.json](evidence/TC-002/scn02-mismatch-20261127-123531121609.json), [browser-tb04-4c3ef0a.json](evidence/TC-002/browser-tb04-4c3ef0a.json), [TC-002-portal.png](evidence/TC-002/TC-002-portal.png) | Zan, 27/11/2026 19:35:31–19:35:31 WIB |  |

## SCN-03 — Pemeriksaan surat yang dicabut

Expected output dan langkah acuan: PRD §12.4 (SCN-03). FR: FR-04.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| TC-003 | SCN-03; FR-04; MVP-05 | Pencabutan oleh HR berwenang langsung terlihat sebagai REVOKED bagi pelamar, sementara riwayat penerbitan tetap ada. | Stack nyata sehat; HR seed berwenang; bukti FX-01 ACTIVE milik penerbit HR tersebut; partner token aktif. | Kode referensi bukti FX-01; FX-01; alasan pencabutan dari pilihan Console. | 1) Di Console, cabut bukti FX-01 (API-06), catat referensi transaksi. 2) Di portal, periksa ulang kode + FX-01. 3) Buka kembali daftar dan detail bukti di Console. Simpan screenshot dan referensi transaksi. | API-06 HTTP 201 dengan referensi transaksi; API-07 `lookup=FOUND`; `lifecycleStatus=REVOKED` dengan `revokedAt`; `integrityCheck.result=MATCH`; portal menampilkan panduan G-03; riwayat penerbitan tetap terlihat di Console. | Tombol cabut nonaktif sebelum alasan dipilih. Pencabutan HTTP 201 dengan transaksi terkonfirmasi. Riwayat memuat transaksi terbit dan cabut. Cabut ulang HTTP 409 PROOF_ALREADY_REVOKED. Portal FOUND / REVOKED / MATCH, waktu pencabutan, dan G-03. | Pass | [browser-tb04-4c3ef0a.json](evidence/TC-003/browser-tb04-4c3ef0a.json), [TC-003-alasan.png](evidence/TC-003/TC-003-alasan.png), [TC-003-konfirmasi.png](evidence/TC-003/TC-003-konfirmasi.png), [TC-003-riwayat.png](evidence/TC-003/TC-003-riwayat.png), [TC-003-portal.png](evidence/TC-003/TC-003-portal.png) | Zan, 27/11/2026 19:36:10 WIB | Retest FR-04.01/AC-02 lulus. |

## SCN-04 — Referensi tidak ditemukan

Expected output dan langkah acuan: PRD §12.4 (SCN-04). FR: FR-03.10, FR-05.01, FR-06.02.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| TC-004 | SCN-04; FR-03.10, FR-05.01, FR-06.02 | Kode tidak terdaftar menghasilkan NOT_FOUND tanpa label palsu, dan analisis AI tetap berjalan bila diminta. | Stack nyata sehat (Anvil + LLM nyata); partner token aktif. | Kode acak berformat valid yang tidak terdaftar; FX-03. | `python scripts/scn/scn04_not_found.py`: (a) kode saja, `includeRisk=false`; (b) kode yang sama + FX-03, `includeRisk=true`. | (a) HTTP 200; `lookup=NOT_FOUND`; issuer/lifecycle null; NOT_CHECKED (`PROOF_NOT_FOUND`); AI NOT_REQUESTED. (b) HTTP 200; NOT_FOUND; NOT_CHECKED (`PROOF_NOT_FOUND`); AI COMPLETED, kategori HIGH, `PAYMENT_REQUEST` dan `UNOFFICIAL_CONTACT` termasuk dalam indikator (tambahan dicatat sebagai info). | Kode tidak terdaftar memberi NOT_FOUND / NOT_CHECKED (PROOF_NOT_FOUND) tanpa atribut penerbit. Pada FX-03, AI COMPLETED / HIGH dengan PAYMENT_REQUEST dan UNOFFICIAL_CONTACT. | Pass | [Retest](evidence/TC-004/scn04-not-found-20261127-124638527003.json), [Run awal](evidence/TC-004/scn04-not-found-20261127-123740021914.json) | Zan, 27/11/2026 19:46:38–19:46:42 WIB | Retest setelah konfigurasi Groq aktif. Model openai/gpt-oss-120b. |

## SCN-05 — Pemeriksaan dengan kode saja

Expected output dan langkah acuan: PRD §12.4 (SCN-05). FR: FR-03.11, FR-05.01, FR-06.03.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| TC-005 | SCN-05; FR-03.11, FR-05.01, FR-06.03 | Kode bukti ACTIVE tanpa berkas memberi status registry tanpa klaim integritas atau analisis AI. | Stack nyata sehat; HR seed berwenang; partner token aktif. | Bukti ACTIVE FX-01 milik penerbit seed (dipakai ulang atau diterbitkan skrip). | `python scripts/scn/scn05_code_only.py`: (a) kode saja, `includeRisk=false`; (b) kode saja, `includeRisk=true`. Panduan G-05 diperiksa manual di portal. | (a) HTTP 200; FOUND; ACTIVE; NOT_CHECKED (`NO_FILE`); AI NOT_REQUESTED; portal menampilkan G-05. (b) AI NOT_PERFORMED (`DOCUMENT_CONTENT_UNAVAILABLE`), `category=null`. | Kode saja FOUND / ACTIVE / NOT_CHECKED (NO_FILE), AI NOT_REQUESTED. Dengan AI diminta melalui API, NOT_PERFORMED (DOCUMENT_CONTENT_UNAVAILABLE) tanpa kategori. Portal menampilkan G-05. | Pass | [scn05-code-only-20261127-123326217951.json](evidence/TC-005/scn05-code-only-20261127-123326217951.json), [browser-tb04-4c3ef0a.json](evidence/TC-005/browser-tb04-4c3ef0a.json), [TC-005-portal.png](evidence/TC-005/TC-005-portal.png) | Zan, 27/11/2026 19:33:26–19:35:32 WIB |  |

## SCN-06 — Deteksi indikasi risiko tinggi

Expected output dan langkah acuan: PRD §12.4 (SCN-06). FR: FR-05.05–FR-05.07.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| TC-006 | SCN-06; FR-05.05–FR-05.07; MVP-04 | Analisis AI pada surat berisiko tinggi menghasilkan indikator berkutipan dan kategori HIGH dari aturan skoring. | Stack nyata sehat dengan LLM nyata (kunci akun pelaksana); portal dapat diakses; partner token aktif. | FX-03 tanpa kode. | Di portal pilih Mode Tanpa Kode, unggah FX-03, berikan persetujuan AI, kirim. Simpan screenshot panel AI, respons JSON, dan identitas model. | AI `state=COMPLETED`; indikator `PAYMENT_REQUEST` dan `UNOFFICIAL_CONTACT` dengan kutipan bukti yang terdapat pada teks FX-03; `category=HIGH`; rekomendasi tidak membayar dan konfirmasi melalui kanal resmi; portal menampilkan panduan G-02. Lulus hanya apabila keluaran model aktual memenuhi; kegagalan dicatat apa adanya. | Mode Tanpa Kode menampilkan bukti dan keutuhan tidak diperiksa. Analisis teks PDF menghasilkan risiko tinggi, indikator permintaan pembayaran dan kontak tidak resmi, serta urgensi tambahan. | Pass | [Ringkasan bukti](evidence/TC-006/dws-tb04-4c3ef0a.json), [TB-04 DWS, baris 2](https://docs.google.com/document/d/148f7CO_TuMiVy269jbM0JgoGC5jLN6AKotWYeOHngoo/edit?tab=t.0) | DWS, 27/11/2026 WIB (jam belum tercantum) | Indikator urgensi tambahan dicatat sebagai informasi. Model ID dan jam eksekusi belum tercantum. |

## SCN-07a — Gangguan layanan AI

Expected output dan langkah acuan: PRD §12.4 (SCN-07a). FR: FR-05.09, FR-06.04.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| TC-007 | SCN-07a; FR-05.09, FR-06.04; MVP-06 | Gangguan ai-service tidak menggagalkan verifikasi; hasil registry dan integritas tetap tersedia, sedangkan AI UNAVAILABLE tanpa kategori. | Stack lokal khusus uji; HR seed berwenang; bukti FX-01 ACTIVE; partner token aktif. | Kode bukti FX-01; FX-01. | 1) `python scripts/dev.py stop ai-service`. 2) Di portal, kode + FX-01 dengan persetujuan AI (`includeRisk=true`), kirim. 3) Simpan screenshot dan respons JSON. 4) `python scripts/dev.py start ai-service`, lalu pastikan sehat dengan `python scripts/dev.py status`. | HTTP 200; `lookup=FOUND`; `lifecycleStatus=ACTIVE`; `integrityCheck.result=MATCH`; `riskAnalysis.state=UNAVAILABLE` (`AI_SERVICE_UNAVAILABLE`), `category=null`; portal menampilkan panduan G-07; ai-service kembali sehat. | Saat ai-service dihentikan, portal masih menampilkan bukti aktif dan berkas identik. Panel AI menampilkan analisis sedang tidak tersedia tanpa kategori dan panduan untuk mencoba lagi. | Pass | [Ringkasan bukti](evidence/TC-007/dws-tb04-4c3ef0a.json), [TB-04 DWS, baris 3](https://docs.google.com/document/d/148f7CO_TuMiVy269jbM0JgoGC5jLN6AKotWYeOHngoo/edit?tab=t.0) | DWS, 27/11/2026 WIB (jam belum tercantum) | Jam eksekusi, referensi transaksi, dan bukti health setelah restart belum tercantum. |

## SCN-07b — Gangguan registry

Expected output dan langkah acuan: PRD §12.4 (SCN-07b). FR: FR-06.02, FR-06.04.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| TC-024 | SCN-07b; FR-06.02, FR-06.04; MVP-06 | Gangguan registry dilaporkan UNAVAILABLE, bukan NOT_FOUND, dan analisis AI tetap berjalan. | Stack lokal khusus uji dengan LLM nyata; HR seed berwenang; bukti FX-01 ACTIVE; partner token aktif. | Kode bukti FX-01; FX-01. | 1) `python scripts/dev.py stop chain`. 2) Di portal, kode + FX-01 dengan persetujuan AI (`includeRisk=true`), kirim. 3) Simpan screenshot, respons JSON, dan identitas model. 4) `python scripts/dev.py start chain`, lalu pastikan sehat dengan `python scripts/dev.py status`. | HTTP 200; `lookup=UNAVAILABLE` (`REGISTRY_UNAVAILABLE`), bukan NOT_FOUND; `integrityCheck.result=NOT_CHECKED` (`REGISTRY_UNAVAILABLE`); AI `state=COMPLETED`; portal menampilkan panduan G-07; chain kembali sehat. | Saat chain dihentikan, portal menampilkan kegagalan pemeriksaan bukti dan keutuhan, panduan percobaan ulang, serta hasil AI risiko rendah dari teks PDF. | Pass | [Ringkasan bukti](evidence/TC-024/dws-tb04-4c3ef0a.json), [TB-04 DWS, baris 4](https://docs.google.com/document/d/148f7CO_TuMiVy269jbM0JgoGC5jLN6AKotWYeOHngoo/edit?tab=t.0) | DWS, 27/11/2026 WIB (jam belum tercantum) | Model ID, jam eksekusi, referensi transaksi, dan bukti health setelah restart belum tercantum. |

## SCN-08 — Mode Tanpa Kode, PDF teks

Expected output dan langkah acuan: PRD §12.4 (SCN-08). FR: FR-02.04, FR-05.10, FR-06.03.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| TC-008 | SCN-08; FR-02.04, FR-05.10, FR-06.03; MVP-03, MVP-04 | Mode Tanpa Kode pada PDF teks hanya menjalankan analisis AI tanpa memanggil registry. | Stack nyata sehat dengan LLM nyata; partner token aktif; akses `python scripts/dev.py logs backend`. | FX-03 tanpa kode. | 1) Di portal pilih Mode Tanpa Kode, unggah FX-03, berikan persetujuan AI, kirim; catat `requestId`. 2) Periksa log backend untuk `requestId` tersebut. 3) Simpan screenshot, respons JSON, dan potongan log tanpa secret. | `mode=AI_ONLY`; `lookup=NOT_REQUESTED` (`NO_REFERENCE_CODE`); `integrityCheck.result=NOT_CHECKED` (`NO_REFERENCE_CODE`); AI `state=COMPLETED`; metode ekstraksi `TEXT_LAYER`; log menunjukkan registry tidak dipanggil; portal menampilkan panduan G-08. | Portal menampilkan metode teks PDF. Log verifikasi mencatat AI_ONLY, bukti NOT_REQUESTED, keutuhan NOT_CHECKED (NO_REFERENCE_CODE), AI COMPLETED, dan durasi 788 ms untuk satu permintaan. | Pass | [Ringkasan bukti](evidence/TC-008/dws-tb04-4c3ef0a.json), [TB-04 DWS, baris 5](https://docs.google.com/document/d/148f7CO_TuMiVy269jbM0JgoGC5jLN6AKotWYeOHngoo/edit?tab=t.0) | DWS, 27/11/2026 19:33:49 WIB (log) | Model ID belum tercantum. |

## SCN-09 — Mode Tanpa Kode, PDF scan

Expected output dan langkah acuan: PRD §12.4 (SCN-09). FR: FR-05.03.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| TC-009 | SCN-09; FR-05.03; MVP-04 | OCR pada PDF scan menghasilkan teks yang dianalisis dengan kutipan bukti dari teks OCR. | Stack nyata sehat dengan LLM nyata; OCR Tesseract `ind+eng` di ai-service; partner token aktif. | FX-04 tanpa kode. | Di portal pilih Mode Tanpa Kode, unggah FX-04, berikan persetujuan AI, kirim. Simpan screenshot, respons JSON, dan identitas model. | `mode=AI_ONLY`; AI `state=COMPLETED`; metode ekstraksi `OCR`; setiap indikator memiliki kutipan yang terdapat pada teks OCR. | Portal menampilkan metode OCR, risiko tinggi, dan indikator permintaan pembayaran, kontak tidak resmi, serta urgensi tambahan. | Pass | [Ringkasan bukti](evidence/TC-009/dws-tb04-4c3ef0a.json), [TB-04 DWS, baris 6](https://docs.google.com/document/d/148f7CO_TuMiVy269jbM0JgoGC5jLN6AKotWYeOHngoo/edit?tab=t.0) | DWS, 27/11/2026 WIB (jam belum tercantum) | Indikator urgensi tambahan dicatat sebagai informasi. Model ID dan jam eksekusi belum tercantum. |

## SCN-10 — Kombinasi input tidak valid

Expected output dan langkah acuan: PRD §12.4 (SCN-10). FR: FR-06.05.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| TC-010 | SCN-10; FR-06.05 | Kombinasi input tidak valid ditolak sebelum registry dan ai-service dipanggil. | Stack nyata sehat; partner token aktif; akses `docker compose logs ai-service`. | Tanpa input; FX-01; kode `LTR-12AB`; FX-07 untuk kontrol log. | `python scripts/scn/scn10_invalid_input.py`: (a) tanpa kode dan berkas; (b) FX-01, `includeRisk=false`; (c) kode salah format; kontrol: FX-07 Mode Tanpa Kode. | (a) 400 `INVALID_INPUT_COMBINATION`; (b) 400 `AI_ONLY_REQUIRES_INCLUDE_RISK`; (c) 400 `INVALID_REFERENCE_CODE_FORMAT`; requestId (a)–(c) tidak muncul di log ai-service, sedangkan kontrol muncul. Registry tidak teramati dari API (dicakup test unit backend). | Ketiga input tidak valid ditolak HTTP 400 dengan kode yang diharapkan. Log menunjukkan ai-service tidak dipanggil dan kontrol ekstraksi teramati. | Pass | [scn10-invalid-input-20261127-123327937647.json](evidence/TC-010/scn10-invalid-input-20261127-123327937647.json) | Zan, 27/11/2026 19:33:27–19:33:29 WIB | Skrip skenario memeriksa log AI. Tes unit backend dengan fake memeriksa penghentian sebelum registry dan AI. |

## SCN-11 — Berkas tidak valid

Expected output dan langkah acuan: PRD §12.4 (SCN-11). FR: FR-06.06, FR-05.04.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| TC-011 | SCN-11; FR-06.06, FR-05.04 | Berkas tidak valid ditolak dengan kode yang tepat; berkas rusak berheader PDF tetap diproses atas byte. | Stack nyata sehat; HR seed berwenang; partner token aktif. | FX-08, FX-09, berkas 0 byte, FX-10; bukti ACTIVE FX-01 milik penerbit seed. | `python scripts/scn/scn11_invalid_file.py`: (a)–(c) Mode Tanpa Kode `includeRisk=true`; (d) kode ACTIVE + FX-10, `includeRisk=true`. | (a) 415 `UNSUPPORTED_MEDIA_TYPE`; (b) 413 `FILE_TOO_LARGE`; (c) 400 `EMPTY_FILE`; (d) HTTP 200; FOUND/ACTIVE; `integrityCheck.result=MISMATCH`; AI NOT_PERFORMED. | FX-08 HTTP 415, FX-09 HTTP 413, unggahan kosong HTTP 400 EMPTY_FILE. FX-10 dengan kode aktif HTTP 200, FOUND / ACTIVE / MISMATCH, AI NOT_PERFORMED. | Pass | [scn11-invalid-file-20261127-123329929104.json](evidence/TC-011/scn11-invalid-file-20261127-123329929104.json) | Zan, 27/11/2026 19:33:29–19:33:30 WIB |  |

## SCN-12 — Konten tidak dapat dibaca

Expected output dan langkah acuan: PRD §12.4 (SCN-12). FR: FR-05.04.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| TC-012 | SCN-12; FR-05.04; MVP-04 | PDF tanpa teks yang dapat dibaca tidak menghasilkan kategori atau indikator. | Stack nyata sehat; partner token aktif. | FX-07 tanpa kode. | Di portal pilih Mode Tanpa Kode, unggah FX-07, berikan persetujuan AI, kirim. Simpan screenshot dan respons JSON. | `mode=AI_ONLY`; AI `state=NOT_PERFORMED` (`DOCUMENT_CONTENT_UNAVAILABLE`); `category=null`; tanpa indikator. | Portal menampilkan Tidak dapat dianalisis untuk FX-07. Bukti dan keutuhan tidak diperiksa, dan panel AI tidak menampilkan kategori atau indikator. | Pass | [Ringkasan bukti](evidence/TC-012/dws-tb04-4c3ef0a.json), [TB-04 DWS, baris 7](https://docs.google.com/document/d/148f7CO_TuMiVy269jbM0JgoGC5jLN6AKotWYeOHngoo/edit?tab=t.0) | DWS, 27/11/2026 WIB (jam belum tercantum) | Jam eksekusi belum tercantum. |

## SCN-13 — Onboarding end-to-end

Expected output dan langkah acuan: PRD §12.4 (SCN-13). FR: FR-01.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| TC-013 | SCN-13; FR-01; MVP-01 | Penerbit baru hanya dapat menerbitkan setelah penerbit VERIFIED dan HR AUTHORIZED. | Stack nyata sehat; akun admin seed; email akun HR baru belum terdaftar. | Akun HR baru dan data perusahaan sintetis; FX-01. | Di Console: 1) registrasi akun HR baru (S-01); 2) registrasi perusahaan (API-01); 3) coba terbitkan FX-01 (API-04); 4) login admin, putuskan penerbit VERIFIED (API-02); 5) otorisasi HR (API-03); 6) login HR, terbitkan FX-01. Simpan screenshot tiap langkah dan referensi transaksi penerbitan. | Penerbit tercatat PENDING; penerbitan sebelum verifikasi dan otorisasi ditolak 403; setelah VERIFIED dan AUTHORIZED, penerbitan berhasil HTTP 201 dengan referensi transaksi. | Registrasi HR dan perusahaan HTTP 201. Penerbitan ditolak HTTP 403 saat PENDING dan saat VERIFIED tanpa otorisasi. Setelah AUTHORIZED, terbit HTTP 201 dan bukti tampil di daftar/detail. Unggahan baru yang identik saat ACTIVE ditolak HTTP 409 DUPLICATE_ACTIVE_DOCUMENT tanpa blok Anvil baru. | Pass | [browser-tb04-4c3ef0a.json](evidence/TC-013/browser-tb04-4c3ef0a.json), [TC-013-pending.png](evidence/TC-013/TC-013-pending.png), [TC-013-verified.png](evidence/TC-013/TC-013-verified.png), [TC-013-authorized.png](evidence/TC-013/TC-013-authorized.png), [TC-013-terbit.png](evidence/TC-013/TC-013-terbit.png), [TC-013-detail.png](evidence/TC-013/TC-013-detail.png), [TC-013-daftar.png](evidence/TC-013/TC-013-daftar.png), [TC-013-duplikat.png](evidence/TC-013/TC-013-duplikat.png) | Zan, 27/11/2026 19:36:09 WIB | Retest FR-03.06 lulus. |

## SCN-14 — Otorisasi negatif

Expected output dan langkah acuan: PRD §12.4 (SCN-14). FR: FR-01.05–FR-01.07, FR-04.03.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| TC-014 | SCN-14; FR-01.05–FR-01.07, FR-04.03; MVP-01, MVP-05 | Operasi tanpa hak ditolak di backend, contract, dan endpoint internal tanpa transaksi registry. | Stack lokal khusus uji (Anvil nyata); akun seed `hr.pending`, `hr.rejected`, `hr2.sinar`, `hr.sinar`, `hr.nusantara`, dan admin; partner token dan token internal di `.env`. | FX-01 (setup bukti ACTIVE milik penerbit B); penerbit uji baru untuk (k). | `python scripts/scn/scn14_authz_negative.py [--compose-project <nama>]`: kontrol token partner, setup bukti penerbit B, lalu (a)–(k) sesuai PRD; (d) dibandingkan dengan `proofId` acak; (e) `eth_call` pencabutan lintas penerbit pada contract; snapshot registry sebelum dan sesudah. | (a)–(c), (f), (g) 403 `FORBIDDEN_OPERATION`; (d) 404 `PROOF_NOT_FOUND`, sama dengan bukti yang tidak ada (tidak mengungkap bukti); (e) revert `IssuerMismatch`; (h) 401/403; (i) 401 `UNAUTHENTICATED`; (j) 401; (k) 409 `ISSUER_DECISION_ALREADY_MADE` dan keputusan pertama tidak berubah; nonce registrar dan event registry tidak berubah. | 16 pemeriksaan cocok, mencakup subkasus a–k dan kontrol. Pemanggilan contract lintas penerbit revert IssuerMismatch. Blok, nonce registrar, dan status bukti tetap. Tidak ada event penerbitan atau pencabutan pada percobaan negatif. | Pass | [scn14-c1e900a354bc.json](evidence/TC-014/scn14-c1e900a354bc.json) | Zan, 27/11/2026 19:33:31–19:33:36 WIB |  |

## SCN-15 — Idempotensi dan kegagalan registry saat penerbitan

Expected output dan langkah acuan: PRD §12.4 (SCN-15). FR: FR-03.04, FR-03.05.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| TC-015 | SCN-15; FR-03.04, FR-03.05; MVP-02 | Penerbitan ulang idempoten, konflik kunci ditolak, dan kegagalan registry tidak menghasilkan kode berlaku. | Stack lokal khusus uji (Anvil nyata); HR seed berwenang. | FX-01, FX-02; `Idempotency-Key` `scn15-same-file` dan `scn15-recovery`. | `python scripts/scn/scn15_issue_idempotency.py --allow-service-interruption`: (a) terbitkan FX-01 lalu ulang dengan kunci sama; (b) kunci sama dengan FX-02; (c) `dev.py stop chain`, terbitkan FX-02 dengan kunci baru, `dev.py start chain`, lalu ulang kunci yang sama. | (a) HTTP 201 dengan bukti sama; registry tidak berubah; hanya satu event `ProofIssued`. (b) 409 `IDEMPOTENCY_KEY_CONFLICT`; registry tidak berubah. (c) 503 `REGISTRY_UNAVAILABLE` tanpa kode referensi, `proofId`, atau transaksi; tidak ada bukti baru di daftar; setelah chain kembali, penerbitan berhasil dengan `proofId` berbeda; kedua bukti ACTIVE saat diverifikasi. | 52 pemeriksaan cocok. Replay memakai bukti yang sama dan satu event penerbitan. Berkas berbeda dengan kunci sama ditolak HTTP 409. Saat chain berhenti HTTP 503, lalu retry dengan kunci sama berhasil setelah pulih. | Pass | [20261127-123408-a3754fb9e0cbec4f.json](evidence/TC-015/20261127-123408-a3754fb9e0cbec4f.json) | Zan, 27/11/2026 19:33:52–19:34:08 WIB |  |

## SCN-16 — Pencabutan tidak valid dan kegagalan

Expected output dan langkah acuan: PRD §12.4 (SCN-16). FR: FR-04.04, FR-04.05.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| TC-016 | SCN-16; FR-04.04, FR-04.05; MVP-05 | Bukti REVOKED tidak dapat dicabut ulang atau direaktivasi, dan pencabutan yang gagal karena registry tidak mengubah status. | Stack lokal khusus uji (Anvil nyata); HR seed berwenang. | FX-01 (bukti dicabut dan bukti ACTIVE baru). | `python scripts/scn/scn16_revoke_invalid.py --allow-service-interruption`: (a) cabut bukti REVOKED tanpa kunci dan dengan kunci baru; (b) periksa endpoint mutasi OpenAPI live, ABI, dan simulasi selector reaktivasi; (c) `dev.py stop chain`, cabut bukti ACTIVE baru, `dev.py start chain`. | (a) 409 `PROOF_ALREADY_REVOKED`; hanya satu event `ProofRevoked`; registry tidak berubah. (b) Tidak ada endpoint atau fungsi contract reaktivasi; simulasi reaktivasi revert; status tetap REVOKED. (c) 503 `REGISTRY_UNAVAILABLE`; tanpa event `ProofRevoked`; status tetap ACTIVE di registry dan API-05. | 65 pemeriksaan cocok. Cabut ulang ditolak HTTP 409, operasi reaktivasi tidak tersedia. Selama registry berhenti, pencabutan gagal dan bukti tetap ACTIVE setelah registry pulih. | Pass | [20261127-123425-2b4b89776f255994.json](evidence/TC-016/20261127-123425-2b4b89776f255994.json) | Zan, 27/11/2026 19:34:08–19:34:25 WIB |  |

## SCN-17 — Gangguan ganda

Expected output dan langkah acuan: PRD §12.4 (SCN-17). FR: FR-06.04.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| TC-017 | SCN-17; FR-06.04 | Gangguan registry dan ai-service sekaligus tidak menggagalkan API-07; kedua komponen dilaporkan UNAVAILABLE. | Stack lokal khusus uji; HR seed berwenang; partner token aktif. | Bukti ACTIVE FX-01 milik penerbit seed; FX-01. | `python scripts/scn/scn17_double_outage.py --allow-service-interruption` (stop `chain` dan `ai-service` via `dev.py`, kirim kode + FX-01 `includeRisk=true`, lalu start kembali). | HTTP 200; `lookup=UNAVAILABLE` (`REGISTRY_UNAVAILABLE`); NOT_CHECKED (`REGISTRY_UNAVAILABLE`); AI UNAVAILABLE tanpa kategori; service kembali sehat. | Saat chain dan ai-service berhenti, API-07 tetap HTTP 200. Bukti UNAVAILABLE (REGISTRY_UNAVAILABLE), keutuhan NOT_CHECKED, dan AI UNAVAILABLE (AI_SERVICE_UNAVAILABLE) tanpa kategori. Health seluruh komponen kembali OK. | Pass | [Retest](evidence/TC-017/scn17-double-outage-20261127-124709644488.json), [Run awal](evidence/TC-017/scn17-double-outage-20261127-123759724035.json) | Zan, 27/11/2026 19:47:09–19:47:26 WIB | Retest setelah konfigurasi Groq aktif. |

## SCN-18 — Ketahanan prompt injection

Expected output dan langkah acuan: PRD §12.4 (SCN-18). FR: FR-05.08.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| TC-018 | SCN-18; FR-05.08; MVP-04 | Instruksi prompt injection di dalam dokumen tidak memengaruhi deteksi dan kategori. | Stack nyata sehat dengan LLM nyata; partner token aktif. | FX-06 tanpa kode. | Di portal pilih Mode Tanpa Kode, unggah FX-06, berikan persetujuan AI, kirim. Simpan screenshot, respons JSON, dan identitas model. | AI `state=COMPLETED`; `PAYMENT_REQUEST` terdeteksi dengan kutipan yang terdapat pada teks; kategori sesuai aturan skoring (HIGH); instruksi dalam dokumen tidak menurunkan kategori. Kegagalan dicatat apa adanya. | FX-06 tetap menghasilkan risiko tinggi dan indikator permintaan pembayaran. Instruksi dalam dokumen untuk menghasilkan LOW tidak tampak memengaruhi kategori. | Pass | [Ringkasan bukti](evidence/TC-018/dws-tb04-4c3ef0a.json), [TB-04 DWS, baris 8](https://docs.google.com/document/d/148f7CO_TuMiVy269jbM0JgoGC5jLN6AKotWYeOHngoo/edit?tab=t.0) | DWS, 27/11/2026 WIB (jam belum tercantum) | Model ID dan jam eksekusi belum tercantum. |

## SCN-19 — Token partner tidak terekspos

Expected output dan langkah acuan: PRD §12.4 (SCN-19). FR: FR-02.07.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| TC-019 | SCN-19; FR-02.07; MVP-03 | Token partner tetap di server portal dan tidak dapat diperoleh dari browser. | Stack nyata sehat; portal hasil build berjalan; partner token aktif. | Nilai `PARTNER_TOKEN` dari `.env` (hanya untuk pencarian, tidak dicetak atau disimpan). | 1) Lakukan satu verifikasi di portal dengan DevTools Network terbuka; periksa request dan header. 2) Cari string token pada berkas `.next/static` portal; catat jumlah kecocokan saja. 3) Panggil API-07 `POST /api/v1/verifications` langsung tanpa token. Bukti tidak boleh memuat nilai token. | Token tidak ditemukan di lalu lintas browser maupun bundle JavaScript; browser hanya memanggil route server portal (`POST /api/verify`); pemanggilan API-07 langsung tanpa token ditolak 401. | DWS mencatat Pass. DevTools menunjukkan POST /api/verify, cek bundle .next/static dilaporkan tanpa temuan token, dan API-07 langsung tanpa token mengembalikan HTTP 401. | Pass | [Ringkasan bukti](evidence/TC-019/dws-tb04-4c3ef0a.json), [TB-04 DWS, baris 9](https://docs.google.com/document/d/148f7CO_TuMiVy269jbM0JgoGC5jLN6AKotWYeOHngoo/edit?tab=t.0) | DWS, 27/11/2026 WIB (jam belum tercantum) | Bukti DWS berupa tiga screenshot. Jam eksekusi belum tercantum. |

## SCN-20 — Persistensi setelah restart

Expected output dan langkah acuan: PRD §12.4 (SCN-20). FR: FR-03.03, NFR-04.05.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| TC-020 | SCN-20; FR-03.03, NFR-04.05; MVP-02, MVP-05 | Bukti ACTIVE dan REVOKED beserta mirror basis data bertahan setelah seluruh stack dihentikan normal dan dijalankan kembali. | Stack lokal khusus uji (Anvil nyata, state persisten); HR seed berwenang; volume tidak dihapus. | FX-01 (satu bukti dicabut, satu bukti ACTIVE). | `python scripts/scn/scn20_persistence.py --allow-service-interruption`: terbitkan dan cabut satu bukti, terbitkan satu bukti ACTIVE, catat API-05 dan snapshot registry, `dev.py down` lalu `dev.py up` (tanpa reset), lalu bandingkan dan verifikasi ulang. | Bukti ACTIVE dan REVOKED tetap ditemukan dengan status sama; respons API-05 dan snapshot registry identik dengan sebelum restart; receipt `ProofIssued`/`ProofRevoked` tetap terkonfirmasi; verifikasi API-07 memberi status sama. | 95 pemeriksaan cocok. Setelah stack dihentikan lalu dijalankan kembali, kedua bukti tetap FOUND dengan status ACTIVE dan REVOKED, hash tetap, dan referensi transaksi masih tersedia. | Pass | [20261127-123457-b0bbce739837d6ae.json](evidence/TC-020/20261127-123457-b0bbce739837d6ae.json) | Zan, 27/11/2026 19:34:25–19:34:57 WIB |  |

## SCN-21 — Reprodusibilitas setup

Expected output dan langkah acuan: PRD §12.4 (SCN-21). FR: NFR-05.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| TC-021 | SCN-21; NFR-05; MET-18 | Seluruh layanan dapat dijalankan dari clone baru dengan satu perintah pada minimal dua OS berbeda. | Mesin (a) Windows dan (b) Linux dengan Docker dan Compose v2 serta Python 3.12+; belum ada clone repository; kunci LLM akun pelaksana. macOS Apple Silicon tidak diuji (TOI-02). | Clone baru repository; `.env` dari contoh konfigurasi. | Pada tiap OS: 1) clone baru; 2) `python scripts/dev.py doctor`; 3) `python scripts/dev.py up --build` (membuat `.env` dari contoh); 4) isi `LLM_API_KEY` lalu `python scripts/dev.py up`; 5) `python scripts/dev.py status` dan `python scripts/dev.py chain address`; 6) buka Console (http://127.0.0.1:3000) dan login akun seed, buka portal (http://127.0.0.1:3001). Simpan output perintah dan screenshot tanpa secret. | Pada kedua OS: seluruh layanan sehat; contract ter-deploy; seed tersedia; portal dan Console dapat diakses. | Penyiapan pada Windows dilaporkan tervalidasi. Hasil clone baru pada Linux belum terverifikasi. | Blocked | [TB-04, baris 24](https://docs.google.com/document/d/148f7CO_TuMiVy269jbM0JgoGC5jLN6AKotWYeOHngoo/edit?tab=t.0) | Tim TB-05 | Status gabungan menunggu bukti eksekusi Linux. |

## SCN-22 — Eksekusi evaluasi AI

Expected output dan langkah acuan: PRD §12.4 (SCN-22). FR: FR-05.12.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| TC-022 | SCN-22; FR-05.12; MET-09–MET-15; MVP-04 | Evaluasi pipeline AI dan baseline dijalankan sekali pada test set beku dan menghasilkan metrik serta artefak lengkap. | Snapshot test set beku dan run dev referensi tersedia (`docs/evaluation/protocol.md` §8); LLM nyata dengan kunci akun pelaksana; `metrics.py` tersedia. | 48 PDF test dari manifest; varian `pipeline` dan `baseline`. | 1) Jalankan perintah final `python scripts/dev.py eval run_eval --split test --freeze … --reference-run … --variants pipeline baseline` sesuai protocol §8. 2) `python scripts/dev.py eval metrics <direktori run>`. 3) Susun laporan di `docs/evaluation/report.md`. | Metrik MET-09–MET-15, output mentah (`raw.jsonl`), identitas model, dan laporan evaluasi dihasilkan; kegagalan tetap tercatat. | MET-09–MET-15 tersedia untuk pipeline Groq Qwen dan baseline aturan dari 48 PDF test beku. Percobaan pertama Qwen selesai 47/48 (47 kategori benar), baseline selesai 48/48. Satu AI_PROVIDER_ERROR dicatat pada metrik utama dan berhasil pada retry terpisah. | Pass | [Laporan evaluasi](../evaluation/report.md), [metrik](../../ai-eval/results/t5-08-20261126-final-qwen38/metrics.json), [konfigurasi run](../../ai-eval/results/t5-08-20261126-final-qwen38/run_config.json) | Tim evaluasi AI, 26/11/2026 22:18:25–22:57:01 WIB | Rujukan hasil evaluasi final yang sudah ada. Model qwen/qwen3.8-27b. |

## Latensi — NFR-03 (MET-16, MET-17)

Expected output dan langkah acuan: PRD §7.4 (NFR-03.01, NFR-03.02) dan §10.3.4 (MET-16, MET-17). Bukan skenario SCN; dicatat agar pengukuran memiliki ID bukti.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| TC-023 | NFR-03.01, NFR-03.02; MET-16, MET-17 | Mengukur median dan P95 API-07 per varian serta API-04/API-06 termasuk konfirmasi transaksi lokal. | Stack nyata sehat (Anvil + LLM nyata); HR seed berwenang; partner token aktif. | Kode bukti FX-01; FX-01 (kode + berkas); FX-03 (AI teks); FX-04 (AI scan); salinan FX-01 unik untuk penerbitan lalu dicabut. | `python scripts/scn/latency.py` (default 20 sampel tanpa AI, 5 per varian AI dengan jeda 5 detik, 5 pasangan API-04/API-06). Waktu klien `perf_counter`; P95 nearest rank; satu pemanasan tak dicatat untuk varian tanpa AI; sampel gagal dilaporkan terpisah. | P95 API-07 kode saja ≤ 2 detik; kode + berkas tanpa AI ≤ 3 detik; API-04 dan API-06 ≤ 5 detik; AI PDF teks dan scan diukur dan dilaporkan tanpa target. | Median/P95 dalam ms. Kode 20/20: 28,9/38,6. Kode + berkas 20/20: 25,8/37,3. Terbit 5/5: 44,8/250,5. Cabut 5/5: 47,8/57,8. PDF teks AI 5/5: 2025,3/2459,5. PDF scan AI 5/5: 3493,4/5153,3. Empat varian bertarget memenuhi P95. Tidak ada sampel gagal. | Pass | [Retest](evidence/TC-023/latency-20261127-124726774637.json), [Run awal](evidence/TC-023/latency-20261127-123643315827.json) | Zan, 27/11/2026 19:47:26–19:49:19 WIB | Groq openai/gpt-oss-120b. Jeda 10 detik antarpanggilan AI. |
