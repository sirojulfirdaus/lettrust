# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: SA §10.7, §20.2
"""Akses contracts/examples dan index.json (satu-satunya pemetaan contoh → skema)."""

import json
import os
from pathlib import Path
from typing import Any


# Folder contracts/ (env CONTRACTS_DIR di container, atau relatif repo saat native).
def contracts_dir() -> Path:
    if os.environ.get("CONTRACTS_DIR"):
        return Path(os.environ["CONTRACTS_DIR"])
    parents = Path(__file__).resolve().parents
    if len(parents) > 4 and (parents[4] / "contracts").is_dir():
        return parents[4] / "contracts"
    raise RuntimeError("contracts/ tidak ditemukan; set CONTRACTS_DIR (python scripts/dev.py test memasang /contracts)")


# Folder contracts/examples.
def examples_dir() -> Path:
    return contracts_dir() / "examples"


# Daftar entri index.json: {file, schema, apps?, service?}.
def example_index() -> list[dict[str, Any]]:
    return json.loads((examples_dir() / "index.json").read_text(encoding="utf-8"))["examples"]


# Memuat satu contoh JSON berdasarkan path relatif terhadap contracts/examples.
def load_example(relative_path: str) -> Any:
    return json.loads((examples_dir() / relative_path).read_text(encoding="utf-8"))
