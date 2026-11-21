# Lettrust

Lettrust adalah prototipe akademik (II3120 LaSTI, ITB, Kelompok 04, Deliverable 3) berupa layanan verifikasi offer letter dan analisis risiko penipuan rekrutmen yang terintegrasi ke portal karier simulasi melalui REST API. Bukti penerbitan dicatat pada registry smart contract lokal (Anvil), isi surat dianalisis model bahasa pra-latih, dan hasil disajikan sebagai tiga komponen terpisah tanpa vonis gabungan. Acuan: [PRD](docs/prd/), [SYSTEM_ARCHITECTURE](docs/SYSTEM_ARCHITECTURE.md), [AGENTS.md](AGENTS.md). Seluruh data sintetis.

> Status: walking skeleton. Infrastruktur, kontrak API, skema data, dan health check berjalan; logika bisnis masih STUB (HTTP 501 `NOT_IMPLEMENTED`). Rincian: [docs/SCAFFOLD_REPORT.md](docs/SCAFFOLD_REPORT.md).

## Prasyarat

- Docker Desktop (Windows: backend WSL2; macOS) atau Docker Engine + plugin Compose v2 (Linux).
- Python 3.12+ untuk launcher `scripts/dev.py` (hanya standard library).
- Opsional: Node.js 24 LTS (frontend native), Foundry (contract native). Tanpa keduanya, launcher memakai container.

## Quick Start

```
python scripts/dev.py doctor          # cek Docker, Compose v2, port, .env
python scripts/dev.py up --build      # membuat .env (secret lokal acak) lalu menjalankan semua service
```

Lalu isi `LLM_API_KEY` di `.env` dengan kunci akun Anda sendiri (Groq free tier) dan jalankan `python scripts/dev.py stop ai-service` + `start ai-service`. Tanpa kunci, AI berstatus `unconfigured`. Jangan pernah commit `.env`.

## Service dan Port

| Service | URL host | Keterangan |
| ----- | ----- | ----- |
| `issuer-console` | http://127.0.0.1:3000 | Lettrust Console (HR, Admin) |
| `partner-portal` | http://127.0.0.1:3001 | Portal Karier Mitra (Simulasi); BFF `POST /api/verify` |
| `backend` | http://127.0.0.1:8000 | API `/api/v1/*`, health `/api/v1/health`, docs `/docs` |
| `ai-service` | http://127.0.0.1:8001 | Internal `/internal/v1/*` (butuh `X-Internal-Token`) |
| `chain` | http://127.0.0.1:8545 | Anvil, chainId 31337, state persisten |
| `chain-deployer` | — | One-shot: deploy `OfferProofRegistry` bila belum ada |

Seluruh port terikat ke `127.0.0.1`.

## Akun Seed

| Akun | Email | Password |
| ----- | ----- | ----- |
| Administrator | `admin@lettrust.test` | `SEED_ADMIN_PASSWORD` di `.env` |
| HR PT Sinar Demo Sejahtera (VERIFIED, AUTHORIZED) | `hr.sinar@lettrust.test` | `SEED_HR_PASSWORD` |
| HR PT Nusantara Contoh Digital (VERIFIED, AUTHORIZED) | `hr.nusantara@lettrust.test` | `SEED_HR_PASSWORD` |
| HR PT Menunggu Verifikasi Demo (PENDING) | `hr.pending@lettrust.test` | `SEED_HR_PASSWORD` |
| HR PT Ditolak Demo (REJECTED) | `hr.rejected@lettrust.test` | `SEED_HR_PASSWORD` |
| HR Sinar belum diotorisasi | `hr2.sinar@lettrust.test` | `SEED_HR_PASSWORD` |
| Partner Portal Karier Mitra (Simulasi) | — | token = `PARTNER_TOKEN` |

Catatan: seed belum diimplementasikan (`python -m app.cli seed` masih STUB); akun di atas belum tersedia. Kredensial hanya untuk environment lokal.

## Perintah Launcher

| Perintah | Fungsi |
| ----- | ----- |
| `python scripts/dev.py doctor` | Cek Docker, Compose v2, port 3000/3001/8000/8001/8545, kelengkapan `.env` |
| `python scripts/dev.py up [--build] [--dev] [--except SVC ...]` | Jalankan service (`--dev`: bind mount + reload backend/ai-service) |
| `python scripts/dev.py down` | Hentikan service, data tetap |
| `python scripts/dev.py reset [--yes]` | Hapus volume `chain-data`, `backend-data`, `shared`, lalu up ulang |
| `python scripts/dev.py status` | `docker compose ps` + ringkasan health |
| `python scripts/dev.py logs [SVC]` | Ikuti log |
| `python scripts/dev.py seed` | Seed ulang (idempotent) |
| `python scripts/dev.py stop SVC` / `start SVC` | Hentikan/jalankan satu service (skenario kegagalan) |
| `python scripts/dev.py chain address` | Alamat contract |
| `python scripts/dev.py chain proof <proofId>` | `getProof` langsung dari contract |
| `python scripts/dev.py chain events <proofId>` | Event `ProofIssued`/`ProofRevoked` |
| `python scripts/dev.py openapi` | Ekspor `contracts/openapi.json` + regenerasi `schema.d.ts` kedua app |
| `python scripts/dev.py test [SVC]` | Unit test di container (`blockchain`, `backend`, `ai-service`, `issuer-console`, `partner-portal`) |
| `python scripts/dev.py eval <script> ...` | Jalankan `ai-eval/scripts/<script>.py` di image ai-service |
| `python scripts/dev.py lock [backend\|ai-service]` | Kunci dependency Python termasuk transitif (`pip freeze`) ke `services/<svc>/constraints.txt`; tanpa argumen = keduanya |
| `python scripts/export_abi.py` | Ekspor ABI contract ke modul registry backend |

### Mengubah dependency Python

Image backend dan ai-service dipasang dengan `-c constraints.txt` sehingga dependency transitif juga terkunci. Untuk menambah atau mengubah dependency:

1. Edit `services/<svc>/requirements.txt` atau `requirements-dev.txt` (versi exact `==`).
2. `python scripts/dev.py lock <svc>`
3. `python scripts/dev.py up --build`
4. `python scripts/dev.py test <svc>`
5. Commit `requirements*.txt` dan `constraints.txt` bersama-sama.

## Jalur Native (Cadangan)

Untuk anggota tanpa Docker (SA §15.4). Jalankan dari root repo; sesuaikan URL di environment ke `127.0.0.1`.

| Komponen | Prasyarat | Perintah |
| ----- | ----- | ----- |
| Chain | Foundry | `anvil --chain-id 31337 --state .local/anvil-state.json --state-interval 5` |
| Deploy | Foundry | `cd blockchain && forge script script/Deploy.s.sol --broadcast --rpc-url http://127.0.0.1:8545`, lalu tulis `.local/deployments/local.json` (`chainId`, `contractAddress`, `deployer`, `deployedAtBlock`, `abiSha256`) |
| Backend | Python 3.12 | lihat [services/backend/README.md](services/backend/README.md) |
| ai-service | Python 3.12, Tesseract dengan data bahasa `ind` dan `eng` | lihat [services/ai-service/README.md](services/ai-service/README.md) |
| Frontend | Node 24 LTS | `npm ci`, `npm run dev` di `apps/<app>` |

Tesseract: Debian/Ubuntu `apt install tesseract-ocr tesseract-ocr-ind tesseract-ocr-eng`; macOS `brew install tesseract tesseract-lang`; Windows installer UB-Mannheim dengan memilih bahasa Indonesian. Verifikasi dengan `tesseract --list-langs`.

## Catatan Windows

- Docker Desktop dengan backend WSL2; jalankan launcher dari PowerShell (`python scripts/dev.py ...`).
- `.gitattributes` memaksa LF untuk skrip dan Dockerfile. Bila clone lama ber-CRLF, jalankan `git add --renormalize .` setelah koordinasi.
- Bind mount `--dev` dari drive Windows (mis. `D:\`) lambat dan memakai polling (`WATCHFILES_FORCE_POLLING`); untuk performa, clone di filesystem WSL. Frontend sebaiknya native (`npm run dev`) dengan `dev.py up --except issuer-console partner-portal`.
- Di Git Bash, path container dapat dikonversi otomatis; gunakan PowerShell atau `MSYS_NO_PATHCONV=1` untuk perintah `docker` manual.

## Kontribusi

- Branch dari `main` terbaru; nama berdasarkan fungsi: `feat/issuers-api`, `fix/registry-timeout`, `docs/...`, `test/...`, `chore/...`.
- Commit: `feat:`, `fix:`, `docs:`, `test:`, `chore:`.
- PR ke `main` dengan minimal satu approval; merge commit. Template PR: `.github/pull_request_template.md`.
- Seluruh operasi git dilakukan manusia (coding agent tidak menjalankan git write).
- Jangan pernah commit `.env` atau secret apa pun.
