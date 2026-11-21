# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: SA §10, §20.2
"""Setiap contoh publik di contracts/examples/index.json valid terhadap skema Pydantic backend dan komponen OpenAPI."""

import inspect

import pytest
from fakes.contracts import example_index, examples_dir, load_example
from pydantic import BaseModel

from app.core import errors as core_errors
from app.core import schemas as core_schemas
from app.main import app
from app.modules.auth import schemas as auth_schemas
from app.modules.health import schemas as health_schemas
from app.modules.issuers import schemas as issuer_schemas
from app.modules.proofs import schemas as proof_schemas
from app.modules.verifications import schemas as verification_schemas

MODELS: dict[str, type[BaseModel]] = {
    name: cls
    for module in (core_schemas, auth_schemas, issuer_schemas, proof_schemas, verification_schemas, health_schemas)
    for name, cls in inspect.getmembers(module, inspect.isclass)
    if issubclass(cls, BaseModel)
}
ENTRIES = example_index()
PUBLIC = [entry for entry in ENTRIES if entry.get("service", "backend") == "backend"]
APPS = {"issuer-console", "partner-portal"}


# Setiap berkas JSON di contracts/examples (termasuk internal/) terdaftar tepat sekali di index.json.
def test_every_example_file_is_indexed():
    files = sorted(
        path.relative_to(examples_dir()).as_posix()
        for path in examples_dir().rglob("*.json")
        if path.name != "index.json"
    )
    indexed = [entry["file"] for entry in ENTRIES]
    assert len(indexed) == len(set(indexed)), "entri index.json duplikat"
    assert files == sorted(indexed)


# Set contoh publik mencakup sukses setiap endpoint SA §10.4 (kecuali API-04/API-07 multipart request).
def test_every_endpoint_has_success_example():
    prefixes = {entry["file"].split(".")[0] for entry in PUBLIC if not entry["file"].startswith("error.")}
    expected = {f"s-0{i}" for i in range(1, 8)} | {f"api-0{i}" for i in range(1, 8)}
    assert expected <= prefixes


# Setiap contoh publik tervalidasi penuh (field tak dikenal ditolak) dan round-trip identik.
@pytest.mark.parametrize("entry", PUBLIC, ids=lambda e: e["file"])
def test_example_matches_schema(entry):
    assert entry["schema"] in MODELS, f"skema {entry['schema']} tidak ada di backend"
    data = load_example(entry["file"])
    model = MODELS[entry["schema"]].model_validate(data)
    assert model.model_dump(by_alias=True, mode="json") == data


# Nama skema contoh untuk frontend harus ada sebagai komponen OpenAPI (dipakai fixture TypeScript `satisfies`).
@pytest.mark.parametrize("entry", [e for e in PUBLIC if e.get("apps")], ids=lambda e: e["file"])
def test_fixture_schema_is_openapi_component(entry):
    assert set(entry["apps"]) <= APPS
    assert entry["schema"] in app.openapi()["components"]["schemas"]


# Contoh error memakai pesan default dan HTTP status katalog backend (SA §10.3).
@pytest.mark.parametrize("entry", [e for e in PUBLIC if e["schema"] == "ErrorEnvelope"], ids=lambda e: e["file"])
def test_error_example_matches_catalog(entry):
    error = load_example(entry["file"])["error"]
    code = core_schemas.ErrorCode(error["code"])
    assert error["message"] == core_errors.DEFAULT_MESSAGES[code]
    assert entry["httpStatus"] == core_errors.ERROR_HTTP_STATUS[code]
