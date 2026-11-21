# Owner: B (PIC 5) | Status: COMPLETE | Ref: SA §7.4.1, §14.2, AD-16; PRD FR-05.13
"""Konfigurasi ai-service dari environment; menolak start dengan LLM mock di luar APP_ENV=test."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Seluruh variabel ai-service SA §14.2; LLM_API_KEY kosong berarti LLM `unconfigured`."""

    model_config = SettingsConfigDict(env_file=None, case_sensitive=False, extra="ignore")

    app_env: Literal["local", "test"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    max_upload_bytes: int = Field(default=5_242_880, ge=1)
    internal_api_token: SecretStr = Field(min_length=16)

    llm_provider: Literal["openai_compatible", "mock"] = "openai_compatible"
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_api_key: SecretStr = SecretStr("")
    llm_model: str = Field(default="openai/gpt-oss-120b", min_length=1)
    llm_reasoning_effort: Literal["", "low", "medium", "high"] = ""
    llm_request_timeout_seconds: float = Field(default=40, gt=0)
    llm_max_output_tokens: int = Field(default=900, ge=1)
    prompt_version: str = Field(default="v1", min_length=1)

    ai_max_pages: int = Field(default=5, ge=1)
    ai_max_chars: int = Field(default=12_000, ge=1)
    ocr_min_chars_per_page: int = Field(default=25, ge=0)
    ocr_dpi: int = Field(default=300, ge=72)
    ocr_page_timeout_seconds: float = Field(default=20, gt=0)
    evidence_fuzzy_threshold: int = Field(default=90, ge=0, le=100)

    # Guard AD-16: provider mock hanya boleh aktif pada konfigurasi test eksplisit.
    @model_validator(mode="after")
    def _reject_mock_outside_test(self) -> "Settings":
        if self.llm_provider == "mock" and self.app_env != "test":
            raise ValueError("LLM_PROVIDER=mock hanya diizinkan bila APP_ENV=test")
        return self

    # True bila provider nyata dan API key tersedia.
    @property
    def llm_configured(self) -> bool:
        return self.llm_provider == "openai_compatible" and bool(self.llm_api_key.get_secret_value())


# Mengembalikan Settings tunggal per proses; gagal cepat bila konfigurasi tidak valid.
@lru_cache
def get_settings() -> Settings:
    return Settings()
