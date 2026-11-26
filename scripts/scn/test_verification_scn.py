# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: T1-08; SA §18.3
"""Test unit helper T1-08 tanpa stack: ringkasan, sanitasi, target lokal, setup bukti, pemulihan, dan latensi."""

import hashlib

import httpx
import pytest

import _verification_scn as helper
import scn17_double_outage
from _verification_scn import Step, check_ai_subset, evidence_body, masked_code, summarize
from common import ScenarioError, ScenarioSettings
from latency import ai_stop_reason, measure_api07, nearest_rank, stats

SETTINGS = ScenarioSettings("http://127.0.0.1:8000", "hr@lettrust.test", "sandi-uji", "token-uji")

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
    assert stats([], None)["complete"] is False
    assert stats(samples, None)["complete"] is True


@pytest.mark.parametrize("url", ["https://example.com", "http://10.0.0.5:8000", "http://127.0.0.1:8000/api"])
def test_local_settings_rejects_non_loopback_before_compose(monkeypatch: pytest.MonkeyPatch, url: str) -> None:
    """URL non-loopback ditolak sebelum pengecekan port Compose, login, atau token dipakai."""
    monkeypatch.setenv("COMPOSE_PROJECT_NAME", "lettrust")
    monkeypatch.setattr(helper, "load_settings", lambda: ScenarioSettings(url, "hr", "pw", "tok"))
    monkeypatch.setattr(helper, "require_compose_port", lambda *_: pytest.fail("port tidak boleh diperiksa"))
    with pytest.raises(ScenarioError):
        helper.local_settings("lettrust")
    with pytest.raises(ScenarioError):
        helper.local_settings("Proyek Lain")


def proofs_client(monkeypatch: pytest.MonkeyPatch, handler) -> list[str]:
    """Memasang transport palsu untuk httpx.Client di helper dan mencatat method/path setiap request."""
    seen: list[str] = []
    original = httpx.Client

    def recording(request: httpx.Request) -> httpx.Response:
        seen.append(f"{request.method} {request.url.path}?{request.url.query.decode()}")
        return handler(request)

    monkeypatch.setattr(helper, "login_seed_hr", lambda *_: "jwt-uji")
    monkeypatch.setattr(
        helper.httpx, "Client", lambda **kwargs: original(transport=httpx.MockTransport(recording), **kwargs)
    )
    return seen


def test_active_proof_detail_failure_never_issues(monkeypatch: pytest.MonkeyPatch) -> None:
    """Detail 503 menghentikan setup; tidak ada POST penerbitan."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == helper.PROOFS_PATH and request.method == "GET":
            return httpx.Response(200, json={"items": [{"proofId": "0xaa"}], "total": 1})
        if request.method == "GET":
            return httpx.Response(503, json={"error": {"code": "REGISTRY_UNAVAILABLE"}})
        return httpx.Response(201, json={})

    seen = proofs_client(monkeypatch, handler)
    with pytest.raises(ScenarioError):
        helper.ensure_active_proof(SETTINGS)
    assert not [call for call in seen if call.startswith("POST")]


def test_active_proof_scans_every_page(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bukti ACTIVE di halaman kedua dipakai ulang tanpa penerbitan baru."""
    digest = hashlib.sha256(helper.fixture_bytes("FX-01.pdf")).hexdigest()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == helper.PROOFS_PATH and request.method == "GET":
            offset = int(request.url.params["offset"])
            return httpx.Response(200, json={"items": [{"proofId": f"0x{offset + 1}"}], "total": 2})
        if request.method == "GET":
            proof_id = request.url.path.rsplit("/", 1)[-1]
            document = digest if proof_id == "0x2" else "f" * 64
            body = {"proofId": proof_id, "referenceCode": "LTR-AAAA-BBBB-CCCC", "documentHash": document}
            return httpx.Response(200, json={**body, "lifecycleStatus": "ACTIVE", "issueTransaction": None})
        return httpx.Response(201, json={})

    seen = proofs_client(monkeypatch, handler)
    assert helper.ensure_active_proof(SETTINGS).proof_id == "0x2"
    assert not [call for call in seen if call.startswith("POST")]
    assert sum(call.startswith(f"GET {helper.PROOFS_PATH}?") for call in seen) == 2


def test_restore_services_tries_each_service(monkeypatch: pytest.MonkeyPatch) -> None:
    """Kegagalan start chain tidak melewatkan start ai-service; keduanya dilaporkan."""
    calls: list[tuple[str, str]] = []

    def fake_dev(action: str, service: str) -> None:
        calls.append((action, service))
        if service == "chain":
            raise ScenarioError("gagal")

    monkeypatch.setattr(scn17_double_outage, "run_dev_service", fake_dev)
    with pytest.raises(ScenarioError, match="chain"):
        scn17_double_outage.restore_services()
    assert calls == [("start", "chain"), ("start", "ai-service")]


def test_ai_measurement_stops_on_quota() -> None:
    """AI_QUOTA_EXCEEDED menghentikan panggilan AI berikutnya; varian tanpa sukses ditandai tidak lengkap."""
    calls: list[int] = []
    quota = {**BODY, "riskAnalysis": {"state": "UNAVAILABLE", "reason": "AI_QUOTA_EXCEEDED", "category": None}}

    def handler(_: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(200, json=quota)

    with httpx.Client(base_url="http://127.0.0.1:8000", transport=httpx.MockTransport(handler)) as client:
        samples = measure_api07(client, 5, False, 0, lambda a: a.get("riskState") == "COMPLETED", include_risk=True)
    assert len(calls) == len(samples) == 1
    assert ai_stop_reason(samples) == "AI_QUOTA_EXCEEDED"
    assert stats(samples, None)["complete"] is False
