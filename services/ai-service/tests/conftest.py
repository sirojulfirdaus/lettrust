# Owner: B (PIC 5) | Status: COMPLETE | Ref: SA §18.1, §18.2
"""Fixture pytest ai-service: environment test tanpa API key LLM."""

import os
from collections.abc import Iterator

import pytest

INTERNAL_TOKEN = "test-internal-token-value"
os.environ.update(
    {
        "APP_ENV": "test",
        "LOG_LEVEL": "WARNING",
        "INTERNAL_API_TOKEN": INTERNAL_TOKEN,
        "LLM_PROVIDER": "openai_compatible",
        "LLM_API_KEY": "",
        "LLM_MODEL": "openai/gpt-oss-120b",
    }
)

from fastapi.testclient import TestClient  # noqa: E402

from app.main import create_app  # noqa: E402


# Klien HTTP untuk aplikasi ai-service.
@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client
