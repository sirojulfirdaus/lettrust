# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: PRD FR-02, FR-03.10, FR-03.11, FR-05.10, FR-06.01–FR-06.06, FR-06.08;
# SA §5.2, §5.6, §9.2
"""Orkestrasi API-07: bukti, integritas, dan AI diproses terpisah dan paralel."""

import asyncio
import logging
import time
from datetime import UTC, datetime
from enum import Enum

from app.core.db import get_session_factory
from app.core.errors import AppError
from app.core.files import ValidatedFile
from app.core.ids import InvalidReferenceCodeError, new_verification_id, normalize_reference_code
from app.core.schemas import ErrorCode
from app.modules.partners.models import Partner

# Dipanggil lewat atribut modul (SA §5.6) agar test dapat memasang FakeProofReader / FakeAiService.
from app.modules.proofs import service as proofs_service
from app.modules.verifications import ai_client
from app.modules.verifications.integrity import integrity_from
from app.modules.verifications.models import VerificationLog
from app.modules.verifications.schemas import (
    IntegrityCheck,
    IntegrityReason,
    IntegrityResult,
    ProofCheck,
    ProofLookup,
    ProofReason,
    RiskAnalysis,
    RiskReason,
    RiskState,
    VerificationMode,
    VerificationResponse,
)

logger = logging.getLogger("app.verifications.orchestrator")

# proofCheck Mode Tanpa Kode (SA §5.3.1): registry tidak dipanggil.
PROOF_NOT_REQUESTED = ProofCheck(
    lookup=ProofLookup.NOT_REQUESTED,
    reason=ProofReason.NO_REFERENCE_CODE,
    issuer=None,
    issuer_verified=None,
    lifecycle_status=None,
    issued_at=None,
    revoked_at=None,
)
# proofCheck saat pembacaan bukti gagal tak terduga (SA §5.3.1 baris registry error).
PROOF_UNAVAILABLE = PROOF_NOT_REQUESTED.model_copy(
    update={"lookup": ProofLookup.UNAVAILABLE, "reason": ProofReason.REGISTRY_UNAVAILABLE}
)


# SA §5.2 langkah 4–5: normalisasi kode (kosong/spasi = tidak ada) lalu validasi kombinasi input.
# `has_file` hanya menandai keberadaan field `file`; isi berkas divalidasi sesudahnya (langkah 6).
def resolve_reference_code(raw_code: str | None, has_file: bool, include_risk: bool) -> str | None:
    try:
        code = normalize_reference_code(raw_code)
    except InvalidReferenceCodeError:
        raise AppError(ErrorCode.INVALID_REFERENCE_CODE_FORMAT) from None
    if code is None and not has_file:
        raise AppError(ErrorCode.INVALID_INPUT_COMBINATION)
    if code is None and not include_risk:
        raise AppError(ErrorCode.AI_ONLY_REQUIRES_INCLUDE_RISK)
    return code


# Mengorkestrasi pemeriksaan bukti, integritas, dan analisis AI secara terpisah (SA §5.2 langkah 7–10).
# Bukti dan AI berjalan paralel; AI_ONLY tidak memanggil pembacaan bukti/registry. `file.sha256` dihitung
# core.files dari byte yang sama yang dikirim ke ekstraksi, dan dipakai integrity_from(mode, proof_check,
# registry_document_hash, file_sha256) tanpa hash ulang. Hanya pembatalan request yang diteruskan (tugas AI
# dibatalkan); kegagalan lain, termasuk stub T3-05 (NotImplementedError), menjadi status komponen.
# Setiap respons yang dihasilkan dicatat ke verification_logs (T1-06) atas nama `partner`.
async def verify_offer(
    partner: Partner,
    reference_code: str | None,
    file: ValidatedFile | None,
    include_risk: bool,
    request_id: str,
) -> VerificationResponse:
    started = time.monotonic()
    mode = VerificationMode.REFERENCE_CHECK if reference_code else VerificationMode.AI_ONLY
    risk_task = asyncio.create_task(_risk_analysis(file, include_risk, request_id))
    try:
        proof_check, registry_hash = await _proof_check(reference_code)
    except BaseException:
        risk_task.cancel()
        raise
    risk_analysis = await risk_task
    integrity = _integrity_check(mode, proof_check, registry_hash, file)
    response = VerificationResponse(
        verification_id=new_verification_id(),
        mode=mode,
        proof_check=proof_check,
        integrity_check=integrity,
        risk_analysis=risk_analysis,
    )
    await _record_log(partner.id, response, round((time.monotonic() - started) * 1000))
    return response


# Log verifikasi minimal (FR-06.08, SA §9.2): hanya enum hasil, mode, durasi, partner, dan verificationId; tidak
# ada kode referensi, hash berkas, teks, atau berkas. Ditulis di threadpool agar event loop tidak terblokir.
# Kegagalan tulis tidak mengubah respons API-07; hanya dicatat sebagai nama tipe exception.
async def _record_log(partner_id: str, response: VerificationResponse, duration_ms: int) -> None:
    proof, integrity, risk = response.proof_check, response.integrity_check, response.risk_analysis
    row = VerificationLog(
        id=response.verification_id,
        partner_id=partner_id,
        mode=response.mode.value,
        lookup=proof.lookup.value,
        lifecycle_status=_enum_value(proof.lifecycle_status),
        integrity_result=integrity.result.value,
        risk_state=risk.state.value,
        risk_category=_enum_value(risk.category),
        proof_reason=_enum_value(proof.reason),
        integrity_reason=_enum_value(integrity.reason),
        risk_reason=_enum_value(risk.reason),
        duration_ms=duration_ms,
        created_at=datetime.now(UTC),
    )
    try:
        await asyncio.to_thread(_insert_log, row)
    except Exception as exc:
        logger.error(
            "verification.log_failed", exc_info=(type(exc), None, None), extra={"event": "verification.log_failed"}
        )


# Menyimpan satu baris log dalam transaksi sendiri (session sinkron, dipanggil dari threadpool).
def _insert_log(row: VerificationLog) -> None:
    with get_session_factory().begin() as db:
        db.add(row)


# Nilai string enum, atau None bila komponen tidak memiliki nilai tersebut.
def _enum_value(value: Enum | None) -> str | None:
    return value.value if value is not None else None


# Komponen proofCheck dan documentHash registry (SA §5.3.1). Kontrak T3-05: pembaca tidak raise. Pengaman kedua
# (DLT-14): exception apa pun, termasuk stub NotImplementedError, menjadi UNAVAILABLE / REGISTRY_UNAVAILABLE (bukan
# NOT_FOUND); stub dicatat dengan reason=not_implemented agar tetap terlihat di log.
async def _proof_check(reference_code: str | None) -> tuple[ProofCheck, str | None]:
    if not reference_code:
        return PROOF_NOT_REQUESTED, None
    try:
        # Bergantung pada T3-05; diuji dengan FakeProofReader.
        read = await proofs_service.read_proof_for_verification(reference_code)
        return read.proof_check, read.registry_document_hash
    except Exception as exc:
        _log_unexpected(
            "proof.read_failed",
            exc,
            reason="not_implemented" if isinstance(exc, NotImplementedError) else "unexpected_error",
            errorCode=ProofReason.REGISTRY_UNAVAILABLE.value,
            lookup=ProofLookup.UNAVAILABLE.value,
        )
        return PROOF_UNAVAILABLE, None


# integrityCheck dari integrity_from; kombinasi mustahil (ValueError, mis. FOUND tanpa hash) menjadi
# NOT_CHECKED / REGISTRY_UNAVAILABLE alih-alih 500.
def _integrity_check(
    mode: VerificationMode, proof_check: ProofCheck, registry_hash: str | None, file: ValidatedFile | None
) -> IntegrityCheck:
    try:
        return integrity_from(mode, proof_check, registry_hash, file.sha256 if file else None)
    except ValueError as exc:
        _log_unexpected(
            "integrity.check_failed",
            exc,
            errorCode=IntegrityReason.REGISTRY_UNAVAILABLE.value,
            lookup=proof_check.lookup.value,
        )
        return IntegrityCheck(
            result=IntegrityResult.NOT_CHECKED, reason=IntegrityReason.REGISTRY_UNAVAILABLE, hash_algorithm=None
        )


# Komponen riskAnalysis (SA §5.3.3). Pengaman kedua: exception tak terduga dari jalur AI menjadi
# UNAVAILABLE / AI_SERVICE_UNAVAILABLE agar proofCheck dan integrityCheck tetap dikembalikan.
async def _risk_analysis(file: ValidatedFile | None, include_risk: bool, request_id: str) -> RiskAnalysis:
    if not include_risk:
        return _without_result(RiskState.NOT_REQUESTED, None)
    if file is None:
        return _without_result(RiskState.NOT_PERFORMED, RiskReason.DOCUMENT_CONTENT_UNAVAILABLE)
    try:
        # Bergantung pada T5-04 (API-08 nyata); diuji dengan FakeAiService.
        return await ai_client.run_risk_pipeline(file.content, request_id)
    except Exception as exc:
        _log_unexpected(
            "ai.pipeline_failed",
            exc,
            errorCode=RiskReason.AI_SERVICE_UNAVAILABLE.value,
            riskState=RiskState.UNAVAILABLE.value,
        )
        return _without_result(RiskState.UNAVAILABLE, RiskReason.AI_SERVICE_UNAVAILABLE)


# Log kegagalan tak terduga: reason (default unexpected_error) dan nama tipe exception saja (exc_info tanpa
# nilai/traceback, sehingga pesan exception yang bisa memuat data tidak pernah tercatat).
def _log_unexpected(event: str, exc: Exception, reason: str = "unexpected_error", **fields: str) -> None:
    logger.error(event, exc_info=(type(exc), None, None), extra={"event": event, "reason": reason, **fields})


# riskAnalysis tanpa hasil: category dan metadata null, sama dengan contoh API-07.
def _without_result(state: RiskState, reason: RiskReason | None) -> RiskAnalysis:
    return RiskAnalysis(
        state=state,
        reason=reason,
        category=None,
        indicators=[],
        indicator_details=[],
        explanation=None,
        recommendation=None,
        extraction_method=None,
        content_truncated=None,
        pages_analyzed=None,
        pages_total=None,
    )
