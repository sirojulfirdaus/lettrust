// Owner: Van (PIC 2) | Status: STUB | Ref: PRD FR-01.03, §9.8; SA §10.5 (API-01)
// TODO: Formulir registrasi perusahaan untuk HR tanpa membership; panggil API-01; tangani error §9.8.
import { PlaceholderPage } from "@/components/placeholder-page";

// Halaman Registrasi Perusahaan (placeholder).
export default function CompanyOnboardingPage() {
  return (
    <PlaceholderPage
      title="Registrasi Perusahaan"
      owner="Van (PIC 2)"
      refs={["PRD FR-01.03", "PRD §9.8", "SA §10.5 API-01"]}
      checklist={[
        "Hanya untuk HR tanpa membership (guard UX; backend tetap menegakkan).",
        "Field companyName (3–120), registrationNumber (3–40, [A-Za-z0-9./-]), contactEmail.",
        "API-01 POST /api/v1/issuers -> 201 {issuerId, issuerStatus: PENDING}; arahkan ke /hr.",
        "ACCOUNT_ALREADY_AFFILIATED dan REGISTRATION_NUMBER_ALREADY_EXISTS sesuai pesan §9.8.",
        "Validasi per field dari VALIDATION_ERROR (AC-07).",
        "State Processing dengan tombol nonaktif.",
      ]}
    />
  );
}
