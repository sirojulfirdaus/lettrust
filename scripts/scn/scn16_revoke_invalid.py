# Owner: Sat (PIC 6) | Status: COMPLETE | Ref: T6-06; PRD SCN-16, FR-04.04/FR-04.05; SA §18.3
"""Menguji penolakan pencabutan ulang, ketiadaan reaktivasi, dan kegagalan registry."""

from _registry_scn import Scenario, run_cli


def run_scenario(scenario: Scenario) -> None:
    """Menjaga bukti REVOKED tetap final serta bukti ACTIVE tetap aktif saat pencabutan gagal."""
    issued = scenario.issue(scenario.fx01, "scn16-issued")
    proof_id = issued["proofId"]
    revoked = scenario.expect("revoke", scenario.revoke(proof_id, "scn16-revoke"), 201)
    scenario.confirmed(revoked, "ProofRevoked")
    before = scenario.registry.snapshot(proof_id)
    scenario.check("revoked-on-chain", "REVOKED", before["lifecycleStatus"])
    for key in (None, "scn16-another-revoke"):
        scenario.expect("16a-already-revoked", scenario.revoke(proof_id, key), 409, "PROOF_ALREADY_REVOKED")
        scenario.check("16a-no-mutation", before, scenario.registry.snapshot(proof_id))
    scenario.check("16a-one-revoke-event", 1, len(scenario.events(proof_id, "ProofRevoked")))
    scenario.no_reactivation(proof_id)
    scenario.check("16b-no-reactivation", before, scenario.registry.snapshot(proof_id))
    scenario.verify(issued, scenario.fx01, "REVOKED")

    # File sama boleh diterbitkan sebagai bukti baru setelah bukti lama dicabut; ini bukan reaktivasi.
    active = scenario.issue(scenario.fx01, "scn16-new-proof")
    active_id = active["proofId"]
    scenario.check("16c-new-proof-id", True, active_id != proof_id)
    active_before = scenario.registry.snapshot(active_id)
    with scenario.chain_outage():
        scenario.expect(
            "16c-revoke-unavailable", scenario.revoke(active_id, "scn16-outage"), 503, "REGISTRY_UNAVAILABLE"
        )
    scenario.check("16c-active-unchanged", active_before, scenario.registry.snapshot(active_id))
    scenario.check("16c-no-revoke-event", 0, len(scenario.events(active_id, "ProofRevoked")))
    scenario.check("16c-api-still-active", "ACTIVE", scenario.read(active_id)["lifecycleStatus"])
    scenario.verify(active, scenario.fx01, "ACTIVE")


if __name__ == "__main__":
    raise SystemExit(run_cli("SCN-16", "TC-016", run_scenario))
