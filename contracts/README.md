# Kontrak API

Owner: Dws (PIC 1) · Ref: SA §10, §20.2, AD-17

| Berkas | Isi |
| ----- | ----- |
| `openapi.json` | OpenAPI dihasilkan backend (`python scripts/dev.py openapi`). Jangan diedit manual. |
| `examples/*.json` | Contoh respons kontrak untuk frontend (bukan untuk demo). |

Konvensi nama contoh: `<prefiks>.<varian>.json` dengan prefiks `api-04.`, `api-05.`, `api-07.`, `s-03.`, `error.`. Setiap contoh divalidasi `services/backend/tests/test_contract_examples.py`; contoh dengan prefiks baru harus didaftarkan di test tersebut.

Perubahan kontrak hanya melalui Dws: ubah skema Pydantic → `python scripts/dev.py openapi` (juga meregenerasi `apps/*/src/lib/api/schema.d.ts`) → perbarui contoh bila terdampak → beri tahu PIC frontend. Field D2 tidak boleh diubah nama atau dihapus; perubahan D3 hanya aditif.
