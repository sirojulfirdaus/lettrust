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

## SCN-05 — Pemeriksaan dengan kode saja

Expected output dan langkah acuan: PRD §12.4 (SCN-05). FR: FR-03.11, FR-05.01, FR-06.03.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |

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

## SCN-11 — Berkas tidak valid

Expected output dan langkah acuan: PRD §12.4 (SCN-11). FR: FR-06.06, FR-05.04.

| Test case ID | Referensi (SCN, FR/AC, MVP) | Tujuan | Prasyarat | Data uji | Langkah / input | Expected result | Actual result | Status | Bukti | Penguji dan waktu | Catatan defect |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |

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
