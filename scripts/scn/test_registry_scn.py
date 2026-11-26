# Owner: Sat (PIC 6) | Status: COMPLETE | Ref: T6-06; SA §18.3; PRD §12.5
"""Regresi pengaman skrip registry; mock hanya dipakai dalam unit test, bukan evidence SCN."""

import json
import subprocess
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

import _registry_scn as helper
import common

PROOF = "0x" + "1" * 64
TX = "0x" + "2" * 64
ADDRESS = "0x" + "3" * 40


@pytest.fixture
def scenario() -> Iterator[helper.Scenario]:
    """Membuat konteks lokal tanpa jaringan, kredensial pengguna, atau mutasi stack."""
    with httpx.Client(
        base_url="http://127.0.0.1", transport=httpx.MockTransport(lambda request: httpx.Response(200, json={}))
    ) as client:
        registry = SimpleNamespace(address=ADDRESS)
        report = {"checks": [], "requests": [], "transactions": []}
        yield helper.Scenario(client, client, registry, report, [])


def test_failed_check_is_recorded(scenario: helper.Scenario) -> None:
    """Kegagalan tetap menyimpan expected/actual yang dapat dievaluasi manusia."""
    with pytest.raises(common.ScenarioError):
        scenario.check("lifecycle", "ACTIVE", "REVOKED")
    assert scenario.report["checks"] == [
        {"name": "lifecycle", "expected": "ACTIVE", "actual": "REVOKED", "matches": False}
    ]


@pytest.mark.parametrize("failure", [None, "body", "stop"])
def test_chain_is_restarted_on_failure(
    scenario: helper.Scenario, monkeypatch: pytest.MonkeyPatch, failure: str | None
) -> None:
    """Chain tetap dicoba dipulihkan ketika stop gagal atau pemeriksaan di tengah outage gagal."""
    calls = []

    def control(action: str, service: str) -> None:
        """Mencatat stop/start sintetis tanpa memanggil Docker."""
        calls.append((action, service))
        if failure == "stop" and action == "stop":
            raise common.ScenarioError("stop failed")

    monkeypatch.setattr(helper, "run_dev_service", control)
    monkeypatch.setattr(scenario, "wait_ready", lambda: calls.append(("ready", "chain")))
    if failure is None:
        with scenario.chain_outage():
            calls.append(("body", "chain"))
    else:
        with pytest.raises(common.ScenarioError):
            with scenario.chain_outage():
                raise common.ScenarioError("body failed")
    assert calls[0] == ("stop", "chain")
    assert calls[-2:] == [("start", "chain"), ("ready", "chain")]


@pytest.mark.parametrize("down_fails", [False, True])
def test_stack_is_restored_even_when_down_fails(
    scenario: helper.Scenario, monkeypatch: pytest.MonkeyPatch, down_fails: bool
) -> None:
    """Restart normal selalu mencoba up tanpa reset atau penghapusan volume."""
    calls = []

    def dev(action: str) -> None:
        """Menyimulasikan down yang dapat gagal sebagian."""
        calls.append(action)
        if action == "down" and down_fails:
            raise common.ScenarioError("down failed")

    monkeypatch.setattr(scenario, "dev", dev)
    monkeypatch.setattr(scenario, "wait_ready", lambda: calls.append("ready"))
    if down_fails:
        with pytest.raises(common.ScenarioError):
            scenario.restart_stack()
    else:
        scenario.restart_stack()
    assert calls == ["down", "up", "ready"]


@pytest.mark.parametrize("action", ["reset", "up --build", "down -v"])
def test_stack_rejects_unsupported_actions(scenario: helper.Scenario, action: str) -> None:
    """Wrapper restart menolak penghapusan volume dan penyisipan argumen tambahan."""
    with pytest.raises(common.ScenarioError):
        scenario.dev(action)


@pytest.mark.parametrize("defect", ["status", "hash", "block", "contract", "duplicates", "event_hash", None])
def test_receipt_and_event_must_match_api(
    scenario: helper.Scenario, monkeypatch: pytest.MonkeyPatch, defect: str | None
) -> None:
    """Receipt gagal atau event ganda tidak boleh dianggap bukti transaksi API yang sah."""
    receipt = {"status": "0x1", "transactionHash": TX, "blockNumber": "0xc", "to": ADDRESS}
    event = {"transactionHash": TX, "blockNumber": "0xc"}
    if defect == "status":
        receipt["status"] = "0x0"
    elif defect == "hash":
        receipt["transactionHash"] = PROOF
    elif defect == "block":
        receipt["blockNumber"] = "0xd"
    elif defect == "contract":
        receipt["to"] = "0x" + "4" * 40
    elif defect == "event_hash":
        event["transactionHash"] = PROOF
    scenario.registry.cast = lambda *args: json.dumps(receipt)
    monkeypatch.setattr(scenario, "events", lambda *_args: [event, event] if defect == "duplicates" else [event])
    body = {"proofId": PROOF, "transaction": {"hash": TX, "blockNumber": 12}}
    if defect is None:
        scenario.confirmed(body, "ProofIssued")
        assert scenario.report["transactions"][0]["hash"] == TX
    else:
        with pytest.raises(common.ScenarioError):
            scenario.confirmed(body, "ProofIssued")
        assert scenario.report["transactions"] == []


@pytest.mark.parametrize("proof,event", [("--help", "ProofIssued"), (PROOF, "UnknownEvent")])
def test_event_filter_is_validated(scenario: helper.Scenario, proof: str, event: str) -> None:
    """Filter Cast tidak boleh menerima proofId atau nama event di luar kontrak."""
    with pytest.raises(common.ScenarioError):
        scenario.events(proof, event)


def test_no_reactivation_report_is_json_serializable(
    scenario: helper.Scenario, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pemeriksaan endpoint/ABI harus menghasilkan evidence JSON, bukan set Python yang tidak terserialisasi."""
    schema = {"paths": {helper.PROOFS: {"post": {}}, f"{helper.PROOFS}/{{proofId}}/revocations": {"post": {}}}}
    abi_path = tmp_path / "services/backend/app/modules/registry/abi/OfferProofRegistry.json"
    abi_path.parent.mkdir(parents=True)
    abi_path.write_text(
        json.dumps(
            [{"type": "function", "name": name} for name in ["getProof", "issueProof", "registrar", "revokeProof"]]
        )
    )
    monkeypatch.setattr(helper, "ROOT", tmp_path)
    monkeypatch.setattr(
        helper, "command_result", lambda *_args: subprocess.CompletedProcess([], 1, "", "execution reverted")
    )
    scenario.registry.cast_command, scenario.registry.rpc_args, scenario.registry.registrar = (), (), ADDRESS
    with httpx.Client(
        base_url="http://127.0.0.1", transport=httpx.MockTransport(lambda request: httpx.Response(200, json=schema))
    ) as client:
        scenario.client = client
        scenario.no_reactivation(PROOF)
    json.dumps(scenario.report)
    assert all(check["matches"] for check in scenario.report["checks"])


@pytest.mark.parametrize("arguments", [[], ["--allow-service-interruption", "--compose-project", "../other"]])
def test_cli_rejects_unsafe_arguments_before_setup(monkeypatch: pytest.MonkeyPatch, arguments: list[str]) -> None:
    """CLI tanpa izin interupsi atau nama project valid berhenti sebelum membaca credential/mengubah stack."""
    monkeypatch.setattr("sys.argv", ["scn", *arguments])

    def forbidden_settings() -> None:
        """Mendeteksi akses credential yang seharusnya belum diizinkan oleh validasi argumen."""
        pytest.fail("Settings tidak boleh dibaca untuk argumen yang ditolak.")

    monkeypatch.setattr(helper, "load_settings", forbidden_settings)
    with pytest.raises(SystemExit) as error:
        helper.run_cli("SCN-15", "TC-015", lambda run: None)
    assert error.value.code == 2


@pytest.mark.parametrize("fail", [False, True])
def test_cli_sanitizes_evidence_and_failure_without_corrupting_hashes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], fail: bool
) -> None:
    """Nilai konfigurasi biasa tidak menyamarkan hash; secret dan pesan exception tidak bocor ke evidence/stdout."""
    secret = "synthetic-secret-t606"
    settings = common.ScenarioSettings("http://127.0.0.1:8000", "hr@example.test", secret, secret)
    monkeypatch.setattr(helper, "ROOT", tmp_path)
    monkeypatch.setattr(common, "EVIDENCE_ROOT", tmp_path / "docs/testing/evidence")
    monkeypatch.setattr(helper, "load_settings", lambda: settings)
    monkeypatch.setattr(
        helper, "_read_env", lambda path: {"SEED_ADMIN_PASSWORD": secret, "APP_ENV": "local", "OCR_DPI": "300"}
    )
    monkeypatch.setattr(helper, "Registry", lambda *_args: SimpleNamespace(address=ADDRESS))
    monkeypatch.setattr(helper, "require_compose_port", lambda *_args: None)
    monkeypatch.setattr(helper.Scenario, "wait_ready", lambda self: None)
    monkeypatch.setattr(helper.Scenario, "setup", lambda *_args: None)
    monkeypatch.setattr("sys.argv", ["scn", "--allow-service-interruption"])
    monkeypatch.delenv("COMPOSE_PROJECT_NAME", raising=False)
    monkeypatch.delenv("SEED_ADMIN_PASSWORD", raising=False)

    def execute(run: helper.Scenario) -> None:
        """Menyisipkan secret sintetis hanya untuk menguji redaksi hasil dan exception."""
        run.report["sample"] = {
            "accessToken": secret,
            "referenceCode": "LTR-SYNTHETIC",
            "documentHash": "300" + "0" * 61,
        }
        run.check("synthetic", True, True)
        if fail:
            raise ValueError(secret)

    assert helper.run_cli("SCN-15", "TC-015", execute) == (1 if fail else 0)
    saved = list((tmp_path / "docs/testing/evidence/TC-015").glob("*.json"))
    assert len(saved) == 1
    contents = saved[0].read_text()
    record: dict[str, Any] = json.loads(contents)
    assert secret not in contents
    assert record["sample"]["accessToken"] == record["sample"]["referenceCode"] == "[DIHAPUS]"
    assert record["sample"]["documentHash"] == "300" + "0" * 61
    assert record["completed"] is not fail
    output = capsys.readouterr()
    assert secret not in output.out + output.err
