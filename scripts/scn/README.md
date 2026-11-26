# Skrip Skenario API

Owner: Pash (PIC 4) · Status: COMPLETE untuk SCN-02 · Ref: SA §18.3, §21.2; PRD §12.4

Skrip Python memakai `httpx` untuk skenario deterministik pada stack nyata. Skrip yang belum ditugaskan/diimplementasikan tercantum sebagai rencana.

| Skrip | Skenario |
| ----- | ----- |
| `scn02_mismatch.py` | SCN-02 |
| `scn04_not_found.py` | SCN-04 (tersedia) |
| `scn05_code_only.py` | SCN-05 (tersedia) |
| `scn10_invalid_input.py` | SCN-10 (tersedia) |
| `scn11_invalid_file.py` | SCN-11 (tersedia) |
| `scn14_authorization.py` | SCN-14 (rencana) |
| `scn15_issue_idempotency.py` | SCN-15 (rencana) |
| `scn16_revoke_invalid.py` | SCN-16 (rencana) |
| `scn17_double_outage.py` | SCN-17 (tersedia; wajib `--allow-service-interruption`) |
| `scn20_persistence.py` | SCN-20 (rencana) |
| `latency.py` | MET-16, MET-17 (tersedia) |

`common.py` memuat `.env` tanpa mencetak nilainya, menyediakan login HR seed dan klien API-07 bertoken partner, menyimpan evidence yang disanitasi, menjalankan `dev.py stop/start`, serta mencetak expected dan actual.

## Menjalankan SCN-02

Prasyarat: stack nyata sehat, FX-01 telah diterbitkan dan ACTIVE, FX-02 tersedia, serta API-04/API-07 sudah terintegrasi. Dari root repository:

```powershell
python -m pip install -r scripts/scn/requirements.txt
python scripts/scn/scn02_mismatch.py --fx02 fixtures/FX-02.pdf
```

Kode referensi diminta melalui input tersembunyi. Skrip mengirim FX-02 ke API-07 dan menyimpan ringkasan request serta respons yang disanitasi di `docs/testing/evidence/TC-002/`. Kode referensi, token, password, dan kutipan evidence tidak dicetak atau disimpan. Skrip tidak mengisi status pada test case; penguji menilai hasil dan mencatatnya setelah eksekusi nyata.

## Menjalankan SCN-04, 05, 10, 11, 17 dan latensi (T1-08)

Prasyarat: stack nyata sehat (Anvil + LLM nyata) dan HR seed berwenang. Skrip mencari bukti ACTIVE FX-01 milik penerbit seed dan hanya menerbitkan baru bila belum ada; kode referensi tidak diminta dan disimpan hanya sebagai empat karakter terakhir. Helper bersama ada di `_verification_scn.py` (di atas `common.py`).

```powershell
python scripts/scn/scn04_not_found.py
python scripts/scn/scn05_code_only.py
python scripts/scn/scn10_invalid_input.py
python scripts/scn/scn11_invalid_file.py
python scripts/scn/scn17_double_outage.py --allow-service-interruption
python scripts/scn/latency.py
```

SCN-17 menghentikan `chain` dan `ai-service` melalui `dev.py`, lalu selalu menjalankannya kembali dan menunggu health; tanpa `--allow-service-interruption` skrip menolak berjalan. Langkah dengan LLM nyata memeriksa `state`, kategori, dan indikator label sebagai subset; indikator tambahan dicatat sebagai info. SCN-10 memeriksa log `ai-service` per `requestId` sehingga membutuhkan akses `docker compose logs`. `latency.py` (TC-023) memakai default 20 sampel tanpa AI, 5 per varian AI, dan 5 pasangan API-04/API-06 (salinan FX-01 unik yang langsung dicabut); jumlah dapat diubah dengan `--samples`, `--ai-samples`, `--ai-interval`, dan `--issue-samples`.

Setiap skrip skenario wajib menyimpan request ringkas tanpa secret dan respons JSON, lalu mencetak expected vs actual tanpa menetapkan PASS di dokumen. Dependency host `httpx` dikunci di `requirements.txt` pada direktori ini.
