// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-01.03, §9.8; SA §10.5 (API-01, S-03)
import {
  ApiError,
  apiFetch,
  fetchSessionProfile,
  type RegisterIssuerResponse,
} from "@/lib/api/client";
import { readSession } from "@/lib/session";
import {
  mapValidationDetailsToFieldErrors,
  normalizeCompanyPayload,
  validateCompanyForm,
  type CompanyFieldErrors,
  type CompanyFormValues,
} from "./validation";

// Status pesan kesalahan pengiriman formulir pendaftaran perusahaan.
export type SubmitErrorState = {
  message: string;
  showHrLink: boolean;
};

// Hasil pemeriksaan guard sesi sebelum menampilkan formulir onboarding perusahaan.
export type OnboardingGuardResult =
  | { kind: "redirect"; to: "/login" | "/admin/issuers" | "/hr" }
  | { kind: "ready"; displayName: string }
  | { kind: "unauthorized" }
  | { kind: "aborted" }
  | { kind: "error"; message: string };

// Hasil pengiriman formulir pendaftaran perusahaan ke API-01 POST /api/v1/issuers.
export type OnboardingSubmitResult =
  | { kind: "validation_error"; fieldErrors: CompanyFieldErrors }
  | { kind: "success"; data: RegisterIssuerResponse; redirectTo: "/hr" }
  | { kind: "unauthorized" }
  | { kind: "aborted" }
  | { kind: "error"; submitError: SubmitErrorState; fieldErrors?: CompanyFieldErrors };

// Memeriksa sesi dan profil S-03 untuk menentukan akses atau arah redirect halaman onboarding.
export async function loadOnboardingGuard(options?: {
  signal?: AbortSignal;
  onUnauthorized?: () => void;
}): Promise<OnboardingGuardResult> {
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
    if (profile.membership !== null) {
      return { kind: "redirect", to: "/hr" };
    }
    return { kind: "ready", displayName: profile.displayName };
  } catch (error: unknown) {
    if (options?.signal?.aborted) {
      return { kind: "aborted" };
    }
    if (error instanceof ApiError && error.status === 401) {
      return { kind: "unauthorized" };
    }
    const detail =
      error instanceof ApiError
        ? error.message
        : "Tidak dapat menghubungi layanan backend. Pastikan layanan aktif lalu coba lagi.";
    return {
      kind: "error",
      message: `Data profil sesi belum dapat dimuat. ${detail}`,
    };
  }
}

// Memvalidasi dan mengirim data pendaftaran perusahaan ke API-01 POST /api/v1/issuers.
export async function submitCompanyRegistration(
  values: CompanyFormValues,
  options?: { signal?: AbortSignal; onUnauthorized?: () => void },
): Promise<OnboardingSubmitResult> {
  const clientErrors = validateCompanyForm(values);
  if (Object.keys(clientErrors).length > 0) {
    return { kind: "validation_error", fieldErrors: clientErrors };
  }

  const submittedToken = readSession()?.accessToken ?? null;
  const isStaleOrAborted = () =>
    Boolean(options?.signal?.aborted) || (readSession()?.accessToken ?? null) !== submittedToken;

  try {
    const payload = normalizeCompanyPayload(values);
    const data = await apiFetch<RegisterIssuerResponse>("/api/v1/issuers", {
      method: "POST",
      body: payload,
      signal: options?.signal,
      onUnauthorized: options?.onUnauthorized,
    });
    if (isStaleOrAborted()) {
      return { kind: "aborted" };
    }
    return { kind: "success", data, redirectTo: "/hr" };
  } catch (error: unknown) {
    if (isStaleOrAborted()) {
      return { kind: "aborted" };
    }
    if (error instanceof ApiError) {
      if (error.status === 401) {
        return { kind: "unauthorized" };
      }
      if (error.code === "ACCOUNT_ALREADY_AFFILIATED") {
        return {
          kind: "error",
          submitError: {
            message: "Akun Anda sudah terhubung dengan perusahaan.",
            showHrLink: true,
          },
        };
      }
      if (error.code === "REGISTRATION_NUMBER_ALREADY_EXISTS") {
        return {
          kind: "error",
          fieldErrors: {
            registrationNumber: "Nomor registrasi perusahaan sudah terdaftar.",
          },
          submitError: {
            message: "Nomor registrasi perusahaan sudah terdaftar.",
            showHrLink: false,
          },
        };
      }
      if (error.code === "VALIDATION_ERROR") {
        const mapped = mapValidationDetailsToFieldErrors(error.details);
        return {
          kind: "error",
          fieldErrors: mapped,
          submitError: {
            message:
              Object.keys(mapped).length > 0
                ? "Periksa kembali data perusahaan yang ditandai di bawah."
                : "Periksa kembali data yang Anda masukkan.",
            showHrLink: false,
          },
        };
      }
      if (error.status === 403 || error.code === "FORBIDDEN_OPERATION") {
        return {
          kind: "error",
          submitError: {
            message: "Anda tidak memiliki izin untuk tindakan ini.",
            showHrLink: false,
          },
        };
      }
      return {
        kind: "error",
        submitError: {
          message: error.message,
          showHrLink: false,
        },
      };
    }

    return {
      kind: "error",
      submitError: {
        message: "Gagal mengirim pendaftaran perusahaan. Periksa koneksi Anda lalu coba lagi.",
        showHrLink: false,
      },
    };
  }
}
