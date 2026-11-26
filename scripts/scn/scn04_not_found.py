# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: PRD SCN-04, FR-03.10, FR-05.01, FR-06.02; SA §18.3
"""SCN-04: kode berformat valid yang tidak terdaftar, tanpa berkas lalu dengan FX-03 dan analisis AI."""

from __future__ import annotations

import secrets

import httpx

from _verification_scn import (
    Step,
    active_llm_model,
    ai_service_saw,
    check_ai_subset,
    fixture_bytes,
    post_verification,
    response_body,
    run_scenario,
    scenario_cli,
    summarize,
)
from common import ScenarioSettings

CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
FX03_LABEL_INDICATORS = {"PAYMENT_REQUEST", "UNOFFICIAL_CONTACT"}


def unregistered_code() -> str:
    """Kode acak berformat valid; peluang bentrok dengan kode terdaftar diabaikan (32^12 kombinasi)."""
    groups = ("".join(secrets.choice(CROCKFORD) for _ in range(4)) for _ in range(3))
    return "LTR-" + "-".join(groups)


def no_false_labels(response: httpx.Response) -> bool:
    """NOT_FOUND tidak membawa issuer, status verifikasi penerbit, atau lifecycle (tidak ada label palsu)."""
    proof = (response_body(response) or {}).get("proofCheck") or {}
    return all(proof.get(key) is None for key in ("issuer", "issuerVerified", "lifecycleStatus", "issuedAt"))


def execute(_: ScenarioSettings, client: httpx.Client) -> list[Step]:
    """(a) kode saja → NOT_FOUND tanpa AI; (b) kode + FX-03 + includeRisk → NOT_FOUND dengan AI COMPLETED."""
    code = unregistered_code()
    response, request, _ = post_verification(client, code=code, include_risk=False)
    step_a = Step(
        "4a-kode-tidak-terdaftar-tanpa-berkas",
        request,
        {
            "httpStatus": 200,
            "lookup": "NOT_FOUND",
            "integrityResult": "NOT_CHECKED",
            "integrityReason": "PROOF_NOT_FOUND",
            "riskState": "NOT_REQUESTED",
            "noFalseLabels": True,
        },
        {**summarize(response), "noFalseLabels": no_false_labels(response)},
        response_body(response),
    )
    response, request, _ = post_verification(
        client, code=code, file=("FX-03.pdf", fixture_bytes("FX-03.pdf")), include_risk=True
    )
    step_b = Step(
        "4b-kode-tidak-terdaftar-fx03-ai",
        request,
        {
            "httpStatus": 200,
            "lookup": "NOT_FOUND",
            "integrityResult": "NOT_CHECKED",
            "integrityReason": "PROOF_NOT_FOUND",
            "riskState": "COMPLETED",
            "category": "HIGH",
            "noFalseLabels": True,
        },
        {**summarize(response), "noFalseLabels": no_false_labels(response)},
        response_body(response),
        {"model": active_llm_model(), "aiServiceSawRequest": ai_service_saw(request["requestId"])},
    )
    check_ai_subset(step_b, FX03_LABEL_INDICATORS)
    return [step_a, step_b]


if __name__ == "__main__":
    args = scenario_cli("SCN-04: kode tidak terdaftar pada stack lokal.")
    raise SystemExit(run_scenario("SCN-04", "TC-004", "scn04-not-found", execute, args.compose_project))
