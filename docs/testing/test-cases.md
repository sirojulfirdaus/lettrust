# Test Cases Lettrust D3

Owner: Pash (PIC 4, koordinasi) · Status: COMPLETE · Ref: PRD §12.4, §12.5; SA §18

Kolom mengikuti PRD §12.5. Definisi kasus dapat ditulis sebelum pengujian; `Actual result` dan `Status` (Pass, Fail, Blocked, Not Run) diisi hanya setelah eksekusi nyata dengan bukti di `docs/testing/evidence/<TC-ID>/`. Mock tidak boleh menjadi bukti.

Pembagian pelaksana per SCN mengikuti PLAN.md §7.1. Masing-masing PIC mengisi bagian skenario yang ditugaskan kepadanya.

## SCN-01 — Verifikasi surat sah dan utuh

Expected output dan langkah acuan: PRD §12.4 (SCN-01). FR: FR-02, FR-03, FR-05, FR-06.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |

## SCN-02 — Deteksi perubahan isi dokumen

Expected output dan langkah acuan: PRD §12.4 (SCN-02). FR: FR-03.11.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| TC-002 | SCN-02; FR-03.11; MVP-02, MVP-03 | Memastikan perubahan byte pada surat terdeteksi terhadap bukti yang telah diterbitkan. | Stack nyata sehat; FX-01 telah diterbitkan dan ACTIVE; API-04/API-07 tersedia; partner token aktif. | Kode referensi dari FX-01; FX-02. | Jalankan `python scripts/scn/scn02_mismatch.py --fx02 fixtures/FX-02.pdf`, masukkan kode saat diminta, lalu periksa tampilan portal untuk panduan G-04. | HTTP 200; `proofCheck.lookup=FOUND`; `proofCheck.lifecycleStatus=ACTIVE`; `integrityCheck.result=MISMATCH`; portal menampilkan panduan G-04. |  |  | `docs/testing/evidence/TC-002/` |  |  |

## SCN-03 — Pemeriksaan surat yang dicabut

Expected output dan langkah acuan: PRD §12.4 (SCN-03). FR: FR-04.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |

## SCN-04 — Referensi tidak ditemukan

Expected output dan langkah acuan: PRD §12.4 (SCN-04). FR: FR-03.10, FR-05.01, FR-06.02.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| TC-004 | SCN-04; FR-03.10, FR-05.01, FR-06.02 | Kode tidak terdaftar menghasilkan NOT_FOUND tanpa label palsu, dan analisis AI tetap berjalan bila diminta. | Stack nyata sehat (Anvil + LLM nyata); partner token aktif. | Kode acak berformat valid yang tidak terdaftar; FX-03. | `python scripts/scn/scn04_not_found.py`: (a) kode saja, `includeRisk=false`; (b) kode yang sama + FX-03, `includeRisk=true`. | (a) HTTP 200; `lookup=NOT_FOUND`; issuer/lifecycle null; NOT_CHECKED (`PROOF_NOT_FOUND`); AI NOT_REQUESTED. (b) HTTP 200; NOT_FOUND; NOT_CHECKED (`PROOF_NOT_FOUND`); AI COMPLETED, kategori HIGH, `PAYMENT_REQUEST` dan `UNOFFICIAL_CONTACT` termasuk dalam indikator (tambahan dicatat sebagai info). |  |  | `docs/testing/evidence/TC-004/` |  |  |

## SCN-05 — Pemeriksaan dengan kode saja

Expected output dan langkah acuan: PRD §12.4 (SCN-05). FR: FR-03.11, FR-05.01, FR-06.03.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| TC-005 | SCN-05; FR-03.11, FR-05.01, FR-06.03 | Kode bukti ACTIVE tanpa berkas memberi status registry tanpa klaim integritas atau analisis AI. | Stack nyata sehat; HR seed berwenang; partner token aktif. | Bukti ACTIVE FX-01 milik penerbit seed (dipakai ulang atau diterbitkan skrip). | `python scripts/scn/scn05_code_only.py`: (a) kode saja, `includeRisk=false`; (b) kode saja, `includeRisk=true`. Panduan G-05 diperiksa manual di portal. | (a) HTTP 200; FOUND; ACTIVE; NOT_CHECKED (`NO_FILE`); AI NOT_REQUESTED; portal menampilkan G-05. (b) AI NOT_PERFORMED (`DOCUMENT_CONTENT_UNAVAILABLE`), `category=null`. |  |  | `docs/testing/evidence/TC-005/` |  |  |

## SCN-06 — Deteksi indikasi risiko tinggi

Expected output dan langkah acuan: PRD §12.4 (SCN-06). FR: FR-05.05–FR-05.07.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |

## SCN-07a — Gangguan layanan AI

Expected output dan langkah acuan: PRD §12.4 (SCN-07a). FR: FR-05.09, FR-06.04.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |

## SCN-07b — Gangguan registry

Expected output dan langkah acuan: PRD §12.4 (SCN-07b). FR: FR-06.02, FR-06.04.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |

## SCN-08 — Mode Tanpa Kode, PDF teks

Expected output dan langkah acuan: PRD §12.4 (SCN-08). FR: FR-02.04, FR-05.10, FR-06.03.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |

## SCN-09 — Mode Tanpa Kode, PDF scan

Expected output dan langkah acuan: PRD §12.4 (SCN-09). FR: FR-05.03.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |

## SCN-10 — Kombinasi input tidak valid

Expected output dan langkah acuan: PRD §12.4 (SCN-10). FR: FR-06.05.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| TC-010 | SCN-10; FR-06.05 | Kombinasi input tidak valid ditolak sebelum registry dan ai-service dipanggil. | Stack nyata sehat; partner token aktif; akses `docker compose logs ai-service`. | Tanpa input; FX-01; kode `LTR-12AB`; FX-07 untuk kontrol log. | `python scripts/scn/scn10_invalid_input.py`: (a) tanpa kode dan berkas; (b) FX-01, `includeRisk=false`; (c) kode salah format; kontrol: FX-07 Mode Tanpa Kode. | (a) 400 `INVALID_INPUT_COMBINATION`; (b) 400 `AI_ONLY_REQUIRES_INCLUDE_RISK`; (c) 400 `INVALID_REFERENCE_CODE_FORMAT`; requestId (a)–(c) tidak muncul di log ai-service, sedangkan kontrol muncul. Registry tidak teramati dari API (dicakup test unit backend). |  |  | `docs/testing/evidence/TC-010/` |  |  |

## SCN-11 — Berkas tidak valid

Expected output dan langkah acuan: PRD §12.4 (SCN-11). FR: FR-06.06, FR-05.04.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| TC-011 | SCN-11; FR-06.06, FR-05.04 | Berkas tidak valid ditolak dengan kode yang tepat; berkas rusak berheader PDF tetap diproses atas byte. | Stack nyata sehat; HR seed berwenang; partner token aktif. | FX-08, FX-09, berkas 0 byte, FX-10; bukti ACTIVE FX-01 milik penerbit seed. | `python scripts/scn/scn11_invalid_file.py`: (a)–(c) Mode Tanpa Kode `includeRisk=true`; (d) kode ACTIVE + FX-10, `includeRisk=true`. | (a) 415 `UNSUPPORTED_MEDIA_TYPE`; (b) 413 `FILE_TOO_LARGE`; (c) 400 `EMPTY_FILE`; (d) HTTP 200; FOUND/ACTIVE; `integrityCheck.result=MISMATCH`; AI NOT_PERFORMED. |  |  | `docs/testing/evidence/TC-011/` |  |  |

## SCN-12 — Konten tidak dapat dibaca

Expected output dan langkah acuan: PRD §12.4 (SCN-12). FR: FR-05.04.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |

## SCN-13 — Onboarding end-to-end

Expected output dan langkah acuan: PRD §12.4 (SCN-13). FR: FR-01.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |

## SCN-14 — Otorisasi negatif

Expected output dan langkah acuan: PRD §12.4 (SCN-14). FR: FR-01.05–FR-01.07, FR-04.03.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |

## SCN-15 — Idempotensi dan kegagalan registry saat penerbitan

Expected output dan langkah acuan: PRD §12.4 (SCN-15). FR: FR-03.04, FR-03.05.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |

## SCN-16 — Pencabutan tidak valid dan kegagalan

Expected output dan langkah acuan: PRD §12.4 (SCN-16). FR: FR-04.04, FR-04.05.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |

## SCN-17 — Gangguan ganda

Expected output dan langkah acuan: PRD §12.4 (SCN-17). FR: FR-06.04.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| TC-017 | SCN-17; FR-06.04 | Gangguan registry dan ai-service sekaligus tidak menggagalkan API-07; kedua komponen dilaporkan UNAVAILABLE. | Stack lokal khusus uji; HR seed berwenang; partner token aktif. | Bukti ACTIVE FX-01 milik penerbit seed; FX-01. | `python scripts/scn/scn17_double_outage.py --allow-service-interruption` (stop `chain` dan `ai-service` via `dev.py`, kirim kode + FX-01 `includeRisk=true`, lalu start kembali). | HTTP 200; `lookup=UNAVAILABLE` (`REGISTRY_UNAVAILABLE`); NOT_CHECKED (`REGISTRY_UNAVAILABLE`); AI UNAVAILABLE tanpa kategori; service kembali sehat. |  |  | `docs/testing/evidence/TC-017/` |  |  |

## SCN-18 — Ketahanan prompt injection

Expected output dan langkah acuan: PRD §12.4 (SCN-18). FR: FR-05.08.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |

## SCN-19 — Token partner tidak terekspos

Expected output dan langkah acuan: PRD §12.4 (SCN-19). FR: FR-02.07.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |

## SCN-20 — Persistensi setelah restart

Expected output dan langkah acuan: PRD §12.4 (SCN-20). FR: FR-03.03, NFR-04.05.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |

## SCN-21 — Reprodusibilitas setup

Expected output dan langkah acuan: PRD §12.4 (SCN-21). FR: NFR-05.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |

## SCN-22 — Eksekusi evaluasi AI

Expected output dan langkah acuan: PRD §12.4 (SCN-22). FR: FR-05.12.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |

## Latensi — NFR-03 (MET-16, MET-17)

Expected output dan langkah acuan: PRD §7.4 (NFR-03.01, NFR-03.02) dan §10.3.4 (MET-16, MET-17). Bukan skenario SCN; dicatat agar pengukuran memiliki ID bukti.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| TC-023 | NFR-03.01, NFR-03.02; MET-16, MET-17 | Mengukur median dan P95 API-07 per varian serta API-04/API-06 termasuk konfirmasi transaksi lokal. | Stack nyata sehat (Anvil + LLM nyata); HR seed berwenang; partner token aktif. | Kode bukti FX-01; FX-01 (kode + berkas); FX-03 (AI teks); FX-04 (AI scan); salinan FX-01 unik untuk penerbitan lalu dicabut. | `python scripts/scn/latency.py` (default 20 sampel tanpa AI, 5 per varian AI dengan jeda 5 detik, 5 pasangan API-04/API-06). Waktu klien `perf_counter`; P95 nearest rank; satu pemanasan tak dicatat untuk varian tanpa AI; sampel gagal dilaporkan terpisah. | P95 API-07 kode saja ≤ 2 detik; kode + berkas tanpa AI ≤ 3 detik; API-04 dan API-06 ≤ 5 detik; AI PDF teks dan scan diukur dan dilaporkan tanpa target. |  |  | `docs/testing/evidence/TC-023/` |  |  |
