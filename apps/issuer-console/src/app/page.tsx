// Owner: Van (PIC 2) | Status: STUB | Ref: PRD FR-01.02/AC-07; SA §11.2.1, §11.2.2
// TODO: Redirect berdasarkan sesi dan role dari S-03: tanpa sesi -> /login; ADMIN -> /admin/issuers; HR tanpa membership -> /onboarding/company; HR -> /hr.
import { PlaceholderPage } from "@/components/placeholder-page";

// Halaman akar Console: placeholder logika redirect sesuai sesi.
export default function HomePage() {
  return (
    <PlaceholderPage
      title="Redirect sesuai sesi"
      owner="Van (PIC 2)"
      refs={["PRD FR-01.02/AC-07", "SA §11.2.1", "SA §11.2.2"]}
      checklist={[
        "Baca sesi dari sessionStorage (lettrust.session); tanpa sesi atau kedaluwarsa -> /login.",
        "Panggil S-03 GET /api/v1/auth/me untuk role dan membership.",
        "ADMIN -> /admin/issuers; HR tanpa membership -> /onboarding/company; HR terafiliasi -> /hr.",
        "Respons 401 -> hapus sesi -> /login dengan pesan sesi berakhir.",
        "State Loading selama menentukan tujuan.",
      ]}
    />
  );
}
