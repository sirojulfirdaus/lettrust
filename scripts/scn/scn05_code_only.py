# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: PRD SCN-05, FR-03.11, FR-05.01, FR-06.03; SA §18.3
"""SCN-05: kode bukti ACTIVE tanpa berkas, dengan includeRisk=false lalu true."""

from __future__ import annotations

import httpx

from _verification_scn import Step, ensure_active_proof, post_verification, response_body, run_scenario, summarize
from common import ScenarioSettings


def execute(settings: ScenarioSettings, client: httpx.Client) -> list[Step]:
    """(a) kode saja → FOUND/ACTIVE, NOT_CHECKED (NO_FILE); (b) includeRisk tanpa berkas → AI NOT_PERFORMED."""
    proof = ensure_active_proof(settings)
    setup = {"proofId": proof.proof_id, "issueTransaction": proof.issue_transaction}
    response, request, _ = post_verification(client, code=proof.reference_code, include_risk=False)
    step_a = Step(
        "5a-kode-saja",
        request,
        {
            "httpStatus": 200,
            "lookup": "FOUND",
            "lifecycleStatus": "ACTIVE",
            "integrityResult": "NOT_CHECKED",
            "integrityReason": "NO_FILE",
            "riskState": "NOT_REQUESTED",
        },
        summarize(response),
        response_body(response),
        {**setup, "guidanceG05": "Panduan G-05 adalah tampilan portal; diperiksa manual di UI, bukan oleh skrip API."},
    )
    response, request, _ = post_verification(client, code=proof.reference_code, include_risk=True)
    step_b = Step(
        "5b-kode-saja-include-risk",
        request,
        {
            "httpStatus": 200,
            "lookup": "FOUND",
            "integrityReason": "NO_FILE",
            "riskState": "NOT_PERFORMED",
            "riskReason": "DOCUMENT_CONTENT_UNAVAILABLE",
            "category": None,
        },
        summarize(response),
        response_body(response),
        setup,
    )
    return [step_a, step_b]


if __name__ == "__main__":
    raise SystemExit(run_scenario("SCN-05", "TC-005", "scn05-code-only", execute))
