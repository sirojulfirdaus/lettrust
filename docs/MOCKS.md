# Mock, Fake, dan Contoh Bersama

Owner: Dws (PIC 1) · Status: COMPLETE · Ref: SA §5, §6.2–§6.4, §7, §10, §18; PRD §8.4, FR-02–FR-06

## Aturan Tim

1. Kode produksi selalu memanggil antarmuka nyata. Selama provider belum selesai, panggilan itu tetap gagal secara eksplisit (501 / `NotImplementedError`). Konsumen membuktikan kodenya dengan unit test yang menginjeksi mock/fake di bawah ini; setelah provider merge, kode konsumen bekerja tanpa ditulis ulang.
2. Mock tidak pernah menjadi default atau fallback. Satu-satunya pemilihan mock yang sah adalah `get_provider()` di ai-service ketika `LLM_PROVIDER=mock` DAN `APP_ENV=test` (SA AD-16), dengan `mock_provider` diimpor secara lazy di dalam cabang itu. `MockRegistryAdapter` hanya dipilih oleh test. Mock di sisi `app/` menolak dibuat kecuali `APP_ENV=test`; fake khusus test berada di `tests/`.
3. Hanya Dws yang mengubah mock, fake, dan contoh. Bila mock tampak salah, provider melapor ke Dws, tidak mengedit sendiri.
4. Provider wajib lulus suite conformance dengan implementasi nyata sebelum menyatakan modulnya siap integrasi.
5. Mock harus jujur: perilakunya mengikuti SA. Suite conformance dijalankan terhadap mock sekarang dan terhadap implementasi nyata nanti.

## Ringkasan

| Set | Path | Antarmuka yang ditiru | Provider | Konsumen |
| ----- | ----- | ----- | ----- | ----- |
| MockRegistryAdapter | `services/backend/app/modules/registry/mock.py` | `RegistryAdapter` (SA §6.4) | Sat (PIC 6) | Zan (proofs), Dws (verifications) |
| Conformance registry | `services/backend/tests/conformance/` | `RegistryAdapter` | Sat | — |
| Fake proof reader | `services/backend/tests/fakes/proofs.py` | `proofs.service.read_proof_for_verification` → `ProofVerificationRead` | Zan | Dws (orchestrator) |
| Fake ai-service HTTP | `services/backend/tests/fakes/ai_service.py` | I-01, API-08, I-02 (SA §10.8) | B (PIC 5) | Dws (`verifications/ai_client.py`) |
| MockLLMProvider + skenario | `services/ai-service/app/analysis/mock_provider.py` | `LLMProvider` (SA §7.4.1) | B | B (pipeline analisis, evaluasi) |
| Contoh kontrak publik | `contracts/examples/*.json` | API S-01…S-07, API-01…API-07, error envelope | Zan, Dws | Van (PIC 2), Pash (PIC 4) |
| Contoh internal | `contracts/examples/internal/*.json` | I-01, API-08, I-02, error ai-service | B | Dws |
| Fixture TypeScript | `apps/*/src/fixtures/api/` (generated) | Tipe OpenAPI (`components["schemas"][…]`) | — | Van, Pash |

## MockRegistryAdapter

Registry in-memory: satu transaksi per blok (auto-mine Anvil), `tx_hash` berformat `0x` + 64 hex (deterministik), `block_timestamp` dari clock yang dapat diinjeksi. Revert contract dipetakan seperti adapter nyata (SA §6.4): `InvalidInput`, `ProofAlreadyExists`, dan `ProofNotFound` menjadi `RegistryTransactionFailed(revert_name)`; `ProofNotActive` menjadi `ProofNotActiveOnChain`; `IssuerMismatch` menjadi `IssuerMismatchOnChain`. `get_proof` bukti tidak ada mengembalikan `exists=False` dengan nilai nol. `health()` tidak pernah raise.

```python
from app.modules.registry.adapter import RegistryTransactionPending, RegistryUnavailable
from app.modules.registry.mock import MockRegistryAdapter

registry = MockRegistryAdapter(clock=lambda: 1_790_000_000, start_block=12)
registry.fail_next("get_proof", RegistryUnavailable("timeout"))          # satu panggilan berikut gagal
registry.fail_next("issue_proof", RegistryTransactionPending(), commit=True)  # tercatat di chain, receipt timeout
registry.set_unavailable(True)                                            # semua RPC gagal, health False
registry.proofs, registry.calls, registry.reset()                         # inspeksi (bukan bagian Protocol)
```

Injeksi ke kode proofs: berikan instance mock di tempat `get_registry_adapter()` dipakai, misalnya `monkeypatch.setattr("app.modules.proofs.service.get_registry_adapter", lambda: registry)` bila service memanggil fungsi itu melalui atribut modul, atau `app.dependency_overrides[get_registry_adapter] = lambda: registry` bila disuntik sebagai dependency FastAPI.

Failure-injection API: `fail_next(operation, error, commit=False)` dengan `operation` ∈ `issue_proof`, `revoke_proof`, `get_proof`, `find_issue_tx`, `find_revoke_tx`, `health`, `is_transaction_failed_or_dropped`, `is_issue_failed_or_dropped`; `set_unavailable(flag, error=None)`. Hanya exception yang memang dapat dihasilkan adapter nyata yang diterima (`ALLOWED_FAILURES`): operasi baca dan `health` hanya `RegistryUnavailable`; `issue_proof` juga `RegistryTransactionFailed`/`RegistryTransactionPending`; `revoke_proof` juga `ProofNotActiveOnChain`/`IssuerMismatchOnChain`. Kombinasi lain → `ValueError`. Timeout RPC dinyatakan sebagai `RegistryUnavailable` (sama seperti adapter nyata); receipt timeout sebagai `RegistryTransactionPending`. Antrean node: `RegistryTransactionPending` tanpa commit berarti transaksi masih di antrean (pelacakan mengembalikan False/belum pasti); `drop_pending(proof_id=None)` mensimulasikan transaksi hilang dari node, dan transaksi yang berhasil ditambang untuk proofId dan operasi yang sama mengosongkan entrinya (D-28).

## Conformance Registry (untuk Sat)

Suite di `tests/conformance/test_registry_conformance.py` hanya memakai Protocol dan diparametrisasi atas `mock` dan `web3`. Varian `web3` bermarker `real_registry` dan di-deselect secara default (`pyproject.toml`), sehingga `pytest` dan `python scripts/dev.py test` tetap hijau. Test injeksi kegagalan hanya untuk mock.

Perintah provider (stack hidup, setelah `python scripts/dev.py up --build`):

```
docker compose exec backend python -m pytest -m real_registry tests/conformance
```

Path `tests/conformance` wajib: `docker compose exec` tidak me-mount `contracts/`, sehingga test contoh kontrak di luar folder itu tidak dapat dikoleksi di container yang berjalan.

Varian `web3` memakai env registry asli container (disimpan `tests/conftest.py` sebelum ditimpa nilai test) dan proofId acak baru setiap run karena state Anvil persisten.

## Fake Proof Reader (untuk Dws, provider Zan)

Factory: `found_active()`, `found_revoked()`, `found_issuer_not_verified()`, `not_found()`, `registry_unavailable()`, `not_requested()`. Nilainya sama dengan `proofCheck` di contoh API-07. `REGISTRY_DOCUMENT_HASH` = SHA-256 dari `MATCHING_FILE_BYTES`; `MISMATCHING_FILE_BYTES` menghasilkan MISMATCH.

```python
from fakes.proofs import FakeProofReader, found_active, install_fake_proof_reader

reader = install_fake_proof_reader(monkeypatch, FakeProofReader({"LTR-7K3M-9QX2-H4TD": found_active()}))
# ... jalankan orkestrator ...
assert reader.calls == []          # mis. mode AI_ONLY tidak boleh memanggil registry
```

Syarat: orkestrator memanggil `proofs_service.read_proof_for_verification(code)` melalui atribut modul `app.modules.proofs.service` (sesuai pseudo-code SA §5.6), bukan `from … import read_proof_for_verification`.

## Fake ai-service HTTP (untuk Dws, provider B)

```python
import httpx
from fakes.ai_service import FakeAiService, assert_internal_headers

fake = FakeAiService(extraction="ok", analysis="quota_exceeded")
async with httpx.AsyncClient(base_url=settings.ai_service_url, transport=fake.transport()) as client:
    ...
assert_internal_headers(fake.requests[0], request_id="req_…")
```

Mode sukses: I-01 `ok`, `ok_truncated`, `no_content`, `unreadable`; API-08 `high`, `medium`, `low`; I-02 `ok`, `unconfigured`, `ocr_missing_language`. Mode error per endpoint (hanya yang dapat dikembalikan ai-service nyata, SA §10.3; mode lain → `ValueError`): I-01 `validation_error` (400), `unauthorized` (401), `server_error` (500), `file_too_large` (413), `unsupported_media_type` (415), `empty_file` (400); API-08 `validation_error`, `unauthorized`, `server_error`, `quota_exceeded` (503), `provider_error` (503), `unconfigured` (503), `output_invalid` (502), `provider_timeout` (504); I-02 tidak pernah error HTTP (hanya kegagalan transport). Kegagalan transport: `timeout` (`httpx.ReadTimeout`), `unavailable` (`httpx.ConnectError`). Fake menolak token internal salah dengan 401 seperti aslinya dan memantulkan `X-Request-ID`.

## MockLLMProvider (untuk B)

```python
from app.analysis.mock_provider import SCENARIOS, MockLLMProvider
from app.analysis.provider import ProviderTimeout

provider = MockLLMProvider('{"indicators": [], "explanation": "…"}', ProviderTimeout("timeout"))
scenario = SCENARIOS["quote_not_in_document"]
provider = scenario.provider()          # respons terjadwal skenario
provider.received                       # salinan pesan yang diterima (tidak di-log)
```

Skenario: `high_payment_and_contact`, `all_severities` (HIGH+MEDIUM+LOW), `medium_only`, `two_distinct_low`, `single_low`, `no_indicators`, `company_paid_costs_not_payment`, `quote_not_in_document`, `unknown_indicator_code`, `prompt_injection`, `malformed_json_twice`, `schema_invalid_twice`, `malformed_then_valid`, `rate_limited`, `timeout`, `provider_unavailable`, `unconfigured`. Setiap skenario memuat `document_text`, `responses`, dan hasil yang diharapkan menurut SA/PRD (`expected_codes`, `expected_category`, `expected_error`, `expected_dropped`).

## Contoh Kontrak dan Fixture Frontend

`contracts/examples/index.json` adalah satu-satunya pemetaan contoh → skema (nama komponen OpenAPI = kelas Pydantic). Pemetaan ini dipakai `services/backend/tests/test_contract_examples.py`, `services/ai-service/tests/test_internal_examples.py`, dan generator fixture di `python scripts/dev.py openapi`. Entri berisi `file`, `schema`, `apps` (fixture frontend), `service` (`ai-service` untuk contoh internal), dan `httpStatus` (contoh error).

Fixture frontend dihasilkan ke `apps/issuer-console/src/fixtures/api/` dan `apps/partner-portal/src/fixtures/api/`, satu berkas per contoh plus `index.ts`:

```ts
import { api07AiOnly, errorFileTooLarge } from "@/fixtures/api";
```

Setiap fixture ditulis `export const x = {…} satisfies components["schemas"]["…"]`, sehingga `next build`/`tsc` gagal bila contoh menyimpang dari tipe OpenAPI. Jangan mengedit fixture; ubah contoh lalu jalankan `python scripts/dev.py openapi`.

## Asumsi

1. Input berformat salah (proofId bukan `0x`+64 hex, documentHash/issuerRef bukan 64 hex) di MockRegistryAdapter menghasilkan `ValueError` sebelum "transaksi", seperti codec yang memvalidasi panjang (SA §6.3). Conformance suite tidak menguji kasus ini terhadap adapter nyata karena SA tidak menetapkannya.
2. Revert `InvalidInput`, `ProofAlreadyExists`, dan `ProofNotFound` dipetakan ke `RegistryTransactionFailed` dengan `revert_name` berisi nama custom error, karena SA §6.4 hanya memetakan khusus `ProofNotActive` dan `IssuerMismatch`.
3. Urutan pemeriksaan revoke di mock mengikuti urutan revert SA §6.2.2: `ProofNotFound` → `ProofNotActive` → `IssuerMismatch`.
4. `issuedAt`/`revokedAt` on-chain sama dengan `block_timestamp` transaksi (Anvil auto-mine satu transaksi per blok).
5. `health()` mock mengembalikan False (tidak raise) saat diinjeksi gagal, seperti `Web3RegistryAdapter.health()`.
6. Skenario LLM `malformed_*`/`schema_invalid_*` berisi dua respons karena SA §7.3 menetapkan satu kali retry untuk output tidak valid; kegagalan provider (429, timeout, error) berisi satu respons karena tidak di-retry (SA §7.4.1).
7. Kategori yang diharapkan di skenario LLM dihitung dari aturan PRD §8.5 atas kode yang lolos validasi kutipan sederhana (NFKC, lowercase, whitespace tunggal, substring).
8. Fake ai-service memvalidasi bentuk body secara minimal (I-01 multipart, API-08 `documentContent` string non-kosong) lalu mengembalikan contoh internal; batas ukuran/halaman dan isi analisis tidak disimulasikan.
9. `FakeProofReader` default mengembalikan NOT_FOUND untuk kode yang tidak didaftarkan, sama seperti kode yang tidak ada di pemetaan (SA §5.3.1).
