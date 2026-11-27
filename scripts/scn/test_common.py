# Owner: Pash (PIC 4) | Status: COMPLETE | Ref: PRD §12.5; SA §18.3, §21.2
"""Memastikan sanitasi evidence menjaga anotasi hasil yang tidak sensitif."""

import json
from pathlib import Path

import pytest

import common
from scn02_mismatch import evidence_filename


# Menyimpan evidence sementara dan memastikan indikator tetap ada sementara kutipan disamarkan.
def test_save_evidence_keeps_indicator_codes_and_redacts_quotes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(common, "EVIDENCE_ROOT", tmp_path)
    evidence = {
        "response": {
            "riskAnalysis": {
                "indicators": ["PAYMENT_REQUEST"],
                "indicatorDetails": [{"code": "PAYMENT_REQUEST", "severity": "HIGH", "evidence": ["synthetic quote"]}],
            }
        }
    }

    path = common.save_evidence("TC-002", evidence_filename(), evidence)
    saved = json.loads(path.read_text(encoding="utf-8"))

    assert saved["response"]["riskAnalysis"]["indicators"] == ["PAYMENT_REQUEST"]
    indicator = saved["response"]["riskAnalysis"]["indicatorDetails"][0]
    assert indicator["code"] == "PAYMENT_REQUEST"
    assert indicator["severity"] == "HIGH"
    assert indicator["evidence"] == "[DIHAPUS]"
