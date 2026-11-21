# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: SA §18.1, §18.2
"""Fixture pytest backend: environment test terisolasi (APP_ENV=test, DB sementara, upstream tak terjangkau)."""

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

_TMP_DIR = Path(tempfile.mkdtemp(prefix="lettrust-test-"))
# Konfigurasi registry asli container (sebelum ditimpa) untuk suite conformance `-m real_registry` (Anvil nyata).
REAL_REGISTRY_ENV = {
    key: os.environ.get(key, "")
    for key in (
        "REGISTRY_RPC_URL",
        "REGISTRY_DEPLOYMENT_FILE",
        "REGISTRY_CONTRACT_ADDRESS",
        "REGISTRY_SIGNER_PRIVATE_KEY",
    )
}
# Nilai test non-rahasia; upstream sengaja diarahkan ke port tertutup agar unit test tidak bergantung stack.
os.environ.update(
    {
        "APP_ENV": "test",
        "LOG_LEVEL": "WARNING",
        "DATABASE_URL": f"sqlite:///{(_TMP_DIR / 'test.db').as_posix()}",
        "JWT_SECRET": "test-jwt-secret-value-with-at-least-32-chars",
        "INTERNAL_API_TOKEN": "test-internal-token-value",
        "PARTNER_TOKEN": "test-partner-token-value",
        "REGISTRY_SIGNER_PRIVATE_KEY": "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
        "REGISTRY_RPC_URL": "http://127.0.0.1:9",
        "REGISTRY_DEPLOYMENT_FILE": str(_TMP_DIR / "missing-deployment.json"),
        "REGISTRY_CONTRACT_ADDRESS": "",
        "REGISTRY_RPC_TIMEOUT_SECONDS": "1",
        "AI_SERVICE_URL": "http://127.0.0.1:9",
        "SEED_ADMIN_PASSWORD": "Admin#Test2026",
        "SEED_HR_PASSWORD": "Hr#Test2026",
    }
)

from fastapi.testclient import TestClient  # noqa: E402

from app.core.db import init_db  # noqa: E402
from app.main import create_app  # noqa: E402


# Klien HTTP untuk aplikasi dengan tabel yang sudah dibuat.
@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    init_db()
    with TestClient(create_app()) as test_client:
        yield test_client
