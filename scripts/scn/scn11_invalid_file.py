# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: PRD SCN-11, FR-06.06, FR-05.04; SA §18.3
"""SCN-11: FX-08, FX-09, berkas kosong ditolak; FX-10 dengan kode ACTIVE dihitung integritasnya atas byte."""

from __future__ import annotations

import httpx

from _verification_scn import (
    Step,
    ensure_active_proof,
    fixture_bytes,
    post_verification,
    response_body,
    run_scenario,
    summarize,
)
from common import ScenarioSettings


def execute(settings: ScenarioSettings, client: httpx.Client) -> list[Step]:
    """(a) 415, (b) 413, (c) 400 pada Mode Tanpa Kode; (d) FX-10 + kode ACTIVE → 200, MISMATCH, AI NOT_PERFORMED."""
    steps = []
    for name, file, status, code in (
        ("11a-fx08-bukan-pdf", ("FX-08.pdf", fixture_bytes("FX-08.pdf")), 415, "UNSUPPORTED_MEDIA_TYPE"),
        ("11b-fx09-melebihi-batas", ("FX-09.pdf", fixture_bytes("FX-09.pdf")), 413, "FILE_TOO_LARGE"),
        ("11c-berkas-kosong", ("kosong.pdf", b""), 400, "EMPTY_FILE"),
    ):
        response, request, _ = post_verification(client, file=file, include_risk=True)
        steps.append(
            Step(name, request, {"httpStatus": status, "errorCode": code}, summarize(response), response_body(response))
        )
    proof = ensure_active_proof(settings)
    response, request, _ = post_verification(
        client, code=proof.reference_code, file=("FX-10.pdf", fixture_bytes("FX-10.pdf")), include_risk=True
    )
    steps.append(
        Step(
            "11d-fx10-rusak-dengan-kode-active",
            request,
            {
                "httpStatus": 200,
                "lookup": "FOUND",
                "lifecycleStatus": "ACTIVE",
                "integrityResult": "MISMATCH",
                "riskState": "NOT_PERFORMED",
            },
            summarize(response),
            response_body(response),
            {"proofId": proof.proof_id, "issueTransaction": proof.issue_transaction},
        )
    )
    return steps


if __name__ == "__main__":
    raise SystemExit(run_scenario("SCN-11", "TC-011", "scn11-invalid-file", execute))
