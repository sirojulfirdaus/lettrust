# Owner: B (PIC 5) | Status: COMPLETE | Ref: SA §7.4.1, AD-16; PRD FR-05.13
"""Test guard konfigurasi: LLM mock hanya diizinkan saat APP_ENV=test."""

import pytest
from pydantic import ValidationError

from app.analysis.mock_provider import MockLLMProvider
from app.core.config import Settings

BASE = {"internal_api_token": "test-internal-token-value"}


# LLM_PROVIDER=mock dengan APP_ENV=local ditolak saat start.
def test_mock_rejected_outside_test():
    with pytest.raises(ValidationError, match="LLM_PROVIDER=mock"):
        Settings(app_env="local", llm_provider="mock", **BASE)


# LLM_PROVIDER=mock diizinkan saat APP_ENV=test, tetapi tidak dianggap LLM terkonfigurasi.
def test_mock_allowed_in_test():
    settings = Settings(app_env="test", llm_provider="mock", **BASE)
    assert settings.llm_provider == "mock"
    assert settings.llm_configured is False


# Provider nyata tanpa API key → unconfigured; dengan API key → configured.
def test_llm_configured_flag():
    assert Settings(app_env="local", llm_api_key="", **BASE).llm_configured is False
    assert Settings(app_env="local", llm_api_key="dummy-key", **BASE).llm_configured is True


# MockLLMProvider menolak dibuat di luar APP_ENV=test.
def test_mock_provider_guard(monkeypatch):
    monkeypatch.setattr("app.analysis.mock_provider.get_settings", lambda: Settings(app_env="local", **BASE))
    with pytest.raises(RuntimeError, match="APP_ENV=test"):
        MockLLMProvider("{}")
