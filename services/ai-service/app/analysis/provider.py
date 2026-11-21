# Owner: B (PIC 5) | Status: STUB | Ref: PRD FR-05.05, FR-05.09, FR-05.13; SA §7.4.1, AD-08, AD-16
# TODO: OpenAICompatibleProvider (SDK openai, base_url, temperature 0, json_object, timeout); petakan 429/timeout/error.
"""Adapter provider LLM OpenAI-compatible; tanpa fallback ke provider lain, mock, atau baseline."""

from dataclasses import dataclass
from typing import Protocol

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class CompletionResult:
    """Konten mentah respons model (tidak pernah dicatat ke log) dan latensi."""

    content: str
    latency_ms: int


class ProviderError(Exception):
    """Basis kegagalan provider → AI_PROVIDER_ERROR (503)."""


class ProviderUnconfigured(ProviderError):
    """LLM_API_KEY kosong → AI_PROVIDER_UNCONFIGURED (503)."""


class ProviderQuotaExceeded(ProviderError):
    """HTTP 429/kuota → AI_QUOTA_EXCEEDED (503); tidak di-retry."""


class ProviderTimeout(ProviderError):
    """Timeout → AI_TIMEOUT (504)."""


class LLMProvider(Protocol):
    """Kontrak provider yang dipakai pipeline analisis."""

    # Mengirim pesan chat dan mengembalikan konten JSON mentah.
    def complete(self, messages: list[dict[str, str]]) -> CompletionResult: ...


class OpenAICompatibleProvider:
    """Provider nyata melalui SDK openai dengan base_url yang dapat dikonfigurasi (Groq sebagai utama)."""

    # Menyimpan konfigurasi; client dibuat saat dibutuhkan.
    def __init__(self, settings: Settings):
        self._settings = settings

    # Lihat LLMProvider.complete.
    def complete(self, messages: list[dict[str, str]]) -> CompletionResult:
        raise NotImplementedError("OpenAICompatibleProvider.complete belum diimplementasikan")


class MockLLMProvider:
    """Provider palsu khusus unit test; menolak dibuat di luar APP_ENV=test."""

    # Guard AD-16: mock tidak dapat aktif melalui konfigurasi local.
    def __init__(self, canned_content: str):
        if get_settings().app_env != "test":
            raise RuntimeError("MockLLMProvider hanya boleh dipakai saat APP_ENV=test")
        self._canned_content = canned_content

    # Lihat LLMProvider.complete.
    def complete(self, messages: list[dict[str, str]]) -> CompletionResult:
        raise NotImplementedError("MockLLMProvider.complete belum diimplementasikan")


# Memilih provider dari konfigurasi; mock hanya bila LLM_PROVIDER=mock dan APP_ENV=test.
def get_provider(settings: Settings) -> LLMProvider:
    raise NotImplementedError("provider.get_provider belum diimplementasikan")
