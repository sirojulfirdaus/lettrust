# Owner: Sat (PIC 6) | Status: STUB | Ref: SA §18.1, §18.2, AD-16
# TODO: Implementasikan registry in-memory untuk unit test proofs/verifications (perilaku revert sama dengan contract).
"""MockRegistryAdapter khusus unit test; menolak dibuat di luar APP_ENV=test."""

from app.core.config import get_settings
from app.modules.registry.adapter import ProofRecord, TxResult


class MockRegistryAdapter:
    """Registry palsu in-memory untuk unit test; tidak pernah dipakai pada demo atau skenario."""

    # Menolak instansiasi di luar test agar mock tidak dapat aktif melalui konfigurasi lokal.
    def __init__(self) -> None:
        if get_settings().app_env != "test":
            raise RuntimeError("MockRegistryAdapter hanya boleh dipakai saat APP_ENV=test")

    # Lihat RegistryAdapter.issue_proof.
    def issue_proof(self, proof_id: str, document_hash: str, issuer_ref: str) -> TxResult:
        raise NotImplementedError("MockRegistryAdapter.issue_proof belum diimplementasikan")

    # Lihat RegistryAdapter.revoke_proof.
    def revoke_proof(self, proof_id: str, issuer_ref: str) -> TxResult:
        raise NotImplementedError("MockRegistryAdapter.revoke_proof belum diimplementasikan")

    # Lihat RegistryAdapter.get_proof.
    def get_proof(self, proof_id: str) -> ProofRecord:
        raise NotImplementedError("MockRegistryAdapter.get_proof belum diimplementasikan")

    # Lihat RegistryAdapter.find_issue_tx.
    def find_issue_tx(self, proof_id: str) -> TxResult | None:
        raise NotImplementedError("MockRegistryAdapter.find_issue_tx belum diimplementasikan")

    # Lihat RegistryAdapter.find_revoke_tx.
    def find_revoke_tx(self, proof_id: str) -> TxResult | None:
        raise NotImplementedError("MockRegistryAdapter.find_revoke_tx belum diimplementasikan")

    # Lihat RegistryAdapter.health.
    def health(self) -> bool:
        raise NotImplementedError("MockRegistryAdapter.health belum diimplementasikan")
