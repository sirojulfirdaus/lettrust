# Owner: B (PIC 5) | Status: COMPLETE | Ref: PRD FR-05.07; SA §7.7
"""Komposisi respons API-08 dari indikator tervalidasi dan kategori."""

import re

from app.analysis.taxonomy import TAXONOMY
from app.analysis.validator import ValidatedIndicator
from app.schemas import AnalysisMeta, IndicatorDetail, RiskAnalysisResponse, RiskCategory

# Penjelasan yang memakai kosakata vonis diganti templat agar tidak menjadi klaim dari model.
_VERDICT_WORDS = re.compile(r"\b(asli|palsu|aman|penipuan|authentic|fake|safe|scam|fraud)\b", re.IGNORECASE)


# Menyusun rekomendasi deterministik: selalu kanal resmi; + larangan bayar/beri data sesuai indikator; + catatan LOW.
def build_recommendation(category: RiskCategory, codes: set[str]) -> str:
    parts = []
    if "PAYMENT_REQUEST" in codes:
        parts.append("Jangan melakukan pembayaran apa pun untuk proses rekrutmen.")
    if "SENSITIVE_DATA_REQUEST" in codes:
        parts.append("Jangan memberikan OTP, PIN, password, atau data dan akses sensitif.")
    parts.append("Konfirmasikan penawaran melalui situs atau kontak resmi perusahaan yang Anda cari sendiri.")
    if category is RiskCategory.LOW:
        parts.append("Risiko rendah tidak menjamin surat aman.")
    return " ".join(parts)


# Menyusun RiskAnalysisResponse lengkap; label indikator diambil dari taksonomi.
def compose_result(
    indicators: list[ValidatedIndicator], category: RiskCategory, model_explanation: str | None, meta: AnalysisMeta
) -> RiskAnalysisResponse:
    details = [
        IndicatorDetail(
            code=item.code,
            label=TAXONOMY[item.code].label,
            severity=TAXONOMY[item.code].severity,
            evidence=list(item.evidence),
        )
        for item in indicators
    ]
    explanation = model_explanation.strip() if model_explanation else ""
    # Model dapat masih menjelaskan bukti yang dibuang; templat hanya merujuk indikator yang lolos.
    if (
        not details
        or meta.dropped_indicators
        or not explanation
        or len(explanation) > 600
        or len(re.split(r"(?<=[.!?])\s+", explanation)) > 3
        or _VERDICT_WORDS.search(explanation)
    ):
        explanation = (
            "Indikator yang ditemukan: " + "; ".join(item.label for item in details) + "."
            if details
            else "Tidak ditemukan pola dari daftar indikator."
        )
    return RiskAnalysisResponse(
        category=category,
        indicators=[f"{item.label}: “{item.evidence[0]}”" for item in details],
        indicator_details=details,
        explanation=explanation,
        recommendation=build_recommendation(category, {item.code for item in details}),
        meta=meta,
    )
