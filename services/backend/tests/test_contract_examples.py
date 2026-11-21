# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: SA §10.7, §20.2
"""Setiap berkas contracts/examples/*.json harus valid terhadap skema Pydantic kontrak."""

import json
import os
from pathlib import Path

import pytest
from pydantic import BaseModel

from app.core.schemas import ErrorEnvelope
from app.modules.auth.schemas import MeResponse
from app.modules.proofs.schemas import IssueProofResponse, ProofStatusResponse
from app.modules.verifications.schemas import VerificationResponse

# Prefiks nama berkas contoh → skema respons. Contoh baru wajib memakai salah satu prefiks ini.
SCHEMA_BY_PREFIX: dict[str, type[BaseModel]] = {
    "api-04.": IssueProofResponse,
    "api-05.": ProofStatusResponse,
    "api-07.": VerificationResponse,
    "s-03.": MeResponse,
    "error.": ErrorEnvelope,
}


# Menentukan folder contracts/examples (env CONTRACTS_DIR di container, atau relatif repo saat native).
def examples_dir() -> Path:
    base = (
        Path(os.environ["CONTRACTS_DIR"])
        if os.environ.get("CONTRACTS_DIR")
        else Path(__file__).resolve().parents[3] / "contracts"
    )
    return base / "examples"


EXAMPLES = sorted(examples_dir().glob("*.json"))


# Folder contoh harus ada dan berisi contoh API-07 SA §10.7.3–§10.7.6.
def test_examples_present():
    names = {path.name for path in EXAMPLES}
    assert len([n for n in names if n.startswith("api-07.")]) >= 4, f"contoh API-07 kurang di {examples_dir()}"
    assert {"api-04.", "api-05.", "s-03.", "error."} <= {
        next(p for p in SCHEMA_BY_PREFIX if n.startswith(p)) for n in names
    }


# Setiap contoh tervalidasi penuh (field tak dikenal ditolak) terhadap skemanya.
@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name)
def test_example_matches_schema(path: Path):
    prefix = next((p for p in SCHEMA_BY_PREFIX if path.name.startswith(p)), None)
    assert prefix is not None, f"{path.name} tidak memakai prefiks yang dikenal: {list(SCHEMA_BY_PREFIX)}"
    data = json.loads(path.read_text(encoding="utf-8"))
    model = SCHEMA_BY_PREFIX[prefix].model_validate(data)
    assert model.model_dump(by_alias=True, mode="json") == data
