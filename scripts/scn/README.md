# Skrip Skenario API

Owner: Pash (PIC 4) · Status: COMPLETE · Ref: SA §18.3, §21.2; PRD §12.4

Skrip Python `httpx` menjalankan skenario deterministik pada stack nyata. Skrip tidak memakai mock dan tidak menulis status hasil ke dokumen test case.

| Skrip (rencana) | Skenario |
| ----- | ----- |
| `scn02_mismatch.py` | SCN-02; FX-01 yang sudah diterbitkan dan FX-02 |
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

`common.py` menyediakan pembacaan `.env` tanpa mencetak nilainya, login akun HR seed, request API-07 dengan token partner, penyimpanan evidence tersanitasi, stop/start service lewat `dev.py`, dan ringkasan expected vs actual.

## Menjalankan SCN-02

Prasyarat: stack nyata sudah sehat; FX-01 telah diterbitkan melalui alur SCN-01; API-04 dan API-07 telah terintegrasi; fixture sintetis FX-02 tersedia. Dari root repository:

```powershell
python -m pip install -r scripts/scn/requirements.txt
python scripts/scn/scn02_mismatch.py --fx02 fixtures/FX-02.pdf
```

Skrip meminta kode referensi dengan input tersembunyi, mengirim FX-02 ke API-07, lalu menyimpan respons yang disanitasi di `docs/testing/evidence/TC-002/`. Kode referensi, token, password, dan kutipan evidence tidak ditulis ke output atau file evidence. Kode keluar non-zero menandakan hasil aktual tidak memenuhi expected result; penguji tetap menilai dan mengisi status test case secara terpisah.

Dependency host terpisah dikunci di `requirements.txt`; versi `httpx` mengikuti dependency backend.

Setiap skrip skenario wajib:

1. Membaca kredensial seed dari `.env` dan token partner dari `PARTNER_TOKEN` tanpa mencetaknya.
2. Menjalankan langkah skenario; menghentikan/menjalankan service via `python scripts/dev.py stop|start <svc>` bila perlu.
3. Menyimpan request ringkas (tanpa secret) dan respons JSON ke `docs/testing/evidence/<TC-ID>/`.
4. Mencetak ringkasan expected vs actual tanpa menandai PASS otomatis di dokumen.
