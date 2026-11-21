// Owner: Van (PIC 2) | Status: STUB | Ref: PRD FR-01.01, §9.8; SA §10.5 (S-01)
// TODO: Formulir registrasi akun HR (tanpa pilihan role), validasi field, pesan error §9.8, pemberitahuan data sintetis.
import { PlaceholderPage } from "@/components/placeholder-page";

// Halaman Registrasi Akun HR (placeholder).
export default function RegisterPage() {
  return (
    <PlaceholderPage
      title="Registrasi Akun"
      owner="Van (PIC 2)"
      refs={["PRD FR-01.01", "PRD §9.8", "SA §10.5 S-01"]}
      checklist={[
        "Field displayName (2–80), email, password (8–128); tidak ada pilihan role (AC-02).",
        "S-01 POST /api/v1/auth/register -> 201 lalu arahkan ke /login.",
        "EMAIL_ALREADY_REGISTERED: \"Email sudah terdaftar. Silakan masuk.\"",
        "VALIDATION_ERROR: tampilkan pesan per field dari error.details.",
        "Pemberitahuan bahwa prototipe hanya memakai data sintetis (AC-07).",
        "State Processing dengan tombol nonaktif.",
      ]}
    />
  );
}
