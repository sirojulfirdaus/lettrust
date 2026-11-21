// Owner: Van (PIC 2) | Status: COMPLETE | Ref: SA §11.2.1; PRD §9.3.1, §9.11

// Kelompok akses UI sebuah route; penegakan tetap di backend.
export type RouteAccess = "public" | "hr" | "admin";

export type ConsoleRoute = {
  path: string;
  title: string;
  access: RouteAccess;
};

// Daftar route Console sesuai SA §11.2.1, dipakai navigasi placeholder.
export const CONSOLE_ROUTES: readonly ConsoleRoute[] = [
  { path: "/", title: "Redirect sesuai sesi", access: "public" },
  { path: "/login", title: "Masuk", access: "public" },
  { path: "/register", title: "Registrasi Akun", access: "public" },
  { path: "/onboarding/company", title: "Registrasi Perusahaan", access: "hr" },
  { path: "/hr", title: "Beranda HR", access: "hr" },
  { path: "/hr/proofs", title: "Daftar Bukti", access: "hr" },
  { path: "/hr/proofs/new", title: "Terbitkan Bukti", access: "hr" },
  { path: "/hr/proofs/[proofId]", title: "Detail Bukti", access: "hr" },
  { path: "/admin/issuers", title: "Daftar Penerbit", access: "admin" },
  { path: "/admin/issuers/[issuerId]", title: "Detail Penerbit", access: "admin" },
];
