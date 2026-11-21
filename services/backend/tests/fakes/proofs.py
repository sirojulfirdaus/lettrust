# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: SA §5.3.1, §5.3.2, §5.6, §10.7; PRD §8.3.1
"""Fake pembaca bukti untuk test orkestrator API-07 (pengganti proofs.service.read_proof_for_verification).

Injeksi: orkestrator memanggil `proofs_service.read_proof_for_verification(code)` melalui atribut modul (SA §5.6),
sehingga test cukup `install_fake_proof_reader(monkeypatch, FakeProofReader(...))`.
"""

import hashlib
from datetime import UTC, datetime

from app.modules.proofs.service import ProofVerificationRead
from app.modules.verifications.schemas import (
    ProofCheck,
    ProofLifecycleStatus,
    ProofLookup,
    ProofReason,
    VerifiedIssuer,
)

ISSUER = VerifiedIssuer(issuer_id="ISS-4D8N2P6R", company_name="PT Sinar Demo Sejahtera")
ISSUED_AT = datetime(2026, 11, 23, 4, 12, 9, tzinfo=UTC)
REVOKED_AT = datetime(2026, 11, 24, 8, 1, 44, tzinfo=UTC)
# Berkas sintetis yang SHA-256-nya menjadi documentHash registry; berkas lain menghasilkan MISMATCH.
MATCHING_FILE_BYTES = b"%PDF-1.4\n% Lettrust FX-01 (sintetis) - offer letter wajar\n%%EOF\n"
MISMATCHING_FILE_BYTES = b"%PDF-1.4\n% Lettrust FX-02 (sintetis) - nominal gaji diubah\n%%EOF\n"
REGISTRY_DOCUMENT_HASH = hashlib.sha256(MATCHING_FILE_BYTES).hexdigest()


# FOUND + ACTIVE dari penerbit VERIFIED (sama dengan proofCheck contoh api-07.reference-match-ai.json).
def found_active(issuer_verified: bool = True) -> ProofVerificationRead:
    check = ProofCheck(
        lookup=ProofLookup.FOUND,
        reason=None,
        issuer=ISSUER,
        issuer_verified=issuer_verified,
        lifecycle_status=ProofLifecycleStatus.ACTIVE,
        issued_at=ISSUED_AT,
        revoked_at=None,
    )
    return ProofVerificationRead(proof_check=check, registry_document_hash=REGISTRY_DOCUMENT_HASH)


# FOUND + REVOKED; integritas tetap diperiksa (FR-03.11/AC-03).
def found_revoked(issuer_verified: bool = True) -> ProofVerificationRead:
    check = ProofCheck(
        lookup=ProofLookup.FOUND,
        reason=None,
        issuer=ISSUER,
        issuer_verified=issuer_verified,
        lifecycle_status=ProofLifecycleStatus.REVOKED,
        issued_at=ISSUED_AT,
        revoked_at=REVOKED_AT,
    )
    return ProofVerificationRead(proof_check=check, registry_document_hash=REGISTRY_DOCUMENT_HASH)


# FOUND dari penerbit yang kini tidak VERIFIED (issuerVerified=false, PRD §8.3.1).
def found_issuer_not_verified() -> ProofVerificationRead:
    return found_active(issuer_verified=False)


# NOT_FOUND: kode tidak terpetakan, pemetaan PENDING/FAILED, atau registry exists=false.
def not_found() -> ProofVerificationRead:
    check = ProofCheck(
        lookup=ProofLookup.NOT_FOUND,
        reason=None,
        issuer=None,
        issuer_verified=None,
        lifecycle_status=None,
        issued_at=None,
        revoked_at=None,
    )
    return ProofVerificationRead(proof_check=check, registry_document_hash=None)


# UNAVAILABLE / REGISTRY_UNAVAILABLE: registry error/timeout atau issuerRef tidak cocok (contoh registry-unavailable).
def registry_unavailable() -> ProofVerificationRead:
    check = ProofCheck(
        lookup=ProofLookup.UNAVAILABLE,
        reason=ProofReason.REGISTRY_UNAVAILABLE,
        issuer=None,
        issuer_verified=None,
        lifecycle_status=None,
        issued_at=None,
        revoked_at=None,
    )
    return ProofVerificationRead(proof_check=check, registry_document_hash=None)


# NOT_REQUESTED / NO_REFERENCE_CODE: dibentuk orkestrator untuk AI_ONLY; pembaca nyata tidak pernah mengembalikannya.
def not_requested() -> ProofVerificationRead:
    check = ProofCheck(
        lookup=ProofLookup.NOT_REQUESTED,
        reason=ProofReason.NO_REFERENCE_CODE,
        issuer=None,
        issuer_verified=None,
        lifecycle_status=None,
        issued_at=None,
        revoked_at=None,
    )
    return ProofVerificationRead(proof_check=check, registry_document_hash=None)


class FakeProofReader:
    """Pengganti async read_proof_for_verification: hasil per referenceCode atau default; mencatat setiap panggilan."""

    # Menyimpan hasil per kode ternormalisasi dan hasil default (NOT_FOUND seperti kode tak terdaftar).
    def __init__(
        self, results: dict[str, ProofVerificationRead] | None = None, default: ProofVerificationRead | None = None
    ) -> None:
        self.results = dict(results or {})
        self.default = default or not_found()
        self.calls: list[str] = []

    # Signature sama dengan proofs.service.read_proof_for_verification; tidak pernah raise.
    async def __call__(self, reference_code: str) -> ProofVerificationRead:
        self.calls.append(reference_code)
        return self.results.get(reference_code, self.default)


# Memasang fake pada atribut modul proofs.service yang dipanggil orkestrator (pytest monkeypatch).
def install_fake_proof_reader(monkeypatch, reader: FakeProofReader) -> FakeProofReader:
    monkeypatch.setattr("app.modules.proofs.service.read_proof_for_verification", reader)
    return reader
