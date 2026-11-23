// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-01.04, §9.3.1, §9.5, §9.9.3; SA §10.5 (S-03), §10.6 (S-06)
import {
  ApiError,
  apiFetch,
  fetchSessionProfile,
  type MeResponse,
  type ProofListResponse,
} from "@/lib/api/client";
import { canIssueProofs } from "@/lib/routes";
import { readSession } from "@/lib/session";
import {
  getHrStatusPresentation,
  type HrStatusPresentation,
  type IssuerMembership,
} from "./hr-status";

// Hasil pemuatan profil sesi S-03 untuk halaman Beranda HR.
export type HrProfileLoadResult =
  | { kind: "redirect"; to: "/login" | "/admin/issuers" | "/onboarding/company" }
  | {
      kind: "ready";
      profile: MeResponse;
      membership: IssuerMembership;
      status: HrStatusPresentation;
      shouldLoadProofs: boolean;
    }
  | { kind: "unauthorized" }
  | { kind: "aborted" }
  | { kind: "error"; message: string };

// Hasil pemuatan ringkasan bukti S-06 untuk HR yang telah diotorisasi.
export type HrProofSummaryLoadResult =
  | { kind: "ready"; data: ProofListResponse }
  | { kind: "unauthorized" }
  | { kind: "aborted" }
  | { kind: "error"; message: string };

// Hasil gabungan pemuatan awal Beranda HR (profil S-03 dan opsional ringkasan bukti S-06).
export type HrHomeLoadResult =
  | { kind: "redirect"; to: "/login" | "/admin/issuers" | "/onboarding/company" }
  | { kind: "unauthorized" }
  | { kind: "aborted" }
  | { kind: "profile_error"; message: string }
  | {
      kind: "ready";
      profile: MeResponse;
      membership: IssuerMembership;
      status: HrStatusPresentation;
      proofs: ProofListResponse | null;
      proofsError: string | null;
    };

// Memuat profil sesi dari S-03 GET /api/v1/auth/me dan menentukan status afiliasi Beranda HR.
export async function loadHrProfile(options?: {
  signal?: AbortSignal;
  onUnauthorized?: () => void;
}): Promise<HrProfileLoadResult> {
  const session = readSession();
  if (!session) {
    return { kind: "redirect", to: "/login" };
  }

  try {
    const profile = await fetchSessionProfile({
      signal: options?.signal,
      onUnauthorized: options?.onUnauthorized,
    });
    if (options?.signal?.aborted) {
      return { kind: "aborted" };
    }
    if (profile.role === "ADMIN") {
      return { kind: "redirect", to: "/admin/issuers" };
    }
    if (profile.membership === null) {
      return { kind: "redirect", to: "/onboarding/company" };
    }
    return {
      kind: "ready",
      profile,
      membership: profile.membership,
      status: getHrStatusPresentation(profile.membership),
      shouldLoadProofs: canIssueProofs(profile),
    };
  } catch (error: unknown) {
    if (options?.signal?.aborted) {
      return { kind: "aborted" };
    }
    if (error instanceof ApiError && error.status === 401) {
      return { kind: "unauthorized" };
    }
    const message =
      error instanceof ApiError
        ? error.message
        : "Tidak dapat menghubungi layanan backend. Pastikan layanan aktif lalu coba lagi.";
    return { kind: "error", message };
  }
}

// Memuat 5 ringkasan bukti terbaru dari S-06 GET /api/v1/proofs?limit=5&offset=0.
export async function loadHrProofSummary(options?: {
  signal?: AbortSignal;
  onUnauthorized?: () => void;
}): Promise<HrProofSummaryLoadResult> {
  try {
    const data = await apiFetch<ProofListResponse>("/api/v1/proofs", {
      method: "GET",
      query: { limit: 5, offset: 0 },
      signal: options?.signal,
      onUnauthorized: options?.onUnauthorized,
    });
    if (options?.signal?.aborted) {
      return { kind: "aborted" };
    }
    return { kind: "ready", data };
  } catch (error: unknown) {
    if (options?.signal?.aborted) {
      return { kind: "aborted" };
    }
    if (error instanceof ApiError && error.status === 401) {
      return { kind: "unauthorized" };
    }
    const message =
      error instanceof ApiError
        ? error.message
        : "Ringkasan bukti belum dapat dimuat. Coba lagi beberapa saat lagi.";
    return { kind: "error", message };
  }
}

// Menjalankan alur muat Beranda HR: selalu memuat S-03, dan hanya memanggil S-06 bila VERIFIED + AUTHORIZED.
export async function loadHrHomeData(options?: {
  signal?: AbortSignal;
  onUnauthorized?: () => void;
}): Promise<HrHomeLoadResult> {
  const profileResult = await loadHrProfile(options);
  if (profileResult.kind === "redirect") {
    return profileResult;
  }
  if (profileResult.kind === "unauthorized" || profileResult.kind === "aborted") {
    return profileResult;
  }
  if (profileResult.kind === "error") {
    return { kind: "profile_error", message: profileResult.message };
  }

  if (!profileResult.shouldLoadProofs) {
    return {
      kind: "ready",
      profile: profileResult.profile,
      membership: profileResult.membership,
      status: profileResult.status,
      proofs: null,
      proofsError: null,
    };
  }

  const proofResult = await loadHrProofSummary(options);
  if (proofResult.kind === "unauthorized" || proofResult.kind === "aborted") {
    return proofResult;
  }
  if (proofResult.kind === "error") {
    return {
      kind: "ready",
      profile: profileResult.profile,
      membership: profileResult.membership,
      status: profileResult.status,
      proofs: null,
      proofsError: proofResult.message,
    };
  }

  return {
    kind: "ready",
    profile: profileResult.profile,
    membership: profileResult.membership,
    status: profileResult.status,
    proofs: proofResult.data,
    proofsError: null,
  };
}
