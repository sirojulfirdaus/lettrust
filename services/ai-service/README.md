# ai-service — Ekstraksi, OCR, Analisis Risiko (`/internal/v1`)

Owner: B (PIC 5) · Ref: SA §7, §10.8

Endpoint: I-01 `POST /internal/v1/document-extractions`, API-08 `POST /internal/v1/risk-analyses` (keduanya wajib `X-Internal-Token`), I-02 `GET /internal/v1/health`.

```
python scripts/dev.py test ai-service
docker compose run --rm --no-deps -e RUFF_CACHE_DIR=/tmp/ruff ai-service ruff check app tests
```

Native (cadangan): Python 3.12 + Tesseract dengan data `ind` dan `eng` (`tesseract --list-langs`), `pip install -r requirements-dev.txt`, `uvicorn app.main:app --port 8001`.

Status: config (guard mock), auth internal, skema, taksonomi, health COMPLETE; ekstraksi, OCR, analisis STUB (501). `LLM_PROVIDER=mock` hanya diterima bila `APP_ENV=test`.
