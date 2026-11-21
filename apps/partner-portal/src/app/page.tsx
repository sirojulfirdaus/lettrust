// Owner: Pash (PIC 4) | Status: STUB | Ref: PRD FR-02.01, §9.3.2; SA §11.3.1
// TODO: Beranda portal simulasi sederhana dengan identitas portal dan akses ke fitur Cek Offer Letter; tanpa lowongan atau merek nyata.
import Link from "next/link";
import { PlaceholderPage } from "@/components/placeholder-page";

// Halaman Beranda Portal (placeholder).
export default function PortalHomePage() {
  return (
    <div className="space-y-4">
      <PlaceholderPage
        title="Beranda Portal"
        owner="Pash (PIC 4)"
        refs={["PRD FR-02.01", "PRD §9.3.2", "SA §11.3.1"]}
        checklist={[
          "Identitas \"Portal Karier Mitra (Simulasi)\" dengan label Simulasi.",
          "Akses jelas ke fitur Cek Offer Letter.",
          "Tidak menampilkan lowongan nyata, merek job portal nyata, atau data yang menyerupai platform tertentu.",
          "Responsif untuk desktop dan browser mobile (PRD §9.11).",
        ]}
      />
      <Link href="/cek-offer-letter" className="text-primary underline">
        Cek Offer Letter
      </Link>
    </div>
  );
}
