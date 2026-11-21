#!/usr/bin/env python3
# Owner: Sat (PIC 6) | Status: COMPLETE | Ref: SA §6.4
"""Mengekspor ABI OfferProofRegistry dari build Foundry ke modul registry backend."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "services" / "backend" / "app" / "modules" / "registry" / "abi" / "OfferProofRegistry.json"


# Menjalankan `forge inspect` di image chain-deployer dan mengembalikan ABI JSON apa adanya.
def inspect_abi() -> str:
    compose = ["docker", "compose", "-f", str(ROOT / "compose.yaml")]
    build = subprocess.run(compose + ["build", "chain-deployer"], cwd=str(ROOT), check=False)
    if build.returncode != 0:
        raise SystemExit("Build image chain-deployer gagal.")
    cmd = compose + ["run", "--rm", "--no-deps", "-T", "chain-deployer", "forge", "inspect", "OfferProofRegistry", "abi", "--json"]
    result = subprocess.run(cmd, cwd=str(ROOT), check=False, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise SystemExit(f"forge inspect gagal (exit {result.returncode}):\n{result.stderr.strip()}")
    output = result.stdout
    json.loads(output)
    return output


# Menulis ABI ke berkas backend dengan byte yang sama seperti output forge (agar abiSha256 cocok).
def main() -> int:
    abi_text = inspect_abi()
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_bytes(abi_text.encode("utf-8"))
    digest = hashlib.sha256(abi_text.encode("utf-8")).hexdigest()
    print(f"ABI ditulis ke {TARGET.relative_to(ROOT)} (sha256 {digest})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
