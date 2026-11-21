# backend — Lettrust API (`/api/v1`)

Owner: Dws (core, main, verifications, partners, health), Zan (auth, issuers, proofs, models, seed), Sat (registry) · Ref: SA §4, §5, §8–§10

Modular monolith FastAPI, SQLite (WAL), web3.py. Satu-satunya penulis registry dan pemanggil ai-service.

```
python scripts/dev.py test backend            # pytest di container (contracts/ ter-mount)
python scripts/dev.py openapi                 # contracts/openapi.json + tipe frontend
docker compose run --rm --no-deps -e RUFF_CACHE_DIR=/tmp/ruff backend ruff check app tests
```

Native (cadangan): Python 3.12, `python -m venv .venv`, `pip install -r requirements-dev.txt`, set env dari `.env` (sesuaikan `DATABASE_URL`, `REGISTRY_RPC_URL=http://127.0.0.1:8545`, `REGISTRY_DEPLOYMENT_FILE=../../.local/deployments/local.json`, `AI_SERVICE_URL=http://127.0.0.1:8001`), lalu `python -m app.cli init-db && uvicorn app.main:app --port 8000`.

Status: core, skema, model, health COMPLETE; seluruh endpoint bisnis STUB (501 `NOT_IMPLEMENTED`).
