"""Menguji hasil pembaca nyata API-07 dengan SQLite dan adapter registry pengujian."""

import asyncio
from datetime import UTC, datetime
from typing import Never

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.exc import OperationalError
from test_proofs_issue import BLOCK_TIME, PDF
from test_proofs_issue import registry as registry
from test_proofs_read import change_mirror
from test_proofs_read import owned_proof as owned_proof
from test_verifications import install_fake_ai

from app.core.db import get_session_factory
from app.core.ids import compute_issuer_ref
from app.modules.auth.schemas import IssuerStatus
from app.modules.issuers.models import Issuer
from app.modules.proofs import service
from app.modules.proofs.service import read_proof_for_verification
from app.modules.registry.mock import MockRegistryAdapter


@pytest.mark.parametrize("case", ["unknown", "pending", "failed", "missing_on_chain", "rpc_failed", "issuer_mismatch"])
def test_lookup_without_confirmed_record(registry: MockRegistryAdapter, owned_proof: tuple, case: str) -> None:
    """Membedakan bukti tidak ditemukan dari gangguan registry atau pemetaan yang tidak konsisten."""
    _, _, proof = owned_proof
    proof_id, code = proof["proofId"], proof["referenceCode"]
    if case == "unknown":
        code = "LTR-0000-0000-0000" if code != "LTR-0000-0000-0000" else "LTR-1111-1111-1111"
    elif case in ("pending", "failed"):
        change_mirror(proof_id, status=case.upper())
    elif case == "rpc_failed":
        registry.set_unavailable(True)
    else:
        registry.reset()
        if case == "issuer_mismatch":
            registry.issue_proof(proof_id, proof["documentHash"], "e" * 64)

    registry.calls.clear()
    result = asyncio.run(read_proof_for_verification(code))
    unavailable = case in ("rpc_failed", "issuer_mismatch")
    assert result.registry_document_hash is None
    assert result.proof_check.model_dump(mode="json", by_alias=True) == {
        "lookup": "UNAVAILABLE" if unavailable else "NOT_FOUND",
        "reason": "REGISTRY_UNAVAILABLE" if unavailable else None,
        "issuer": None,
        "issuerVerified": None,
        "lifecycleStatus": None,
        "issuedAt": None,
        "revokedAt": None,
    }
    expected_calls = [] if case in ("unknown", "pending", "failed") else [("get_proof", (proof_id,))]
    assert registry.calls == expected_calls


@pytest.mark.parametrize("revoked", [False, True])
def test_lookup_found_uses_registry_and_current_issuer(
    registry: MockRegistryAdapter, owned_proof: tuple, revoked: bool
) -> None:
    """FOUND memakai hash, lifecycle, dan waktu registry serta verifikasi issuer terkini."""
    issuer_id, _, proof = owned_proof
    proof_id = proof["proofId"]
    change_mirror(proof_id, document_hash="f" * 64, issued_at=datetime.fromtimestamp(BLOCK_TIME - 1, UTC))
    if revoked:
        registry.revoke_proof(proof_id, compute_issuer_ref(issuer_id))
        with get_session_factory().begin() as db:
            db.execute(update(Issuer).where(Issuer.id == issuer_id).values(status=IssuerStatus.PENDING))

    result = asyncio.run(read_proof_for_verification(proof["referenceCode"]))
    check = result.proof_check
    assert check.lookup == "FOUND" and check.reason is None
    assert check.issuer is not None
    assert (check.issuer.issuer_id, check.issuer.company_name) == (issuer_id, "PT Uji API-04")
    assert check.issuer_verified is (not revoked)
    assert check.lifecycle_status == ("REVOKED" if revoked else "ACTIVE")
    assert check.issued_at == datetime.fromtimestamp(BLOCK_TIME, UTC)
    assert check.revoked_at == (datetime.fromtimestamp(BLOCK_TIME, UTC) if revoked else None)
    assert result.registry_document_hash == proof["documentHash"]


@pytest.mark.parametrize(
    ("file_bytes", "expected"), [(PDF, "MATCH"), (PDF + b"%beda", "MISMATCH")], ids=["matching-file", "changed-file"]
)
def test_api07_uses_registry_hash_with_normalized_code(
    client: TestClient, partner_headers: dict[str, str], owned_proof: tuple, file_bytes: bytes, expected: str
) -> None:
    """API-07 menormalisasi kode dan menghitung integritas dari hash registry."""
    _, _, proof = owned_proof
    change_mirror(proof["proofId"], document_hash="f" * 64)
    code = proof["referenceCode"].lower().replace("-", " ")
    response = client.post(
        "/api/v1/verifications",
        headers=partner_headers,
        data={"referenceCode": code},
        files={"file": ("offer.pdf", file_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["proofCheck"]["lookup"] == "FOUND"
    assert result["integrityCheck"] == {"result": expected, "reason": None, "hashAlgorithm": "SHA-256"}


def test_api07_registry_outage_preserves_independent_risk(
    client: TestClient,
    partner_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    registry: MockRegistryAdapter,
    owned_proof: tuple,
) -> None:
    """Kegagalan pembaca nyata meniadakan integritas, sementara jalur risiko tetap berjalan."""
    _, _, proof = owned_proof
    registry.set_unavailable(True)
    registry.calls.clear()
    install_fake_ai(monkeypatch, analysis="low")
    response = client.post(
        "/api/v1/verifications",
        headers=partner_headers,
        data={"referenceCode": proof["referenceCode"], "includeRisk": "true"},
        files={"file": ("offer.pdf", PDF, "application/pdf")},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["proofCheck"]["lookup"] == "UNAVAILABLE"
    assert result["proofCheck"]["reason"] == "REGISTRY_UNAVAILABLE"
    assert result["integrityCheck"]["result"] == "NOT_CHECKED"
    assert result["integrityCheck"]["reason"] == "REGISTRY_UNAVAILABLE"
    assert result["riskAnalysis"]["state"] == "COMPLETED"
    assert registry.calls == [("get_proof", (proof["proofId"],))]


def test_lookup_database_error_returns_unavailable(
    registry: MockRegistryAdapter, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Gangguan SQLite menjadi UNAVAILABLE tanpa RPC atau pembocoran detail exception."""

    def fail_lookup() -> Never:
        """Menyuntikkan error database sebelum lookup mendapatkan metadata."""
        raise OperationalError("SELECT 1", None, RuntimeError("rincian-internal-uji"))

    monkeypatch.setattr(service, "get_session_factory", fail_lookup)
    check = asyncio.run(read_proof_for_verification("LTR-0000-0000-0000"))
    assert check.proof_check.lookup == "UNAVAILABLE"
    assert check.proof_check.reason == "REGISTRY_UNAVAILABLE"
    assert check.registry_document_hash is None
    assert registry.calls == []
    assert "proof.lookup_db_failed" in caplog.text
    assert "rincian-internal-uji" not in caplog.text
