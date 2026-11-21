# Owner: Dws (PIC 1) | Status: STUB | Ref: PRD FR-02, FR-03.10, FR-03.11, FR-05.10, FR-06.01–FR-06.06; SA §5.2, §5.6
# TODO: Implementasikan validasi input/berkas (SA §5.2 langkah 3–7) dan orkestrasi paralel di bawah.
"""Orkestrasi API-07: bukti, integritas, dan AI diproses terpisah dan paralel."""

from app.modules.partners.models import Partner
from app.modules.verifications.schemas import VerificationResponse


# Mengorkestrasi pemeriksaan bukti, integritas, dan analisis AI secara terpisah.
async def verify_offer(
    partner: Partner, reference_code: str | None, file_bytes: bytes | None, include_risk: bool, request_id: str
) -> VerificationResponse:
    """Pseudo-code SA §5.6 (acuan implementasi):

    mode = Mode.REFERENCE_CHECK if reference_code else Mode.AI_ONLY

    proof_coro = (
        proofs_service.read_proof_for_verification(reference_code)
        if mode is Mode.REFERENCE_CHECK
        else as_result(ProofCheck.not_requested())
    )
    if include_risk and file_bytes:
        risk_coro = risk_pipeline.run(file_bytes)        # tidak pernah raise; mengembalikan RiskAnalysis
    elif include_risk:
        risk_coro = as_result(RiskAnalysis.not_performed("DOCUMENT_CONTENT_UNAVAILABLE"))
    else:
        risk_coro = as_result(RiskAnalysis.not_requested())

    proof_check, risk_analysis = await asyncio.gather(proof_coro, risk_coro)
    integrity = integrity_from(mode, proof_check, file_bytes)
    return VerificationResponse(
        verification_id=new_id("VER"), mode=mode,
        proof_check=proof_check, integrity_check=integrity, risk_analysis=risk_analysis,
    )

    Ketentuan: read_proof_for_verification dan risk pipeline tidak melempar exception; pembacaan web3 di
    asyncio.to_thread; berkas dibaca sekali ke memori dan tidak ditulis ke disk; hash dihitung dari byte
    yang sama yang dikirim ke ekstraksi; mode AI_ONLY tidak pernah memanggil registry.
    """
    raise NotImplementedError("orchestrator.verify_offer belum diimplementasikan")
