# Owner: B (PIC 5) | Status: COMPLETE | Ref: PLAN T5-04; SA §7.3–§7.7
"""Pipeline analisis bersama untuk router; menerima provider eksplisit untuk unit test."""

from app.analysis.compose import compose_result
from app.analysis.prompt import build_messages
from app.analysis.provider import LLMProvider, ProviderError, get_provider
from app.analysis.scoring import score
from app.analysis.validator import parse_model_output, validate_indicators
from app.core.config import Settings
from app.core.errors import AppError, ErrorCode, ErrorDetail
from app.schemas import AnalysisMeta, RiskAnalysisResponse


# Memvalidasi input, mengulang hanya output tidak valid satu kali, lalu menghitung hasil dari bukti tervalidasi.
def analyze_document(
    document_text: str,
    settings: Settings,
    extraction_method: str | None = None,
    provider: LLMProvider | None = None,
) -> RiskAnalysisResponse:
    if not document_text.strip() or len(document_text) > settings.ai_max_chars:
        issue = "string_too_long" if len(document_text) > settings.ai_max_chars else "string_too_short"
        raise AppError(ErrorCode.VALIDATION_ERROR, details=[ErrorDetail(field="documentContent", issue=issue)])
    selected_provider = provider if provider is not None else get_provider(settings)
    messages = build_messages(document_text)
    latency_ms = 0
    for attempt in range(2):
        try:
            # Bergantung pada T5-03; diuji dengan MockLLMProvider.
            completion = selected_provider.complete(messages)
        except ProviderError as error:
            raise AppError(error.code) from None
        latency_ms += completion.latency_ms
        try:
            output = parse_model_output(completion.content)
        except ValueError:
            if attempt == 1:
                raise AppError(ErrorCode.AI_OUTPUT_INVALID) from None
            continue
        indicators, dropped = validate_indicators(
            output["indicators"], document_text, extraction_method, settings.evidence_fuzzy_threshold
        )
        return compose_result(
            indicators,
            score({item.code for item in indicators}),
            output["explanation"],
            AnalysisMeta(
                model=settings.llm_model,
                prompt_version=settings.prompt_version,
                latency_ms=latency_ms,
                dropped_indicators=dropped,
            ),
        )
    raise AssertionError("Pipeline analisis berakhir tanpa hasil atau error.")
