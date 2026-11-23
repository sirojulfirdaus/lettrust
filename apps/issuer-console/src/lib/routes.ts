// Owner: Van (PIC 2) | Status: COMPLETE | Ref: SA §11.2.1; PRD FR-01.02, FR-01.04, §9.3.1, §9.11
import type { components } from "@/lib/api/schema";

// Kelompok akses UI sebuah route; penegakan tetap di backend.
export type RouteAccess = "public" | "hr" | "admin";

export type ConsoleRoute = {
  path: string;
  title: string;
  access: RouteAccess;
};

// Profil sesi dari S-03 GET /api/v1/auth/me.
export type SessionProfile = components["schemas"]["MeResponse"];

// Daftar route Console sesuai SA §11.2.1.
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

// Menentukan apakah route termasuk halaman publik yang tidak memerlukan sesi.
export function isPublicRoute(pathname: string): boolean {
  return pathname === "/login" || pathname === "/register";
}

// Menentukan tujuan redirect awal berdasarkan role dan afiliasi dari S-03 GET /auth/me.
export function resolveLandingRoute(profile: SessionProfile): string {
  if (profile.role === "ADMIN") {
    return "/admin/issuers";
  }
  if (!profile.membership) {
    return "/onboarding/company";
  }
  return "/hr";
}

// Memeriksa apakah HR memiliki hak penerbitan aktif (penerbit VERIFIED dan HR AUTHORIZED).
export function canIssueProofs(profile: SessionProfile): boolean {
  return (
    profile.role === "HR" &&
    profile.membership !== null &&
    profile.membership.issuerStatus === "VERIFIED" &&
    profile.membership.authorizationStatus === "AUTHORIZED"
  );
}

// Menyusun daftar tautan navigasi header sesuai peran dan status afiliasi pengguna.
export function getNavRoutesForUser(profile: SessionProfile): readonly ConsoleRoute[] {
  if (profile.role === "ADMIN") {
    return CONSOLE_ROUTES.filter((r) => r.path === "/admin/issuers");
  }

  if (!profile.membership) {
    return CONSOLE_ROUTES.filter((r) => r.path === "/onboarding/company");
  }

  if (canIssueProofs(profile)) {
    return CONSOLE_ROUTES.filter(
      (r) => r.path === "/hr" || r.path === "/hr/proofs" || r.path === "/hr/proofs/new",
    );
  }

  return CONSOLE_ROUTES.filter((r) => r.path === "/hr");
}
