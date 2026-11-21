# Lettrust Console (`apps/issuer-console`)

Owner: Van (PIC 2). Console untuk HR penerbit dan Administrator (PRD FR-01, FR-03, FR-04; SA §11.2).

Status: kerangka (walking skeleton). Seluruh halaman masih placeholder berisi daftar periksa implementasi; `src/lib/api/client.ts` dan `src/lib/session.ts` masih stub yang melempar `NOT_IMPLEMENTED`.

## Menjalankan secara native

```bash
npm ci
npm run gen:api   # menghasilkan src/lib/api/schema.d.ts dari ../../contracts/openapi.json (jangan diedit manual)
npm run dev       # http://localhost:3000
```

Jalankan backend lewat Docker tanpa service ini: `python scripts/dev.py up --except issuer-console` (dari root repo).

`NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`) dibaca saat build.

## Pemeriksaan

```bash
npm run lint
npm test          # Vitest (logika non-visual)
npm run build
```

Komponen `src/components/ui/*` dihasilkan oleh shadcn/ui CLI dan dibiarkan dalam bentuk hasil generate.
