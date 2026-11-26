# Owner: Sat (PIC 6) | Status: COMPLETE | Ref: T6-06; PRD SCN-15, FR-03.04/FR-03.05; SA §18.3
"""Menguji replay penerbitan, konflik payload, dan pemulihan registry dengan fixture asli."""

from _registry_scn import PROOFS, Scenario, run_cli


def run_scenario(scenario: Scenario) -> None:
    """Membuktikan satu event per bukti dan tidak ada kode final saat chain gagal."""
    first = scenario.issue(scenario.fx01, "scn15-same-file")
    proof_id = first["proofId"]
    before = scenario.registry.snapshot(proof_id)
    replay = scenario.expect(
        "15a-replay", scenario.request("POST", PROOFS, key="scn15-same-file", pdf=scenario.fx01), 201
    )
    scenario.check("15a-same-proof", first, replay)
    scenario.check("15a-no-new-transaction", before, scenario.registry.snapshot(proof_id))
    scenario.check("15a-one-issue-event", 1, len(scenario.events(proof_id, "ProofIssued")))
    scenario.expect(
        "15b-key-conflict",
        scenario.request("POST", PROOFS, key="scn15-same-file", pdf=scenario.fx02),
        409,
        "IDEMPOTENCY_KEY_CONFLICT",
    )
    scenario.check("15b-no-mutation", before, scenario.registry.snapshot(proof_id))
    with scenario.chain_outage():
        failed = scenario.expect(
            "15c-chain-unavailable",
            scenario.request("POST", PROOFS, key="scn15-recovery", pdf=scenario.fx02),
            503,
            "REGISTRY_UNAVAILABLE",
        )
        scenario.check(
            "15c-no-final-proof", False, any(key in failed for key in ("referenceCode", "proofId", "transaction"))
        )
    scenario.check("15c-no-broadcast-during-outage", before, scenario.registry.snapshot(proof_id))
    listed = scenario.expect("15c-no-public-pending-proof", scenario.request("GET", PROOFS), 200)
    scenario.check("15c-only-original-public-proof", [proof_id], [item["proofId"] for item in listed["items"]])
    recovered = scenario.issue(scenario.fx02, "scn15-recovery")
    scenario.check("15c-distinct-proof", True, recovered["proofId"] != proof_id)
    scenario.verify(first, scenario.fx01, "ACTIVE")
    scenario.verify(recovered, scenario.fx02, "ACTIVE")


if __name__ == "__main__":
    raise SystemExit(run_cli("SCN-15", "TC-015", run_scenario))
