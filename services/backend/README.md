# backend — Lettrust API (`/api/v1`)

Owner: Dws (core, main, verifications, partners, health), Zan (auth, issuers, proofs, models, seed), Sat (registry) · Ref: SA §4, §5, §8–§10

Modular monolith FastAPI, SQLite (WAL), web3.py. Satu-satunya penulis registry dan pemanggil ai-service.

```
python scripts/dev.py test backend            # pytest di container (contracts/ ter-mount)
python scripts/dev.py openapi                 # contracts/openapi.json + tipe frontend
docker compose run --rm --no-deps -e RUFF_CACHE_DIR=/tmp/ruff backend ruff check app tests
```

Native (cadangan): Python 3.12, `python -m venv .venv`, `pip install -r requirements-dev.txt`, set env dari `.env` (sesuaikan `DATABASE_URL`, `REGISTRY_RPC_URL=http://127.0.0.1:8545`, `REGISTRY_DEPLOYMENT_FILE=../../.local/deployments/local.json`, `AI_SERVICE_URL=http://127.0.0.1:8001`), lalu `python -m app.cli init-db && uvicorn app.main:app --port 8000`.

Status implementasi mengikuti header modul dan router masing-masing. API-04, API-05, API-06, serta S-06 sudah memiliki pengujian integrasi registry berikut.

## Integrasi registry dengan Anvil (T6-04)

Jalankan dari root repository dengan Docker/Compose dan `.env` lokal yang sudah disiapkan sesuai README utama:

```bash
docker compose build backend chain-deployer
docker compose up -d --wait chain chain-deployer backend
docker compose exec -T backend python -m pytest -q --tb=no -m real_registry tests/conformance tests/integration
python scripts/dev.py test backend
```

Build ulang backend setelah perubahan tes agar direktori `tests/integration/` ikut tersalin ke image. Suite ini tidak memerlukan ai-service, frontend, atau panggilan LLM. Jika menggunakan nama proyek atau port Compose lain, gunakan konfigurasi yang sama pada seluruh perintah.

Tes menggunakan `TestClient` FastAPI, autentikasi JWT asli, akun/penerbit sintetis, dan SQLite sementara dari fixture induk. Factory registry diarahkan ke `Web3RegistryAdapter` dengan konfigurasi Compose asli, bukan mock. Database demo dalam volume backend tidak dipakai untuk data tes. Marker `real_registry` membuat seluruh suite integrasi di-deselect pada test default; memilih marker itu tanpa chain/contract yang sehat akan gagal dengan jelas.

Cakupan: unggah PDF sintetis satu halaman, hash byte asli, penerbitan dan pembacaan API-04/API-05, pencabutan API-06 dan daftar S-06, kecocokan mirror/receipt/event, replay kedua operasi, konflik key/payload, pembatasan lintas penerbit, dan dua issuance bersamaan. Nonce dan jumlah event diperiksa untuk memastikan replay/konflik tidak mengirim transaksi tambahan.

Jalankan suite secara serial tanpa proses pengujian lain yang menulis ke chain yang sama. Setiap tes membuat identifier dan penerbit baru; tes dapat diulang pada state Anvil persisten tanpa reset, penghapusan volume, atau perubahan automining. Chain akan menyimpan bukti sintetis hasil tes. Gunakan `--tb=no` seperti contoh agar kegagalan probe tidak menampilkan token atau payload dari konteks traceback. Hasil suite ini merupakan verifikasi otomatis, bukan bukti eksekusi skenario SCN atau evaluasi AI.
