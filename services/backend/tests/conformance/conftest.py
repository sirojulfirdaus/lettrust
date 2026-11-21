# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: SA §6.4, §18.1
"""Fixture conformance registry: parametrisasi MockRegistryAdapter dan Web3RegistryAdapter (marker real_registry)."""

import hashlib
from collections.abc import Callable
from dataclasses import dataclass

import pytest
from conftest import REAL_REGISTRY_ENV
from pydantic import SecretStr

from app.core.config import get_settings
from app.core.ids import compute_issuer_ref, new_issuer_id, new_proof_id
from app.modules.registry.adapter import RegistryAdapter, Web3RegistryAdapter
from app.modules.registry.mock import MockRegistryAdapter


@dataclass(frozen=True)
class ProofInput:
    """Input bukti acak baru: proofId, documentHash, dan issuerRef dalam format SA §6.3."""

    proof_id: str
    document_hash: str
    issuer_ref: str


# Membuat Web3RegistryAdapter dengan konfigurasi registry asli container (bukan nilai test yang tak terjangkau).
def _real_adapter() -> Web3RegistryAdapter:
    if not REAL_REGISTRY_ENV["REGISTRY_RPC_URL"] or not REAL_REGISTRY_ENV["REGISTRY_SIGNER_PRIVATE_KEY"]:
        pytest.fail(
            "real_registry butuh env registry asli; jalankan: "
            "docker compose exec backend python -m pytest -m real_registry tests/conformance"
        )
    settings = get_settings().model_copy(
        update={
            "registry_rpc_url": REAL_REGISTRY_ENV["REGISTRY_RPC_URL"],
            "registry_deployment_file": REAL_REGISTRY_ENV["REGISTRY_DEPLOYMENT_FILE"],
            "registry_contract_address": REAL_REGISTRY_ENV["REGISTRY_CONTRACT_ADDRESS"],
            "registry_signer_private_key": SecretStr(REAL_REGISTRY_ENV["REGISTRY_SIGNER_PRIVATE_KEY"]),
        }
    )
    return Web3RegistryAdapter(settings)


# Adapter yang diuji: mock (default) atau web3 nyata (hanya dengan `-m real_registry`).
@pytest.fixture(
    params=[
        pytest.param("mock", id="mock"),
        pytest.param("web3", id="web3", marks=pytest.mark.real_registry),
    ]
)
def registry(request) -> RegistryAdapter:
    return MockRegistryAdapter() if request.param == "mock" else _real_adapter()


# Pembuat input bukti acak baru; proofId selalu baru karena state chain nyata persisten.
@pytest.fixture
def new_proof() -> Callable[[], ProofInput]:
    # Menghasilkan satu input bukti unik.
    def make() -> ProofInput:
        proof_id = new_proof_id()
        return ProofInput(
            proof_id=proof_id,
            document_hash=hashlib.sha256(proof_id.encode()).hexdigest(),
            issuer_ref=compute_issuer_ref(new_issuer_id()),
        )

    return make
