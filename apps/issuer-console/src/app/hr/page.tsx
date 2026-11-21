// Owner: Van (PIC 2) | Status: STUB | Ref: PRD FR-01.04, §9.3.1, §9.5; SA §10.5 (S-03), §10.6 (S-06)
// TODO: Kartu status penerbit dan otorisasi dari S-03 setiap halaman dimuat; ringkasan bukti; tombol Terbitkan Bukti sesuai status.
import { PlaceholderPage } from "@/components/placeholder-page";

// Halaman Beranda HR (placeholder).
export default function HrHomePage() {
  return (
    <PlaceholderPage
      title="Beranda HR"
      owner="Van (PIC 2)"
      refs={["PRD FR-01.04", "PRD §9.3.1", "PRD §9.5", "SA §10.5 S-03", "SA §10.6 S-06"]}
      checklist={[
        "Kartu nama perusahaan, issuerStatus, dan authorizationStatus dari S-03 setiap halaman dimuat (AC-06).",
        "PENDING: status menunggu verifikasi; Terbitkan Bukti Disabled beserta alasannya.",
        "REJECTED: status ditolak beserta reviewNote bila ada; penerbitan tidak tersedia.",
        "VERIFIED + NOT_AUTHORIZED: jelaskan bahwa otorisasi Administrator masih diperlukan.",
        "VERIFIED + AUTHORIZED: tombol Terbitkan Bukti aktif dan ringkasan bukti (S-06).",
        "HR tanpa membership diarahkan ke /onboarding/company.",
        "State Loading dan Error.",
      ]}
    />
  );
}
