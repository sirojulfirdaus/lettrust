# PLAN — Rencana Kerja Implementasi Lettrust (D3)

Versi 1.0 · 21 November 2026 · Disusun oleh Dws (PIC 1, koordinator dan Technical Lead)

Acuan: `docs/prd/` (PRD v1.2), `docs/SYSTEM_ARCHITECTURE.md` (SA v1.2), `docs/SCAFFOLD_REPORT.md`, `docs/MOCKS.md`, dan `AGENTS.md`. Detail teknis tidak disalin ke dokumen ini; setiap tugas merujuk ke bagian PRD atau SA yang relevan.

Tracker status: [Tracker Tubes D3](https://docs.google.com/spreadsheets/d/1KiFtGlmIF04NtcN9b-AXfuUEezCH6Oypl4mzjLPao8c). PLAN.md tidak mencatat status; status hanya ada di tracker.

## 1. Cara Memakai Dokumen Ini

### 1.1 ID tugas

| Format | Arti | Contoh |
| ----- | ----- | ----- |
| `TB-xx` | Tugas bersama | `TB-03` integrasi end-to-end |
| `T<PIC>-xx` | Tugas individu, dikerjakan berurutan per orang | `T3-02` = tugas kedua Zan (PIC 3) |

| PIC | Nama | Area |
| ----- | ----- | ----- |
| 1 | Dws | Koordinator, core, verifikasi (API-07), partner |
| 2 | Van | Lettrust Console |
| 3 | Zan | Akun, penerbit, penerbitan dan pembacaan bukti |
| 4 | Pash | Portal Karier Mitra, koordinasi pengujian |
| 5 | B | ai-service, dataset, evaluasi |
| 6 | Sat | Contract, registry adapter, pencabutan, baseline |

Tugas individu berjalan **paralel antar-orang** dan **berurutan di dalam daftar masing-masing**. Kerjakan tugasmu sesuai urutan nomor.

### 1.2 Menyuruh agent

Cukup katakan `kerjakan T3-02`. Agent mengikuti AGENTS.md §5 "Executing a PLAN task": membaca blok tugas di §6, hanya mengubah file yang tercantum, memakai mock bila dependensi belum merge, menjalankan verifikasi, lalu melapor per kriteria. Setelah tugas di-merge, katakan `kerjakan T3-03`.

### 1.3 Membaca blok tugas

| Field | Arti |
| ----- | ----- |
| File | Path lengkap. Bila beberapa file berada di folder yang sama, folder ditulis sekali lalu nama-nama filenya. `(baru)` = file belum ada. Test dan helper kecil di folder yang sama boleh ditambah asal disebut di PR. |
| Ref | Bagian PRD (FR, BR, SCN) dan SA yang wajib dibaca. |
| Tergantung | Tugas lain yang dipakai. Bila belum merge, pakai mock/fake di kolom "Selama menunggu". |
| Selesai bila | Kriteria yang harus terpenuhi semuanya. |
| Verifikasi | Perintah yang wajib dijalankan dan hasil yang diharapkan. |
| Serah terima | Siapa yang perlu diberi tahu setelah merge. |

### 1.4 Definisi selesai

Sebuah tugas selesai bila:

| No | Syarat |
| ----- | ----- |
| 1 | Semua kriteria "Selesai bila" terpenuhi. |
| 2 | Perintah "Verifikasi" sudah dijalankan dan lulus; `python scripts/dev.py test <svc>` lulus untuk service yang terdampak. |
| 3 | Header file yang sudah lengkap diubah dari `Status: STUB` menjadi `Status: COMPLETE` dan baris `TODO` dihapus. |
| 4 | PR sudah di-merge ke `main` dengan 1 approval. |
| 5 | PIC mengumumkan "`<ID>` merged" di grup WA dan mengubah status di tracker menjadi Merged. |

## 2. Milestone dan Jadwal

Semua waktu dalam WIB. Jadwal ini sama dengan PRD §11.6 dan SA §20.1.

| Milestone | Tenggat | Kondisi selesai |
| ----- | ----- | ----- |
| M0 | Sab 21/11 | PRD, SA, AGENTS.md, MOCKS.md, dan PLAN.md di `main`. |
| M1 | Sab 21/11 | Scaffold, mock bersama, dan kontrak beku di `main` (sudah tercapai). Seluruh anggota menyelesaikan TB-01. |
| M2 | Sen 23/11 12.00 | Seluruh tugas bertanda M2 di `main`: setiap modul berjalan mandiri (boleh diuji dengan mock). Pukul 23.59 di hari yang sama: model LLM dipilih (OI-01) dan test set evaluasi dibekukan. |
| **M3 — soft deadline** | **Sel 24/11 23.59** | **Alur demo PRD §12.7.1 berjalan end-to-end di stack nyata dengan LLM nyata. Feature freeze: setelah ini hanya PR perbaikan defect, test, dan dokumen.** |
| M4 | Kam 26/11 23.59 | Seluruh SCN dieksekusi dengan bukti, evaluasi AI selesai, tidak ada defect Critical/High terbuka, laporan dan deck final, gladi demo dan rekaman cadangan selesai. |
| M5 | Jum 27/11 23.59 | Laporan PDF dan deck gabungan dikumpulkan. Target internal 21.00. |

### 2.1 Fase dan fokus harian

| Hari | Fase | Fokus |
| ----- | ----- | ----- |
| Sab 21/11 | Paralel | TB-01. Tugas pertama setiap orang dimulai: seed, contract, validasi berkas, format templat dataset. |
| Min 22/11 | Paralel | Auth, issuers, adapter registry, partner, ai_client, ekstraksi, provider LLM, BFF, library portal, client dan halaman awal Console, templat dataset. |
| Sen 23/11 | Paralel → integrasi parsial | 12.00 M2: penerbitan, pencabutan, orkestrator, API-08, halaman Console dan portal versi fixture. Sore: dataset, fixture, pembacaan bukti. 20.00 TB-02. 23.59 model dipilih dan test set beku. |
| Sel 24/11 | Integrasi | Console dan portal tersambung ke API nyata, integration test Anvil, baseline dan metrik, TB-03. 23.59 feature freeze. |
| Rab 25/11 | Stabilisasi | Eksekusi SCN (TB-04), run evaluasi final, perbaikan defect, penghapusan `NOT_IMPLEMENTED`. |
| Kam 26/11 | Stabilisasi | Retest defect, SCN-21 (TB-05), laporan dan deck final, gladi demo dan rekaman (TB-06). |
| Jum 27/11 | Pengumpulan | Cadangan penuh. TB-08. |

## 3. Aturan Kerja

### 3.1 Git dan PR

| No | Aturan |
| ----- | ----- |
| 1 | Semua operasi git dilakukan manusia. Agent hanya boleh `git status/diff/log` (AGENTS.md §4). |
| 2 | Branch dibuat dari `main` terbaru dengan nama di blok tugas (`feat/…`, `fix/…`, `test/…`, `docs/…`, `chore/…`). Satu PR untuk satu tugas. |
| 3 | Pesan commit diawali `feat:`, `fix:`, `docs:`, `test:`, atau `chore:`. Judul PR memuat ID tugas, misalnya `feat: issuers API (T3-03)`. |
| 4 | Sebelum membuka PR: `git fetch` lalu `git merge origin/main` di branch sendiri; jalankan verifikasi tugas; pastikan `python scripts/dev.py up --build` tetap sehat. |
| 5 | Setiap PR butuh 1 approval dan di-merge dengan **merge commit**. Reviewer menanggapi dalam 2 jam; bila tidak tersedia, Dws mengambil alih review. |
| 6 | `main` harus selalu bisa `up` dan semua test lulus. PR yang merusak `main` di-revert dulu, baru diperbaiki. |

### 3.2 Pasangan reviewer

| Penulis | Reviewer utama |
| ----- | ----- |
| Zan | Sat |
| Sat | Zan |
| Van | Pash |
| Pash | Van |
| B | Dws |
| Dws | Zan |

Perubahan berikut **wajib** juga direview Dws: `services/backend/app/core/`, `compose*.yaml`, `scripts/dev.py`, `.env.example`, `contracts/`, perubahan skema API, dan perubahan antarmuka contract (ABI).

### 3.3 Kontrak, skema, mock, dan dependency

| Hal | Aturan |
| ----- | ----- |
| Kontrak API | Beku. Perubahan skema Pydantic harus disetujui Dws lebih dulu di WA, disertai `python scripts/dev.py openapi` (meregenerasi `contracts/openapi.json`, `schema.d.ts`, dan fixture frontend), di-commit di PR yang sama, dan diumumkan ke Van dan Pash. |
| Contract atau ABI | Jalankan `python scripts/export_abi.py` dan commit ABI di PR yang sama. Setelah merge, semua anggota menjalankan `python scripts/dev.py reset --yes` lalu `python scripts/dev.py up --build`. |
| Model SQLAlchemy | Tidak ada migrasi. Setelah merge, semua anggota menjalankan `python scripts/dev.py reset --yes`. |
| Mock dan fake | Milik Dws (`docs/MOCKS.md`). Provider tidak mengedit mock; bila mock salah, laporkan ke Dws. Kode produksi selalu memanggil antarmuka nyata. |
| Pola akses antarmuka | Registry diakses melalui `get_registry_adapter()` yang dipanggil lewat atribut modul (`registry_adapter.get_registry_adapter()`), dan pembacaan bukti lewat `proofs_service.read_proof_for_verification(...)`. Jangan `from … import` fungsi tersebut, agar mock dapat diinjeksi (`docs/MOCKS.md`). |
| Dependency Python | `python scripts/dev.py lock <svc>` hanya bila `requirements*.txt` berubah, hanya oleh owner service (Dws untuk backend, B untuk ai-service). `constraints.txt` di-commit di PR yang sama. |
| Deviasi dari SA | Dicatat di `docs/SCAFFOLD_REPORT.md` §6 dengan persetujuan Dws. |

### 3.4 Koordinasi

| No | Aturan |
| ----- | ----- |
| 1 | Setiap hari pukul 21.00 setiap anggota mengirim laporan singkat di WA: selesai / berikutnya / blocker. |
| 2 | Blocker yang menghambat lebih dari 1 jam langsung dilaporkan, tidak menunggu 21.00, dan status tracker diubah menjadi Blocked. |
| 3 | Dependensi dianggap tersedia setelah PR di-merge dan diumumkan (SA §20.4). |
| 4 | Perubahan cakupan P0 hanya dengan persetujuan Dws (PRD Bab 1). |

### 3.5 Kunci LLM dan kuota

| No | Aturan |
| ----- | ----- |
| 1 | Setiap anggota memakai kunci Groq miliknya sendiri. Kunci tidak dibagikan dan tidak ditulis di WA, PR, atau bukti. |
| 2 | Run evaluasi final memakai kunci B. |
| 3 | Demo memakai kunci Dws yang belum dipakai pada hari demo (PRD §12.7.2). |
| 4 | B memantau kuota (OI-05). Bila kuota menipis sebelum evaluasi final, pemanggilan LLM untuk pengujian manual dihemat. |

## 4. Peta Dependensi

### 4.1 Siapa menunggu siapa

| Antarmuka | Penyedia | Pemakai | Selama menunggu | Tersedia (target) |
| ----- | ----- | ----- | ----- | ----- |
| Seed akun dan partner token | T3-01 | Semua | — | Sab 21/11 23.59 |
| Contract dan ABI final | T6-01 | T6-02 | Contract stub | Sab 21/11 23.59 |
| Validasi berkas (`core/files.py`) | T1-02 | T3-04, T1-05 | — | Min 22/11 12.00 |
| Dependency auth (`current_user`, `require_admin`, `require_hr`) | T3-02 | T3-03, T3-04, T6-03 | — | Min 22/11 12.00 |
| `Web3RegistryAdapter` | T6-02 | T3-04, T3-05, T6-03 | `MockRegistryAdapter` | Min 22/11 18.00 |
| Dependency issuers (`authorized_hr`) | T3-03 | T3-04, T6-03 | — | Min 22/11 23.59 |
| I-01 nyata | T5-02 | T1-04, T1-05 | `FakeAiService` | Min 22/11 18.00 |
| API-08 nyata | T5-04 | T1-05 | `FakeAiService` | Sen 23/11 12.00 |
| `read_proof_for_verification` (D-09) | T3-05 | T1-05 | `FakeProofReader` | Sen 23/11 18.00 |
| API S-01–S-07, API-01–API-06 nyata | T3-02–T3-05, T6-03 | T2-07 | Fixture `apps/issuer-console/src/fixtures/api/` | Sen 23/11 18.00 |
| API-07 nyata | T1-05 | T4-06 | Fixture `apps/partner-portal/src/fixtures/api/` | Sen 23/11 12.00 |
| Format templat dataset | T5-01 | T2-04, T4-03 | — | Sab 21/11 23.59 |
| Templat dataset ID dan EN | T2-04, T4-03 | T5-05 | — | Min 22/11 23.59 |
| Dataset, manifest, fixture FX | T5-05, T5-06 | T4-07, T6-05, TB-04 | — | Sen 23/11 15.00 |
| `scripts/scn/common.py` dan templat TC | T4-05 | T1-08, T3-06, T6-06, TB-04 | — | Sen 23/11 18.00 |

### 4.2 Jalur kritis

```
Zan  T3-01 seed ─► T3-02 auth ─► T3-03 issuers ─► T3-04 penerbitan ─► T3-05 baca + lookup ─┐
Sat  T6-01 contract ─► T6-02 adapter ─────────────┴─► T6-03 pencabutan ──────────────────────┤
Dws  T1-02 files ─► T1-03 partner ─► T1-04 ai_client + integrity ─► T1-05 orkestrator ───────┤
B    T5-02 ekstraksi ─► T5-03 provider ─► T5-04 API-08 ───────────────┘                       ├─► TB-03 E2E
Van  T2-01 … T2-06 (fixture) ─► T2-07 sambung API ────────────────────────────────────────────┤
Pash T4-01 lib ─► T4-02 BFF ─► T4-04 halaman (fixture) ─► T4-06 sambung API-07 ───────────────┘
B    T5-01 format ─► (T2-04, T4-03 templat) ─► T5-05 dataset ─► T5-07 model ─► T5-08 freeze + run
```

### 4.3 Titik integrasi per pasangan

Integrasi dilakukan begitu kedua sisi di-merge, tidak menunggu TB-03.

| Pasangan | Yang disambungkan | Paling lambat |
| ----- | ----- | ----- |
| Zan + Van | Login dan registrasi Console ke S-01–S-03 | Min 22/11 23.59 |
| Sat + Zan | Penerbitan ke Anvil nyata (`dev.py chain proof`) | Sen 23/11 15.00 |
| B + Dws | Orkestrator ke ai-service nyata (I-01, API-08) | Sen 23/11 18.00 |
| Dws + Pash | BFF portal ke API-07 nyata | Sen 23/11 20.00 (TB-02) |
| Zan + Sat + Van | Halaman bukti Console ke API-04/S-06/API-05/API-06 | Sel 24/11 18.00 |

## 5. Ringkasan Tugas

Urutan global (kolom No) dipakai di tracker. Urutan disusun menurut tenggat, lalu dependensi. Kolom M menunjukkan milestone.

| No | ID | Tugas | PIC | Tergantung | Tenggat | M |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| 1 | T1-01 | Mock, fake, contoh kontrak, conformance | Dws | — | Sab 21/11 (selesai) | M1 |
| 2 | TB-01 | Jalankan stack lokal, kunci Groq, lapor OS | Semua | — | Sab 21/11 20.00 | M1 |
| 3 | T5-01 | Format templat dataset | B | — | Sab 21/11 23.59 | M2 |
| 4 | T3-01 | Seed data | Zan | — | Sab 21/11 23.59 | M2 |
| 5 | T6-01 | Fungsi contract dan 10 test wajib | Sat | — | Sab 21/11 23.59 | M2 |
| 6 | T1-02 | Validasi berkas bersama | Dws | — | Min 22/11 12.00 | M2 |
| 7 | T2-01 | API client, sesi, dan guard Console | Van | — | Min 22/11 12.00 | M2 |
| 8 | T3-02 | Auth API dan dependency peran | Zan | T3-01 | Min 22/11 12.00 | M2 |
| 9 | T4-01 | Library tampilan portal | Pash | — | Min 22/11 12.00 | M2 |
| 10 | T1-03 | Autentikasi partner | Dws | T3-01 | Min 22/11 18.00 | M2 |
| 11 | T2-02 | Halaman login dan registrasi | Van | T2-01 | Min 22/11 18.00 | M2 |
| 12 | T5-02 | Ekstraksi PDF, OCR, dan I-01 | B | — | Min 22/11 18.00 | M2 |
| 13 | T6-02 | Codec dan `Web3RegistryAdapter` | Sat | T6-01 | Min 22/11 18.00 | M2 |
| 14 | T1-04 | `ai_client` dan pemeriksaan integritas | Dws | — | Min 22/11 23.59 | M2 |
| 15 | T2-03 | Onboarding perusahaan dan beranda HR | Van | T2-01 | Min 22/11 23.59 | M2 |
| 16 | T2-04 | Templat dataset bahasa Indonesia | Van | T5-01 | Min 22/11 23.59 | M2 |
| 17 | T3-03 | Issuers API | Zan | T3-02 | Min 22/11 23.59 | M2 |
| 18 | T4-02 | BFF `/api/verify` dan TOI-03 | Pash | — | Min 22/11 23.59 | M2 |
| 19 | T4-03 | Templat dataset bahasa Inggris | Pash | T5-01 | Min 22/11 23.59 | M2 |
| 20 | T5-03 | Provider LLM dan prompt | B | — | Min 22/11 23.59 | M2 |
| 21 | T1-05 | Orkestrator dan router API-07 | Dws | T1-02, T1-03, T1-04 | Sen 23/11 12.00 | M2 |
| 22 | T2-05 | Halaman bukti HR (fixture) | Van | T2-01 | Sen 23/11 12.00 | M2 |
| 23 | T2-06 | Halaman administrator penerbit (fixture) | Van | T2-01 | Sen 23/11 12.00 | M2 |
| 24 | T3-04 | Penerbitan bukti (API-04) | Zan | T1-02, T3-03 | Sen 23/11 12.00 | M2 |
| 25 | T4-04 | Halaman cek offer letter (fixture) | Pash | T4-01 | Sen 23/11 12.00 | M2 |
| 26 | T5-04 | Validator, skoring, komposisi, dan API-08 | B | T5-03 | Sen 23/11 12.00 | M2 |
| 27 | T6-03 | Pencabutan bukti (API-06) | Sat | T3-03, T6-02 | Sen 23/11 12.00 | M2 |
| 28 | T5-05 | Generator dataset dan dataset 72 PDF | B | T5-01, T2-04, T4-03 | Sen 23/11 15.00 | M3 |
| 29 | T5-06 | Fixture FX-01–FX-10 | B | T5-05 | Sen 23/11 15.00 | M3 |
| 30 | T3-05 | Daftar dan detail bukti, lookup verifikasi | Zan | T3-04 | Sen 23/11 18.00 | M3 |
| 31 | T4-05 | Templat test case, `common.py`, skrip SCN-02 | Pash | — | Sen 23/11 18.00 | M3 |
| 32 | TB-02 | Integrasi parsial | Semua | tugas M2 | Sen 23/11 20.00 | M3 |
| 33 | T5-07 | Pemilihan model (OI-01) | B | T5-04, T5-05 | Sen 23/11 21.00 | M3 |
| 34 | T5-08 | Bekukan test set dan run evaluasi final | B | T5-07, T4-07, T6-05 | Sen 23/11 23.59 · run Rab 25/11 12.00 | M4 |
| 35 | T1-06 | Log verifikasi minimal (P1) | Dws | T1-05 | Sel 24/11 18.00 | M3 |
| 36 | T2-07 | Sambung Console ke API nyata | Van | T2-02, T2-03, T2-05, T2-06, T3-05, T6-03 | Sel 24/11 18.00 | M3 |
| 37 | T4-06 | Sambung portal ke API-07 nyata | Pash | T4-02, T4-04, T1-05 | Sel 24/11 18.00 | M3 |
| 38 | T4-07 | Skrip metrik evaluasi | Pash | T5-05 | Sel 24/11 18.00 | M3 |
| 39 | T6-04 | Integration test dengan Anvil nyata | Sat | T3-04, T6-03 | Sel 24/11 18.00 | M3 |
| 40 | T6-05 | Baseline berbasis aturan | Sat | T5-05 | Sel 24/11 18.00 | M3 |
| 41 | TB-03 | Integrasi end-to-end dan feature freeze | Semua | semua tugas M3 | Sel 24/11 23.59 | M3 |
| 42 | T1-07 | Hapus `NOT_IMPLEMENTED` dari kontrak | Dws | TB-03 | Rab 25/11 12.00 | M4 |
| 43 | T1-08 | Skrip SCN-04, 05, 10, 11, 17, dan latensi | Dws | T4-05 | Rab 25/11 12.00 | M4 |
| 44 | T3-06 | Skrip SCN-14 | Zan | T4-05 | Rab 25/11 12.00 | M4 |
| 45 | T6-06 | Skrip SCN-15, 16, 20 | Sat | T4-05 | Rab 25/11 12.00 | M4 |
| 46 | TB-04 | Eksekusi SCN dan retest | Semua | TB-03, T4-05 | Rab 25/11 23.59 · retest Kam 26/11 18.00 | M4 |
| 47 | T5-09 | Laporan evaluasi | B | T5-08 | Rab 25/11 23.59 | M4 |
| 48 | TB-05 | SCN-21 reprodusibilitas Windows dan Linux | 2 anggota (TB-01) | T1-07 | Kam 26/11 12.00 | M4 |
| 49 | TB-06 | Gladi demo dan rekaman cadangan | Dws, Pash | TB-04 | Kam 26/11 22.00 | M4 |
| 50 | TB-07 | Laporan dan deck D3 (pembagian menyusul) | Semua | — | Kam 26/11 23.59 | M4 |
| 51 | TB-08 | Pengumpulan | Dws | TB-06, TB-07 | Jum 27/11 21.00 | M5 |

## 6. Detail Tugas

### 6.1 Tugas Bersama

### TB-01 — Jalankan stack lokal, kunci Groq, lapor OS

| Atribut | Isi |
| ----- | ----- |
| PIC | Semua anggota |
| Tenggat | Sab 21/11 20.00 · M1 |
| Langkah | 1) `git switch main`, `git pull`.<br>2) `python scripts/dev.py doctor`, lalu `python scripts/dev.py up --build`.<br>3) Isi `LLM_API_KEY` di `.env` dengan kunci Groq milik sendiri, lalu `python scripts/dev.py up`.<br>4) Kirim "siap" di WA beserta OS yang dipakai. Dari laporan ini ditetapkan satu anggota Windows dan satu anggota Linux untuk TB-05. |
| Selesai bila | `python scripts/dev.py status` menunjukkan enam service sehat; `GET http://127.0.0.1:8000/api/v1/health` menunjukkan `aiService` bukan `unavailable`. |
| Verifikasi | `python scripts/dev.py status`; `python scripts/dev.py test` lulus. |

### TB-02 — Integrasi parsial

| Atribut | Isi |
| ----- | ----- |
| PIC | Semua anggota (sesi daring ±1 jam) |
| Tenggat | Sen 23/11 20.00 · M3 |
| Tergantung | Semua tugas bertanda M2 |
| Langkah | 1) Semua `git pull` dan `python scripts/dev.py up --build`.<br>2) Setiap PIC mendemokan modulnya di stack nyata: login akun seed, registrasi dan verifikasi penerbit, penerbitan via API lalu `python scripts/dev.py chain proof <proofId>`, ekstraksi dan analisis satu fixture, BFF ke API-07.<br>3) Setiap masalah integrasi dicatat di WA beserta PIC dan tenggat perbaikan. |
| Selesai bila | Tidak ada tugas M2 yang belum di `main`, dan daftar masalah integrasi beserta PIC-nya tercatat. |

### TB-03 — Integrasi end-to-end dan feature freeze

| Atribut | Isi |
| ----- | ----- |
| PIC | Semua anggota. Perbaikan di modul tertentu dikerjakan PIC modul tersebut. |
| Tenggat | Sel 24/11 23.59 · M3 |
| Tergantung | Semua tugas bertanda M3 |
| Ref | PRD §12.7.1; SA §20.4 |
| Selesai bila | 1) Alur demo PRD §12.7.1 langkah 1–7 berjalan di stack nyata dengan LLM nyata.<br>2) Koordinator mengumumkan feature freeze di WA.<br>3) Daftar defect terbuka beserta PIC dan severity (PRD §12.6) tercatat. |

### TB-04 — Eksekusi SCN dan retest

| Atribut | Isi |
| ----- | ----- |
| PIC | Sesuai pembagian §7.1 |
| Tenggat | Rab 25/11 23.59 · retest Kam 26/11 18.00 · M4 |
| Tergantung | TB-03, T4-05 |
| File | `docs/testing/test-cases.md` (hanya bagian SCN milik sendiri)<br>`docs/testing/evidence/<TC-ID>/` |
| Ref | PRD §12.4–§12.6; SA §18.3, §21.2 |
| Selesai bila | 1) Baris TC ditulis paling lambat Sel 24/11 23.59, lalu dieksekusi.<br>2) Setiap TC memuat field PRD §12.5 dengan actual result dan status hasil eksekusi nyata.<br>3) Bukti tersimpan tanpa secret.<br>4) Defect dilaporkan ke PIC modul dengan severity PRD §12.6, lalu diuji ulang setelah perbaikan di-merge. |

### TB-05 — SCN-21 reprodusibilitas Windows dan Linux

| Atribut | Isi |
| ----- | ----- |
| PIC | Satu anggota Windows dan satu anggota Linux (ditetapkan saat TB-01) |
| Tenggat | Kam 26/11 12.00 · M4 |
| Tergantung | T1-07 |
| Ref | PRD SCN-21, NFR-05, MET-18; SA TOI-02, TOI-10 |
| Langkah | 1) Clone baru dari `main` ke folder kosong.<br>2) `python scripts/dev.py up --build`.<br>3) Periksa: seluruh service sehat, contract ter-deploy, seed tersedia, Console dan portal dapat diakses.<br>4) Catat durasi (MET-18). Anggota Windows yang memakai `--dev` mencatat pengalaman bind mount (TOI-10). |
| Selesai bila | TC SCN-21 terisi untuk kedua OS. TOI-02 (Apple Silicon) dicatat tidak diuji. |

### TB-06 — Gladi demo dan rekaman cadangan

| Atribut | Isi |
| ----- | ----- |
| PIC | Dws (mesin demo), Pash (rekaman) |
| Tenggat | Kam 26/11 22.00 · M4 |
| Tergantung | TB-04 |
| Ref | PRD §12.7 |
| Selesai bila | 1) Alur PRD §12.7.1 berjalan penuh di mesin demo dalam ≤ 5 menit.<br>2) Rekaman video lengkap tersedia.<br>3) Kunci LLM untuk hari demo belum terpakai (PRD §12.7.2). |

### TB-07 — Laporan dan deck D3

| Atribut | Isi |
| ----- | ----- |
| PIC | Semua anggota |
| Tenggat | Kam 26/11 23.59 · M4 |
| Catatan | Pembagian bab dan slide ditetapkan pada revisi PLAN berikutnya (§8). |

### TB-08 — Pengumpulan

| Atribut | Isi |
| ----- | ----- |
| PIC | Dws |
| Tenggat | Jum 27/11 21.00 (batas resmi 23.59) · M5 |
| Tergantung | TB-06, TB-07 |
| Ref | PRD §12.8 |
| Selesai bila | Laporan PDF dan deck gabungan memenuhi PRD §12.8 dan sudah diunggah; bukti unggah dikirim ke WA. |

### 6.2 Dws (PIC 1) — Core, Verifikasi, Partner

| ID | Tugas | Tenggat |
| ----- | ----- | ----- |
| T1-01 | Mock, fake, contoh kontrak, conformance | Sab 21/11 (selesai) |
| T1-02 | Validasi berkas bersama | Min 22/11 12.00 |
| T1-03 | Autentikasi partner | Min 22/11 18.00 |
| T1-04 | `ai_client` dan pemeriksaan integritas | Min 22/11 23.59 |
| T1-05 | Orkestrator dan router API-07 | Sen 23/11 12.00 |
| T1-06 | Log verifikasi minimal (P1) | Sel 24/11 18.00 |
| T1-07 | Hapus `NOT_IMPLEMENTED` dari kontrak | Rab 25/11 12.00 |
| T1-08 | Skrip SCN-04, 05, 10, 11, 17, dan latensi | Rab 25/11 12.00 |

### T1-01 — Mock, fake, contoh kontrak, conformance

| Atribut | Isi |
| ----- | ----- |
| Status | Selesai dan merged (PR `chore/shared-mocks`). Rincian di `docs/MOCKS.md` dan `docs/SCAFFOLD_REPORT.md` §10. |

### T1-02 — Validasi berkas bersama

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | Dws · Zan |
| Branch | `feat/upload-validation` |
| Tenggat | Min 22/11 12.00 · M2 |
| Tujuan | Satu fungsi validasi berkas yang dipakai API-04 dan API-07 agar penolakan berkas konsisten. |
| File | `services/backend/app/core/files.py` (baru)<br>`services/backend/tests/test_files.py` (baru) |
| Ref | SA §5.2, §10.3; FR-03.01, FR-06.06; NFR-02.01 |
| Tergantung | — |
| Selesai bila | 1) Pemetaan kesalahan: lebih dari 1 berkas → `MULTIPLE_FILES` (400); berkas kosong → `EMPTY_FILE` (400); di atas batas → `FILE_TOO_LARGE` (413); tanpa tanda tangan `%PDF-` → `UNSUPPORTED_MEDIA_TYPE` (415).<br>2) Berkas dibaca di memori saja, dan SHA-256 dihitung dari byte asli.<br>3) Berkas FX-10 (header PDF valid tetapi rusak) lolos validasi, sesuai SCN-11(d). |
| Verifikasi | `python scripts/dev.py test backend` |
| Serah terima | Zan (T3-04) |

### T1-03 — Autentikasi partner

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | Dws · Zan |
| Branch | `feat/partner-auth` |
| Tenggat | Min 22/11 18.00 · M2 |
| Tujuan | Dependency `partner_client` untuk API-07. |
| File | `services/backend/app/modules/partners/dependencies.py`<br>`services/backend/tests/test_partners.py` (baru) |
| Ref | SA §8.2, §8.3; FR-02.07, FR-06.09 |
| Tergantung | T3-01 (partner tersimpan di seed). Selama menunggu: data partner dibuat langsung di test. |
| Selesai bila | 1) Token valid → objek partner; tanpa token atau token salah → 401 envelope.<br>2) Token dibandingkan dalam bentuk hash SHA-256 dengan constant-time compare.<br>3) Token tidak pernah tercatat di log. |
| Verifikasi | `python scripts/dev.py test backend` |

### T1-04 — `ai_client` dan pemeriksaan integritas

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | Dws · B |
| Branch | `feat/verification-ai-client` |
| Tenggat | Min 22/11 23.59 · M2 |
| Tujuan | Klien backend ke ai-service dan penentuan MATCH/MISMATCH. |
| File | `services/backend/app/modules/verifications/` → `ai_client.py`, `integrity.py`<br>`services/backend/tests/` → `test_ai_client.py`, `test_integrity.py` (baru) |
| Ref | SA §5.3.2, §5.3.3, §10.8, §17.1; FR-03.11, FR-05.01, FR-05.09; SCAFFOLD_REPORT §10 butir 5 |
| Tergantung | T5-02, T5-04 untuk ai-service nyata. Selama menunggu: `FakeAiService` (`services/backend/tests/fakes/ai_service.py`). |
| Selesai bila | 1) Model respons Pydantic untuk I-01 dan API-08 ditambahkan dan divalidasi terhadap `contracts/examples/internal/`.<br>2) `ai_client` memanggil I-01 lalu API-08 dengan `X-Internal-Token`, `X-Request-ID`, dan timeout dari config.<br>3) Error jaringan, timeout, dan 5xx dipetakan ke state AI §5.3.3 (`UNAVAILABLE`, `NOT_PERFORMED`).<br>4) `integrity` menghasilkan MATCH/MISMATCH/NOT_CHECKED beserta reason sesuai tabel §5.3.2. |
| Verifikasi | `python scripts/dev.py test backend` (test memakai seluruh mode `FakeAiService` yang relevan) |

### T1-05 — Orkestrator dan router API-07

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | Dws · Zan |
| Branch | `feat/verify-offer` |
| Tenggat | Sen 23/11 12.00 · M2 |
| Tujuan | API-07 lengkap untuk semua mode dan kondisi kegagalan. |
| File | `services/backend/app/modules/verifications/` → `orchestrator.py`, `router.py`<br>`services/backend/tests/test_verifications.py` (baru) |
| Ref | SA §5.2–§5.6, §10.7; FR-02.03, FR-02.04, FR-03.10, FR-05.10, FR-06.01–FR-06.05, FR-06.07 |
| Tergantung | T1-02, T1-03, T1-04. T3-05 (lookup) dan T5-04 (API-08) untuk komponen nyata. Selama menunggu: `FakeProofReader` dan `FakeAiService`. |
| Selesai bila | 1) Langkah §5.2: validasi kombinasi input dan berkas dihentikan sebelum registry/AI dipanggil.<br>2) Proof task dan AI task berjalan paralel; Mode Tanpa Kode tidak memanggil pembacaan bukti.<br>3) Pembacaan bukti lewat `proofs_service.read_proof_for_verification(...)` (atribut modul).<br>4) Respons sesuai keempat contoh API-07 di `contracts/examples/`.<br>5) Test mencakup SCN-04, 05, 07a, 07b, 08, 10, dan 17 dengan fake. |
| Verifikasi | `python scripts/dev.py test backend`; setelah T3-05 dan T5-04 merge: satu API-07 nyata via `curl` dengan `PARTNER_TOKEN` |
| Serah terima | Pash (T4-06), seluruh tim (TB-02) |

### T1-06 — Log verifikasi minimal (P1)

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | Dws · Zan |
| Branch | `feat/verification-log` |
| Tenggat | Sel 24/11 18.00 · M3 · masuk daftar potong (§9.2) |
| File | `services/backend/app/modules/verifications/` → `orchestrator.py`, `models.py` |
| Ref | SA §9.2 (`verification_logs`); FR-06.08 |
| Tergantung | T1-05 |
| Selesai bila | Setiap API-07 yang sukses mencatat kolom SA §9.2 (enum dan durasi saja), tanpa isi berkas, teks dokumen, kode referensi lengkap, atau token. |
| Verifikasi | `python scripts/dev.py test backend` |

### T1-07 — Hapus `NOT_IMPLEMENTED` dari kontrak

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | Dws · Van |
| Branch | `chore/remove-not-implemented` |
| Tenggat | Rab 25/11 12.00 · M4 |
| File | `services/backend/app/core/` → `errors.py`, `schemas.py`<br>`services/backend/tests/test_routes_exist.py`<br>`contracts/openapi.json`, `contracts/examples/index.json` (bila ada entri terkait)<br>`apps/issuer-console/src/lib/api/schema.d.ts`, `apps/partner-portal/src/lib/api/schema.d.ts` (generated)<br>`docs/SCAFFOLD_REPORT.md` (§7 butir 3 ditandai selesai) |
| Ref | SCAFFOLD_REPORT D-04 |
| Tergantung | TB-03 |
| Selesai bila | Tidak ada lagi stub 501; pencarian `NOT_IMPLEMENTED` di `services/*/app/` dan `apps/*/src/` kosong (kecuali file generated yang sudah diregenerasi); `python scripts/dev.py openapi` sudah dijalankan; seluruh test lulus. |
| Verifikasi | `python scripts/dev.py openapi`; `python scripts/dev.py test` |

### T1-08 — Skrip SCN-04, 05, 10, 11, 17, dan latensi

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | Dws · Pash |
| Branch | `test/scn-verification` |
| Tenggat | Rab 25/11 12.00 · M4 |
| File | `scripts/scn/` → `scn04_not_found.py`, `scn05_code_only.py`, `scn10_invalid_input.py`, `scn11_invalid_file.py`, `scn17_double_outage.py`, `latency.py` (baru) |
| Ref | SA §18.3, §21.2; PRD §12.4; MET-16, MET-17 |
| Tergantung | T4-05 (`common.py`), TB-03 |
| Selesai bila | Setiap skrip memakai `common.py`, menyimpan bukti ke `docs/testing/evidence/<TC-ID>/`, dan mencetak ringkasan expected vs actual tanpa menandai PASS otomatis. |
| Verifikasi | Jalankan setiap skrip di stack nyata dan periksa folder bukti |

### 6.3 Van (PIC 2) — Lettrust Console

Halaman dibangun dari fixture kontrak (`apps/issuer-console/src/fixtures/api/`), lalu disambungkan ke API nyata di T2-07. Semua teks UI mengikuti PRD Bab 9.

| ID | Tugas | Tenggat |
| ----- | ----- | ----- |
| T2-01 | API client, sesi, dan guard Console | Min 22/11 12.00 |
| T2-02 | Halaman login dan registrasi | Min 22/11 18.00 |
| T2-03 | Onboarding perusahaan dan beranda HR | Min 22/11 23.59 |
| T2-04 | Templat dataset bahasa Indonesia | Min 22/11 23.59 |
| T2-05 | Halaman bukti HR (fixture) | Sen 23/11 12.00 |
| T2-06 | Halaman administrator penerbit (fixture) | Sen 23/11 12.00 |
| T2-07 | Sambung Console ke API nyata | Sel 24/11 18.00 |

### T2-01 — API client, sesi, dan guard Console

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | Van · Pash |
| Branch | `feat/console-session` |
| Tenggat | Min 22/11 12.00 · M2 |
| File | `apps/issuer-console/src/lib/` → `api/client.ts`, `session.ts`, `routes.ts`, `session.test.ts` (baru)<br>`apps/issuer-console/src/app/page.tsx`<br>`apps/issuer-console/src/components/console-header.tsx` |
| Ref | SA §11.2.1, §11.2.2; FR-01.02; TOI-13 |
| Tergantung | — (memakai tipe `schema.d.ts` dan fixture) |
| Selesai bila | 1) Client bertipe dari `schema.d.ts` dan membaca error envelope.<br>2) Sesi disimpan di `sessionStorage` dengan kunci `lettrust.session`.<br>3) Respons 401 → sesi dihapus dan pengguna diarahkan ke `/login`.<br>4) Route `/` mengarahkan berdasarkan `GET /auth/me`.<br>5) Header menampilkan nav sesuai peran dan tombol keluar. |
| Verifikasi | `python scripts/dev.py test issuer-console`; `python scripts/dev.py up --build` sukses |

### T2-02 — Halaman login dan registrasi

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | Van · Pash |
| Branch | `feat/console-auth-pages` |
| Tenggat | Min 22/11 18.00 · M2 |
| File | `apps/issuer-console/src/app/` → `login/page.tsx`, `register/page.tsx` |
| Ref | FR-01.01, FR-01.02; PRD §9.8 |
| Tergantung | T2-01; T3-02 untuk API nyata (selama menunggu: fixture S-01/S-02) |
| Selesai bila | Validasi form, state loading dan error (pesan PRD §9.8) tampil; setelah T3-02 merge, login akun seed berhasil di stack nyata. |
| Verifikasi | `python scripts/dev.py test issuer-console`; cek manual `http://127.0.0.1:3000/login` |
| Serah terima | Zan (integrasi pasangan §4.3) |

### T2-03 — Onboarding perusahaan dan beranda HR

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | Van · Pash |
| Branch | `feat/console-onboarding` |
| Tenggat | Min 22/11 23.59 · M2 |
| File | `apps/issuer-console/src/app/` → `onboarding/company/page.tsx`, `hr/page.tsx` |
| Ref | FR-01.03, FR-01.04; SA §11.2.1 |
| Tergantung | T2-01; T3-03 untuk API nyata (selama menunggu: fixture API-01, S-03, S-05) |
| Selesai bila | HR tanpa membership dapat mendaftarkan perusahaan; beranda HR menampilkan kartu status penerbit dan otorisasi (PENDING/VERIFIED/REJECTED, AUTHORIZED/NOT_AUTHORIZED) beserta ringkasan bukti. |
| Verifikasi | `python scripts/dev.py test issuer-console`; cek manual di browser |

### T2-04 — Templat dataset bahasa Indonesia

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | Van · Pash |
| Branch | `feat/eval-templates-id` |
| Tenggat | Min 22/11 23.59 · M2 |
| File | `ai-eval/templates/` → `id-low.json`, `id-medium.json`, `id-high.json` (baru) |
| Ref | PRD §10.4.1, §10.4.2; taksonomi PRD §8.4; BR-04.06 |
| Tergantung | T5-01 (format) |
| Aturan | 1) Tiap file berisi 6 surat dengan format `ai-eval/templates/README.md`.<br>2) Templat ditulis anggota selain pengembang prompt (PRD §10.4.2 butir 3).<br>3) Bila memakai bantuan model bahasa, modelnya berbeda dari kandidat model evaluasi dan setiap surat ditinjau manual (butir 4).<br>4) Semua identitas fiktif.<br>5) Surat LOW memuat pola wajar yang mirip indikator, misalnya biaya ditanggung perusahaan. |
| Selesai bila | 18 surat dengan label kategori dan indikator referensi yang konsisten dengan aturan skoring BR-04.06, sudah ditinjau Pash. |
| Verifikasi | Validasi format sesuai README T5-01 (skrip atau pemeriksaan manual yang disebut di PR) |
| Serah terima | B (T5-05) |

### T2-05 — Halaman bukti HR (fixture)

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | Van · Pash |
| Branch | `feat/console-proofs` |
| Tenggat | Sen 23/11 12.00 · M2 |
| File | `apps/issuer-console/src/app/hr/proofs/` → `page.tsx`, `new/page.tsx`, `[proofId]/page.tsx`<br>`apps/issuer-console/src/components/proofs/` → `proof-upload-form.tsx`, `proof-result-card.tsx`, `proof-status-badge.tsx`, `revoke-dialog.tsx` (baru) |
| Ref | SA §11.2.3; FR-03.01, FR-03.07, FR-03.08, FR-04.01, FR-04.07 |
| Tergantung | T2-01 (fixture API-04, S-06, API-05, API-06) |
| Selesai bila | 1) `Idempotency-Key` dibuat per upaya; "Coba lagi" memakai kunci yang sama.<br>2) Dialog konfirmasi sebelum unggah final dan sebelum pencabutan.<br>3) Halaman hasil menampilkan field FR-03.07 (kode, hash, txHash, blok) dengan tombol salin.<br>4) Detail bukti menampilkan riwayat lifecycle.<br>5) Semua state (loading, kosong, error) dari fixture tampil. |
| Verifikasi | `python scripts/dev.py test issuer-console`; `python scripts/dev.py up --build` sukses |

### T2-06 — Halaman administrator penerbit (fixture)

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | Van · Pash |
| Branch | `feat/console-admin` |
| Tenggat | Sen 23/11 12.00 · M2 |
| File | `apps/issuer-console/src/app/admin/issuers/` → `page.tsx`, `[issuerId]/page.tsx`<br>`apps/issuer-console/src/components/issuers/` → `issuer-status-badge.tsx`, `verification-decision-dialog.tsx`, `hr-authorization-panel.tsx` (baru) |
| Ref | FR-01.05, FR-01.06; SA §11.2.1 |
| Tergantung | T2-01 (fixture S-04, S-05, API-02, API-03) |
| Selesai bila | Daftar penerbit dengan filter status; keputusan VERIFIED/REJECTED dengan dialog konfirmasi; keputusan kedua menampilkan pesan 409; panel otorisasi HR. |
| Verifikasi | `python scripts/dev.py test issuer-console`; `python scripts/dev.py up --build` sukses |

### T2-07 — Sambung Console ke API nyata

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | Van · Pash |
| Branch | `feat/console-live-api` |
| Tenggat | Sel 24/11 18.00 · M3 |
| File | File halaman dan komponen dari T2-02, T2-03, T2-05, T2-06 (hanya bagian pemanggilan data); `apps/issuer-console/src/lib/api/client.ts` |
| Ref | SA §11.2; PRD §12.7.1 langkah 1–3 |
| Tergantung | T2-02, T2-03, T2-05, T2-06, T3-02–T3-05, T6-03 |
| Selesai bila | Registrasi akun, registrasi perusahaan, verifikasi admin, otorisasi HR, penerbitan, daftar, detail, dan pencabutan berjalan di stack nyata tanpa fixture di jalur produksi. |
| Verifikasi | Alur manual di `http://127.0.0.1:3000` dengan akun seed; `python scripts/dev.py test issuer-console` |

### 6.4 Zan (PIC 3) — Akun, Penerbit, Penerbitan dan Pembacaan Bukti

| ID | Tugas | Tenggat |
| ----- | ----- | ----- |
| T3-01 | Seed data | Sab 21/11 23.59 |
| T3-02 | Auth API dan dependency peran | Min 22/11 12.00 |
| T3-03 | Issuers API | Min 22/11 23.59 |
| T3-04 | Penerbitan bukti (API-04) | Sen 23/11 12.00 |
| T3-05 | Daftar dan detail bukti, lookup verifikasi | Sen 23/11 18.00 |
| T3-06 | Skrip SCN-14 | Rab 25/11 12.00 |

### T3-01 — Seed data

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | Zan · Sat |
| Branch | `feat/seed` |
| Tenggat | Sab 21/11 23.59 · M2 |
| File | `services/backend/app/cli.py` (perintah `seed`, opsi `--if-empty`)<br>`services/backend/tests/test_seed.py` (baru) |
| Ref | SA §9.5; FR-01.08 |
| Tergantung | — |
| Selesai bila | 1) `python scripts/dev.py reset --yes` lalu `up` menghasilkan seluruh entitas SA §9.5.<br>2) Password dari `SEED_ADMIN_PASSWORD` dan `SEED_HR_PASSWORD`.<br>3) Partner tersimpan sebagai hash dari `PARTNER_TOKEN`.<br>4) `--if-empty` tidak menggandakan data.<br>5) Opsi `--with-sample-proofs` (P1) tidak dikerjakan sebelum freeze. |
| Verifikasi | `python scripts/dev.py test backend`; `python scripts/dev.py reset --yes` lalu `python scripts/dev.py up` dan periksa log seed |
| Serah terima | Semua anggota (akun seed siap) |

### T3-02 — Auth API dan dependency peran

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | Zan · Sat |
| Branch | `feat/auth-api` |
| Tenggat | Min 22/11 12.00 · M2 |
| File | `services/backend/app/modules/auth/` → `router.py`, `service.py`, `dependencies.py`<br>`services/backend/tests/test_auth.py` (baru) |
| Ref | SA §8.1–§8.3, §10.5 (S-01, S-02, S-03); FR-01.01, FR-01.02, FR-01.04 |
| Tergantung | T3-01 |
| Selesai bila | 1) Registrasi, login (JWT HS256 8 jam), dan `GET /auth/me` sesuai kontrak dan contoh.<br>2) `current_user`, `require_admin`, dan `require_hr` siap dipakai modul lain.<br>3) Token salah atau kedaluwarsa → 401; peran salah → 403. |
| Verifikasi | `python scripts/dev.py test backend`; login akun seed via `curl` ke `/api/v1/auth/login` |
| Serah terima | Van (T2-02), Sat (T6-03) |

### T3-03 — Issuers API

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | Zan · Sat |
| Branch | `feat/issuers-api` |
| Tenggat | Min 22/11 23.59 · M2 |
| File | `services/backend/app/modules/issuers/` → `router.py`, `service.py`, `dependencies.py`<br>`services/backend/tests/test_issuers.py` (baru) |
| Ref | SA §10.5 (API-01, S-04, S-05, API-02, API-03); FR-01.03–FR-01.07 |
| Tergantung | T3-02 |
| Selesai bila | 1) Registrasi perusahaan menghasilkan PENDING.<br>2) Keputusan verifikasi kedua kali → 409.<br>3) Otorisasi HR berfungsi.<br>4) `require_unaffiliated_hr` dan `authorized_hr` menolak HR penerbit PENDING/REJECTED, HR NOT_AUTHORIZED, dan administrator (SCN-14 a–c, f, g). |
| Verifikasi | `python scripts/dev.py test backend` |
| Serah terima | Van (T2-03, T2-06), Sat (T6-03) |

### T3-04 — Penerbitan bukti (API-04)

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | Zan · Sat |
| Branch | `feat/issue-proof` |
| Tenggat | Sen 23/11 12.00 · M2 |
| File | `services/backend/app/modules/proofs/` → `router.py` (handler API-04), `service.py`<br>`services/backend/tests/test_proofs_issue.py` (baru) |
| Ref | SA §6.5, §10.6 (API-04); FR-03.01–FR-03.05, FR-03.07 |
| Tergantung | T1-02, T3-03; T6-02 untuk registry nyata. Selama menunggu: `MockRegistryAdapter`. |
| Selesai bila | 1) Validasi berkas memakai `core/files.py`.<br>2) Alur PENDING → ACTIVE/FAILED sesuai §6.5; `referenceCode` hanya dikembalikan setelah ACTIVE.<br>3) Idempotensi: kunci sama dan berkas sama → hasil sama; kunci sama dan berkas berbeda → 409.<br>4) Registry tidak tersedia → 503 tanpa kode berlaku.<br>5) Registry dipanggil lewat `registry_adapter.get_registry_adapter()` (atribut modul).<br>6) Penolakan duplikat FR-03.06 (P1) hanya bila waktu cukup. |
| Verifikasi | `python scripts/dev.py test backend`; setelah T6-02 merge: terbitkan satu bukti di stack lalu `python scripts/dev.py chain proof <proofId>` |
| Serah terima | Sat (T6-03, T6-04), Van (T2-07) |

### T3-05 — Daftar dan detail bukti, lookup verifikasi

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | Zan · Dws |
| Branch | `feat/proof-read` |
| Tenggat | Sen 23/11 18.00 · M3 |
| File | `services/backend/app/modules/proofs/` → `router.py` (handler S-06 dan API-05), `service.py` (termasuk `read_proof_for_verification`)<br>`services/backend/tests/` → `test_proofs_read.py`, `test_proofs_lookup.py` (baru) |
| Ref | SA §5.3.1, §10.6 (S-06, API-05); FR-03.08–FR-03.10, FR-04.06, FR-04.07; SCAFFOLD_REPORT D-09 |
| Tergantung | T3-04; T6-02 untuk registry nyata (selama menunggu: `MockRegistryAdapter`) |
| Selesai bila | 1) Daftar hanya memuat bukti ACTIVE/REVOKED milik penerbit HR.<br>2) Detail membaca status dari registry dan menampilkan riwayat penerbitan dan pencabutan; bukti penerbit lain → 404.<br>3) `read_proof_for_verification(code)` mengembalikan `ProofVerificationRead` untuk semua baris tabel §5.3.1: tidak ada pemetaan atau PENDING/FAILED → NOT_FOUND; registry error → UNAVAILABLE; `issuerRef` tidak cocok → UNAVAILABLE; `documentHash` dari registry.<br>4) Nilai yang dikembalikan konsisten dengan `services/backend/tests/fakes/proofs.py`. |
| Verifikasi | `python scripts/dev.py test backend` |
| Serah terima | Dws (T1-05), Van (T2-07) |

### T3-06 — Skrip SCN-14

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | Zan · Sat |
| Branch | `test/scn14-authz` |
| Tenggat | Rab 25/11 12.00 · M4 |
| File | `scripts/scn/scn14_authz_negative.py` (baru) |
| Ref | PRD SCN-14; SA §18.3 |
| Tergantung | T4-05, TB-03 |
| Selesai bila | Subkasus (a)–(k) dijalankan dengan akun seed, termasuk (e) pencabutan lintas penerbit langsung ke contract melalui `cast` atau web3. Bukti tersimpan per TC. |
| Verifikasi | Jalankan skrip di stack nyata dan periksa folder bukti |

### 6.5 Pash (PIC 4) — Portal Karier Mitra, Koordinasi Pengujian

| ID | Tugas | Tenggat |
| ----- | ----- | ----- |
| T4-01 | Library tampilan portal | Min 22/11 12.00 |
| T4-02 | BFF `/api/verify` dan TOI-03 | Min 22/11 23.59 |
| T4-03 | Templat dataset bahasa Inggris | Min 22/11 23.59 |
| T4-04 | Halaman cek offer letter (fixture) | Sen 23/11 12.00 |
| T4-05 | Templat test case, `common.py`, skrip SCN-02 | Sen 23/11 18.00 |
| T4-06 | Sambung portal ke API-07 nyata | Sel 24/11 18.00 |
| T4-07 | Skrip metrik evaluasi | Sel 24/11 18.00 |

### T4-01 — Library tampilan portal

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | Pash · Van |
| Branch | `feat/portal-logic` |
| Tenggat | Min 22/11 12.00 · M2 |
| File | `apps/partner-portal/src/lib/verification/` → `labels.ts`, `guidance.ts`, `reference-code.ts`, `consent.ts`, `labels.test.ts`, `guidance.test.ts`, `reference-code.test.ts` (tiga file test baru) |
| Ref | PRD §9.6, §9.7 (G-01–G-10); SA §6.3.1, §11.3.3; FR-02.06, FR-02.10 |
| Tergantung | — (fixture `apps/partner-portal/src/fixtures/api/`) |
| Selesai bila | 1) Pemetaan enum → label persis PRD §9.6, tanpa vonis asli/palsu atau aman/penipuan.<br>2) Aturan panduan berupa fungsi murni.<br>3) Normalisasi kode (O→0, I/L→1, spasi, tanda hubung) sama dengan backend.<br>4) Test memakai fixture API-07. |
| Verifikasi | `python scripts/dev.py test partner-portal` |

### T4-02 — BFF `/api/verify` dan TOI-03

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | Pash · Van |
| Branch | `feat/portal-bff` |
| Tenggat | Min 22/11 23.59 · M2 |
| File | `apps/partner-portal/src/app/api/verify/` → `route.ts`, `route.test.ts` (baru)<br>`apps/partner-portal/src/lib/server/config.ts` |
| Ref | SA §11.3.2; FR-02.07; TOI-03 |
| Tergantung | — (backend masih 501 sampai T1-05) |
| Selesai bila | 1) Hanya `referenceCode`, `file`, dan `includeRisk` yang diteruskan.<br>2) `Authorization` dan `X-Request-ID` dipasang di server; token tidak pernah ke browser.<br>3) Error jaringan, timeout, dan 401 upstream → 503 `SERVICE_UNAVAILABLE`.<br>4) `requestId` dari backend diteruskan, bukan dibuat sendiri (SCAFFOLD_REPORT §7 butir 8).<br>5) Batas body: unggahan 5 MB diterima dan FX-09 ditolak dengan kode yang benar; hasilnya dicatat sebagai TOI-03 di `docs/SCAFFOLD_REPORT.md` §5. |
| Verifikasi | `python scripts/dev.py test partner-portal`; `curl -X POST http://127.0.0.1:3001/api/verify` dengan berkas 5 MB |

### T4-03 — Templat dataset bahasa Inggris

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | Pash · Van |
| Branch | `feat/eval-templates-en` |
| Tenggat | Min 22/11 23.59 · M2 |
| File | `ai-eval/templates/` → `en-low.json`, `en-medium.json`, `en-high.json` (baru) |
| Ref | Sama dengan T2-04 |
| Tergantung | T5-01 (format) |
| Aturan | Sama dengan T2-04. |
| Selesai bila | 18 surat berlabel konsisten, sudah ditinjau Van. |
| Serah terima | B (T5-05) |

### T4-04 — Halaman cek offer letter (fixture)

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | Pash · Van |
| Branch | `feat/portal-check-page` |
| Tenggat | Sen 23/11 12.00 · M2 |
| File | `apps/partner-portal/src/app/` → `page.tsx`, `cek-offer-letter/page.tsx`<br>`apps/partner-portal/src/components/verification/` → `verify-form.tsx`, `mode-selector.tsx`, `consent-checkbox.tsx`, `processing-status.tsx`, `result-panels.tsx`, `guidance-list.tsx` (baru) |
| Ref | FR-02.01–FR-02.11; PRD §9.3–§9.8, §9.9.2 |
| Tergantung | T4-01 |
| Selesai bila | 1) Mode Dengan Kode dan Mode Tanpa Kode.<br>2) Persetujuan AI wajib sebelum analisis.<br>3) Validasi berkas di sisi klien.<br>4) Status pemrosesan tampil.<br>5) Tiga panel hasil terpisah, panduan tindak lanjut, penanganan error, dan pemeriksaan ulang, untuk semua fixture API-07 dan error.<br>6) Label "Simulasi" dan "Didukung Lettrust" tetap ada. |
| Verifikasi | `python scripts/dev.py test partner-portal`; `python scripts/dev.py up --build` sukses |

### T4-05 — Templat test case, `common.py`, skrip SCN-02

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | Pash · Dws |
| Branch | `test/scn-common` |
| Tenggat | Sen 23/11 18.00 (templat dan `common.py`) · Rab 25/11 12.00 (SCN-02) · M3 |
| File | `docs/testing/` → `README.md`, `test-cases.md`<br>`scripts/scn/` → `README.md`, `common.py` (baru), `scn02_mismatch.py` (baru) |
| Ref | PRD §12.4, §12.5; SA §18.3, §21.2 |
| Tergantung | — |
| Selesai bila | 1) `test-cases.md` memuat format TC sesuai §12.5, satu contoh TC lengkap, dan bagian per SCN sesuai pembagian §7.1.<br>2) `common.py` menyediakan pembacaan `.env` tanpa mencetak secret, login akun seed, klien API-07 dengan token partner, penyimpanan bukti, `dev.py stop/start`, dan pencetakan expected vs actual.<br>3) Pash memantau progres eksekusi SCN di tracker. |
| Verifikasi | Jalankan `scn02_mismatch.py` di stack nyata setelah TB-03 |
| Serah terima | Semua pelaksana skrip SCN (T1-08, T3-06, T6-06) |

### T4-06 — Sambung portal ke API-07 nyata

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | Pash · Van |
| Branch | `feat/portal-live-api` |
| Tenggat | Sel 24/11 18.00 · M3 |
| File | `apps/partner-portal/src/components/verification/verify-form.tsx`, `apps/partner-portal/src/app/api/verify/route.ts` (hanya penyesuaian integrasi) |
| Ref | SA §11.3; PRD §12.7.1 langkah 4–7 |
| Tergantung | T4-02, T4-04, T1-05 |
| Selesai bila | Mode Dengan Kode dan Tanpa Kode berjalan di stack nyata melalui BFF, termasuk kondisi ai-service mati dan chain mati. |
| Verifikasi | Alur manual di `http://127.0.0.1:3001/cek-offer-letter` dengan FX-01 dan FX-03; `python scripts/dev.py test partner-portal` |

### T4-07 — Skrip metrik evaluasi

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | Pash · B |
| Branch | `feat/eval-metrics` |
| Tenggat | Sel 24/11 18.00 · M3 |
| File | `ai-eval/scripts/metrics.py` |
| Ref | SA §7.9; PRD §10.3 MET-09–MET-15 |
| Tergantung | T5-05 (format manifest) |
| Selesai bila | Dari `results/<timestamp>/raw.jsonl` dan `manifest.csv` dihasilkan precision/recall/F1 per kategori, macro F1, confusion matrix, recall per indikator, dan statistik latensi ke `metrics.json` dan `confusion.csv`. Diuji dengan data buatan kecil. |
| Verifikasi | `python scripts/dev.py eval metrics <args>` pada data buatan |

### 6.6 B (PIC 5) — ai-service, Dataset, Evaluasi

| ID | Tugas | Tenggat |
| ----- | ----- | ----- |
| T5-01 | Format templat dataset | Sab 21/11 23.59 |
| T5-02 | Ekstraksi PDF, OCR, dan I-01 | Min 22/11 18.00 |
| T5-03 | Provider LLM dan prompt | Min 22/11 23.59 |
| T5-04 | Validator, skoring, komposisi, dan API-08 | Sen 23/11 12.00 |
| T5-05 | Generator dataset dan dataset 72 PDF | Sen 23/11 15.00 |
| T5-06 | Fixture FX-01–FX-10 | Sen 23/11 15.00 |
| T5-07 | Pemilihan model (OI-01) | Sen 23/11 21.00 |
| T5-08 | Bekukan test set dan run evaluasi final | Sen 23/11 23.59 · run Rab 25/11 12.00 |
| T5-09 | Laporan evaluasi | Rab 25/11 23.59 |

### T5-01 — Format templat dataset

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | B · Pash |
| Branch | `docs/eval-template-format` |
| Tenggat | Sab 21/11 23.59 · M2 |
| File | `ai-eval/templates/README.md` |
| Ref | SA §7.9; PRD §10.4.1, §10.4.2; OI-02 |
| Tergantung | — |
| Selesai bila | Format JSON templat ditetapkan (teks surat, kategori, indikator referensi, bahasa, catatan) dengan satu contoh lengkap per kategori. |
| Serah terima | Van (T2-04), Pash (T4-03) |

### T5-02 — Ekstraksi PDF, OCR, dan I-01

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | B · Dws |
| Branch | `feat/ai-extraction` |
| Tenggat | Min 22/11 18.00 · M2 |
| File | `services/ai-service/app/extraction/` → `pdf_text.py`, `ocr.py`, `service.py`<br>`services/ai-service/app/routers/extractions.py`<br>`services/ai-service/tests/test_extraction.py` (baru) |
| Ref | SA §7.2, §10.8 (I-01); FR-05.02–FR-05.04; TOI-06 |
| Tergantung | — |
| Selesai bila | 1) PDF teks → `TEXT_LAYER`; PDF scan → `OCR` dengan Tesseract `ind+eng`; PDF tanpa teks terbaca → `NO_CONTENT` dengan `reasonDetail`.<br>2) Batas halaman AI dihormati dan `truncated` diisi.<br>3) Berkas hanya di memori.<br>4) Respons sesuai contoh internal I-01. |
| Verifikasi | `python scripts/dev.py test ai-service` |
| Serah terima | Dws (T1-04) |

### T5-03 — Provider LLM dan prompt

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | B · Dws |
| Branch | `feat/ai-provider` |
| Tenggat | Min 22/11 23.59 · M2 |
| File | `services/ai-service/app/analysis/` → `provider.py`, `prompt.py`<br>`services/ai-service/tests/test_provider.py` (baru) |
| Ref | SA §7.3, §7.4; AD-16; FR-05.08, FR-05.11, FR-05.13; TOI-04, TOI-05 |
| Tergantung | — |
| Selesai bila | 1) Provider OpenAI-compatible ke Groq dengan JSON mode, timeout, dan retry sesuai SA.<br>2) Error provider dipetakan ke kode SA §10.3.<br>3) `promptVersion` tercatat; teks dokumen dibatasi sebagai data, bukan instruksi.<br>4) `get_provider()` hanya memilih `MockLLMProvider` bila `LLM_PROVIDER=mock` dan `APP_ENV=test`, dengan impor lazy (`docs/MOCKS.md` aturan 2).<br>5) Satu panggilan nyata berhasil dengan kunci sendiri. |
| Verifikasi | `python scripts/dev.py test ai-service` |

### T5-04 — Validator, skoring, komposisi, dan API-08

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | B · Dws |
| Branch | `feat/ai-analysis` |
| Tenggat | Sen 23/11 12.00 · M2 |
| File | `services/ai-service/app/analysis/` → `validator.py`, `scoring.py`, `compose.py`<br>`services/ai-service/app/routers/risk_analyses.py`<br>`services/ai-service/tests/` → `test_validator.py`, `test_scoring.py`, `test_compose.py` (baru) |
| Ref | SA §7.3, §7.5–§7.7; FR-05.05–FR-05.07, FR-05.09; BR-04.06 |
| Tergantung | T5-03. Test memakai skenario `MockLLMProvider` (`SCENARIOS` di `mock_provider.py`). |
| Selesai bila | 1) Hanya kode taksonomi tertutup yang diterima.<br>2) Kutipan divalidasi dengan substring ternormalisasi, ditambah rapidfuzz ≥ 90 untuk OCR.<br>3) Skoring HIGH/MEDIUM/LOW sesuai aturan; rekomendasi dari templat.<br>4) Seluruh 17 skenario `MockLLMProvider` menghasilkan nilai `expected_*` masing-masing.<br>5) `meta` tidak bocor ke API-07.<br>6) Satu analisis nyata lewat API-08 berhasil. |
| Verifikasi | `python scripts/dev.py test ai-service` |
| Serah terima | Dws (T1-05) |

### T5-05 — Generator dataset dan dataset 72 PDF

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | B · Pash |
| Branch | `feat/eval-dataset` |
| Tenggat | Sen 23/11 15.00 · M3 |
| File | `ai-eval/scripts/` → `generate_pdfs.py`, `make_scans.py`<br>`ai-eval/dataset/` → `manifest.csv`, `pdf/` (hasil generator) |
| Ref | SA §7.9; PRD §10.4.1, §10.4.2; OI-02 |
| Tergantung | T5-01, T2-04, T4-03 |
| Selesai bila | 1) 36 surat diubah menjadi 36 PDF teks dan 36 PDF scan (total 72).<br>2) Manifest memuat `id, split, lang, format, label, indicators, file, sha256`, dengan pembagian sekitar 24 dev dan 48 test yang seimbang.<br>3) Semua skrip dijalankan via `python scripts/dev.py eval`. |
| Verifikasi | `python scripts/dev.py eval generate_pdfs`; `python scripts/dev.py eval make_scans` |
| Serah terima | Pash (T4-07), Sat (T6-05) |

### T5-06 — Fixture FX-01–FX-10

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | B · Pash |
| Branch | `feat/fixtures` |
| Tenggat | Sen 23/11 15.00 · M3 |
| File | `fixtures/` → `README.md`, `FX-01.pdf` … `FX-10.pdf` (baru) |
| Ref | PRD §12.4.1; SA §7.9 |
| Tergantung | T5-05 (tooling) |
| Selesai bila | Kesepuluh fixture sesuai PRD §12.4.1 (FX-02 = FX-01 dengan isi diubah, FX-08 bukan PDF berekstensi `.pdf`, FX-09 melebihi batas, FX-10 header PDF tetapi rusak), dihasilkan dari tooling yang sama, dan README memuat tujuan serta checksum setiap fixture. |
| Serah terima | Semua anggota (TB-02, TB-04) |

### T5-07 — Pemilihan model (OI-01)

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | B · Dws |
| Branch | `feat/model-selection` |
| Tenggat | Sen 23/11 21.00 · M3 |
| File | `ai-eval/scripts/run_eval.py`<br>`docs/evaluation/protocol.md`<br>`.env.example` (nilai default `LLM_MODEL`) |
| Ref | PRD §10.4.3; SA §7.4.1; OI-01, OI-02; TOI-04, TOI-06, TOI-07 |
| Tergantung | T5-04, T5-05 |
| Selesai bila | 1) Kedua kandidat model dijalankan **hanya** di dev set.<br>2) Pilihan model, alasan, serta ambang OCR dan fuzzy dicatat di `protocol.md`.<br>3) `LLM_MODEL` di `.env.example` diperbarui dan diumumkan ke tim. |
| Verifikasi | `python scripts/dev.py eval run_eval --split dev` (argumen sesuai implementasi) |

### T5-08 — Bekukan test set dan run evaluasi final

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | B · Dws |
| Branch | `feat/eval-freeze`, lalu `docs/eval-results` |
| Tenggat | Freeze Sen 23/11 23.59 · run final Rab 25/11 12.00 · M4 |
| File | `ai-eval/scripts/` → `freeze_testset.py`, `run_eval.py`<br>`ai-eval/results/<timestamp>/` → `raw.jsonl`, `metrics.json`, `confusion.csv`, `run_config.json` |
| Ref | PRD §10.4.3; SA §7.9; SCN-22; FR-05.12 |
| Tergantung | T5-07, T4-07, T6-05 |
| Selesai bila | 1) Checksum test set dicatat sebelum tuning final.<br>2) Pipeline AI dan baseline dijalankan **sekali** pada test set yang sama.<br>3) Output mentah, identitas model, tanggal, parameter, dan versi prompt tersimpan.<br>4) Metrik dihitung oleh `metrics.py`. |
| Verifikasi | `python scripts/dev.py eval freeze_testset`; `python scripts/dev.py eval run_eval --split test` |

### T5-09 — Laporan evaluasi

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | B · Dws |
| Branch | `docs/eval-report` |
| Tenggat | Rab 25/11 23.59 · M4 |
| File | `docs/evaluation/report.md` (baru) |
| Ref | PRD §10.4, §10.4.4; ACC-06 |
| Tergantung | T5-08 |
| Selesai bila | Hasil aktual MET-09–MET-15, perbandingan dengan baseline, analisis kualitatif kesalahan, dan keterbatasan (PRD §10.4.4) tertulis, termasuk kegagalan. |

### 6.7 Sat (PIC 6) — Contract, Registry, Pencabutan, Baseline

| ID | Tugas | Tenggat |
| ----- | ----- | ----- |
| T6-01 | Fungsi contract dan 10 test wajib | Sab 21/11 23.59 |
| T6-02 | Codec dan `Web3RegistryAdapter` | Min 22/11 18.00 |
| T6-03 | Pencabutan bukti (API-06) | Sen 23/11 12.00 |
| T6-04 | Integration test dengan Anvil nyata | Sel 24/11 18.00 |
| T6-05 | Baseline berbasis aturan | Sel 24/11 18.00 |
| T6-06 | Skrip SCN-15, 16, 20 | Rab 25/11 12.00 |

### T6-01 — Fungsi contract dan 10 test wajib

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | Sat · Zan, plus Dws (ABI) |
| Branch | `feat/registry-contract` |
| Tenggat | Sab 21/11 23.59 · M2 |
| File | `blockchain/src/OfferProofRegistry.sol`<br>`blockchain/test/OfferProofRegistry.t.sol`<br>`services/backend/app/modules/registry/abi/OfferProofRegistry.json` (dihasilkan `python scripts/export_abi.py`) |
| Ref | SA §6.2.1–§6.2.3, §6.7 |
| Tergantung | — |
| Selesai bila | 1) `issueProof`, `revokeProof`, dan `getProof` (view) sesuai §6.2.2; `error NotImplemented()` dihapus.<br>2) 10 test §6.2.3 lulus dan `forge fmt --check` bersih.<br>3) ABI diekspor ulang.<br>4) Setelah merge, semua anggota diminta `python scripts/dev.py reset --yes` (§3.3). |
| Verifikasi | `python scripts/dev.py test blockchain` |
| Serah terima | Semua anggota (reset), Zan, Dws |

### T6-02 — Codec dan `Web3RegistryAdapter`

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | Sat · Zan |
| Branch | `feat/registry-adapter` |
| Tenggat | Min 22/11 18.00 · M2 |
| File | `services/backend/app/modules/registry/` → `adapter.py`, `codec.py`<br>`services/backend/tests/test_registry_codec.py` (baru) |
| Ref | SA §6.3, §6.4; AD-22; `docs/MOCKS.md` (pemetaan exception dan asumsi) |
| Tergantung | T6-01 |
| Selesai bila | 1) `issue_proof`, `revoke_proof`, `get_proof`, `find_issue_tx`, dan `find_revoke_tx` sesuai §6.4, dengan signer lock dan timeout dari config.<br>2) Pemetaan exception sama dengan `MockRegistryAdapter` (`docs/MOCKS.md`).<br>3) **Suite conformance lulus dengan adapter nyata.**<br>4) `registry/mock.py` tidak diubah. |
| Verifikasi | `python scripts/dev.py test backend`; dengan stack hidup: `docker compose exec backend python -m pytest -m real_registry tests/conformance` (semua lulus) |
| Serah terima | Zan (T3-04, T3-05), Dws |

### T6-03 — Pencabutan bukti (API-06)

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | Sat · Zan |
| Branch | `feat/revoke-proof` |
| Tenggat | Sen 23/11 12.00 · M2 |
| File | `services/backend/app/modules/proofs/` → `revocation.py` (baru), `router.py` (**hanya** handler API-06)<br>`services/backend/tests/test_proofs_revoke.py` (baru) |
| Ref | SA §6.6, §10.6 (API-06); FR-04.01–FR-04.05 |
| Tergantung | T3-02, T3-03 (`authorized_hr`); T6-02 untuk registry nyata (selama menunggu: `MockRegistryAdapter`) |
| Selesai bila | 1) Langkah §6.6 nomor 1–7 terpenuhi.<br>2) Bukti milik penerbit lain → 404; bukti yang sudah REVOKED → 409.<br>3) Idempotensi dengan kunci yang sama → 201 hasil sebelumnya (FR-04.04).<br>4) Registry gagal → status tetap ACTIVE dan respons 503.<br>5) Registry lewat `registry_adapter.get_registry_adapter()` (atribut modul).<br>6) Tidak mengubah handler lain di `router.py` maupun `service.py` milik Zan. |
| Verifikasi | `python scripts/dev.py test backend`; setelah T3-04 merge: cabut satu bukti di stack lalu `python scripts/dev.py chain events <proofId>` |
| Serah terima | Van (T2-07), Zan |

### T6-04 — Integration test dengan Anvil nyata

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | Sat · Zan |
| Branch | `test/registry-integration` |
| Tenggat | Sel 24/11 18.00 · M3 |
| File | `services/backend/tests/integration/` → `conftest.py`, `test_issue_flow.py`, `test_revoke_flow.py` (baru)<br>`services/backend/README.md` (cara menjalankan) |
| Ref | SA §18.1 |
| Tergantung | T3-04, T6-03 |
| Selesai bila | Penerbitan, pembacaan, pencabutan, dan idempotensi diuji terhadap chain Compose dengan marker `real_registry`; test default tetap hijau. |
| Verifikasi | `docker compose exec backend python -m pytest -m real_registry tests/conformance tests/integration` |

### T6-05 — Baseline berbasis aturan

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | Sat · B |
| Branch | `feat/eval-baseline` |
| Tenggat | Sel 24/11 18.00 · M3 |
| File | `ai-eval/scripts/baseline.py` |
| Ref | SA §7.8; BR-04.12 |
| Tergantung | T5-05 (manifest dan teks dataset) |
| Selesai bila | 1) Pola kata kunci/regex ID dan EN untuk tujuh kode, dengan pengecualian sederhana.<br>2) Evidence berupa kalimat yang memuat pola.<br>3) Skoring sama dengan `scoring.py`.<br>4) Output memakai format pipeline agar dapat dibaca `metrics.py`.<br>5) Baseline tidak dipakai sebagai fallback runtime. |
| Verifikasi | `python scripts/dev.py eval baseline --split dev` (argumen sesuai implementasi) |

### T6-06 — Skrip SCN-15, 16, 20

| Atribut | Isi |
| ----- | ----- |
| PIC · Reviewer | Sat · Zan |
| Branch | `test/scn-registry` |
| Tenggat | Rab 25/11 12.00 · M4 |
| File | `scripts/scn/` → `scn15_issue_idempotency.py`, `scn16_revoke_invalid.py`, `scn20_persistence.py` (baru) |
| Ref | PRD SCN-15, SCN-16, SCN-20; SA §18.3, §21.2 |
| Tergantung | T4-05, TB-03 |
| Selesai bila | Skrip memakai `common.py`, menghentikan dan menjalankan `chain` melalui `dev.py` bila diperlukan, dan menyimpan bukti dengan referensi transaksi. |
| Verifikasi | Jalankan setiap skrip di stack nyata dan periksa folder bukti |

## 7. Pengujian dan Evaluasi

### 7.1 Pembagian SCN

Pelaksana menulis baris TC di bagiannya sendiri di `docs/testing/test-cases.md` paling lambat Sel 24/11 23.59, lalu mengeksekusinya pada Rab 25/11 (TB-04). Retest dilakukan pelaksana yang sama paling lambat Kam 26/11 18.00.

| SCN | Pelaksana | Cara | Fixture/kondisi |
| ----- | ----- | ----- | ----- |
| SCN-01 | Pash | Manual UI (Console + portal) | FX-01 |
| SCN-02 | Pash | Skrip `scn02_mismatch.py` | FX-01, FX-02 |
| SCN-03 | Van | Manual UI | FX-01 |
| SCN-04 | Dws | Skrip `scn04_not_found.py` | FX-03 |
| SCN-05 | Dws | Skrip `scn05_code_only.py` | — |
| SCN-06 | B | Manual UI portal | FX-03 |
| SCN-07a | Pash | Manual UI, `python scripts/dev.py stop ai-service` | FX-01 |
| SCN-07b | Pash | Manual UI, `python scripts/dev.py stop chain` | FX-01 |
| SCN-08 | B | Manual UI portal + log | FX-03 |
| SCN-09 | B | Manual UI portal | FX-04 |
| SCN-10 | Dws | Skrip `scn10_invalid_input.py` | — |
| SCN-11 | Dws | Skrip `scn11_invalid_file.py` | FX-08, FX-09, FX-10, berkas kosong |
| SCN-12 | B | Manual UI portal | FX-07 |
| SCN-13 | Van | Manual UI | Akun baru |
| SCN-14 | Zan | Skrip `scn14_authz_negative.py` | Akun seed |
| SCN-15 | Sat | Skrip `scn15_issue_idempotency.py` | FX-01, FX-02 |
| SCN-16 | Sat | Skrip `scn16_revoke_invalid.py` | FX-01 |
| SCN-17 | Dws | Skrip `scn17_double_outage.py` | FX-01 |
| SCN-18 | B | Manual UI portal | FX-06 |
| SCN-19 | Pash | DevTools + pencarian token di `.next/static` | — |
| SCN-20 | Sat | Skrip `scn20_persistence.py` | FX-01 |
| SCN-21 | Anggota Windows dan Linux (TB-05) | Clone baru | — |
| SCN-22 | B | `python scripts/dev.py eval` (T5-08) | Test set beku |

### 7.2 Jadwal evaluasi AI

| Waktu | Kegiatan | Tugas |
| ----- | ----- | ----- |
| Sab 21/11 23.59 | Format templat ditetapkan | T5-01 |
| Min 22/11 23.59 | Templat ID dan EN selesai dan saling ditinjau | T2-04, T4-03 |
| Sen 23/11 15.00 | Dataset 72 PDF, manifest, dan fixture | T5-05, T5-06 |
| Sen 23/11 21.00 | Pemilihan model di dev set | T5-07 |
| Sen 23/11 23.59 | Test set dibekukan (checksum) | T5-08 |
| Sel 24/11 18.00 | Tuning final hanya di dev set; baseline dan metrik siap | T5-08, T6-05, T4-07 |
| Rab 25/11 12.00 | Run final pipeline dan baseline pada test set (SCN-22) | T5-08 |
| Rab 25/11 23.59 | Laporan evaluasi | T5-09 |

### 7.3 Isu teknis yang diuji

| TOI | Diuji di | Pelaksana |
| ----- | ----- | ----- |
| TOI-01 | Sudah tervalidasi; diuji ulang di SCN-20 | Sat |
| TOI-02 | Tidak diuji (tidak ada perangkat Apple Silicon) | — |
| TOI-03 | T4-02 | Pash |
| TOI-04, TOI-05 | T5-03, T5-07 | B |
| TOI-06, TOI-07 | T5-07 | B |
| TOI-08 | T1-08 (`latency.py`) | Dws |
| TOI-09 | Sudah tervalidasi | — |
| TOI-10 | TB-05 | Anggota Windows pengguna `--dev` |

## 8. Pembagian Laporan dan Deck

Ditunda. Pembagian bab dan slide akan ditambahkan pada revisi PLAN berikutnya dan dicatat sebagai TB-07.

## 9. Beban Kerja dan Daftar Potong

### 9.1 Ringkasan beban kerja

| PIC | Tugas | Di jalur kritis | SCN |
| ----- | ----- | ----- | ----- |
| Dws | T1-01–T1-08 (T1-01 selesai) | T1-02, T1-03, T1-04, T1-05 | 04, 05, 10, 11, 17 |
| Van | T2-01–T2-07 | T2-01, T2-05, T2-07 | 03, 13 |
| Zan | T3-01–T3-06 | T3-01–T3-05 | 14 |
| Pash | T4-01–T4-07 | T4-01, T4-02, T4-04, T4-06 | 01, 02, 07a, 07b, 19 |
| B | T5-01–T5-09 | T5-02–T5-05, T5-07, T5-08 | 06, 08, 09, 12, 18, 22 |
| Sat | T6-01–T6-06 | T6-01, T6-02, T6-03 | 15, 16, 20 |

Penyeimbangan yang diterapkan:

| Keputusan | Alasan |
| ----- | ----- |
| Pencabutan (T6-03) dikerjakan Sat | Mengurangi beban Zan yang seluruh tugasnya di jalur kritis. |
| Templat dataset (T2-04, T4-03) dikerjakan Van dan Pash | Mengurangi beban B dan memenuhi PRD §10.4.2 butir 3 (penulis templat bukan pengembang prompt). |
| Baseline (T6-05) oleh Sat dan metrik (T4-07) oleh Pash | Mengurangi beban B pada jalur evaluasi. |
| Mock dan fake dibuat Dws di awal (T1-01) | Semua workstream dapat berjalan paralel tanpa menunggu penyedia. |

### 9.2 Daftar potong

Bila pada TB-02 (Sen 23/11 20.00) atau Sel 24/11 18.00 ada risiko M3 tidak tercapai, item berikut dipotong sesuai urutan. Setiap item yang dipotong dicatat sebagai keterbatasan di laporan.

| Urutan | Item |
| ----- | ----- |
| 1 | FR-06.10 pembatasan laju partner (P1, Deferred, OI-07) |
| 2 | TOI-12 CI GitHub Actions (P1) |
| 3 | Opsi seed `--with-sample-proofs` (P1) |
| 4 | FR-03.06 penolakan dokumen aktif duplikat (P1) |
| 5 | FR-06.08 log verifikasi minimal (P1, T1-06) |

Requirement P0 tidak dipotong. Bila sebuah P0 terancam, Dws memutuskan bersama PIC terkait: menambah orang ke tugas tersebut, atau mencatatnya sebagai keterbatasan dengan persetujuan koordinator (PRD Bab 1).
