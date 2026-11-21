// Owner: Van (PIC 2) | Status: STUB | Ref: PRD FR-01.05, §9.5; SA §10.5 (S-04)
// TODO: Tabel daftar penerbit dari S-04 dengan filter status, paginasi, empty state, dan tautan detail.
import { PlaceholderPage } from "@/components/placeholder-page";

// Halaman Daftar Penerbit untuk Administrator (placeholder).
export default function IssuerListPage() {
  return (
    <PlaceholderPage
      title="Daftar Penerbit"
      owner="Van (PIC 2)"
      refs={["PRD FR-01.05", "PRD §9.5", "SA §10.5 S-04"]}
      checklist={[
        "S-04 GET /api/v1/issuers dengan filter status PENDING/VERIFIED/REJECTED, limit, dan offset.",
        "Kolom companyName, registrationNumber, issuerStatus, createdAt, memberCount.",
        "Empty state (misalnya tidak ada penerbit PENDING); state Loading dan Error.",
        "403 bagi HR: \"Anda tidak memiliki izin untuk tindakan ini.\"",
        "Tautan ke /admin/issuers/[issuerId].",
      ]}
    />
  );
}
