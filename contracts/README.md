# Kontrak API

Owner: Dws (PIC 1) · Ref: SA §10, §20.2, AD-17

| Berkas | Isi |
| ----- | ----- |
| `openapi.json` | OpenAPI dihasilkan backend (`python scripts/dev.py openapi`). Jangan diedit manual. |
| `examples/*.json` | Contoh request/respons publik dan error envelope untuk frontend dan test (bukan untuk demo). |
| `examples/internal/*.json` | Contoh I-01, API-08, I-02, dan error envelope ai-service (internal backend ↔ ai-service). |
| `examples/index.json` | Satu-satunya pemetaan contoh → skema. |

Konvensi nama contoh: `<id>.<varian>.json`, dengan `<id>` salah satu dari `s-01`…`s-07`, `api-01`…`api-07`, atau `error`. Contoh internal memakai `internal/i-01.`, `internal/api-08.`, `internal/i-02.`, dan `internal/error.`.

`index.json` berisi entri `{file, schema, apps?, service?, httpStatus?}`:
- `schema` adalah nama komponen OpenAPI, sama dengan nama kelas Pydantic.
- `apps` menentukan app frontend mana yang mendapat fixture TypeScript.
- `service: "ai-service"` menandai contoh internal.
- `httpStatus` hanya ada di contoh error.

Setiap berkas contoh wajib terdaftar di `index.json`. Test berikut memvalidasinya:
- `services/backend/tests/test_contract_examples.py`: contoh publik terhadap skema backend dan komponen OpenAPI, serta pesan dan status error terhadap katalog.
- `services/ai-service/tests/test_internal_examples.py`: contoh internal terhadap skema ai-service.

`python scripts/dev.py openapi` melakukan tiga hal:
1. Meregenerasi `openapi.json` (LF).
2. Meregenerasi `apps/*/src/lib/api/schema.d.ts`.
3. Menghasilkan fixture `apps/*/src/fixtures/api/*.ts` (`export const … satisfies components["schemas"]["…"]`) dari `index.json`. Fixture tidak boleh diedit manual.

Perubahan kontrak hanya melalui Dws:
1. Ubah skema Pydantic.
2. Jalankan `python scripts/dev.py openapi`.
3. Perbarui contoh dan `index.json` bila terdampak.
4. Jalankan test.
5. Beri tahu PIC frontend.

Field D2 tidak boleh diubah nama atau dihapus; perubahan D3 hanya aditif. Lihat juga [`docs/MOCKS.md`](../docs/MOCKS.md).
