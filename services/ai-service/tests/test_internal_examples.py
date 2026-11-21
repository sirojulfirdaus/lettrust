# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: SA §7.2, §10.2, §10.3, §10.8
"""Setiap contoh internal (service=ai-service) di contracts/examples/index.json valid terhadap skema ai-service."""

import inspect
import json
import os
from pathlib import Path

import pytest
from pydantic import BaseModel

from app import schemas as ai_schemas
from app.analysis.taxonomy import TAXONOMY
from app.core import errors as ai_errors


# Folder contracts/examples (env CONTRACTS_DIR di container, atau relatif repo saat native).
def examples_dir() -> Path:
    base = (
        Path(os.environ["CONTRACTS_DIR"])
        if os.environ.get("CONTRACTS_DIR")
        else Path(__file__).parents[3] / "contracts"
    )
    return base / "examples"


# Memuat contoh JSON relatif terhadap contracts/examples.
def load(relative: str):
    return json.loads((examples_dir() / relative).read_text(encoding="utf-8"))


MODELS: dict[str, type[BaseModel]] = {
    name: cls
    for module in (ai_schemas, ai_errors)
    for name, cls in inspect.getmembers(module, inspect.isclass)
    if issubclass(cls, BaseModel)
}
INTERNAL = [e for e in load("index.json")["examples"] if e.get("service") == "ai-service"]


# Contoh internal mencakup I-01, API-08 (request/response), I-02, dan error envelope.
def test_internal_examples_cover_endpoints():
    files = {entry["file"] for entry in INTERNAL}
    assert all(f.startswith("internal/") for f in files)
    for prefix in (
        "internal/i-01.",
        "internal/api-08.request",
        "internal/api-08.response",
        "internal/i-02.",
        "internal/error.",
    ):
        assert any(f.startswith(prefix) for f in files), prefix


# Setiap contoh internal tervalidasi penuh dan round-trip identik.
@pytest.mark.parametrize("entry", INTERNAL, ids=lambda e: e["file"])
def test_internal_example_matches_schema(entry):
    data = load(entry["file"])
    model = MODELS[entry["schema"]].model_validate(data)
    assert model.model_dump(by_alias=True, mode="json") == data


# Contoh API-08 memakai kode, label, dan tingkat dari taksonomi (PRD §8.4, §9.6.3).
@pytest.mark.parametrize(
    "entry", [e for e in INTERNAL if e["schema"] == "RiskAnalysisResponse"], ids=lambda e: e["file"]
)
def test_risk_examples_follow_taxonomy(entry):
    for detail in load(entry["file"])["indicatorDetails"]:
        indicator = TAXONOMY[detail["code"]]
        assert (detail["label"], detail["severity"]) == (indicator.label, indicator.severity.value)


# Contoh error internal memakai pesan default dan HTTP status katalog ai-service.
@pytest.mark.parametrize("entry", [e for e in INTERNAL if e["schema"] == "ErrorEnvelope"], ids=lambda e: e["file"])
def test_internal_error_matches_catalog(entry):
    error = load(entry["file"])["error"]
    code = ai_errors.ErrorCode(error["code"])
    assert error["message"] == ai_errors.DEFAULT_MESSAGES[code]
    assert entry["httpStatus"] == ai_errors.ERROR_HTTP_STATUS[code]
