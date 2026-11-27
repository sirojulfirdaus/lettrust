# Skrip Skenario API

Owner: Pash (PIC 4, koordinasi; tiap skrip mencantumkan owner di header) · Status: COMPLETE · Ref: SA §18.3, §21.2; PRD §12.4

Skrip Python memakai `httpx` untuk skenario deterministik pada stack nyata. Skenario lain dijalankan manual melalui UI (PLAN §7.1).

| Skrip | Skenario | Owner | Evidence |
| ----- | ----- | ----- | ----- |
| `scn02_mismatch.py` | SCN-02 | Pash | `TC-002/` |
| `scn04_not_found.py` | SCN-04 | Dws | `TC-004/` |
| `scn05_code_only.py` | SCN-05 | Dws | `TC-005/` |
| `scn10_invalid_input.py` | SCN-10 | Dws | `TC-010/` |
| `scn11_invalid_file.py` | SCN-11 | Dws | `TC-011/` |
| `scn14_authz_negative.py` | SCN-14 | Zan | `TC-014/` |
| `scn15_issue_idempotency.py` | SCN-15 (wajib `--allow-service-interruption`) | Sat | `TC-015/` |
| `scn16_revoke_invalid.py` | SCN-16 (wajib `--allow-service-interruption`) | Sat | `TC-016/` |
| `scn17_double_outage.py` | SCN-17 (wajib `--allow-service-interruption`) | Dws | `TC-017/` |
| `scn20_persistence.py` | SCN-20 (wajib `--allow-service-interruption`) | Sat | `TC-020/` |
| `latency.py` | MET-16, MET-17 | Dws | `TC-023/` |

`common.py` memuat `.env` tanpa mencetak nilainya, menyediakan login HR seed dan klien API-07 bertoken partner, menyimpan evidence yang disanitasi, menjalankan `dev.py stop/start`, serta mencetak expected dan actual.

## Menjalankan SCN-02

Prasyarat: stack nyata sehat, FX-01 telah diterbitkan dan ACTIVE, FX-02 tersedia, serta API-04/API-07 sudah terintegrasi. Dari root repository:

```powershell
python -m pip install -r scripts/scn/requirements.txt
python scripts/scn/scn02_mismatch.py --fx02 fixtures/FX-02.pdf
```

Kode referensi diminta melalui input tersembunyi. Skrip mengirim FX-02 ke API-07 dan menyimpan ringkasan request serta respons yang disanitasi di `docs/testing/evidence/TC-002/`. Kode referensi, token, password, dan kutipan evidence tidak dicetak atau disimpan. Skrip tidak mengisi status pada test case; penguji menilai hasil dan mencatatnya setelah eksekusi nyata.

## Menjalankan SCN-04, 05, 10, 11, 17 dan latensi (T1-08)

Prasyarat: stack nyata sehat (Anvil + LLM nyata) dan HR seed berwenang. Sebelum login atau memakai token, skrip menolak alamat API selain HTTP loopback dan memastikan port backend milik project Compose yang dipilih (`--compose-project`, default `COMPOSE_PROJECT_NAME` atau `lettrust`); project yang sama dipakai untuk `dev.py stop/start` dan `docker compose logs/exec`. Skrip memeriksa seluruh halaman daftar bukti ACTIVE FX-01 milik penerbit seed dan hanya menerbitkan baru bila belum ada; kegagalan daftar atau detail menghentikan setup tanpa penerbitan. Kode referensi tidak diminta dan disimpan hanya sebagai empat karakter terakhir. Helper bersama ada di `_verification_scn.py` (di atas `common.py`).

```powershell
python scripts/scn/scn04_not_found.py
python scripts/scn/scn05_code_only.py
python scripts/scn/scn10_invalid_input.py
python scripts/scn/scn11_invalid_file.py
python scripts/scn/scn17_double_outage.py --allow-service-interruption
python scripts/scn/latency.py
```

SCN-17 menghentikan `chain` dan `ai-service` melalui `dev.py`, lalu selalu mencoba menjalankan kembali keduanya secara terpisah (kegagalan satu service tidak melewatkan yang lain dan dilaporkan dengan perintah pemulihannya) dan menunggu health; tanpa `--allow-service-interruption` skrip menolak berjalan. Langkah dengan LLM nyata memeriksa `state`, kategori, dan indikator label sebagai subset; indikator tambahan dicatat sebagai info. SCN-10 memeriksa log `ai-service` per `requestId` sehingga membutuhkan akses `docker compose logs`. `latency.py` (TC-023) memakai default 20 sampel tanpa AI, 5 per varian AI, dan 5 pasangan API-04/API-06 (salinan FX-01 unik yang langsung dicabut); jumlah dapat diubah dengan `--samples`, `--ai-samples`, `--ai-interval`, dan `--issue-samples`. Sebelum varian AI, skrip memeriksa health `aiService`; bila bukan `ok` varian AI tidak dipanggil. Panggilan AI juga dihentikan saat `AI_QUOTA_EXCEEDED` atau `AI_SERVICE_UNAVAILABLE`; varian tanpa satu pun sampel sukses membuat pengukuran tidak lengkap (exit 2), bukan lulus.

## Menjalankan SCN-14, 15, 16, 20

Prasyarat: stack nyata sehat (`python scripts/dev.py up`) dengan seed bawaan; tidak memakai LLM. Dari root repository:

```powershell
python scripts/scn/scn14_authz_negative.py
python scripts/scn/scn15_issue_idempotency.py --allow-service-interruption
python scripts/scn/scn16_revoke_invalid.py --allow-service-interruption
python scripts/scn/scn20_persistence.py --allow-service-interruption
```

- SCN-14 login dengan akun seed (admin, HR penerbit PENDING/REJECTED, HR belum berwenang, dan HR berwenang dari dua penerbit), menguji penolakan operasi tanpa hak, lalu memastikan tidak ada transaksi registry baru dan bukti tidak berubah. Skrip berhenti bila role/status akun seed berbeda dari prasyarat. `--tc-id` mengganti direktori evidence (default `TC-014`).
- SCN-15, 16, dan 20 (helper `_registry_scn.py`) mendaftarkan HR dan penerbit uji baru melalui admin seed, lalu menerbitkan salinan FX-01. SCN-15 dan 16 menghentikan dan menjalankan kembali `chain`; SCN-20 menjalankan `down`/`up` seluruh stack tanpa menghapus volume. Tanpa `--allow-service-interruption` skrip menolak berjalan, jadi pakai hanya pada stack lokal khusus pengujian.
- Semua skrip menerima `--compose-project` (default `COMPOSE_PROJECT_NAME` atau `lettrust`) dan menyimpan ringkasan tanpa secret di `docs/testing/evidence/<TC>/`, termasuk hasil parsial saat skenario terhambat.

Setiap skrip skenario wajib menyimpan request ringkas tanpa secret dan respons JSON, lalu mencetak expected vs actual tanpa menetapkan PASS di dokumen. Dependency host `httpx` dikunci di `requirements.txt` pada direktori ini.
