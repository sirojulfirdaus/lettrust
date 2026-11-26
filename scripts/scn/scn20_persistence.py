# Owner: Sat (PIC 6) | Status: COMPLETE | Ref: T6-06; PRD SCN-20, FR-03.03/NFR-04.05; SA §18.3
"""Menguji persistensi registry dan mirror SQLite setelah down/up normal tanpa menghapus volume."""

from _registry_scn import Scenario, run_cli


def run_scenario(scenario: Scenario) -> None:
    """Mencocokkan bukti aktif/dicabut, receipt, kode, dan hash sebelum serta setelah restart seluruh stack."""
    revoked = scenario.issue(scenario.fx01, "scn20-revoked-proof")
    revocation = scenario.expect("revoke", scenario.revoke(revoked["proofId"], "scn20-revocation"), 201)
    scenario.confirmed(revocation, "ProofRevoked")
    active = scenario.issue(scenario.fx01, "scn20-active-proof")
    proofs = ((revoked, "REVOKED"), (active, "ACTIVE"))
    before = {}
    for issued, lifecycle in proofs:
        proof_id = issued["proofId"]
        api = scenario.read(proof_id)
        registry = scenario.registry.snapshot(proof_id)
        scenario.check("20-before-status", lifecycle, registry["lifecycleStatus"])
        scenario.check("20-before-api-status", lifecycle, api["lifecycleStatus"])
        before[proof_id] = {"api": api, "registry": registry}
        scenario.verify(issued, scenario.fx01, lifecycle)
    scenario.restart_stack()
    for issued, lifecycle in proofs:
        proof_id = issued["proofId"]
        scenario.check("20-persisted-api", before[proof_id]["api"], scenario.read(proof_id))
        scenario.check("20-persisted-registry", before[proof_id]["registry"], scenario.registry.snapshot(proof_id))
        scenario.confirmed(issued, "ProofIssued")
        scenario.verify(issued, scenario.fx01, lifecycle)
    scenario.confirmed(revocation, "ProofRevoked")


if __name__ == "__main__":
    raise SystemExit(run_cli("SCN-20", "TC-020", run_scenario))
