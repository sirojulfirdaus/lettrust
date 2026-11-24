# Owner: B (PIC 5) | Status: COMPLETE | Ref: PRD FR-05.05, FR-05.09, FR-05.13; SA §7.4.1, AD-08, AD-16
"""Adapter provider LLM OpenAI-compatible; tanpa fallback ke provider lain, mock, atau baseline."""

import logging
from dataclasses import dataclass
from time import perf_counter
from typing import Literal, Protocol, cast

from openai import APITimeoutError, OpenAI, OpenAIError, RateLimitError
from openai.types.chat import ChatCompletionMessageParam
from openai.types.chat.completion_create_params import CompletionCreateParamsNonStreaming
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import Settings
from app.core.errors import ErrorCode

logger = logging.getLogger("app.analysis.provider")


@dataclass(frozen=True)
class CompletionResult:
    """Konten mentah respons model (tidak pernah dicatat ke log) dan latensi."""

    content: str
    latency_ms: int


class ProviderError(Exception):
    """Basis kegagalan provider → AI_PROVIDER_ERROR (503)."""

    code = ErrorCode.AI_PROVIDER_ERROR


class ProviderUnconfigured(ProviderError):
    """LLM_API_KEY kosong → AI_PROVIDER_UNCONFIGURED (503)."""

    code = ErrorCode.AI_PROVIDER_UNCONFIGURED


class ProviderQuotaExceeded(ProviderError):
    """HTTP 429/kuota → AI_QUOTA_EXCEEDED (503); tidak di-retry."""

    code = ErrorCode.AI_QUOTA_EXCEEDED


class ProviderTimeout(ProviderError):
    """Timeout → AI_TIMEOUT (504)."""

    code = ErrorCode.AI_TIMEOUT


class _CompletionMessage(BaseModel):
    """Memvalidasi pesan assistant; metadata tambahan provider tidak menentukan konten analisis."""

    model_config = ConfigDict(strict=True, extra="ignore")

    role: Literal["assistant"]
    content: str | None


class _CompletionChoice(BaseModel):
    """Memvalidasi satu pilihan chat tanpa mengunci metadata khusus vendor."""

    message: _CompletionMessage
    finish_reason: str | None = None


class _CompletionEnvelope(BaseModel):
    """Memastikan respons mempunyai pilihan pesan; skema JSON di dalam konten diperiksa pipeline."""

    choices: list[_CompletionChoice] = Field(min_length=1)


# Memutus log SDK/transport agar URL, body, dan error provider tidak bocor saat DEBUG.
def _disable_transport_logging() -> None:
    # SDK terkunci memakai httpx2/httpcore2; logger transport aktual tetap perlu dilindungi.
    prefixes = ("openai", "httpx", "httpx2", "httpcore", "httpcore2")
    for name in (*prefixes, *tuple(logging.Logger.manager.loggerDict)):
        if name in prefixes or name.startswith(tuple(f"{prefix}." for prefix in prefixes)):
            logger = logging.getLogger(name)
            logger.disabled = True
            logger.propagate = False
            if not logger.handlers:
                logger.addHandler(logging.NullHandler())


# Inisialisasi sekali per proses ketika modul dimuat, sebelum client dapat mengirim request.
_disable_transport_logging()


class LLMProvider(Protocol):
    """Kontrak provider yang dipakai pipeline analisis."""

    # Mengirim pesan chat dan mengembalikan konten JSON mentah.
    def complete(self, messages: list[dict[str, str]]) -> CompletionResult: ...


class OpenAICompatibleProvider:
    """Provider nyata melalui SDK openai; URL, model, dan parameter dibaca dari konfigurasi."""

    # Menyimpan konfigurasi tanpa koneksi; log transport sudah dilindungi saat modul dimuat.
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    # Mengirim sekali; retry output JSON/skema tidak valid menjadi tanggung jawab pipeline SA §7.3 (T5-04).
    def complete(self, messages: list[dict[str, str]]) -> CompletionResult:
        api_key = self._settings.llm_api_key.get_secret_value()
        if not api_key.strip():
            raise ProviderUnconfigured(ErrorCode.AI_PROVIDER_UNCONFIGURED.value)

        params: CompletionCreateParamsNonStreaming = {
            "model": self._settings.llm_model,
            "messages": cast(list[ChatCompletionMessageParam], messages),
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "max_tokens": self._settings.llm_max_output_tokens,
            "stream": False,
        }
        if self._settings.llm_reasoning_effort:
            params["reasoning_effort"] = self._settings.llm_reasoning_effort

        started = perf_counter()
        try:
            with OpenAI(
                api_key=api_key,
                base_url=self._settings.llm_base_url,
                timeout=self._settings.llm_request_timeout_seconds,
                max_retries=0,
            ) as client:
                # Envelope generik menerima metadata vendor; konten model tetap mentah untuk validator T5-04.
                raw_response = client.chat.completions.with_raw_response.create(**params)
                response = _CompletionEnvelope.model_validate_json(raw_response.text)
        except RateLimitError:
            raise ProviderQuotaExceeded(ErrorCode.AI_QUOTA_EXCEEDED.value) from None
        except APITimeoutError:
            raise ProviderTimeout(ErrorCode.AI_TIMEOUT.value) from None
        except (OpenAIError, ValueError):
            # Jangan teruskan pesan SDK karena dapat memuat body respons atau secret.
            raise ProviderError(ErrorCode.AI_PROVIDER_ERROR.value) from None

        latency_ms = max(0, int((perf_counter() - started) * 1000))
        choice = response.choices[0]
        if choice.finish_reason == "length":
            # Catat pemotongan tanpa isi respons; retry dan validasi tetap dimiliki pipeline T5-04.
            logger.warning(
                "ai.output_truncated",
                extra={
                    "event": "ai.output_truncated",
                    "component": "llm",
                    "model": self._settings.llm_model,
                    "promptVersion": self._settings.prompt_version,
                    "latencyMs": latency_ms,
                },
            )
        return CompletionResult(content=choice.message.content or "", latency_ms=latency_ms)


# Memilih provider dari konfigurasi; mock hanya bila LLM_PROVIDER=mock dan APP_ENV=test.
def get_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "mock":
        if settings.app_env != "test":
            raise ValueError("LLM_PROVIDER=mock hanya diizinkan bila APP_ENV=test")
        from app.analysis.mock_provider import MockLLMProvider

        return MockLLMProvider()
    if settings.llm_provider != "openai_compatible":
        raise ValueError("LLM_PROVIDER tidak didukung")
    return OpenAICompatibleProvider(settings)
