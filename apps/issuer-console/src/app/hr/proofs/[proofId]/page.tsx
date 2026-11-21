// Owner: Van (PIC 2) | Status: STUB | Ref: PRD FR-03.08, FR-03.09, FR-04.01–FR-04.07, §9.10; SA §10.6 (API-05, API-06), §11.2.3
// TODO: Detail bukti dari API-05 (status dari registry), riwayat transaksi, dan tindakan Cabut Bukti via API-06 dengan konfirmasi.
import { PlaceholderPage } from "@/components/placeholder-page";

// Halaman Detail Bukti dan pencabutan (placeholder).
export default function ProofDetailPage() {
  return (
    <PlaceholderPage
      title="Detail Bukti"
      owner="Van (PIC 2)"
      refs={["PRD FR-03.08", "PRD FR-03.09", "PRD FR-04.01–FR-04.07", "PRD §9.10", "SA §10.6 API-05/API-06", "SA §11.2.3"]}
      checklist={[
        "API-05 GET /api/v1/proofs/{proofId}: lifecycleStatus, documentHash, issuedAt, revokedAt dibaca dari registry (source REGISTRY).",
        "Referensi transaksi penerbitan; untuk REVOKED juga waktu, alasan, dan transaksi pencabutan (FR-04.07).",
        "Tindakan Cabut Bukti hanya untuk ACTIVE: pilih reasonCode OFFER_WITHDRAWN/ISSUED_IN_ERROR/DOCUMENT_REPLACED/OTHER.",
        "Dialog Confirmation: pencabutan tidak dapat dibatalkan dan pelamar akan melihat status dicabut.",
        "Idempotency-Key per bukti; Coba lagi memakai kunci yang sama; state Processing.",
        "PROOF_ALREADY_REVOKED, REGISTRY_UNAVAILABLE/REGISTRY_TRANSACTION_FAILED sesuai pesan §9.8; status tetap ACTIVE bila gagal.",
        "404 PROOF_NOT_FOUND tanpa mengungkap bukti penerbit lain; state Loading dan Error.",
      ]}
    />
  );
}
