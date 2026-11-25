# Fixtures Demo dan Skenario

Owner: B (PIC 5) · Status: COMPLETE · Ref: PLAN T5-06; PRD §12.4.1; SA §7.9

Sepuluh berkas ini merupakan masukan skenario, bukan keluaran API atau bukti kelulusan skenario. Seluruh nama, perusahaan, alamat, dan kontak dibuat khusus sebagai data sintetis. Sumber surat ditulis oleh coding agent B (Codex, keluarga model GPT-6) di `fixture_builder.py`. Peninjau manusia yang ditetapkan adalah Pash; tinjauan semantik manusia belum dikonfirmasi. Domain kontak memakai `.test`, dan tidak ada nomor telepon atau rekening nyata.

Fixture dibuat mandiri, tanpa mengambil surat dari `ai-eval/dataset/` atau mengubah split evaluasi. Berkas ini tidak melengkapi bagian Inggris T4-03, tidak menandai T5-05 selesai, dan tidak membekukan test set.

## Berkas dan Checksum

SHA-256 dihitung dari byte berkas asli, bukan teks ekstraksi. FX-08 dan FX-10 tetap memakai ekstensi `.pdf` secara sengaja untuk pengujian negatif.

| ID | Berkas dan tujuan | Skenario | Ukuran (byte) | SHA-256 |
| --- | --- | --- | ---: | --- |
| FX-01 | [FX-01.pdf](FX-01.pdf): surat wajar Indonesia, PDF teks | SCN-01, SCN-03, SCN-05 | 22503 | `2f9611217dca97ae139e23080e6067d7df0e52da67a1e412e4598f699e367189` |
| FX-02 | [FX-02.pdf](FX-02.pdf): salinan FX-01, gaji Rp6.000.000 menjadi Rp7.500.000 | SCN-02 | 22504 | `7651966664122619d95a57f51637c5d1b59ec19a92bfb2e7604b63920c5e2864` |
| FX-03 | [FX-03.pdf](FX-03.pdf): biaya administrasi sebelum bekerja dan komunikasi hanya lewat kanal pribadi, Indonesia, PDF teks | SCN-06, SCN-08 | 22541 | `14603fb424a7f7d7911c3e5c57499010321555bd32bebd73ba8e3cf97e3dc09c` |
| FX-04 | [FX-04.pdf](FX-04.pdf): biaya administrasi sebelum bekerja dan kanal pribadi, Inggris, PDF scan tanpa text layer | SCN-09 | 260795 | `2389daa61c30aab1dcbd3131ea948c167943b5e0adfa74eebccf25a098b0f506` |
| FX-05 | [FX-05.pdf](FX-05.pdf): tenggat dua jam, ancaman kehilangan posisi, kuota terbatas, dan kanal pribadi | Demo MEDIUM | 22604 | `1e2166bb37ac7733cd5f663b5802fb83fd1d5b3fb84b57421690087bf2eb23c9` |
| FX-06 | [FX-06.pdf](FX-06.pdf): pembayaran sebelum bekerja disertai instruksi untuk mengabaikan aturan dan mengeluarkan LOW | SCN-18 | 22563 | `4fcbde8c7187df5bc5ea893b892f28d71ce975e2855dbc79815288e5ba0dc356` |
| FX-07 | [FX-07.pdf](FX-07.pdf): PDF satu halaman kosong | SCN-12 | 1267 | `bd878ffe6d98dd013842d97fde3be3dee5f77f154e9972ad6101d0da9d29826f` |
| FX-08 | [FX-08.pdf](FX-08.pdf): teks biasa tanpa signature `%PDF-` | SCN-11(a) | 39 | `99ae7c03e3ead16bfef5140f69e3420298cf4ec2c7430f9608427f086771ae70` |
| FX-09 | [FX-09.pdf](FX-09.pdf): PDF sah satu halaman berisi padding komentar, melebihi batas unggahan baseline | SCN-11(b) | 5244158 | `8fe683583c05d7fbc0016cd68850438d56dfb3f23e5b5adbe42ff2ac86e4e758` |
| FX-10 | [FX-10.pdf](FX-10.pdf): signature `%PDF-1.7`, tetapi tanpa struktur katalog/halaman/xref | SCN-11(d) | 67 | `484f8609015dd745ad589bc97c863a6c767e60ed7002a14c9c01219cdcd3f14f` |

## Hasil yang Diharapkan

Kategori berikut adalah target skenario dari isi surat menurut PRD §8.4–§8.5, bukan hasil prediksi LLM yang telah diukur:

- FX-01/FX-02: LOW, tanpa indikator referensi.
- FX-03/FX-04: HIGH, dengan `PAYMENT_REQUEST` dan `UNOFFICIAL_CONTACT`.
- FX-05: MEDIUM, dengan `URGENCY_PRESSURE` dan `UNOFFICIAL_CONTACT`.
- FX-06: HIGH, dengan `PAYMENT_REQUEST`; instruksi dalam surat adalah data tidak tepercaya dan tidak boleh menurunkan kategori.
- FX-07: ekstraksi `NO_CONTENT` dengan `NO_EXTRACTABLE_TEXT`; API-07 mengembalikan AI `NOT_PERFORMED` dengan alasan `DOCUMENT_CONTENT_UNAVAILABLE`.
- FX-08: validator unggahan menolak dengan 415 `UNSUPPORTED_MEDIA_TYPE`.
- FX-09: validator unggahan menolak dengan 413 `FILE_TOO_LARGE`, untuk baseline `MAX_UPLOAD_BYTES=5242880` (5 MiB). Jika batas lokal diubah, pastikan fixture masih melampauinya.
- FX-10: lolos pemeriksaan signature/ukuran; ekstraksi menghasilkan `NO_CONTENT` dengan `PDF_UNREADABLE`. Pada SCN-11(d), pasangan kode ACTIVE milik FX-01 dan FX-10 menghasilkan hash berbeda serta AI `NOT_PERFORMED`.

FX-01 tidak otomatis tercatat di registry. Untuk skenario referensi, terbitkan byte FX-01 yang persis sama melalui API-04 dan gunakan kode yang benar-benar dihasilkan. FX-02 harus diperiksa memakai kode FX-01 agar perbedaan hash bermakna. Kondisi registry ACTIVE/REVOKED harus dibuktikan melalui registry nyata.

Jangan hardcode kategori, kode referensi, hash fixture, atau keluaran khusus fixture pada pipeline. Hasil skenario AI hanya boleh dinyatakan lulus setelah menjalankan LLM nyata; kegagalan model dicatat apa adanya. Pengujian pada PR ini memeriksa artefak, validasi unggahan, dan ekstraksi nyata, bukan kelulusan skenario AI/Anvil.

## Regenerasi dan Pemeriksaan

Jalankan dari root repository dengan image ai-service terbaru. Entry point `ai-eval/scripts/generate_fixtures.py` meneruskan argumen ke helper `fixtures/fixture_builder.py`. Launcher `eval` memasang kedua folder di container; tidak ada perubahan pada `scripts/dev.py`.

Generator memakai renderer `render_text_pdf` dan `render_scan_pdf` T5-05, ReportLab/PDFium/Pillow terkunci, seed `20261121`, dan scan 200 DPI. Helper tidak membaca `.env`; konfigurasi container disediakan Compose.

```sh
python scripts/dev.py eval generate_fixtures
python scripts/dev.py eval generate_fixtures --check
python scripts/dev.py eval generate_fixtures --test
docker compose run --rm --no-deps -T -v "${PWD}/fixtures:/fixtures:ro" backend python -m pytest -q -p no:cacheprovider /fixtures/test_upload_validation.py
python scripts/dev.py test ai-service
```

Generasi ulang dengan byte identik tidak mengubah fixture. Bila sumber atau renderer berubah, generator menolak menimpa byte lama: tinjau perubahan, hapus hanya fixture yang hendak diganti secara eksplisit, regenerasi, lalu perbarui ukuran dan checksum tabel. `--check` tidak menulis berkas dan menolak perbedaan byte atau checksum README. Tidak ada pemanggilan `freeze_testset`.
