// Owner: Van (PIC 2) | Status: STUB | Ref: PRD FR-01.05, FR-01.06, §9.8; SA §10.5 (S-05, API-02, API-03)
// TODO: Detail penerbit dari S-05, keputusan verifikasi via API-02, dan otorisasi HR via API-03 dengan konfirmasi dan pesan error §9.8.
import { PlaceholderPage } from "@/components/placeholder-page";

// Halaman Detail Penerbit untuk Administrator (placeholder).
export default function IssuerDetailPage() {
  return (
    <PlaceholderPage
      title="Detail Penerbit"
      owner="Van (PIC 2)"
      refs={["PRD FR-01.05", "PRD FR-01.06", "PRD §9.8", "SA §10.5 S-05/API-02/API-03"]}
      checklist={[
        "S-05 GET /api/v1/issuers/{issuerId}: data pengajuan, waktu pengajuan, dan daftar HR terafiliasi.",
        "Keputusan API-02 PATCH .../verification: decision VERIFIED/REJECTED, evidenceRef wajib (3–120), reviewNote opsional (≤ 500).",
        "Dialog Confirmation sebelum keputusan disimpan; hanya untuk penerbit PENDING.",
        "Otorisasi API-03 POST .../hr-authorizations untuk anggota NOT_AUTHORIZED.",
        "ISSUER_DECISION_ALREADY_MADE, ISSUER_NOT_VERIFIED, HR_NOT_AFFILIATED, HR_ALREADY_AUTHORIZED sesuai pesan §9.8.",
        "404 ISSUER_NOT_FOUND; state Loading, Processing, Success, dan Error.",
      ]}
    />
  );
}
