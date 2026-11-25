# SCAFFOLD REPORT — Walking Skeleton Lettrust

Tanggal: 21 November 2026 · Disusun oleh coding agent atas instruksi Technical Lead (Dws, PIC 1) · Acuan: `docs/SYSTEM_ARCHITECTURE.md` (SA), `docs/prd/`, `AGENTS.md`.

## 1. Ringkasan Hasil

Repository sudah memiliki walking skeleton yang dapat dijalankan dengan satu perintah (`python scripts/dev.py up --build`). Keenam service Compose (`chain`, `chain-deployer`, `backend`, `ai-service`, `issuer-console`, `partner-portal`) sehat. Contract `OfferProofRegistry` ter-deploy ke Anvil dan bertahan setelah `down`/`up`. Backend mengekspos seluruh endpoint SA §10.4 dengan skema Pydantic beku, sehingga `contracts/openapi.json` dan tipe TypeScript kedua frontend dapat dihasilkan. Seluruh logika bisnis masih STUB dan gagal secara eksplisit: HTTP 501 `NOT_IMPLEMENTED`, `NotImplementedError`, atau `revert NotImplemented()`. Tidak ada data palsu dan tidak ada keberhasilan palsu.

Seluruh gate 0–6 PASS. Gate 1 dan 4 PASS dengan catatan, dan Gate 6 dijalankan dengan port default setelah konflik port dengan project lain tidak lagi aktif (lihat §5). LLM tidak dipanggil karena API key tidak tersedia, sehingga `aiService` dilaporkan `unconfigured` dan status backend `degraded`.

## 2. Versi

| Komponen | Versi / Tag |
| ----- | ----- |
| Image Python | `python:3.12.16-slim-trixie` (Python 3.12.16, Debian 13.7) |
| Image Node | `node:24.22.3-trixie-slim` (Node 24 LTS) |
| Image Foundry | `ghcr.io/foundry-rs/foundry:v1.9.0` (forge/cast/anvil 1.9.0; v1.10.0 rilis 2 hari sebelumnya sehingga sengaja tidak dipakai) |
| Solidity | `solc 0.8.24` (`foundry.toml`) |
| forge-std | v1.17.0 (vendored, `forge install --no-git`) |
| Tesseract | `tesseract-ocr 5.5.0-1+b1`, `tesseract-ocr-ind 1:4.1.0-2`, `tesseract-ocr-eng 1:4.1.0-2` (Debian trixie) |
| Backend | fastapi 0.165.0, uvicorn 0.54.0, pydantic 2.14.4, pydantic-settings 2.16.3, email-validator 2.4.0, sqlalchemy 2.1.9, pyjwt 2.15.1, bcrypt 5.0.0, web3 8.0.0, httpx 0.28.1, python-multipart 0.0.34 (starlette 1.10.0 transitif) |
| ai-service | fastapi 0.165.0, uvicorn 0.54.0, pydantic 2.14.4, pydantic-settings 2.16.3, python-multipart 0.0.34, httpx 0.28.1, pdfplumber 0.11.10, pypdfium2 5.15.2, pytesseract 0.3.13, rapidfuzz 3.14.6, openai 3.57.0, reportlab 5.1.0, pillow 13.0.0 |
| Dev Python (keduanya) | pytest 9.2.0, ruff 0.17.6, watchfiles 1.3.0 |
| Frontend (keduanya) | create-next-app 16.4.6, next 16.4.6, react / react-dom 19.3.0, typescript 5.9.3, tailwindcss + @tailwindcss/turbopack 4.3.3, tw-animate-css 1.4.0, eslint 9.39.5, eslint-config-next 16.4.6, vitest 5.1.1, shadcn CLI 4.23.0, radix-ui 1.8.1, class-variance-authority 0.7.1, cn 0.5.2, lucide-react 1.77.0, openapi-typescript 7.13.0, @types/node 24.19.2, @types/react / @types/react-dom 19.3.0 |
| Portal saja | server-only 0.0.1 |
| Host (pemeriksaan) | Docker 29.8.0, Docker Compose v5.5.1, Python 3.13.1, Node 24.15.0, npm 11.14.1, Windows 11 + Docker Desktop (WSL2) |

Dependency langsung dipin dengan `==` di `requirements*.txt`; seluruh dependency termasuk transitif dikunci di `services/<svc>/constraints.txt` (backend 64 pin, ai-service 44 pin) sejak §9. Perubahan versi pasca-review: `certifi` 2026.10.23 → 2026.11.20 (transitif, rilis upstream 20/11; lihat §9).

## 3. Struktur Repo

```
lettrust/
├── .github/pull_request_template.md
├── AGENTS.md  README.md  compose.yaml  compose.dev.yaml  .env.example  .gitignore  .gitattributes  .editorconfig
├── apps/
│   ├── issuer-console/        Dockerfile, package.json, src/app/{login,register,onboarding/company,hr,hr/proofs,
│   │                          hr/proofs/new,hr/proofs/[proofId],admin/issuers,admin/issuers/[issuerId]},
│   │                          src/components/{console-header,placeholder-page,ui/*}, src/lib/{api/client.ts,api/schema.d.ts,session.ts,routes.ts}
│   └── partner-portal/        Dockerfile, package.json, src/app/{page,cek-offer-letter,api/verify/route.ts},
│                              src/lib/{server/config.ts,api/{schema.d.ts,types.ts},verification/{labels,guidance,reference-code,consent}.ts}
├── services/
│   ├── backend/               Dockerfile, requirements*.txt, pyproject.toml, tests/,
│   │   └── app/               main.py, cli.py, core/{config,errors,ids,security,db,logging,schemas}.py,
│   │                          modules/{auth,issuers,proofs,registry(abi/),verifications,partners,health}/
│   └── ai-service/            Dockerfile, requirements*.txt, pyproject.toml, tests/,
│       └── app/               main.py, schemas.py, core/{config,errors,logging,auth}.py,
│                              extraction/{pdf_text,ocr,service}.py, analysis/{taxonomy,prompt,provider,validator,scoring,compose}.py,
│                              routers/{health,extractions,risk_analyses}.py
├── blockchain/                Dockerfile, foundry.toml, src/OfferProofRegistry.sol, test/OfferProofRegistry.t.sol,
│                              script/Deploy.s.sol, scripts/deploy-if-needed.sh, lib/forge-std/
├── ai-eval/                   README.md, templates/README.md, dataset/manifest.csv, scripts/*.py, results/.gitkeep
├── fixtures/                   README.md, FX-01–FX-10.pdf, fixture_builder.py, test_*.py
├── contracts/                 README.md, openapi.json, examples/*.json (8 berkas)
├── scripts/                   dev.py, export_abi.py, scn/README.md
└── docs/                      prd/, SYSTEM_ARCHITECTURE.md, SCAFFOLD_REPORT.md, testing/{README.md,test-cases.md,evidence/.gitkeep},
                               evaluation/protocol.md
```

## 4. Tabel File

Status: COMPLETE = berfungsi sekarang; STUB = signature/docstring dengan kegagalan eksplisit; GEN = hasil generator (tanpa header kepemilikan); PARSIAL = artefak tersedia tetapi cakupan atau prasyarat finalisasi belum lengkap.

### Root, launcher, kontrak, dokumentasi

| Path | Owner | Status | Ref | Catatan |
| ----- | ----- | ----- | ----- | ----- |
| `.gitignore`, `.gitattributes`, `.editorconfig` | Dws (PIC 1) | COMPLETE | SA §13.3 | + file OS/editor; LF dipaksa, `*.bat/*.cmd` CRLF |
| `.env.example` | Dws | COMPLETE | SA §14.2 | Semua variabel; secret kosong (diisi dev.py); kunci Anvil #0 berlabel DEV ONLY; override port host (komentar) |
| `compose.yaml` | Dws | COMPLETE | SA §15.1 | 6 service, 3 volume, port 127.0.0.1, healthcheck, depends_on |
| `compose.dev.yaml` | Dws | COMPLETE | SA §15.3 | Bind mount + `--reload` backend/ai-service, polling |
| `scripts/dev.py` | Dws | COMPLETE | SA §15.2 | Seluruh subperintah + ekstensi `openapi` (tipe TS) + `lock` (§9) |
| `scripts/export_abi.py` | Sat (PIC 6) | COMPLETE | SA §6.4 | ABI byte-identik dengan `abiSha256` deployment |
| `scripts/scn/README.md` | Pash (PIC 4) | STUB | SA §18.3 | Daftar skrip rencana |
| `README.md` | Dws | COMPLETE | SA §15 | Seksi sesuai instruksi |
| `.github/pull_request_template.md` | Dws | COMPLETE | AGENTS §5–§8 | |
| `contracts/openapi.json` | Dws | GEN | SA §10, AD-17 | Dari `dev.py openapi`; 12 path, 422 bawaan dihapus |
| `contracts/examples/*.json` (8) | Dws | COMPLETE | SA §10.7.3–§10.7.6 | API-07 ×4, API-04, API-05, S-03, error envelope; ID/hash ditulis lengkap (contoh SA memakai `…`) |
| `contracts/README.md` | Dws | COMPLETE | SA §20.2 | Konvensi prefiks contoh |
| `docs/testing/README.md`, `test-cases.md`, `evidence/.gitkeep` | Pash | STUB | PRD §12.4–§12.5 | Seksi SCN-01…SCN-22 (+07a/07b), tanpa baris TC |
| `docs/evaluation/protocol.md` | B (PIC 5) | STUB | PRD §10.4 | Heading saja |
| `fixtures/README.md`, `FX-01.pdf`…`FX-10.pdf`, `fixture_builder.py`, `test_*.py` | B | COMPLETE | PRD §12.4.1; PLAN T5-06 | Sumber sintetis mandiri, renderer T5-05, checksum, test ekstraksi/OCR dan validasi unggahan; kategori LLM tetap target skenario, bukan hasil terukur |
| `ai-eval/README.md`, `templates/README.md` | B | COMPLETE | SA §7.9 | Dokumentasi format templat dan perintah tooling; status data/evaluasi tetap terpisah |
| `ai-eval/dataset/manifest.csv`, `ai-eval/dataset/pdf/`, `ai-eval/results/.gitkeep` | B | PARSIAL | PRD §10.4; PLAN T5-05 | 36 PDF Indonesia draf; EN, tinjauan manusia dan ID model bantu terverifikasi belum lengkap; jangan freeze atau memakai metrik test split sebagai hasil laporan |
| `ai-eval/scripts/{generate_pdfs,make_scans}.py` | B | COMPLETE | SA §7.9; PLAN T5-05 | Generator deterministik; penyelesaian tooling tidak berarti T5-05 selesai penuh |
| `ai-eval/scripts/generate_fixtures.py` | B | COMPLETE | SA §7.9; PLAN T5-06 | Entry point `dev.py eval` ke `fixtures/fixture_builder.py`; disetujui pengguna, tanpa perubahan launcher atau kontrak |
| `ai-eval/scripts/{freeze_testset,baseline,run_eval,metrics}.py` | B | STUB | SA §7.9 | Tugas evaluasi lanjutan; belum dijalankan pada test split |

### Blockchain

| Path | Owner | Status | Ref | Catatan |
| ----- | ----- | ----- | ----- | ----- |
| `blockchain/src/OfferProofRegistry.sol` | Sat | STUB | SA §6.2 | Enum/struct/registrar/mapping/event/error/constructor/modifier persis SA §6.2.1 + `error NotImplemented()`; tiga fungsi revert |
| `blockchain/test/OfferProofRegistry.t.sol` | Sat | STUB | SA §6.2.3 | Test `registrar == deployer`; 10 test wajib sebagai TODO komentar |
| `blockchain/script/Deploy.s.sol` | Sat | COMPLETE | SA §6.7 | |
| `blockchain/scripts/deploy-if-needed.sh` | Sat | COMPLETE | SA §6.7 | Tanpa jq; tulis atomik `{chainId, contractAddress, deployer, deployedAtBlock, abiSha256}` |
| `blockchain/Dockerfile`, `.dockerignore`, `foundry.toml`, `README.md` | Sat | COMPLETE | SA §6, §15.1 | `forge build` saat build image |
| `blockchain/lib/forge-std/` | — | vendored | — | v1.17.0 |
| `services/backend/app/modules/registry/abi/OfferProofRegistry.json` | Sat | GEN | SA §6.4 | Dari `export_abi.py` |

### Backend

| Path | Owner | Status | Ref | Catatan |
| ----- | ----- | ----- | ----- | ----- |
| `Dockerfile`, `.dockerignore`, `requirements.txt`, `requirements-dev.txt`, `pyproject.toml`, `README.md` | Dws | COMPLETE | SA §15.1, §12.2 | Non-root uid 10001; CMD init-db → seed --if-empty → uvicorn --workers 1 |
| `app/main.py` | Dws | COMPLETE | SA §10.1–§10.2, §16 | Factory, router, X-Request-ID, CORS, handler envelope, 422→400, `/healthz`, OpenAPI tanpa 422 |
| `app/cli.py` | Dws (init-db, export-openapi) / Zan (seed) | COMPLETE / seed STUB | SA §9.5, §10.1 | seed mencetak "belum diimplementasikan" dan exit 0 |
| `app/core/config.py` | Dws | COMPLETE | SA §14 | pydantic-settings, SecretStr, validasi saat start |
| `app/core/errors.py` | Dws | COMPLETE | SA §10.3 | Katalog + HTTP + pesan PRD §9.8 + `NOT_IMPLEMENTED` 501 |
| `app/core/schemas.py` | Dws | COMPLETE | SA §10.1–§10.2 | `ApiModel` camelCase, `ErrorCode`, `ErrorEnvelope`; izin domain `.test` |
| `app/core/ids.py` | Dws | COMPLETE | SA §6.3, §6.3.1 | Generator Crockford, proofId, referenceCode, issuerRef, normalisasi |
| `app/core/security.py` | Dws | COMPLETE | SA §8.1 | bcrypt (potong 72 byte), JWT HS256, hash token, compare constant-time |
| `app/core/db.py` | Dws | COMPLETE | SA §9.1 | SQLite WAL + FK, `init_db` |
| `app/core/logging.py` | Dws | COMPLETE | SA §17.4 | JSON ke stderr, whitelist field |
| `app/core/body_limit.py` | Dws | COMPLETE | NFR-02.01, BR-05.03; SA §10.3 | (§9) Guard body ASGI 413 + `MultiPartParser.spool_max_size` |
| `constraints.txt` | Dws | GEN | SA §12.2, AD-19 | (§9) `dev.py lock backend`, 64 pin |
| `tests/test_body_limit.py` | Dws | COMPLETE | NFR-02.01 | (§9) 5 test |
| `app/modules/*/models.py` (auth, issuers, proofs, partners, verifications) | Zan (PIC 3) | COMPLETE | SA §9.2 | Constraint CHECK/UNIQUE/FK dan index sesuai SA |
| `app/modules/auth/schemas.py`, `issuers/schemas.py`, `proofs/schemas.py` | Zan | COMPLETE | SA §10.5–§10.6 | Kontrak beku |
| `app/modules/verifications/schemas.py`, `health/schemas.py` | Dws | COMPLETE | SA §10.7.2, §17.3 | Kontrak beku |
| `app/modules/auth/{router,service,dependencies}.py` | Zan | STUB | FR-01.01–01.02 | `current_user`, `require_admin`, `require_hr` → 501 |
| `app/modules/issuers/{router,service,dependencies}.py` | Zan | STUB | FR-01.03–01.07 | `require_unaffiliated_hr`, `authorized_hr` → 501 |
| `app/modules/proofs/{router,service}.py` | Zan | STUB | FR-03, FR-04 | `read_proof_for_verification` mengembalikan `ProofVerificationRead` (proofCheck + hash registry) |
| `app/modules/registry/adapter.py` | Sat | STUB (health COMPLETE) | SA §6.4 | Protocol, dataclass, exception, `SIGNER_LOCK`, `load_abi`; `health()` + `resolve_contract_address()` lengkap |
| `app/modules/registry/{codec,mock}.py` | Sat | STUB | SA §6.3, §18.2 | Mock menolak dibuat di luar `APP_ENV=test` |
| `app/modules/verifications/{router,orchestrator,ai_client,integrity}.py` | Dws | STUB | SA §5 | Pseudo-code SA §5.6 di docstring orchestrator |
| `app/modules/partners/dependencies.py` | Dws | STUB | SA §8.2 | `partner_client` → 501 |
| `app/modules/health/{router,service}.py` | Dws | COMPLETE | SA §17.3 | database/registry/aiService paralel, tidak pernah gagal keras |
| `app/__init__.py`, `app/core/__init__.py`, `app/modules/**/__init__.py` | owner modul | sesuai modul | SA §4.2 | Header + docstring |
| `tests/conftest.py`, `test_health.py`, `test_ids.py`, `test_contract_examples.py`, `test_routes_exist.py` | Dws | COMPLETE | SA §18.1 | 74 test |

### ai-service

| Path | Owner | Status | Ref | Catatan |
| ----- | ----- | ----- | ----- | ----- |
| `Dockerfile`, `.dockerignore`, `requirements*.txt`, `pyproject.toml`, `README.md` | B | COMPLETE | SA §7.2, §15.1 | tesseract-ocr + ind + eng; non-root; `PYTHONPATH=/app` untuk skrip eval |
| `app/main.py` | B | COMPLETE | SA §7.1, §10.2 | Envelope, X-Request-ID propagasi |
| `app/core/config.py` | B | COMPLETE | SA §7.4.1, AD-16 | Menolak `LLM_PROVIDER=mock` bila `APP_ENV≠test` |
| `app/core/{errors,logging,auth}.py` | B | COMPLETE | SA §8.2, §10.3, §17.4 | `internal_caller` constant-time; `new_request_id` dipindah ke `logging.py` (§9) |
| `app/core/body_limit.py` | B | COMPLETE | NFR-02.01, BR-05.03; SA §10.3 | (§9) Guard body ASGI 413 + `MultiPartParser.spool_max_size` |
| `constraints.txt` | B | GEN | SA §12.2, AD-19 | (§9) `dev.py lock ai-service`, 44 pin |
| `tests/test_body_limit.py` | B | COMPLETE | NFR-02.01 | (§9) 5 test |
| `app/schemas.py` | B | COMPLETE | SA §7.2, §10.8 | I-01, API-08, I-02 |
| `app/analysis/taxonomy.py` | B | COMPLETE | PRD §8.4, §9.6.3 | 7 kode, label, tingkat, definisi, contoh negatif |
| `app/analysis/{prompt,provider,validator,scoring,compose}.py` | B | STUB | SA §7.3–§7.7 | `MockLLMProvider` menolak dibuat di luar test |
| `app/extraction/{pdf_text,ocr,service}.py` | B | STUB | SA §7.2 | |
| `app/routers/health.py` | B | COMPLETE | SA §7.1 | Tesseract + bahasa, llm configured/unconfigured, model |
| `app/routers/{extractions,risk_analyses}.py` | B | STUB | SA §10.8 | Token internal dicek dulu (401), lalu 501 |
| `tests/{conftest,test_health,test_taxonomy,test_config}.py` | B | COMPLETE | SA §18.1 | 9 test |

### Frontend (dibuat oleh sub-agent di bawah arahan yang sama)

| Path | Owner | Status | Ref | Catatan |
| ----- | ----- | ----- | ----- | ----- |
| `apps/issuer-console/src/app/**/page.tsx` (10 route) | Van (PIC 2) | STUB | SA §11.2.1; PRD Bab 9, FR-01/03/04 | Placeholder: judul, owner, ref, checklist state/elemen |
| `apps/issuer-console/src/app/{layout.tsx,globals.css}` | Van | COMPLETE | PRD §9.9.1, §9.9.3 | Token tema + warna status, Plus Jakarta Sans + Inter |
| `apps/issuer-console/src/components/console-header.tsx` | Van | STUB | PRD §9.11 | Badge "Data sintetis", nav HR/Admin placeholder |
| `apps/issuer-console/src/components/placeholder-page.tsx`, `src/lib/routes.ts`, `routes.test.ts` | Van | COMPLETE | SA §11.2.1 | |
| `apps/issuer-console/src/lib/api/client.ts`, `src/lib/session.ts` | Van | STUB | SA §11.2.2 | throw `NOT_IMPLEMENTED` |
| `apps/issuer-console/{Dockerfile,next.config.ts,eslint.config.mjs,vitest.config.mts,.dockerignore,README.md}` | Van | COMPLETE | SA §11.1, §15.1 | Build arg `NEXT_PUBLIC_API_BASE_URL`, standalone, non-root |
| `apps/partner-portal/src/app/{page.tsx,cek-offer-letter/page.tsx}` | Pash | STUB | FR-02.01–02.11 | "Simulasi", "Didukung Lettrust", "Data sintetis" |
| `apps/partner-portal/src/app/api/verify/route.ts` | Pash | STUB | SA §11.3.2 | 501 envelope, langkah BFF sebagai komentar, `runtime = "nodejs"` |
| `apps/partner-portal/src/lib/server/config.ts`, `config.test.ts` | Pash | COMPLETE | SA §11.3.2 | `server-only`, validasi env lazy |
| `apps/partner-portal/src/lib/api/types.ts` | Pash | COMPLETE | SA §10.7.2 | Tipe API-07 dari OpenAPI |
| `apps/partner-portal/src/lib/verification/{labels,guidance,reference-code,consent}.ts` | Pash | STUB | PRD §9.6, §9.7; SA §6.3.1; FR-02.06 | throw `NOT_IMPLEMENTED` |
| `apps/partner-portal/{Dockerfile,next.config.ts,eslint.config.mjs,vitest.config.mts,.dockerignore,README.md}` | Pash | COMPLETE | SA §15.1 | Env runtime dari Compose |
| `apps/*/src/lib/api/schema.d.ts` | — | GEN | AD-17 | `dev.py openapi` |
| `apps/*/src/components/ui/*` (11), `src/lib/utils.ts`, `components.json`, `tsconfig.json`, `.gitignore`, `favicon.ico`, `package.json`, `package-lock.json` | — | GEN | — | Hasil create-next-app/shadcn |

## 5. Hasil Gate

| Gate | Perintah | Hasil |
| ----- | ----- | ----- |
| 0 | `docker --version`, `docker compose version`, `docker info`, `python --version`, `node --version`, `forge --version` | PASS. Docker 29.8.0, Compose v5.5.1, Python 3.13.1, Node 24.15.0; forge tidak ada di host → dijalankan via image Foundry. |
| 1 | `python scripts/dev.py doctor`; `git status`; `git check-ignore -v .env` | PASS dengan catatan. `.env` dibuat (3 secret acak, nilai tidak dicetak) dan ter-ignore (`.gitignore:2`). Run pertama doctor exit 1 karena port 3000/8001 dipakai container project lain (`ets-gpt`) — perilaku doctor benar. Saat Gate 6: "Selesai: tidak ada masalah." |
| 2 | `forge build`, `forge test -vv`, `forge fmt --check` (container); `docker compose up -d --build chain chain-deployer`; `python scripts/dev.py chain address`; `dev.py down` → `up` | PASS. 1 test lulus; deploy ke `0x5fbdb2315678afecb367f032d93f642f64180aa3` (blok 1); `local.json` ada; setelah down/up deployer mencetak "Contract sudah ada … deployment dilewati" dan `cast code` tidak kosong. `forge build` memberi 3 warning mutabilitas karena fungsi masih stub (diharapkan). |
| 2 / TOI-01 | `dev.py down` (container dihapus, volume tetap) lalu `up` | PASS: state Anvil bertahan (dengan `stop_signal: SIGINT` + `--state-interval 5`). Diuji dua kali (Gate 2 dan Gate 6). |
| 3 | `docker compose up -d --build backend`; `curl /api/v1/health`; `curl -X POST /api/v1/verifications`; `dev.py openapi`; `dev.py test backend`; `ruff check`, `ruff format --check` | PASS. Health `{"status":"degraded","components":{"database":"ok","registry":"ok","aiService":"unavailable"}}` (ai-service belum jalan). Stub → 501 envelope dengan `requestId` = header `X-Request-ID`. `contracts/openapi.json` ditulis (12 path). 74 test lulus. Ruff bersih. |
| 4 | `dev.py test ai-service`; build image + `tesseract --list-langs`; `curl /internal/v1/health`; POST tanpa token | PASS. 9 test lulus. Health: `tesseract.available=true`, `version 5.5.0`, `languages ["eng","ind"]`, `missingLanguages []`, `llm "unconfigured"`. Tanpa `X-Internal-Token` → 401 `UNAUTHENTICATED`. Runtime health di Compose baru diperiksa di Gate 6 karena port 8001 sempat terpakai. |
| 4 / TOI-09 | Build `services/ai-service/Dockerfile` | PASS: paket `tesseract-ocr-ind` tersedia di Debian trixie. |
| 5 | Di host: `npm run lint`, `npm run build`, `npm test` (kedua app); build portal dengan `LETTRUST_PARTNER_TOKEN=<canary>` lalu grep `.next/static` | PASS. Lint 0 error; build sukses dengan `schema.d.ts` asli; test 2 (console) dan 4 (portal) lulus; string `LETTRUST_PARTNER_TOKEN` dan nilai canary: 0 match di `.next/static` dan `.next`. `docker build` kedua app dengan schema asli terbukti di Gate 6. |
| 6 | `python scripts/dev.py up --build` lalu `status` | PASS. Enam service sehat (deployer Exited 0). Health `degraded` hanya karena `aiService=unconfigured` (LLM_API_KEY kosong). |
| 6 | `curl 127.0.0.1:3000/login`, `127.0.0.1:3001/cek-offer-letter`, `127.0.0.1:3001/` | PASS: 200, 200, 200. |
| 6 | `curl -X POST 127.0.0.1:3001/api/verify` | PASS: 501 envelope `NOT_IMPLEMENTED` dengan `requestId` dan header `X-Request-ID`. |
| 6 | `dev.py stop ai-service` → health; `dev.py start ai-service` → health | PASS: `aiService: unavailable`, lalu kembali `unconfigured` setelah start. |
| 6 | `python scripts/dev.py test` | PASS: blockchain 1, backend 74, ai-service 9, issuer-console 2, partner-portal 4. |
| 6 | `dev.py down` lalu `dev.py up` | PASS: alamat contract sama, deployment dilewati, kode contract ada. |
| 6 | Scan nilai `JWT_SECRET`, `INTERNAL_API_TOKEN`, `PARTNER_TOKEN` di 306 berkas repo (kecuali `.git`, `node_modules`, `.next`); `git status` | PASS: 0 match di luar `.env`; `.env` tidak terdaftar oleh git. |
| TOI-02 (Apple Silicon) | — | Tidak diuji. Image yang dipakai hanya diverifikasi untuk amd64. |
| TOI-03 (body 5 MB Route Handler) | `curl -F` ke `http://127.0.0.1:3001/api/verify` dengan PDF sintetis 5.242.880 byte dan 5.242.881 byte | PASS batas unggahan: berkas tepat 5 MiB diteruskan ke API-07 dan menerima respons upstream 501 `NOT_IMPLEMENTED` (backend masih stub); berkas 1 byte di atas batas ditolak BFF dengan 413 `FILE_TOO_LARGE`. |
| TOI-10 (bind mount Windows `--dev`) | — | Tidak diuji. |

SCN-21 dapat dieksekusi pada mesin Windows dan Linux (tim memiliki keduanya); TOI-02 (Apple Silicon) tetap tidak diuji.

Semua pemeriksaan dijalankan terhadap stack nyata (Anvil nyata); tidak ada mock yang dipakai sebagai bukti. LLM tidak dipanggil.

## 6. Deviasi dari SA

| # | Deviasi | Alasan |
| ----- | ----- | ----- |
| D-01 | `dev.py openapi` juga meregenerasi `src/lib/api/schema.d.ts` kedua app via `openapi-typescript@7.13.0` di container Node. | Instruksi scaffolding; SA §15.2 hanya menyebut ekspor OpenAPI. |
| D-02 | Port host dapat dioverride via `CONSOLE_HOST_PORT`, `PORTAL_HOST_PORT`, `BACKEND_HOST_PORT`, `AI_SERVICE_HOST_PORT`, `CHAIN_HOST_PORT` (default tetap SA §15.1). | Port 3000/8001 bentrok dengan aplikasi lain di mesin anggota; port internal tidak berubah. Bila port Console/backend diubah, `CORS_ALLOWED_ORIGINS`/`NEXT_PUBLIC_API_BASE_URL` harus ikut diubah. |
| D-03 | Service `chain` berjalan sebagai `user: "0:0"` dan `stop_signal: SIGINT`. | Image Foundry berjalan sebagai uid 1000, sedangkan volume `/data` dibuat root-owned; SIGINT memastikan anvil menyimpan state saat berhenti (TOI-01). |
| D-04 | Kode error tambahan `NOT_FOUND` (404) dan `METHOD_NOT_ALLOWED` (405) untuk route tidak dikenal, serta `NOT_IMPLEMENTED` (501) sementara. | SA §10.3 tidak punya kode untuk kasus routing; envelope SA §10.2 tetap dipakai. `NOT_IMPLEMENTED` harus dihapus setelah seluruh stub terisi. |
| D-05 | Respons 422 bawaan FastAPI dihapus dari OpenAPI. | Validasi dipetakan ke 400 `VALIDATION_ERROR` (SA §10.1); 422 di kontrak menyesatkan frontend. |
| D-05a | Perubahan atas D-05: yang dihapus hanya 422 validasi bawaan FastAPI (`Validation Error`/`HTTPValidationError`); 422 bisnis dari `error_responses` (API-03 `HR_NOT_AFFILIATED`, SA §10.3) tetap di OpenAPI. | Filter D-05 sebelumnya ikut menghapus 422 bisnis sehingga kontrak dan tipe frontend kehilangan `HR_NOT_AFFILIATED`. |
| D-06 | Domain email `.test` diizinkan dengan menghapus `test` dari `email_validator.SPECIAL_USE_DOMAIN_NAMES`. | email-validator 2.4 menolak `.test`, padahal seed SA §9.5 memakai `@lettrust.test`. Berlaku untuk seluruh input email backend. **Disetujui Dws (21/11).** |
| D-07 | Password dipotong ke 72 byte sebelum bcrypt. | bcrypt 5.0 menolak input >72 byte, sedangkan SA mengizinkan password hingga 128 karakter. Pemotongan sama dengan perilaku bcrypt klasik. **Disetujui Dws (21/11).** |
| D-08 | `app/core/schemas.py` (backend) dan `app/schemas.py` (ai-service) ditambahkan. | Basis `ApiModel`/envelope bersama; SA §13.1 tidak merinci file ini. |
| D-09 | `proofs.service.read_proof_for_verification` mengembalikan `ProofVerificationRead` (proofCheck + documentHash registry), bukan hanya `ProofCheck`. | `ProofCheck` API-07 tidak memuat hash, padahal integritas (§5.3.2) membutuhkan hash dari registry. |
| D-10 | Frontend: `cacheComponents` dan `partialPrefetching` (default create-next-app 16.4) dimatikan. | `cacheComponents` menolak `export const runtime = "nodejs"` yang diwajibkan SA §11.3.2. |
| D-11 | Frontend: TypeScript 5.9.3 (bukan 7.x), `@types/node` 24, `resolve.tsconfigPaths` Vite bawaan; Vitest portal memetakan `server-only` ke modul kosong. | Kompatibilitas tooling Next/ESLint dan agar modul config server dapat diuji. |
| D-12 | shadcn 4.23 memasang paket runtime `cn` dan `shadcn`. | Komponen hasil generate mengimpor `cn` dan CSS mengimpor `shadcn/tailwind.css`. |
| D-13 | Rute test backend memeriksa endpoint lewat `app.openapi()["paths"]`. | FastAPI 0.165 menyimpan router ter-include sebagai `_IncludedRouter` (privat), bukan `APIRoute`. |
| D-14 | `MockLLMProvider` dipindah dari `app/analysis/provider.py` ke `app/analysis/mock_provider.py` (owner Dws). | Memisahkan mock milik Dws dari file provider milik B; Protocol dan provider nyata di `provider.py` tidak berubah (§10). |
| D-15 | Kepemilikan mock dipindah ke Dws: `MockRegistryAdapter` (sebelumnya Sat) dan `MockLLMProvider` (sebelumnya B). | Mock dibangun sekali oleh Dws dan dijaga jujur lewat suite conformance; provider tidak mengedit mock (`docs/MOCKS.md`). |
| D-16 | `python scripts/dev.py openapi` juga menghasilkan fixture TypeScript `apps/*/src/fixtures/api/*.ts` dari `contracts/examples/index.json` dan menulis `openapi.json` dengan LF eksplisit. | Fixture `satisfies` tipe OpenAPI untuk UI; LF agar hasil identik byte-per-byte lintas OS. |
| D-17 | `contracts/examples/index.json` menggantikan pemetaan prefiks di test backend sebagai satu-satunya pemetaan contoh → skema; contoh internal di `contracts/examples/internal/`. | Satu sumber untuk test backend, test ai-service, dan generator fixture. |
| D-18 | `pyproject.toml` backend men-deselect marker `real_registry` secara default; `tests/conftest.py` menyimpan env registry asli (`REAL_REGISTRY_ENV`) sebelum ditimpa. | Suite conformance web3 hanya jalan eksplisit terhadap Anvil nyata; `pytest` dan `dev.py test` tetap hijau. |
| D-19 | `dev.py test ai-service` juga me-mount `contracts/` (`CONTRACTS_DIR`). | Test contoh internal ai-service membaca `contracts/examples`. |
| D-20 | Request API-08 mendapat field opsional `extractionMethod` (`TEXT_LAYER`/`OCR`/`MIXED`, default `TEXT_LAYER`); backend meneruskan `method` dari I-01 dan tidak mengirim field bila `null`. Fuzzy matching kutipan hanya untuk `OCR`/`MIXED`. Request D2 tanpa field tetap valid. | SA §10.8 hanya memuat `documentContent`, padahal SA §7.5 mensyaratkan fuzzy hanya untuk OCR/MIXED; default `TEXT_LAYER` konservatif (tanpa fuzzy). **Disetujui Dws (24/11).** |
| D-21 | `explanation` API-08 memakai templat (bukan teks model) juga bila ada indikator dibuang (`droppedIndicators > 0`), lebih dari tiga kalimat, atau memuat kata vonis (`asli`, `palsu`, `aman`, `penipuan`, `authentic`, `fake`, `safe`, `scam`, `fraud`). | SA §7.7 hanya mensyaratkan tidak kosong dan ≤ 600 karakter; aturan tambahan menjaga SA §7.4.2 (hanya indikator yang ditemukan) dan larangan vonis. Explanation sah yang menyebut kata tersebut ikut diganti templat. |

## 7. Known Issues dan Keputusan untuk Manusia

1. **Selesai (lihat §9, Fix 1).** Multipart Starlette menyimpan berkas >1 MB ke `SpooledTemporaryFile` di disk (default `spool_max_size` 1 MB). Ini bertentangan dengan NFR-02.01/BR-05.03 (berkas hanya di memori). Owner API-04/API-07/I-01 (Zan, Dws, B) perlu memutuskan cara pembacaan berkas, misalnya menaikkan batas spool atau membaca stream mentah.
2. **Diputuskan:** D-06 dan D-07 disetujui Dws (21/11). D-06 dan D-07 adalah keputusan keamanan kecil di `core` yang perlu disetujui Dws.
3. Kode `NOT_IMPLEMENTED` ada di `ErrorCode` OpenAPI. Hapus setelah semua endpoint terimplementasi, lalu jalankan `dev.py openapi`.
4. **Selesai (lihat §9, Fix 2).** Dependency transitif Python tidak dikunci (hanya dependency langsung `==`). Untuk reprodusibilitas penuh, pertimbangkan `pip freeze` ke berkas constraints.
5. Warning `StarletteDeprecationWarning` dari `fastapi.testclient` (httpx → httpx2) muncul di test backend; berasal dari upstream dan tidak memengaruhi hasil.
6. `forge build` memberi 3 warning mutabilitas karena fungsi contract masih stub; hilang setelah implementasi.
7. Seed belum diimplementasikan, sehingga akun di README belum ada dan partner token belum terdaftar (API-07 akan 401 setelah `partner_client` diimplementasikan, sampai seed dibuat).
8. `requestId` buatan BFF portal memakai hex (`req_489806C1A43E4552`), bukan Crockford Base32 seperti backend. Format tetap `req_` + 16 karakter; Pash dapat menyamakan saat implementasi BFF.
9. Healthcheck aiService di backend memakai timeout 5 detik; saat service `ai-service` tidak ada di jaringan, `GET /api/v1/health` bisa memakan ~4 detik (resolusi DNS).
10. TOI-02, TOI-03, dan TOI-10 belum tervalidasi.

## 8. Perintah Penting (Quick Reference)

```
python scripts/dev.py doctor
python scripts/dev.py up --build              # atau: up --dev, up --except issuer-console partner-portal
python scripts/dev.py status | logs [svc] | down
python scripts/dev.py stop <svc> | start <svc>
python scripts/dev.py reset --yes             # menghapus data chain + DB + deployment
python scripts/dev.py test [blockchain|backend|ai-service|issuer-console|partner-portal]
python scripts/dev.py openapi                 # setelah mengubah skema backend
python scripts/export_abi.py                  # setelah mengubah antarmuka contract
python scripts/dev.py chain address | proof <proofId> | events <proofId>
python scripts/dev.py eval <script> [args]
# Port bentrok? set env sebelum up, mis. PowerShell:
#   $env:CONSOLE_HOST_PORT=3100; $env:CORS_ALLOWED_ORIGINS="http://localhost:3100"; python scripts/dev.py up
```

## 9. Perubahan Pasca-Review

Diterapkan 21/11 atas review Dws (PIC 1). Tidak ada logika bisnis yang ditambahkan dan kontrak API tidak berubah.

### Fix 1 — Berkas unggahan tidak pernah menyentuh disk (NFR-02.01, BR-05.03)

- Verifikasi source: Starlette 1.10.0 di image mendefinisikan atribut kelas `MultiPartParser.spool_max_size = 1024 * 1024` (`starlette/formparsers.py:135`) yang dipakai saat membuat `SpooledTemporaryFile(max_size=self.spool_max_size)` untuk setiap part berkas (`formparsers.py:218`).
- Backend dan ai-service: saat start, `MultiPartParser.spool_max_size` diset ke `batas transport + 1` (hanya atribut kelas tersebut, tanpa patch lain).
- Middleware ASGI murni `BodySizeLimitMiddleware` di `app/core/body_limit.py` (satu modul per service). Batas = `MAX_UPLOAD_BYTES` (config yang sudah ada) + 64 KiB margin multipart = 5.308.416 byte.
  - `Content-Length` di atas batas ditolak langsung tanpa memanggil app.
  - Body tanpa `Content-Length` dihitung saat diterima app; melewati batas → app menerima `http.disconnect`, respons app dibuang, dan middleware mengirim penolakan.
  - Penolakan: 413 `FILE_TOO_LARGE` (SA §10.3, kode yang sama di kedua service) dengan envelope SA §10.2, `requestId`, dan header `X-Request-ID`. Middleware tidak mencatat atau membuffer body.
  - Middleware dipasang di dalam middleware request-context (requestId sudah tersedia) dan berlaku untuk semua request.
- ai-service: `new_request_id` dipindah dari `app/main.py` ke `app/core/logging.py` untuk menghindari import sirkular.
- Catatan perilaku: body tanpa `Content-Length` yang tidak pernah dibaca app (mis. ditolak dependency auth lebih dulu) tidak dihitung dan tidak dibuffer; app tetap mengembalikan respons aslinya (501/401). Ini sesuai "count bytes as they are received".
- File: `services/backend/app/core/body_limit.py` (baru), `services/backend/app/main.py`, `services/backend/tests/test_body_limit.py` (baru), `services/ai-service/app/core/body_limit.py` (baru), `services/ai-service/app/main.py`, `services/ai-service/app/core/logging.py`, `services/ai-service/tests/test_body_limit.py` (baru).

### Fix 2 — Dependency transitif Python dikunci

- `services/backend/constraints.txt` (64 pin) dan `services/ai-service/constraints.txt` (44 pin) dihasilkan `pip freeze` (tanpa pip/setuptools/wheel; project sendiri tidak terpasang).
- Kedua Dockerfile memasang dengan `pip install -r requirements-dev.txt -c constraints.txt`.
- `python scripts/dev.py lock [backend|ai-service]`: build image sementara (base diambil dari `FROM` Dockerfile service, tanpa constraints) → `pip freeze` → tulis ulang `constraints.txt` (LF, urutan pip freeze) → hapus image sementara; mencetak pin yang bertambah/berkurang.
- README: baris perintah `lock` dan bagian "Mengubah dependency Python".
- File: `services/{backend,ai-service}/constraints.txt` (baru), `services/{backend,ai-service}/Dockerfile`, `scripts/dev.py`, `README.md`.

### Fix 3 — Deviasi tercatat berlaku bagi agent

- `AGENTS.md` §2: satu aturan baru bahwa deviasi yang tercatat di §6 laporan ini otoritatif dan kode tidak boleh dikembalikan ke teks SA. Tidak ada perubahan lain pada AGENTS.md, PRD, atau SA.

### Verifikasi

| Pemeriksaan | Perintah | Hasil |
| ----- | ----- | ----- |
| Seluruh unit test | `python scripts/dev.py test` | PASS: blockchain 1, backend 79 (+5), ai-service 14 (+5), issuer-console 2, partner-portal 4. Diulang untuk backend/ai-service setelah perbaikan ruff: 79 dan 14 lulus. |
| Lint Python | `ruff check app tests && ruff format --check app tests` (kedua service) | PASS. |
| Stack | `python scripts/dev.py up --build` → `status` | PASS: enam service sehat (deployer Exited 0); `GET /api/v1/health` bentuknya sama: `{"status":"degraded","components":{"database":"ok","registry":"ok","aiService":"unconfigured"}}`. |
| Guard live — Content-Length | `curl` body 5.308.417 byte ke `POST /api/v1/verifications` dan `POST /internal/v1/document-extractions` | 413 `FILE_TOO_LARGE` + `requestId` di keduanya. |
| Guard live — stream | `curl -H 'Transfer-Encoding: chunked'` body > batas ke `POST /api/v1/auth/register` | 413 `FILE_TOO_LARGE`. Body kecil ke endpoint yang sama → 501 `NOT_IMPLEMENTED`. |
| Constraints dipakai image | `pip freeze` di image baru dibanding `constraints.txt` | Identik untuk kedua service. |
| `dev.py lock` | `python scripts/dev.py lock` dua kali | Run pertama dibanding freeze image awal: satu perubahan transitif `certifi 2026.10.23 → 2026.11.20` (rilis upstream 20/11) di kedua service; dipertahankan dan diuji. Run kedua: `+0 / -0`, berkas byte-identik. Dua bug awal `lock` (CRLF di Windows, urutan sort) diperbaiki sebelum verifikasi ini. |
| Kontrak | `python -m app.cli export-openapi` dibanding `contracts/openapi.json` | Identik (tidak diubah). |
| Secret | Scan nilai `JWT_SECRET`, `INTERNAL_API_TOKEN`, `PARTNER_TOKEN` di 312 berkas (kecuali `.env`, `.git`, `node_modules`, `.next`) | 0 match; `.env` ter-ignore dan tidak muncul di `git status`. |

Tidak ada fix yang BLOCKED.

## 10. Mock dan Contoh Bersama

Dibuat 21/11 oleh agent atas instruksi Dws (PIC 1). Tidak ada logika bisnis provider yang diimplementasikan dan tidak ada skema, route, status code, atau kode error yang diubah. Panduan pemakaian: [`docs/MOCKS.md`](MOCKS.md).

### Berkas

| Path | Owner | Status | Catatan |
| ----- | ----- | ----- | ----- |
| `services/backend/app/modules/registry/mock.py` | Dws | COMPLETE | `MockRegistryAdapter` in-memory; `fail_next` (hanya exception yang mungkin dari adapter nyata), `set_unavailable`, `proofs`, `calls`, `reset`; guard `APP_ENV=test` |
| `services/backend/tests/conformance/{__init__,conftest,test_registry_conformance}.py` | Dws | COMPLETE | 10 test Protocol × {mock, web3 (`real_registry`)} + 6 test khusus mock |
| `services/backend/tests/fakes/{__init__,contracts,proofs,ai_service}.py` | Dws | COMPLETE | Akses `index.json`; fake proof reader + factory; fake ai-service `httpx.MockTransport` |
| `services/backend/tests/test_fakes.py` | Dws | COMPLETE | Test fake proof reader dan fake ai-service |
| `services/backend/tests/test_contract_examples.py` | Dws | COMPLETE (diubah) | Memakai `index.json`; setiap berkas terdaftar, sukses tiap endpoint, komponen OpenAPI, katalog error |
| `services/backend/tests/conftest.py` | Dws | COMPLETE (diubah) | `REAL_REGISTRY_ENV` |
| `services/backend/pyproject.toml` | Dws | COMPLETE (diubah) | Marker `real_registry`, deselect default |
| `services/ai-service/app/analysis/mock_provider.py` | Dws | COMPLETE | `MockLLMProvider` terjadwal + 17 `SCENARIOS` |
| `services/ai-service/app/analysis/provider.py` | B | STUB (diubah) | Hanya kelas `MockLLMProvider` dan import `get_settings` dihapus |
| `services/ai-service/tests/test_mock_provider.py`, `test_internal_examples.py` | Dws | COMPLETE | Konsistensi skenario; validasi contoh internal |
| `services/ai-service/tests/test_config.py` | B | COMPLETE (diubah) | Import `MockLLMProvider` dari modul baru |
| `contracts/examples/*.json` (73), `contracts/examples/internal/*.json` (22), `contracts/examples/index.json` | Dws | COMPLETE | Sukses semua endpoint S-01–S-07 dan API-01–API-07; 27 error publik; I-01, API-08, I-02; 11 error internal |
| `contracts/README.md`, `README.md` | Dws | COMPLETE (diubah) | Konvensi baru, generator fixture, tautan `docs/MOCKS.md` |
| `scripts/dev.py` | Dws | COMPLETE (diubah) | `openapi`: fixture TS + LF; `test`: mount `contracts/` untuk ai-service |
| `apps/issuer-console/src/fixtures/api/*.ts` (55 + `index.ts`), `apps/partner-portal/src/fixtures/api/*.ts` (26 + `index.ts`) | — | GEN | `export const … satisfies components["schemas"]["…"]` |
| `apps/issuer-console/src/lib/fixtures.test.ts`, `apps/partner-portal/src/lib/fixtures.test.ts` | Dws | COMPLETE | Sanity Vitest |
| `docs/MOCKS.md` | Dws | COMPLETE | Tabel, cara injeksi, API injeksi kegagalan, perintah conformance, Asumsi, aturan tim |

### Hasil Verifikasi

| Pemeriksaan | Hasil |
| ----- | ----- |
| `python scripts/dev.py test` | PASS. Sebelum → sesudah: blockchain 1 → 1; backend 79 → 284 (+10 deselected `real_registry`); ai-service 14 → 71; issuer-console 2 → 3; partner-portal 4 → 5. |
| Conformance mock | PASS (10 test Protocol + 6 test khusus mock). |
| Conformance nyata: `docker compose exec backend python -m pytest -m real_registry tests/conformance` | Koleksi benar (10 test web3). `test_health[web3]` PASS terhadap Anvil nyata; 9 lainnya FAIL, semuanya `NotImplementedError` (diharapkan, adapter masih stub). Run pertama tanpa path `tests/conformance` gagal di koleksi (`IndexError`) karena `docker compose exec` tidak me-mount `contracts/`; perintah resmi kini menyertakan path tersebut dan error koleksi dibuat jelas (`RuntimeError`). |
| `python scripts/dev.py openapi` | `contracts/openapi.json` byte-identik dengan sebelum task; run kedua: `schema.d.ts` dan fixture kedua app tanpa diff. Semula `openapi.json` tertulis CRLF di Windows (beda byte); diperbaiki dengan LF eksplisit. |
| Uji negatif TypeScript (salinan sementara portal di scratchpad, `node_modules` lewat junction) | Setelah `next typegen`, `tsc --noEmit` baseline exit 0. Mengganti `"mode": "AI_ONLY"` menjadi `"AI_ONLY_TYPO"` di `api07AiOnly.ts` → exit 2 dengan `error TS2322: Type '"AI_ONLY_TYPO"' is not assignable to type '"REFERENCE_CHECK" or "AI_ONLY"'`. `next build` di salinan tidak dapat dijalankan karena Turbopack menolak `node_modules` di luar workspace (junction); bukti memakai `tsc`. Salinan dihapus; `node_modules` asli utuh. |
| `npm run lint`, `npm run build`, `npm test` (kedua app) | PASS. |
| `ruff check`, `ruff format --check` (kedua service) | PASS. |
| Import mock/fake di kode produksi (`services/*/app/` selain berkas mock) | 0 kecocokan. |
| `python scripts/dev.py up --build` → `status` | Enam service sehat (deployer Exited 0); health `degraded` hanya karena `aiService=unconfigured`. |
| Secret | 0 nilai secret di 497 berkas (kecuali `.env`); `.env` ter-ignore. |
| Review internal (`/ponytail-review`) | Tiga temuan diterapkan: fake ai-service menolak mode error yang tidak mungkin per endpoint; token internal fake dibaca dari Settings; `fail_next` mock registry menolak exception yang tidak mungkin per operasi. |

### Masalah Kontrak

Tidak ada skema yang diubah. Temuan untuk diputuskan Dws:

1. SA §10.5 (S-05, API-02): contoh `reviewedBy: "USR-ADMIN001"` memuat huruf `I` dan `O` yang bukan alfabet Crockford; `VerifyIssuerResponse.reviewedBy` berpola `^USR-[0-9A-HJKMNP-TV-Z]{8}$` sehingga contoh SA tidak lolos skema. Contoh repo memakai `USR-ADM9N7Q2`. **Keputusan Dws (21/11):** skema otoritatif; contoh SA keliru/disingkat dan akan dikoreksi pada pembaruan dokumen berikutnya.
2. Contoh SA §10.6 memotong ID/hash dengan `…` (mis. `0x9f1c…e2a4`), tidak valid terhadap pola skema; contoh repo memakai nilai lengkap. **Keputusan Dws (21/11):** skema otoritatif; contoh SA keliru/disingkat dan akan dikoreksi pada pembaruan dokumen berikutnya.
3. SA §7.2: contoh respons ekstraksi OK tidak memuat `reasonDetail`, sedangkan skema ai-service selalu mengirim `reasonDetail` (null untuk OK). Contoh repo menyertakan `"reasonDetail": null`. **Keputusan Dws (21/11):** skema otoritatif; contoh SA keliru/disingkat dan akan dikoreksi pada pembaruan dokumen berikutnya.
4. `app/analysis/provider.py::get_provider` (B) berkomentar "mock hanya bila LLM_PROVIDER=mock dan APP_ENV=test", sedangkan aturan task ini melarang jalur produksi memilih mock. Rekomendasi: `get_provider` tidak mengimpor `mock_provider`; test menginjeksi `MockLLMProvider` langsung. Belum diubah (file milik B). **Keputusan Dws (21/11):** diizinkan sesuai AD-16 dengan aturan `docs/MOCKS.md` (hanya `get_provider()` saat `LLM_PROVIDER=mock` dan `APP_ENV=test`, impor `mock_provider` lazy di cabang itu); pemeriksaan import mock di kode produksi sebelumnya mengecualikan satu cabang ber-guard tersebut.
5. Backend belum punya model respons I-01/API-08 di `verifications/ai_client.py` (mengembalikan `dict`); contoh internal hanya divalidasi terhadap skema ai-service. **Keputusan Dws (21/11):** Dws menambahkan model respons I-01/API-08 di `ai_client.py` sebagai bagian tugas ai_client dan memvalidasinya terhadap `contracts/examples/internal/`.

### BLOCKED

Tidak ada.
