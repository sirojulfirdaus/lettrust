# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: PRD FR-06.08; SA §9.2, §5.2
"""Satu API-07 terhadap registry nyata menghasilkan tepat satu baris verification_logs (FR-06.08)."""

import pytest
from sqlalchemy import func, select

from app.core.db import get_session_factory
from app.modules.verifications.models import VerificationLog

from .conftest import RegistryFlow

pytestmark = pytest.mark.real_registry


# Penerbitan nyata lalu verifikasi kode + berkas sama: satu baris log dengan enum hasil yang sama dengan respons.
def test_api07_writes_one_log_row(flow: RegistryFlow, partner_headers: dict[str, str]) -> None:
    issued = flow.issue()
    assert issued.status_code == 201
    with get_session_factory()() as db:
        before = db.scalar(select(func.count()).select_from(VerificationLog))
    response = flow.client.post(
        "/api/v1/verifications",
        headers=partner_headers,
        data={"referenceCode": issued.json()["referenceCode"], "includeRisk": "false"},
        files={"file": ("offer-sintetis.pdf", flow.pdf, "application/pdf")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["proofCheck"]["lookup"], body["integrityCheck"]["result"]) == ("FOUND", "MATCH")
    with get_session_factory()() as db:
        assert db.scalar(select(func.count()).select_from(VerificationLog)) == before + 1
        row = db.get(VerificationLog, body["verificationId"])
    assert row is not None
    assert (row.mode, row.lookup, row.integrity_result, row.risk_state) == (
        "REFERENCE_CHECK",
        "FOUND",
        "MATCH",
        "NOT_REQUESTED",
    )
