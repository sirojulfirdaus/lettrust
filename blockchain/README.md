# blockchain — OfferProofRegistry

Owner: Sat (PIC 6) · Ref: SA §6

| Path | Status | Isi |
| ----- | ----- | ----- |
| `src/OfferProofRegistry.sol` | STUB | Antarmuka SA §6.2.1 lengkap; `issueProof`/`revokeProof`/`getProof` revert `NotImplemented()` |
| `test/OfferProofRegistry.t.sol` | STUB | Test `registrar == deployer`; daftar 10 test wajib SA §6.2.3 sebagai TODO |
| `script/Deploy.s.sol` | COMPLETE | Deploy dengan `REGISTRY_SIGNER_PRIVATE_KEY` |
| `scripts/deploy-if-needed.sh` | COMPLETE | Deploy hanya bila `/shared/deployments/local.json` belum ada atau alamatnya tanpa kode |
| `lib/forge-std` | vendored | forge-std v1.17.0 (`forge install --no-git`) |

Perintah (tanpa Foundry di host):

```
python scripts/dev.py test blockchain        # forge test di image chain-deployer
python scripts/export_abi.py                  # ABI → services/backend/app/modules/registry/abi/
python scripts/dev.py chain address | proof <proofId> | events <proofId>
```

Dengan Foundry native: `forge build`, `forge test -vv`, `forge fmt`.
Setelah mengubah antarmuka contract, jalankan `python scripts/export_abi.py` dan bangun ulang image (`dev.py up --build`).
