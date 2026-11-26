# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: PRD SCN-10, FR-06.05; SA §5.2, §18.3
"""SCN-10: kombinasi input tidak valid ditolak 400 sebelum ai-service dipanggil."""

from __future__ import annotations

import httpx

from _verification_scn import (
    Step,
    ai_service_saw,
    fixture_bytes,
    post_verification,
    response_body,
    run_scenario,
    scenario_cli,
    summarize,
)
from common import ScenarioSettings

# Pemanggilan registry tidak tercatat per request; jaminannya ada di test unit
# test_invalid_requests_stop_before_registry_and_ai. Skrip ini membuktikan sisi ai-service dari log nyata.
REGISTRY_NOTE = "Pemanggilan registry tidak teramati dari API; dicakup test unit backend."


def rejected(name: str, response: httpx.Response, request: dict, code: str) -> Step:
    """Langkah penolakan: 400 dengan kode error tertentu dan tanpa request ke ai-service."""
    return Step(
        name,
        request,
        {"httpStatus": 400, "errorCode": code, "aiServiceCalled": False},
        {**summarize(response), "aiServiceCalled": ai_service_saw(request["requestId"])},
        response_body(response),
        {"registry": REGISTRY_NOTE},
    )


def execute(_: ScenarioSettings, client: httpx.Client) -> list[Step]:
    """(a) tanpa kode/berkas; (b) berkas tanpa includeRisk; (c) kode salah format; ditambah kontrol log positif."""
    fx01 = ("FX-01.pdf", fixture_bytes("FX-01.pdf"))
    steps = []
    response, request, _ = post_verification(client)
    steps.append(rejected("10a-tanpa-kode-tanpa-berkas", response, request, "INVALID_INPUT_COMBINATION"))
    response, request, _ = post_verification(client, file=fx01, include_risk=False)
    steps.append(rejected("10b-berkas-tanpa-include-risk", response, request, "AI_ONLY_REQUIRES_INCLUDE_RISK"))
    response, request, _ = post_verification(client, code="LTR-12AB", file=fx01, include_risk=True)
    steps.append(rejected("10c-kode-salah-format", response, request, "INVALID_REFERENCE_CODE_FORMAT"))
    # Kontrol tanpa LLM: FX-07 (halaman kosong) memanggil ekstraksi I-01 lalu NOT_PERFORMED, sehingga requestId
    # harus muncul di log ai-service; ini membuktikan metode pemeriksaan log di atas dapat mendeteksi panggilan.
    response, request, _ = post_verification(client, file=("FX-07.pdf", fixture_bytes("FX-07.pdf")), include_risk=True)
    steps.append(
        Step(
            "10-kontrol-log-ai-service",
            request,
            {"httpStatus": 200, "riskState": "NOT_PERFORMED", "aiServiceCalled": True},
            {**summarize(response), "aiServiceCalled": ai_service_saw(request["requestId"])},
            response_body(response),
        )
    )
    return steps


if __name__ == "__main__":
    args = scenario_cli("SCN-10: kombinasi input tidak valid pada stack lokal.")
    raise SystemExit(run_scenario("SCN-10", "TC-010", "scn10-invalid-input", execute, args.compose_project))
