# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: PRD SCN-17, FR-06.04; SA §5.3, §18.3
"""SCN-17: chain dan ai-service dihentikan; API-07 tetap 200 dengan proofCheck dan riskAnalysis UNAVAILABLE."""

from __future__ import annotations

import httpx

from _verification_scn import (
    Step,
    ensure_active_proof,
    fixture_bytes,
    post_verification,
    response_body,
    run_scenario,
    scenario_cli,
    summarize,
    wait_health,
)
from common import ScenarioError, ScenarioSettings, run_dev_service

SERVICES = ("chain", "ai-service")


def restore_services(services: tuple[str, ...] = SERVICES) -> None:
    """Menjalankan kembali setiap service secara terpisah; kegagalan satu service tidak melewatkan yang lain."""
    failed = []
    for service in services:
        try:
            run_dev_service("start", service)
        except ScenarioError:
            failed.append(service)
    if failed:
        commands = "; ".join(f"python scripts/dev.py start {service}" for service in failed)
        raise ScenarioError(f"Service belum berjalan kembali: {', '.join(failed)}. Jalankan manual: {commands}.")


def execute(settings: ScenarioSettings, client: httpx.Client) -> list[Step]:
    """Menyiapkan bukti FX-01 saat chain hidup, menghentikan dua service, lalu selalu menjalankannya kembali."""
    proof = ensure_active_proof(settings)
    try:
        for service in SERVICES:
            run_dev_service("stop", service)
        response, request, _ = post_verification(
            client, code=proof.reference_code, file=("FX-01.pdf", fixture_bytes("FX-01.pdf")), include_risk=True
        )
    finally:
        restore_services()
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
    args = scenario_cli("SCN-17: menghentikan chain dan ai-service lokal sementara.", interruption=True)
    raise SystemExit(run_scenario("SCN-17", "TC-017", "scn17-double-outage", execute, args.compose_project))
