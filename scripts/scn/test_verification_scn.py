# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: T1-08; SA §18.3
"""Test unit helper T1-08 tanpa stack: ringkasan respons, sanitasi evidence, subset indikator, dan statistik latensi."""

import httpx
import pytest

from _verification_scn import Step, check_ai_subset, evidence_body, masked_code, summarize
from latency import nearest_rank, stats

BODY = {
    "verificationId": "VER-0000000000",
    "mode": "AI_ONLY",
    "proofCheck": {"lookup": "NOT_REQUESTED", "reason": "NO_REFERENCE_CODE", "lifecycleStatus": None},
    "integrityCheck": {"result": "NOT_CHECKED", "reason": "NO_REFERENCE_CODE"},
    "riskAnalysis": {
        "state": "COMPLETED",
        "reason": None,
        "category": "HIGH",
        "indicators": ["Permintaan pembayaran kepada pelamar: “bayar Rp1.500.000”"],
        "indicatorDetails": [{"code": "PAYMENT_REQUEST", "evidence": ["bayar Rp1.500.000"]}],
    },
}


def test_summarize_success_and_error() -> None:
    """Ringkasan memuat enum dan kode indikator; respons error hanya memuat kode error."""
    ok = summarize(httpx.Response(200, json=BODY))
    assert (ok["riskState"], ok["category"], ok["indicatorCodes"]) == ("COMPLETED", "HIGH", ["PAYMENT_REQUEST"])
    error = summarize(httpx.Response(400, json={"requestId": "req_X", "error": {"code": "EMPTY_FILE", "message": "x"}}))
    assert error == {"httpStatus": 400, "errorCode": "EMPTY_FILE"}


def test_evidence_body_drops_quotes_without_mutating() -> None:
    """Teks indikator dipotong ke label; body asli tidak berubah."""
    cleaned = evidence_body(BODY)
    assert cleaned["riskAnalysis"]["indicators"] == ["Permintaan pembayaran kepada pelamar"]
    assert "Rp1.500.000" in BODY["riskAnalysis"]["indicators"][0]
    assert masked_code("LTR-AAAA-BBBB-CCCC") == "…CCCC"


@pytest.mark.parametrize(("codes", "present"), [(["PAYMENT_REQUEST", "URGENCY_PRESSURE"], True), (["X"], False)])
def test_ai_subset_extra_is_info(codes: list[str], present: bool) -> None:
    """Indikator label wajib ada; tambahan hanya dicatat di info dan tidak menggagalkan langkah."""
    step = Step("ai", {}, {"riskState": "COMPLETED"}, {"riskState": "COMPLETED", "indicatorCodes": codes})
    check_ai_subset(step, {"PAYMENT_REQUEST"})
    assert step.matches is present
    assert step.info["extraIndicators"] == sorted(set(codes) - {"PAYMENT_REQUEST"})


def test_latency_stats() -> None:
    """P95 nearest rank; target gagal bila ada sampel gagal atau tidak ada sampel sukses."""
    assert nearest_rank([float(v) for v in range(1, 21)], 0.95) == 19.0
    samples = [{"ms": 10.0, "ok": True}, {"ms": 30.0, "ok": True}]
    assert stats(samples, 50)["meetsTarget"] is True
    assert stats([*samples, {"ms": 1.0, "ok": False}], 50)["meetsTarget"] is False
    assert stats([{"ms": 1.0, "ok": False}], 50)["meetsTarget"] is False
    assert stats(samples, None)["meetsTarget"] is None
