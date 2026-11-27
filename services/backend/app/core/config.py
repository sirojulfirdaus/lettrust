# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: SA §14.1, §14.2
"""Konfigurasi backend dari environment, divalidasi saat start (pydantic-settings)."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Seluruh variabel backend SA §14.2; variabel wajib yang hilang menghentikan start."""

    model_config = SettingsConfigDict(env_file=None, case_sensitive=False, extra="ignore")

    app_env: Literal["local", "test"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    database_url: str = "sqlite:////data/lettrust.db"
    jwt_secret: SecretStr = Field(min_length=32)
    jwt_expires_minutes: int = Field(default=480, ge=1, le=1440)
    cors_allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    max_upload_bytes: int = Field(default=5_242_880, ge=1)

    registry_rpc_url: str = "http://chain:8545"
    registry_deployment_file: str = "/shared/deployments/local.json"
    registry_contract_address: str = Field(default="", pattern=r"^(0x[0-9a-fA-F]{40})?$")
    registry_signer_private_key: SecretStr
    registry_rpc_timeout_seconds: float = Field(default=5, gt=0)
    registry_tx_receipt_timeout_seconds: float = Field(default=20, gt=0)

    ai_service_url: str = "http://ai-service:8001"
    internal_api_token: SecretStr = Field(min_length=16)
    ai_extraction_timeout_seconds: float = Field(default=60, gt=0)
    ai_analysis_timeout_seconds: float = Field(default=50, gt=0)

    partner_token: SecretStr = Field(min_length=16)
    partner_rate_limit_per_minute: int = Field(default=60, ge=1)
    seed_admin_password: SecretStr = Field(min_length=8)
    seed_hr_password: SecretStr = Field(min_length=8)

    # Memastikan kunci signer berformat 0x + 64 hex tanpa pernah menampilkan nilainya.
    @field_validator("registry_signer_private_key")
    @classmethod
    def _validate_signer_key(cls, value: SecretStr) -> SecretStr:
        raw = value.get_secret_value()
        if len(raw) != 66 or not raw.startswith("0x") or any(c not in "0123456789abcdefABCDEF" for c in raw[2:]):
            raise ValueError("REGISTRY_SIGNER_PRIVATE_KEY harus berformat 0x + 64 hex")
        return value

    # Mengembalikan daftar origin CORS dari string dipisah koma.
    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


# Mengembalikan Settings tunggal per proses; gagal cepat bila konfigurasi tidak valid.
@lru_cache
def get_settings() -> Settings:
    return Settings()
