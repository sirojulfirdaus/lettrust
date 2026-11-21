# Owner: B (PIC 5) | Status: COMPLETE | Ref: SA §7.2, §15.1, AD-10, TOI-09
FROM python:3.12.16-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

# Tesseract OCR CPU dengan data bahasa Indonesia dan Inggris (TOI-09).
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-ind tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependency dev (pytest, ruff) ikut terpasang, dikunci constraints.txt (termasuk transitif), agar `dev.py test ai-service` berjalan di container.
COPY requirements.txt requirements-dev.txt constraints.txt ./
RUN pip install --root-user-action=ignore -r requirements-dev.txt -c constraints.txt

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home app

COPY --chown=app:app pyproject.toml ./
COPY --chown=app:app app ./app
COPY --chown=app:app tests ./tests

USER app
EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1", "--no-access-log"]
