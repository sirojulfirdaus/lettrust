// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-01.05, FR-01.06, §9.5, §9.8; SA §10.5 (S-04, S-05, API-02, API-03)
import { ApiError, apiFetch, type IssuerDetailResponse } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { readSession } from "@/lib/session";

export type IssuerStatus = components["schemas"]["IssuerStatus"];
export type IssuerDecision = components["schemas"]["IssuerDecision"];
export type IssuerListResponse = components["schemas"]["IssuerListResponse"];
export type VerifyIssuerResponse = components["schemas"]["VerifyIssuerResponse"];
export type AuthorizeHrResponse = components["schemas"]["AuthorizeHrResponse"];

export type IssuerListFilter = "ALL" | IssuerStatus;

export type IssuerListLoadResult =
  | { kind: "redirect"; to: "/login" }
  | { kind: "unauthorized" }
  | { kind: "aborted" }
  | { kind: "forbidden"; message: string }
  | { kind: "error"; message: string }
  | { kind: "ready"; data: IssuerListResponse };

export type IssuerDetailLoadResult =
  | { kind: "redirect"; to: "/login" }
  | { kind: "unauthorized" }
  | { kind: "aborted" }
  | { kind: "forbidden"; message: string }
  | { kind: "not_found"; message: string }
  | { kind: "error"; message: string }
  | { kind: "ready"; data: IssuerDetailResponse };

export type VerificationDecisionSubmitResult =
  | { kind: "redirect"; to: "/login" }
  | { kind: "unauthorized" }
  | { kind: "aborted" }
  | { kind: "error"; code: string | null; status: number | null; message: string }
  | { kind: "ready"; data: VerifyIssuerResponse };

export type HrAuthorizationSubmitResult =
  | { kind: "redirect"; to: "/login" }
  | { kind: "unauthorized" }
  | { kind: "aborted" }
  | { kind: "error"; code: string | null; status: number | null; message: string }
  | { kind: "ready"; data: AuthorizeHrResponse };

export interface VerificationDecisionInput {
  decision: IssuerDecision;
  evidenceRef: string;
  reviewNote: string;
}

export interface VerificationDecisionValidation {
  evidenceRefError?: string;
  reviewNoteError?: string;
}

// Menghitung panjang karakter Unicode (codepoint) agar selaras dengan validasi backend.
function codepointLength(value: string): number {
  return [...value].length;
}

// Memvalidasi input keputusan verifikasi penerbit sebelum dialog konfirmasi dibuka.
export function validateVerificationDecisionInput(
  input: VerificationDecisionInput,
): VerificationDecisionValidation {
  const errors: VerificationDecisionValidation = {};
  const trimmedEvidence = input.evidenceRef.trim();
  const evidenceLength = codepointLength(trimmedEvidence);

  if (evidenceLength < 3 || evidenceLength > 120) {
    errors.evidenceRefError = "Referensi bukti wajib diisi antara 3 hingga 120 karakter.";
  }

  const trimmedNote = input.reviewNote.trim();
  if (codepointLength(trimmedNote) > 500) {
    errors.reviewNoteError = "Catatan peninjauan maksimal 500 karakter.";
  }

  return errors;
}

// Memvalidasi ID HR untuk form otorisasi manual.
export function validateAuthorizeHrId(hrId: string): string | null {
  const trimmed = hrId.trim();
  if (codepointLength(trimmed) === 0) {
    return "ID akun HR wajib diisi.";
  }
  return null;
}

// Memuat daftar penerbit dari S-04 GET /api/v1/issuers untuk halaman Administrator.
export async function loadIssuerList(options: {
  status: IssuerListFilter;
  limit: number;
  offset: number;
  signal?: AbortSignal;
  onUnauthorized?: () => void;
}): Promise<IssuerListLoadResult> {
  if (!readSession()) {
    return { kind: "redirect", to: "/login" };
  }

  try {
    const query: Record<string, string | number | undefined> = {
      limit: options.limit,
      offset: options.offset,
    };
    if (options.status !== "ALL") {
      query.status = options.status;
    }

    const data = await apiFetch<IssuerListResponse>("/api/v1/issuers", {
      method: "GET",
      query,
      signal: options.signal,
      onUnauthorized: options.onUnauthorized,
    });

    if (options.signal?.aborted) {
      return { kind: "aborted" };
    }
    return { kind: "ready", data };
  } catch (error: unknown) {
    if (options.signal?.aborted) {
      return { kind: "aborted" };
    }
    if (error instanceof ApiError) {
      if (error.status === 401) {
        return { kind: "unauthorized" };
      }
      if (error.status === 403 || error.code === "FORBIDDEN_OPERATION") {
        return { kind: "forbidden", message: error.message };
      }
      return { kind: "error", message: error.message };
    }
    return {
      kind: "error",
      message: "Tidak dapat menghubungi layanan backend. Pastikan layanan aktif lalu coba lagi.",
    };
  }
}

// Memuat detail penerbit beserta anggota HR terafiliasi dari S-05 GET /api/v1/issuers/{issuerId}.
export async function loadIssuerDetail(options: {
  issuerId: string;
  signal?: AbortSignal;
  onUnauthorized?: () => void;
}): Promise<IssuerDetailLoadResult> {
  if (!readSession()) {
    return { kind: "redirect", to: "/login" };
  }

  try {
    const data = await apiFetch<IssuerDetailResponse>("/api/v1/issuers/{issuerId}", {
      method: "GET",
      pathParams: { issuerId: options.issuerId },
      signal: options.signal,
      onUnauthorized: options.onUnauthorized,
    });

    if (options.signal?.aborted) {
      return { kind: "aborted" };
    }
    return { kind: "ready", data };
  } catch (error: unknown) {
    if (options.signal?.aborted) {
      return { kind: "aborted" };
    }
    if (error instanceof ApiError) {
      if (error.status === 401) {
        return { kind: "unauthorized" };
      }
      if (error.status === 403 || error.code === "FORBIDDEN_OPERATION") {
        return { kind: "forbidden", message: error.message };
      }
      if (error.status === 404 || error.code === "ISSUER_NOT_FOUND") {
        return { kind: "not_found", message: "Penerbit tidak ditemukan." };
      }
      return { kind: "error", message: error.message };
    }
    return {
      kind: "error",
      message: "Tidak dapat menghubungi layanan backend. Pastikan layanan aktif lalu coba lagi.",
    };
  }
}

// Menyimpan keputusan verifikasi penerbit melalui API-02 PATCH /api/v1/issuers/{issuerId}/verification.
export async function submitVerificationDecision(options: {
  issuerId: string;
  decision: IssuerDecision;
  evidenceRef: string;
  reviewNote: string;
  signal?: AbortSignal;
  onUnauthorized?: () => void;
}): Promise<VerificationDecisionSubmitResult> {
  if (!readSession()) {
    return { kind: "redirect", to: "/login" };
  }

  const trimmedNote = options.reviewNote.trim();
  const payload: components["schemas"]["VerifyIssuerRequest"] = {
    decision: options.decision,
    evidenceRef: options.evidenceRef.trim(),
    reviewNote: trimmedNote.length > 0 ? trimmedNote : null,
  };

  try {
    const data = await apiFetch<VerifyIssuerResponse>("/api/v1/issuers/{issuerId}/verification", {
      method: "PATCH",
      pathParams: { issuerId: options.issuerId },
      body: payload,
      signal: options.signal,
      onUnauthorized: options.onUnauthorized,
    });

    if (options.signal?.aborted) {
      return { kind: "aborted" };
    }
    return { kind: "ready", data };
  } catch (error: unknown) {
    if (options.signal?.aborted) {
      return { kind: "aborted" };
    }
    if (error instanceof ApiError) {
      if (error.status === 401) {
        return { kind: "unauthorized" };
      }
      return {
        kind: "error",
        code: error.code,
        status: error.status,
        message: error.message,
      };
    }
    return {
      kind: "error",
      code: null,
      status: null,
      message: "Tidak dapat menghubungi layanan backend. Pastikan layanan aktif lalu coba lagi.",
    };
  }
}

// Mengotorisasi akun HR melalui API-03 POST /api/v1/issuers/{issuerId}/hr-authorizations, termasuk penanganan 422 HR_NOT_AFFILIATED.
export async function submitHrAuthorization(options: {
  issuerId: string;
  hrId: string;
  signal?: AbortSignal;
  onUnauthorized?: () => void;
}): Promise<HrAuthorizationSubmitResult> {
  if (!readSession()) {
    return { kind: "redirect", to: "/login" };
  }

  const payload: components["schemas"]["AuthorizeHrRequest"] = {
    hrId: options.hrId.trim(),
  };

  try {
    const data = await apiFetch<AuthorizeHrResponse>(
      "/api/v1/issuers/{issuerId}/hr-authorizations",
      {
        method: "POST",
        pathParams: { issuerId: options.issuerId },
        body: payload,
        signal: options.signal,
        onUnauthorized: options.onUnauthorized,
      },
    );

    if (options.signal?.aborted) {
      return { kind: "aborted" };
    }
    return { kind: "ready", data };
  } catch (error: unknown) {
    if (options.signal?.aborted) {
      return { kind: "aborted" };
    }
    if (error instanceof ApiError) {
      if (error.status === 401) {
        return { kind: "unauthorized" };
      }
      return {
        kind: "error",
        code: error.code,
        status: error.status,
        message: error.message,
      };
    }
    return {
      kind: "error",
      code: null,
      status: null,
      message: "Tidak dapat menghubungi layanan backend. Pastikan layanan aktif lalu coba lagi.",
    };
  }
}
