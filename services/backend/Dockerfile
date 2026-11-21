# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: SA §15.1, §12.2
FROM python:3.12.16-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependency dev (pytest, ruff) ikut terpasang, dikunci constraints.txt (termasuk transitif), agar `dev.py test backend` berjalan di container.
COPY requirements.txt requirements-dev.txt constraints.txt ./
RUN pip install --root-user-action=ignore -r requirements-dev.txt -c constraints.txt

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home app \
    && mkdir -p /data /shared \
    && chown app:app /data

COPY --chown=app:app pyproject.toml ./
COPY --chown=app:app app ./app
COPY --chown=app:app tests ./tests

USER app
EXPOSE 8000

CMD ["sh", "-c", "python -m app.cli init-db && python -m app.cli seed --if-empty && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --no-access-log"]
