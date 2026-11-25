# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: PRD FR-03.11; SA §5.3.2
"""Pemeriksaan integritas berkas: SHA-256 byte asli (dihitung core.files) dibandingkan dengan documentHash registry."""

from app.modules.verifications.schemas import (
    IntegrityCheck,
    IntegrityReason,
    IntegrityResult,
    ProofCheck,
    ProofLookup,
    VerificationMode,
)


# Menurunkan integrityCheck dari mode, proofCheck, hash registry, dan SHA-256 berkas (`ValidatedFile.sha256`)
# sesuai tabel SA §5.3.2. Hash tidak dihitung ulang di sini dan tidak pernah berasal dari teks ekstraksi/OCR.
def integrity_from(
    mode: VerificationMode,
    proof_check: ProofCheck,
    registry_document_hash: str | None,
    file_sha256: str | None,
) -> IntegrityCheck:
    if mode is VerificationMode.AI_ONLY:
        return _not_checked(IntegrityReason.NO_REFERENCE_CODE)
    if proof_check.lookup is ProofLookup.NOT_FOUND:
        return _not_checked(IntegrityReason.PROOF_NOT_FOUND)
    if proof_check.lookup is ProofLookup.UNAVAILABLE:
        return _not_checked(IntegrityReason.REGISTRY_UNAVAILABLE)
    if proof_check.lookup is not ProofLookup.FOUND or registry_document_hash is None:
        # REFERENCE_CHECK selalu membaca registry; FOUND selalu membawa hash (D-09). Selain itu bug pemanggil.
        raise ValueError(f"proofCheck tidak konsisten untuk integritas: {proof_check.lookup}")
    if file_sha256 is None:
        return _not_checked(IntegrityReason.NO_FILE)
    result = IntegrityResult.MATCH if file_sha256 == registry_document_hash else IntegrityResult.MISMATCH
    return IntegrityCheck(result=result, reason=None, hash_algorithm="SHA-256")


# integrityCheck NOT_CHECKED dengan alasan; hashAlgorithm null karena tidak ada perbandingan.
def _not_checked(reason: IntegrityReason) -> IntegrityCheck:
    return IntegrityCheck(result=IntegrityResult.NOT_CHECKED, reason=reason, hash_algorithm=None)
