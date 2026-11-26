# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: PRD NFR-03.01–03.02, MET-16, MET-17; SA §17.5, §18.3
"""Mengukur median dan P95 API-07 (empat varian NFR-03.01) serta API-04/API-06 (MET-17) pada stack nyata.

Waktu diukur di klien (perf_counter sekitar satu request HTTP lokal), sehingga mencakup backend, registry, dan
ai-service tetapi bukan jeda antarpermintaan. P95 memakai nearest rank ceil(0,95 × n). Sampel gagal tidak masuk
statistik dan dilaporkan terpisah. Penerbitan memakai HR seed dengan salinan FX-01 unik lalu langsung dicabut.
"""

from __future__ import annotations

import argparse
import math
import secrets
import statistics
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import httpx

from _verification_scn import (
    PROOFS_PATH,
    active_llm_model,
    add_target_argument,
    ensure_active_proof,
    fixture_bytes,
    health_component,
    local_settings,
    partner_client,
    post_verification,
    response_body,
    summarize,
)
from common import (
    ROOT,
    ScenarioError,
    login_seed_hr,
    new_request_id,
    print_expected_actual,
    save_evidence,
)

TEST_CASE = "TC-023"
# Target NFR-03 / MET-17 dalam milidetik; None = diukur dan dilaporkan tanpa target (Open).
TARGETS_MS = {
    "api07CodeOnly": 2000,
    "api07CodeAndFile": 3000,
    "api07AiTextPdf": None,
    "api07AiScanPdf": None,
    "api04Issue": 5000,
    "api06Revoke": 5000,
}
# Alasan AI yang tidak akan pulih dalam satu run; panggilan AI berikutnya dihentikan agar kuota tidak dihabiskan.
# API-07 memetakan provider belum dikonfigurasi dan ai-service mati ke AI_SERVICE_UNAVAILABLE; keduanya juga dicegah
# lebih awal oleh pemeriksaan health `aiService` sebelum varian AI.
AI_STOP_REASONS = {"AI_QUOTA_EXCEEDED", "AI_SERVICE_UNAVAILABLE"}


def nearest_rank(values: list[float], percentile: float) -> float:
    """Persentil nearest rank pada sampel terurut."""
    ordered = sorted(values)
    return ordered[max(1, math.ceil(percentile * len(ordered))) - 1]


def stats(samples: list[dict[str, Any]], target: int | None) -> dict[str, Any]:
    """Ringkasan sampel sukses: n, median, P95, min, maks, kegagalan, status target, dan kelengkapan.

    Varian tanpa satu pun sampel sukses ditandai `complete=False` (pengukuran tidak lengkap, bukan lulus).
    """
    ok = [sample["ms"] for sample in samples if sample["ok"]]
    result: dict[str, Any] = {
        "samples": len(samples),
        "succeeded": len(ok),
        "failed": len(samples) - len(ok),
        "complete": bool(ok),
    }
    if ok:
        result.update(
            medianMs=round(statistics.median(ok), 1),
            p95Ms=round(nearest_rank(ok, 0.95), 1),
            minMs=round(min(ok), 1),
            maxMs=round(max(ok), 1),
        )
    result["targetP95Ms"] = target
    if target is None:
        result["meetsTarget"] = None
    else:
        result["meetsTarget"] = bool(ok) and not result["failed"] and result["p95Ms"] <= target
    return result


def measure_api07(
    client: httpx.Client, count: int, warmup: bool, interval: float, accept: Callable[[dict], bool], **kwargs: Any
) -> list[dict[str, Any]]:
    """Menjalankan API-07 `count` kali; pemanasan opsional tidak dicatat; berhenti bila AI_STOP_REASONS muncul."""
    if warmup:
        post_verification(client, **kwargs)
    samples = []
    for index in range(count):
        if index and interval:
            time.sleep(interval)
        response, request, elapsed = post_verification(client, **kwargs)
        actual = summarize(response)
        samples.append({"requestId": request["requestId"], "ms": round(elapsed, 1), "ok": accept(actual), **actual})
        if actual.get("riskReason") in AI_STOP_REASONS:
            break
    return samples


def ai_stop_reason(samples: list[dict[str, Any]]) -> str | None:
    """Alasan penghentian AI dari sampel terakhir, bila ada."""
    reason = samples[-1].get("riskReason") if samples else None
    return reason if reason in AI_STOP_REASONS else None


def measure_issue_revoke(settings: Any, count: int) -> tuple[list[dict], list[dict]]:
    """API-04 lalu API-06 untuk `count` salinan FX-01 unik; respons sampai receipt terkonfirmasi (SA §6.5)."""
    base = fixture_bytes("FX-01.pdf")
    issues, revokes = [], []
    with httpx.Client(base_url=settings.api_base_url, timeout=60, trust_env=False) as client:
        headers = {"Authorization": f"Bearer {login_seed_hr(client, settings)}"}
        for _ in range(count):
            content = base + f"\n%lettrust-latency-{secrets.token_hex(8)}\n".encode()
            started = time.perf_counter()
            issued = client.post(
                PROOFS_PATH,
                headers={**headers, "X-Request-ID": new_request_id(), "Idempotency-Key": secrets.token_hex(12)},
                files={"file": ("latency.pdf", content, "application/pdf")},
            )
            elapsed = (time.perf_counter() - started) * 1000
            body = response_body(issued) or {}
            ok = issued.status_code == 201 and body.get("lifecycleStatus") == "ACTIVE"
            issues.append(
                {
                    "ms": round(elapsed, 1),
                    "ok": ok,
                    "httpStatus": issued.status_code,
                    "proofId": body.get("proofId"),
                    "transaction": body.get("transaction"),
                    "errorCode": (body.get("error") or {}).get("code"),
                }
            )
            if not ok:
                continue
            started = time.perf_counter()
            revoked = client.post(
                f"{PROOFS_PATH}/{body['proofId']}/revocations",
                headers={**headers, "X-Request-ID": new_request_id(), "Idempotency-Key": secrets.token_hex(12)},
                json={"reasonCode": "OFFER_WITHDRAWN"},
            )
            elapsed = (time.perf_counter() - started) * 1000
            rbody = response_body(revoked) or {}
            revokes.append(
                {
                    "ms": round(elapsed, 1),
                    "ok": revoked.status_code == 201 and rbody.get("lifecycleStatus") == "REVOKED",
                    "httpStatus": revoked.status_code,
                    "proofId": body["proofId"],
                    "transaction": rbody.get("transaction"),
                    "errorCode": (rbody.get("error") or {}).get("code"),
                }
            )
    return issues, revokes


def parse_args() -> argparse.Namespace:
    """Jumlah sampel per varian; AI dibatasi kecil karena memakai kuota LLM nyata."""
    parser = argparse.ArgumentParser(description="Ukur MET-16 dan MET-17 pada stack lokal.")
    parser.add_argument("--samples", type=int, default=20, help="Sampel API-07 tanpa AI per varian.")
    parser.add_argument("--ai-samples", type=int, default=5, help="Sampel API-07 dengan AI per varian (LLM nyata).")
    parser.add_argument("--ai-interval", type=float, default=5, help="Jeda detik antarpanggilan AI (di luar ukuran).")
    parser.add_argument("--issue-samples", type=int, default=5, help="Pasangan API-04/API-06 (HR seed).")
    add_target_argument(parser)
    args = parser.parse_args()
    if min(args.samples, args.ai_samples, args.issue_samples) < 1 or args.ai_interval < 0:
        parser.error("Jumlah sampel minimal 1 dan jeda tidak boleh negatif.")
    return args


def main() -> int:
    """Menjalankan seluruh varian, menyimpan evidence tanpa kode referensi, dan mencetak target vs aktual."""
    args = parse_args()
    started = datetime.now(UTC)
    ai_stopped = None
    try:
        settings = local_settings(args.compose_project)
        proof = ensure_active_proof(settings)
        fx01 = ("FX-01.pdf", fixture_bytes("FX-01.pdf"))
        found = lambda a: a.get("httpStatus") == 200 and a.get("lookup") == "FOUND"  # noqa: E731
        completed = lambda a: a.get("httpStatus") == 200 and a.get("riskState") == "COMPLETED"  # noqa: E731
        with partner_client(settings) as client:
            samples = {
                "api07CodeOnly": measure_api07(
                    client, args.samples, True, 0, found, code=proof.reference_code, include_risk=False
                ),
                "api07CodeAndFile": measure_api07(
                    client,
                    args.samples,
                    True,
                    0,
                    lambda a: found(a) and a.get("integrityResult") == "MATCH",
                    code=proof.reference_code,
                    file=fx01,
                    include_risk=False,
                ),
            }
            # Tanpa LLM terkonfigurasi atau ai-service sehat, varian AI tidak dipanggil sama sekali.
            ai_health = health_component(client, "aiService")
            ai_stopped = None if ai_health == "ok" else f"HEALTH_AI_SERVICE_{str(ai_health).upper()}"
            for name, fixture in (("api07AiTextPdf", "FX-03.pdf"), ("api07AiScanPdf", "FX-04.pdf")):
                samples[name] = (
                    []
                    if ai_stopped
                    else measure_api07(
                        client,
                        args.ai_samples,
                        False,
                        args.ai_interval,
                        completed,
                        file=(fixture, fixture_bytes(fixture)),
                        include_risk=True,
                    )
                )
                ai_stopped = ai_stopped or ai_stop_reason(samples[name])
        samples["api04Issue"], samples["api06Revoke"] = measure_issue_revoke(settings, args.issue_samples)
    except ScenarioError as exc:
        print(f"Pengukuran latensi tidak dapat dijalankan: {exc}", file=sys.stderr)
        return 2
    except httpx.HTTPError as exc:
        print(f"Request gagal ({type(exc).__name__}).", file=sys.stderr)
        return 2
    results = {name: stats(items, TARGETS_MS[name]) for name, items in samples.items()}
    incomplete = [name for name, result in results.items() if not result["complete"]]
    evidence = {
        "testCaseId": TEST_CASE,
        "metrics": ["MET-16", "MET-17"],
        "startedAtUtc": started.isoformat(),
        "finishedAtUtc": datetime.now(UTC).isoformat(),
        "method": {
            "clock": "time.perf_counter di klien host, satu request HTTP ke backend lokal",
            "percentile": "P95 nearest rank ceil(0,95 × n); median statistik biasa",
            "warmup": "Satu permintaan pemanasan tidak dicatat untuk varian tanpa AI",
            "aiInterval": f"{args.ai_interval} detik antarpanggilan AI, di luar pengukuran",
            "fixtures": {
                "codeOnly": "kode FX-01",
                "codeAndFile": "kode + FX-01",
                "aiText": "FX-03",
                "aiScan": "FX-04",
                "issue": "salinan FX-01 unik oleh HR seed, lalu dicabut",
            },
        },
        "model": active_llm_model(),
        "activeProof": {"proofId": proof.proof_id, "issueTransaction": proof.issue_transaction},
        "complete": not incomplete,
        "incompleteVariants": incomplete,
        "aiStoppedReason": ai_stopped,
        "results": results,
        "samples": samples,
    }
    path = save_evidence(
        TEST_CASE,
        f"latency-{started.strftime('%Y%m%d-%H%M%S%f')}.json",
        evidence,
        sensitive_values=(settings.partner_token, settings.seed_hr_password, proof.reference_code),
    )
    print_expected_actual(
        {name: {"targetP95Ms": target} for name, target in TARGETS_MS.items()},
        {
            name: {
                key: result.get(key) for key in ("complete", "succeeded", "failed", "medianMs", "p95Ms", "meetsTarget")
            }
            for name, result in results.items()
        },
    )
    print(f"Evidence tersimpan: {path.relative_to(ROOT).as_posix()}")
    if ai_stopped:
        print(f"Panggilan AI dihentikan karena {ai_stopped}.", file=sys.stderr)
    if incomplete:
        print(f"Pengukuran tidak lengkap; tanpa sampel sukses: {', '.join(incomplete)}.", file=sys.stderr)
        return 2
    return 0 if all(result["meetsTarget"] is not False for result in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
