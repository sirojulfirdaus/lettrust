## Ringkasan

<!-- Apa yang berubah dan mengapa. Rujuk ID: FR-xx.yy, SCN-xx, TC-xxx, SA §x.y. -->

## Modul dan Owner

- [ ] Perubahan hanya di modul milik saya (SA §4.1), atau koordinasi dengan owner terkait sudah dilakukan.
- [ ] Tidak mengubah file bersama (`contracts/`, `compose*.yaml`, `.env.example`, `scripts/dev.py`, `services/backend/app/core/`, `services/backend/app/main.py`) tanpa persetujuan Dws.

## Verifikasi

<!-- Perintah yang dijalankan dan hasil aktual. Sebutkan mock vs Anvil/LLM nyata. -->

- [ ] `python scripts/dev.py test <svc>` untuk layanan terdampak lulus.
- [ ] `python scripts/dev.py up` tetap sehat.
- [ ] Perubahan kontrak API: `python scripts/dev.py openapi` dijalankan dan contoh diperbarui.

## Checklist Invariant

- [ ] Tidak ada vonis gabungan ("asli/palsu", "aman/penipuan"); tiga komponen hasil tetap terpisah.
- [ ] Tidak ada secret di kode, log, bukti, atau commit (`.env` tidak ikut).
- [ ] Komentar Indonesia singkat pada fungsi/komponen baru; tidak ada `dangerouslySetInnerHTML`.
- [ ] Dependency baru dipin exact dan disebutkan di deskripsi.

## Risiko / Belum Selesai
