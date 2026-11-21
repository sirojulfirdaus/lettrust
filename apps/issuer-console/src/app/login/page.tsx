// Owner: Van (PIC 2) | Status: STUB | Ref: PRD FR-01.02, §9.3.1, §9.8; SA §10.5 (S-02, S-03), §11.2.2
// TODO: Formulir login, simpan sesi, panggil /auth/me, redirect sesuai role, tampilkan pesan error §9.8.
import { PlaceholderPage } from "@/components/placeholder-page";

// Halaman Login Console (placeholder).
export default function LoginPage() {
  return (
    <PlaceholderPage
      title="Masuk"
      owner="Van (PIC 2)"
      refs={["PRD FR-01.02", "PRD §9.3.1", "PRD §9.8", "SA §10.5 S-02/S-03", "SA §11.2.2"]}
      checklist={[
        "Formulir email dan password; dapat dioperasikan dengan keyboard.",
        "S-02 POST /api/v1/auth/login; state Processing dengan tombol Masuk nonaktif.",
        "Simpan accessToken dan expiresAt di sessionStorage lettrust.session.",
        "Setelah login panggil S-03 GET /api/v1/auth/me lalu arahkan sesuai role (AC-07).",
        "INVALID_CREDENTIALS: \"Email atau password tidak sesuai.\" tanpa menyebut field yang salah.",
        "Bila datang dari 401: \"Sesi Anda telah berakhir. Silakan masuk kembali.\"",
        "Tautan ke /register.",
      ]}
    />
  );
}
