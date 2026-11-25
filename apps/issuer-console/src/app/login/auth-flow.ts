// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-01.01, FR-01.02, §9.8; SA §10.5 (S-01, S-02, S-03), §11.2.2
import {
  apiFetch,
  fetchSessionProfile,
  type LoginRequest,
  type LoginResponse,
  type MeResponse,
  type RegisterAccountRequest,
  type UserSummary,
} from "@/lib/api/client";
import { resolveLandingRoute } from "@/lib/routes";
import { createSession, saveSession } from "@/lib/session";

export type LoginFlowResult = {
  profile: MeResponse;
  redirectTo: string;
};

// Menjalankan alur login S-02 lalu memuat profil S-03 sebelum menyimpan sesi agar tidak meninggalkan sesi setengah jadi.
export async function submitLoginFlow(
  email: string,
  password: string,
): Promise<LoginFlowResult> {
  const payload: LoginRequest = {
    email: email.trim().toLowerCase(),
    password,
  };

  const loginResponse = await apiFetch<LoginResponse>("/api/v1/auth/login", {
    method: "POST",
    auth: false,
    body: payload,
  });

  // Muat profil memakai token hasil login sebelum menyimpan ke sessionStorage.
  const profile = await fetchSessionProfile({
    accessToken: loginResponse.accessToken,
  });

  saveSession(createSession(loginResponse.accessToken, loginResponse.expiresIn));

  return {
    profile,
    redirectTo: resolveLandingRoute(profile),
  };
}

// Menjalankan alur registrasi akun HR S-01 tanpa mengirim pilihan role dari client.
export async function submitRegisterFlow(
  displayName: string,
  email: string,
  password: string,
): Promise<UserSummary> {
  const payload: RegisterAccountRequest = {
    displayName: displayName.trim(),
    email: email.trim().toLowerCase(),
    password,
  };

  return apiFetch<UserSummary>("/api/v1/auth/register", {
    method: "POST",
    auth: false,
    body: payload,
  });
}
