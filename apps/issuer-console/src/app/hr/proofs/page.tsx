// Owner: Van (PIC 2) | Status: STUB | Ref: PRD FR-03.08, §9.5; SA §10.6 (S-06)
// TODO: Tabel daftar bukti milik penerbit dari S-06 dengan filter status, paginasi, empty state, dan tautan detail.
import { PlaceholderPage } from "@/components/placeholder-page";

// Halaman Daftar Bukti (placeholder).
export default function ProofListPage() {
  return (
    <PlaceholderPage
      title="Daftar Bukti"
      owner="Van (PIC 2)"
      refs={["PRD FR-03.08", "PRD §9.5", "SA §10.6 S-06"]}
      checklist={[
        "S-06 GET /api/v1/proofs dengan filter status ACTIVE/REVOKED, limit, dan offset.",
        "Kolom referenceCode, issuedAt, lifecycleStatus (cermin off-chain), revokedAt.",
        "Hanya bukti ACTIVE dan REVOKED; percobaan FAILED tidak tampil (AC-02).",
        "Empty state dengan ajakan menerbitkan bukti pertama (AC-05).",
        "Tautan ke /hr/proofs/[proofId]; state Loading dan Error; 403 sesuai pesan §9.8.",
      ]}
    />
  );
}
