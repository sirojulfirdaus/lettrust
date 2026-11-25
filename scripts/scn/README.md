# Skrip Skenario API

Owner: Pash (PIC 4) · Status: COMPLETE untuk SCN-02 · Ref: SA §18.3, §21.2; PRD §12.4

Skrip Python memakai `httpx` untuk skenario deterministik pada stack nyata. Skrip yang belum ditugaskan/diimplementasikan tercantum sebagai rencana.

| Skrip | Skenario |
| ----- | ----- |
| `scn02_mismatch.py` | SCN-02 |
| `scn04_not_found.py` | SCN-04 (rencana) |
| `scn05_code_only.py` | SCN-05 (rencana) |
| `scn10_input_combination.py` | SCN-10 (rencana) |
| `scn11_invalid_files.py` | SCN-11 (rencana) |
| `scn14_authorization.py` | SCN-14 (rencana) |
| `scn15_issue_idempotency.py` | SCN-15 (rencana) |
| `scn16_revoke_invalid.py` | SCN-16 (rencana) |
| `scn17_double_outage.py` | SCN-17 (rencana) |
| `scn20_persistence.py` | SCN-20 (rencana) |
| `measure_latency.py` | MET-16, MET-17 (rencana) |

`common.py` memuat `.env` tanpa mencetak nilainya, menyediakan login HR seed dan klien API-07 bertoken partner, menyimpan evidence yang disanitasi, menjalankan `dev.py stop/start`, serta mencetak expected dan actual.

## Menjalankan SCN-02

Prasyarat: stack nyata sehat, FX-01 telah diterbitkan dan ACTIVE, FX-02 tersedia, serta API-04/API-07 sudah terintegrasi. Dari root repository:

```powershell
python -m pip install -r scripts/scn/requirements.txt
python scripts/scn/scn02_mismatch.py --fx02 fixtures/FX-02.pdf
```

Kode referensi diminta melalui input tersembunyi. Skrip mengirim FX-02 ke API-07 dan menyimpan ringkasan request serta respons yang disanitasi di `docs/testing/evidence/TC-002/`. Kode referensi, token, password, dan kutipan evidence tidak dicetak atau disimpan. Skrip tidak mengisi status pada test case; penguji menilai hasil dan mencatatnya setelah eksekusi nyata.

Setiap skrip skenario wajib menyimpan request ringkas tanpa secret dan respons JSON, lalu mencetak expected vs actual tanpa menetapkan PASS di dokumen. Dependency host `httpx` dikunci di `requirements.txt` pada direktori ini.
