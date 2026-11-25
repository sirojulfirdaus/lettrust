# Owner: Sat (PIC 6) | Status: COMPLETE | Ref: SA §18.1, §6.5–§6.6; T6-04
"""Fixture integrasi: HTTP aplikasi dan SQLite uji, dengan adapter Web3 serta chain Compose asli."""

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

import pytest
from conftest import REAL_REGISTRY_ENV
from fastapi.testclient import TestClient
from httpx import Response
from pydantic import SecretStr
from test_proofs_issue import make_account
from web3 import Web3
from web3.types import EventData, TxReceipt

from app.core.config import get_settings
from app.core.db import get_session_factory
from app.core.ids import compute_issuer_ref
from app.modules.proofs.models import Proof
from app.modules.registry import adapter as registry_adapter


# Membuat PDF satu halaman yang valid dan unik tanpa dependency atau dataset eksternal.
def _synthetic_pdf(identifier: str) -> bytes:
    stream = f"BT /F1 12 Tf 20 100 Td (Offer sintetis {identifier}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 500 200] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    document = b"%PDF-1.4\n"
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(document))
        document += f"{index} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(document)
    document += f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode()
    document += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
    return document + f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()


@dataclass(frozen=True)
class RegistryFlow:
    """Satu penerbit dan dokumen sintetis per tes; repr tidak membocorkan token atau isi dokumen."""

    client: TestClient = field(repr=False)
    registry: registry_adapter.Web3RegistryAdapter = field(repr=False)
    issuer_id: str
    issuer_ref: str
    headers: dict[str, str] = field(repr=False)
    pdf: bytes = field(repr=False)
    key: str

    # Mengunggah byte PDF asli melalui API-04 dengan kunci eksplisit untuk pengulangan tes.
    def issue(self, *, key: str | None = None, pdf: bytes | None = None) -> Response:
        return self.client.post(
            "/api/v1/proofs",
            headers={**self.headers, "Idempotency-Key": key or self.key},
            files={"file": ("offer-sintetis.pdf", self.pdf if pdf is None else pdf, "application/pdf")},
        )

    # Membaca status melalui API-05 yang mengambil lifecycle dan hash dari registry.
    def read(self, proof_id: str) -> Response:
        return self.client.get(f"/api/v1/proofs/{proof_id}", headers=self.headers)

    # Mengirim alasan off-chain melalui API-06; None berarti tanpa header idempotensi.
    def revoke(self, proof_id: str, *, key: str | None = "revoke-1", reason: str = "OFFER_WITHDRAWN") -> Response:
        headers = self.headers if key is None else {**self.headers, "Idempotency-Key": key}
        return self.client.post(f"/api/v1/proofs/{proof_id}/revocations", headers=headers, json={"reasonCode": reason})

    # Mengambil mirror melalui sesi terpisah untuk memastikan hasil API sudah di-commit.
    def stored_proof(self, proof_id: str) -> Proof:
        with get_session_factory()() as db:
            proof = db.get(Proof, proof_id)
            assert proof is not None
            return proof

    # Membaca event Anvil berdasarkan proofId, bukan berdasarkan panggilan adapter yang mungkin diulang.
    def events(self, proof_id: str, name: str) -> list[EventData]:
        contract = self.registry._contract(self.registry._web3())
        return list(
            getattr(contract.events, name)().get_logs(
                from_block=0, to_block="latest", argument_filters={"proofId": bytes.fromhex(proof_id[2:])}
            )
        )

    # Memastikan referensi API menunjuk receipt sukses dan tepat satu event untuk bukti yang sama.
    def confirmed_receipt(self, proof_id: str, transaction: dict[str, Any], event: str) -> TxReceipt:
        receipt = self.registry._web3().eth.get_transaction_receipt(transaction["hash"])
        assert receipt["status"] == 1
        assert receipt["blockNumber"] == transaction["blockNumber"]
        logs = self.events(proof_id, event)
        assert len(logs) == 1
        assert Web3.to_hex(logs[0]["transactionHash"]) == transaction["hash"]
        assert logs[0]["blockNumber"] == transaction["blockNumber"]
        return receipt

    # Menghitung nonce registrar untuk mendeteksi transaksi tambahan, termasuk transaksi yang revert.
    def nonce(self, sender: str) -> int:
        return self.registry._web3().eth.get_transaction_count(sender, "latest")


# Menjaga konfigurasi asli Compose meskipun fixture induk mengisolasi konfigurasi unit test.
@pytest.fixture
def real_adapter(monkeypatch: pytest.MonkeyPatch) -> registry_adapter.Web3RegistryAdapter:
    if not REAL_REGISTRY_ENV["REGISTRY_RPC_URL"] or not REAL_REGISTRY_ENV["REGISTRY_SIGNER_PRIVATE_KEY"]:
        pytest.fail("T6-04 memerlukan backend dan Anvil Compose; jalankan suite dengan -m real_registry di container.")
    settings = get_settings().model_copy(
        update={
            **{key.lower(): value for key, value in REAL_REGISTRY_ENV.items() if key != "REGISTRY_SIGNER_PRIVATE_KEY"},
            "registry_signer_private_key": SecretStr(REAL_REGISTRY_ENV["REGISTRY_SIGNER_PRIVATE_KEY"]),
        }
    )
    registry = registry_adapter.Web3RegistryAdapter(settings)
    if not registry.health():
        pytest.fail("Registry Anvil tidak sehat atau contract belum ter-deploy; tidak ada fallback mock.")
    monkeypatch.setattr(registry_adapter, "get_registry_adapter", lambda: registry)
    return registry


# Memakai setup akun sintetis bersama, tanpa mengganti otorisasi, database, atau fungsi bisnis aplikasi.
@pytest.fixture
def flow(client: TestClient, real_adapter: registry_adapter.Web3RegistryAdapter) -> RegistryFlow:
    issuer_id, headers = make_account()
    identifier = uuid4().hex
    return RegistryFlow(
        client,
        real_adapter,
        issuer_id,
        compute_issuer_ref(issuer_id),
        headers,
        _synthetic_pdf(identifier),
        f"issue-{identifier}",
    )
