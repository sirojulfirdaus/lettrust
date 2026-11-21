# Skrip Skenario API (rencana)

Owner: Pash (PIC 4) · Status: STUB · Ref: SA §18.3, §17.5; PRD §12.4

Belum ada skrip. Rencana skrip Python (httpx) untuk skenario deterministik level API:

| Skrip (rencana) | Skenario |
| ----- | ----- |
| `scn02_mismatch.py` | SCN-02 |
| `scn04_not_found.py` | SCN-04 |
| `scn05_code_only.py` | SCN-05 |
| `scn10_input_combination.py` | SCN-10 |
| `scn11_invalid_files.py` | SCN-11 |
| `scn14_authorization.py` | SCN-14 |
| `scn15_issue_idempotency.py` | SCN-15 |
| `scn16_revoke_invalid.py` | SCN-16 |
| `scn17_double_outage.py` | SCN-17 |
| `scn20_persistence.py` | SCN-20 |
| `measure_latency.py` | MET-16, MET-17 (median, P95) |

Setiap skrip wajib:

1. Membaca kredensial seed dari `.env` dan token partner dari `PARTNER_TOKEN` tanpa mencetaknya.
2. Menjalankan langkah skenario; menghentikan/menjalankan service via `python scripts/dev.py stop|start <svc>` bila perlu.
3. Menyimpan request ringkas (tanpa secret) dan respons JSON ke `docs/testing/evidence/<TC-ID>/`.
4. Mencetak ringkasan expected vs actual tanpa menandai PASS otomatis di dokumen.

Catatan: `httpx` belum menjadi dependency host; jalankan skrip di image backend atau tambahkan dependency secara eksplisit saat skrip dibuat.
