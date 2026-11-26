# Portal Karier Mitra — Simulasi (`apps/partner-portal`)

Owner: Pash (PIC 4). Portal job simulasi untuk pelamar tanpa akun, dengan route server (BFF) `/api/verify` sebagai satu-satunya client API-07 (PRD FR-02; SA §11.3).

Status: halaman pemeriksaan, route server `POST /api/verify` (meneruskan ke API-07), modul `src/lib/verification/*`, dan `src/lib/server/config.ts` sudah diimplementasikan.

## Konfigurasi server (tanpa prefiks `NEXT_PUBLIC_`)

| Variabel | Keterangan |
| --- | --- |
| `LETTRUST_API_BASE_URL` | URL backend, mis. `http://localhost:8000` (native) atau `http://backend:8000` (Compose) |
| `LETTRUST_PARTNER_TOKEN` | Token partner (= `PARTNER_TOKEN` di `.env` root); hanya dibaca di server |
| `PORTAL_UPSTREAM_TIMEOUT_MS` | Default `120000` |

Token partner tidak boleh muncul di bundle browser, respons, atau log.

## Menjalankan secara native

```bash
npm ci
npm run gen:api   # menghasilkan src/lib/api/schema.d.ts dari ../../contracts/openapi.json (jangan diedit manual)
npm run dev       # http://localhost:3000; gunakan `npm run dev -- -p 3001` agar sesuai port Compose
```

Jalankan service lain lewat Docker: `python scripts/dev.py up --except partner-portal` (dari root repo).

## Pemeriksaan

```bash
npm run lint
npm test          # Vitest
npm run build
```

Komponen `src/components/ui/*` dihasilkan oleh shadcn/ui CLI dan dibiarkan dalam bentuk hasil generate.
