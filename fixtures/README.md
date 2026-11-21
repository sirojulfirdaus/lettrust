# Fixtures Demo dan Skenario (STUB)

Owner: B (PIC 5) · Status: STUB · Ref: PRD §12.4.1; SA §7.9

Fixture dihasilkan dari tooling `ai-eval/` yang sama. Seluruh isi adalah data sintetis. Belum ada fixture yang dibuat.

| ID | Fixture | Kegunaan | Berkas | Status |
| ----- | ----- | ----- | ----- | ----- |
| FX-01 | Offer letter sintetis wajar, bahasa Indonesia, PDF teks | Penerbitan, SCN-01, SCN-03, SCN-05 | — | Belum dibuat |
| FX-02 | Salinan FX-01 dengan perubahan isi (nominal gaji atau nomor rekening) | SCN-02 | — | Belum dibuat |
| FX-03 | Offer letter berisiko tinggi (biaya administrasi, kontak tidak resmi), ID, PDF teks | SCN-06, SCN-08 | — | Belum dibuat |
| FX-04 | Offer letter berisiko tinggi, bahasa Inggris, PDF scan | SCN-09 | — | Belum dibuat |
| FX-05 | Offer letter berisiko sedang (tekanan waktu, kontak tidak resmi) | Demo kategori MEDIUM | — | Belum dibuat |
| FX-06 | Offer letter berisi instruksi prompt injection dan permintaan pembayaran | SCN-18 | — | Belum dibuat |
| FX-07 | PDF tanpa teks yang dapat dikenali (halaman kosong) | SCN-12 | — | Belum dibuat |
| FX-08 | Berkas bukan PDF dengan ekstensi `.pdf` | SCN-11 | — | Belum dibuat |
| FX-09 | PDF berukuran di atas batas (5 MB) | SCN-11 | — | Belum dibuat |
| FX-10 | Berkas dengan header PDF tetapi rusak | SCN-11 | — | Belum dibuat |

TODO: hasilkan FX-01–FX-10 melalui `ai-eval/scripts/`, catat nama berkas dan SHA-256 di tabel ini. Kategori fixture tidak boleh di-hardcode di pipeline (FR-05.06/AC-05).
