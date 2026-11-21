# Owner: Dws (PIC 1) | Status: STUB | Ref: PRD FR-03.11; SA §5.3.2
# TODO: Hash SHA-256 atas byte berkas asli dan tabel keputusan integritas SA §5.3.2.
"""Pemeriksaan integritas berkas: SHA-256 byte asli dibandingkan dengan documentHash registry."""

from app.modules.verifications.schemas import IntegrityCheck, ProofCheck, VerificationMode


# Menghitung SHA-256 atas byte berkas asli (bukan teks hasil ekstraksi/OCR); hex lowercase 64 karakter.
def compute_document_hash(file_bytes: bytes) -> str:
    raise NotImplementedError("integrity.compute_document_hash belum diimplementasikan")


# Menurunkan integrityCheck dari mode, proofCheck, hash registry, dan berkas (tabel SA §5.3.2).
def integrity_from(
    mode: VerificationMode, proof_check: ProofCheck, registry_document_hash: str | None, file_bytes: bytes | None
) -> IntegrityCheck:
    raise NotImplementedError("integrity.integrity_from belum diimplementasikan")
