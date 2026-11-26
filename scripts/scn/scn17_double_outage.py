# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: PRD SCN-17, FR-06.04; SA §5.3, §18.3
"""SCN-17: chain dan ai-service dihentikan; API-07 tetap 200 dengan proofCheck dan riskAnalysis UNAVAILABLE."""

from __future__ import annotations

import argparse

import httpx

from _verification_scn import (
    Step,
    ensure_active_proof,
    fixture_bytes,
    post_verification,
    response_body,
    run_scenario,
    summarize,
    wait_health,
)
from common import ScenarioSettings, run_dev_service


def execute(settings: ScenarioSettings, client: httpx.Client) -> list[Step]:
    """Menyiapkan bukti FX-01 saat chain hidup, menghentikan dua service, lalu selalu menjalankannya kembali."""
    proof = ensure_active_proof(settings)
    try:
        run_dev_service("stop", "chain")
        run_dev_service("stop", "ai-service")
        response, request, _ = post_verification(
            client, code=proof.reference_code, file=("FX-01.pdf", fixture_bytes("FX-01.pdf")), include_risk=True
        )
    finally:
        run_dev_service("start", "chain")
        run_dev_service("start", "ai-service")
        wait_health(client, ("database", "registry", "aiService"))
    return [
        Step(
            "17-gangguan-ganda",
            request,
            {
                "httpStatus": 200,
                "lookup": "UNAVAILABLE",
                "proofReason": "REGISTRY_UNAVAILABLE",
                "integrityResult": "NOT_CHECKED",
                "integrityReason": "REGISTRY_UNAVAILABLE",
                "riskState": "UNAVAILABLE",
                "category": None,
            },
            summarize(response),
            response_body(response),
            {"proofId": proof.proof_id, "issueTransaction": proof.issue_transaction, "servicesRestored": True},
        )
    ]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SCN-17: menghentikan chain dan ai-service lokal sementara.")
    parser.add_argument(
        "--allow-service-interruption", action="store_true", help="Izinkan stop/start chain dan ai-service."
    )
    if not parser.parse_args().allow_service_interruption:
        parser.error("Tambahkan --allow-service-interruption; skrip menghentikan chain dan ai-service lokal.")
    raise SystemExit(run_scenario("SCN-17", "TC-017", "scn17-double-outage", execute))
