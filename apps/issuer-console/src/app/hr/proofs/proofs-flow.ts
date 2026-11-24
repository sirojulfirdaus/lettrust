// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-03.01–FR-03.09, FR-04.01–FR-04.07, §9.8; SA §10.6, §11.2.3
import {
  ApiError,
  apiFetch,
  fetchSessionProfile,
  type IssueProofResponse,
  type LifecycleStatus,
  type MeResponse,
  type ProofListResponse,
  type ProofStatusResponse,
  type RevocationReasonCode,
  type RevokeProofRequest,
  type RevokeProofResponse,
} from "@/lib/api/client";
import { canIssueProofs } from "@/lib/routes";
import { readSession } from "@/lib/session";

// Batas ukuran berkas PDF default sesuai SA §14 (MAX_UPLOAD_BYTES = 5 MB).
export const MAX_PROOF_FILE_BYTES = 5 * 1024 * 1024;

// Ukuran halaman default untuk tabel daftar bukti S-06.
export const PROOF_LIST_PAGE_SIZE = 20;

// Daftar nilai reasonCode yang sah menurut kontrak API-06.
export const REVOCATION_REASON_CODES: readonly RevocationReasonCode[] = [
  "OFFER_WITHDRAWN",
  "ISSUED_IN_ERROR",
  "DOCUMENT_REPLACED",
  "OTHER",
];

export type ProofFilterStatus = "ALL" | LifecycleStatus;

export type PdfFileValidationResult =
  | { valid: true; file: File }
  | {
      valid: false;
      code: "EMPTY_SELECTION" | "MULTIPLE_FILES" | "EMPTY_FILE" | "UNSUPPORTED_MEDIA_TYPE" | "FILE_TOO_LARGE";
      message: string;
    };

export type HrProofsGuardResult =
  | { kind: "redirect"; to: "/login" | "/admin/issuers" | "/onboarding/company" }
  | { kind: "forbidden"; profile: MeResponse; message: string }
  | { kind: "ready"; profile: MeResponse }
  | { kind: "unauthorized" }
  | { kind: "aborted" }
  | { kind: "error"; message: string };

export type ProofListLoadResult =
  | { kind: "redirect"; to: "/login" }
  | { kind: "ready"; data: ProofListResponse }
  | { kind: "forbidden"; message: string }
  | { kind: "unauthorized" }
  | { kind: "aborted" }
  | { kind: "error"; message: string };

export type ProofDetailLoadResult =
  | { kind: "redirect"; to: "/login" }
  | { kind: "ready"; data: ProofStatusResponse }
  | { kind: "not_found"; message: string }
  | { kind: "forbidden"; message: string }
  | { kind: "unauthorized" }
  | { kind: "aborted" }
  | { kind: "error"; code: string; message: string };

export type IssueProofSubmitResult =
  | { kind: "success"; data: IssueProofResponse }
  | { kind: "unauthorized" }
  | { kind: "aborted" }
  | {
      kind: "error";
      status: number;
      code: string;
      message: string;
      canRetrySameKey: boolean;
      requiresResetKey: boolean;
    };

export type RevokeProofSubmitResult =
  | { kind: "success"; data: RevokeProofResponse }
  | { kind: "already_revoked"; message: string }
  | { kind: "unauthorized" }
  | { kind: "aborted" }
  | {
      kind: "error";
      status: number;
      code: string;
      message: string;
      canRetrySameKey: boolean;
      requiresResetKey: boolean;
    };

// Menghasilkan Idempotency-Key unik (UUID) untuk satu upaya penerbitan atau pencabutan bukti.
export function generateIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  const suffix = Math.random().toString(16).slice(2, 10);
  return `idem-${Date.now().toString(16)}-${suffix}`;
}

// Memeriksa apakah token sesi telah berubah atau dihapus saat permintaan masih berjalan.
function isSessionStale(submittedToken: string | null): boolean {
  const currentToken = readSession()?.accessToken ?? null;
  return currentToken !== submittedToken;
}

// Memvalidasi pilihan berkas PDF di sisi client (tunggal, PDF, tidak kosong, maks 5 MB).
export function validateProofPdfFile(
  files: FileList | readonly File[] | null | undefined,
): PdfFileValidationResult {
  const list = files ? Array.from(files) : [];
  if (list.length === 0) {
    return {
      valid: false,
      code: "EMPTY_SELECTION",
      message: "Pilih satu berkas PDF terlebih dahulu.",
    };
  }
  if (list.length > 1) {
    return {
      valid: false,
      code: "MULTIPLE_FILES",
      message: "Unggah hanya satu berkas PDF.",
    };
  }

  const file = list[0];
  const normalizedType = file.type.trim().toLowerCase();
  const hasPdfExtension = file.name.trim().toLowerCase().endsWith(".pdf");
  const isPdfType = normalizedType === "application/pdf";
  const hasConflictingMime =
    normalizedType.length > 0 &&
    normalizedType !== "application/pdf" &&
    normalizedType !== "application/octet-stream";

  if ((!isPdfType && !hasPdfExtension) || hasConflictingMime) {
    return {
      valid: false,
      code: "UNSUPPORTED_MEDIA_TYPE",
      message: "Berkas harus berformat PDF.",
    };
  }

  if (file.size === 0) {
    return {
      valid: false,
      code: "EMPTY_FILE",
      message: "Berkas kosong tidak dapat diproses.",
    };
  }

  if (file.size > MAX_PROOF_FILE_BYTES) {
    return {
      valid: false,
      code: "FILE_TOO_LARGE",
      message: "Ukuran berkas melebihi batas maksimum 5 MB.",
    };
  }

  return { valid: true, file };
}

// Memastikan nilai reasonCode termasuk dalam daftar kode alasan pencabutan yang diizinkan.
export function isValidRevocationReasonCode(value: string): value is RevocationReasonCode {
  return (REVOCATION_REASON_CODES as readonly string[]).includes(value);
}

// Memformat ukuran berkas dalam byte agar mudah dibaca pengguna.
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

// Memeriksa hak akses HR melalui S-03 GET /api/v1/auth/me sebelum menampilkan halaman penerbitan bukti.
export async function loadHrProofsGuard(options?: {
  signal?: AbortSignal;
  onUnauthorized?: () => void;
}): Promise<HrProofsGuardResult> {
  const session = readSession();
  if (!session) {
    return { kind: "redirect", to: "/login" };
  }
  const submittedToken = session.accessToken;

  try {
    const profile = await fetchSessionProfile({
      signal: options?.signal,
      onUnauthorized: options?.onUnauthorized,
    });
    if (options?.signal?.aborted || isSessionStale(submittedToken)) {
      return { kind: "aborted" };
    }
    if (profile.role === "ADMIN") {
      return { kind: "redirect", to: "/admin/issuers" };
    }
    if (profile.membership === null) {
      return { kind: "redirect", to: "/onboarding/company" };
    }
    if (!canIssueProofs(profile)) {
      return {
        kind: "forbidden",
        profile,
        message:
          "Anda tidak memiliki izin untuk tindakan ini. Pastikan perusahaan telah terverifikasi dan akun HR Anda sudah diotorisasi.",
      };
    }
    return { kind: "ready", profile };
  } catch (error: unknown) {
    if (options?.signal?.aborted) {
      return { kind: "aborted" };
    }
    if (error instanceof ApiError && error.status === 401) {
      return { kind: "unauthorized" };
    }
    if (isSessionStale(submittedToken)) {
      return { kind: "aborted" };
    }
    const message =
      error instanceof ApiError
        ? error.message
        : "Tidak dapat menghubungi layanan backend. Pastikan layanan aktif lalu coba lagi.";
    return { kind: "error", message };
  }
}

// Memuat daftar bukti penerbit dari S-06 GET /api/v1/proofs dengan filter status dan paginasi.
export async function loadProofList(options: {
  status?: ProofFilterStatus;
  limit?: number;
  offset?: number;
  signal?: AbortSignal;
  onUnauthorized?: () => void;
}): Promise<ProofListLoadResult> {
  const session = readSession();
  if (!session) {
    return { kind: "redirect", to: "/login" };
  }
  const submittedToken = session.accessToken;

  try {
    const data = await apiFetch<ProofListResponse>("/api/v1/proofs", {
      method: "GET",
      query: {
        status: options.status && options.status !== "ALL" ? options.status : undefined,
        limit: options.limit ?? PROOF_LIST_PAGE_SIZE,
        offset: options.offset ?? 0,
      },
      signal: options.signal,
      onUnauthorized: options.onUnauthorized,
    });
    if (options.signal?.aborted || isSessionStale(submittedToken)) {
      return { kind: "aborted" };
    }
    return { kind: "ready", data };
  } catch (error: unknown) {
    if (options.signal?.aborted) {
      return { kind: "aborted" };
    }
    if (error instanceof ApiError && error.status === 401) {
      return { kind: "unauthorized" };
    }
    if (isSessionStale(submittedToken)) {
      return { kind: "aborted" };
    }
    if (error instanceof ApiError && error.status === 403) {
      return { kind: "forbidden", message: error.message };
    }
    const message =
      error instanceof ApiError
        ? error.message
        : "Daftar bukti belum dapat dimuat. Pastikan layanan aktif lalu coba lagi.";
    return { kind: "error", message };
  }
}

// Memuat detail bukti langsung dari registry melalui API-05 GET /api/v1/proofs/{proofId}.
export async function loadProofDetail(options: {
  proofId: string;
  signal?: AbortSignal;
  onUnauthorized?: () => void;
}): Promise<ProofDetailLoadResult> {
  const session = readSession();
  if (!session) {
    return { kind: "redirect", to: "/login" };
  }
  const submittedToken = session.accessToken;

  try {
    const data = await apiFetch<ProofStatusResponse>("/api/v1/proofs/{proofId}", {
      method: "GET",
      pathParams: { proofId: options.proofId },
      signal: options.signal,
      onUnauthorized: options.onUnauthorized,
    });
    if (options.signal?.aborted || isSessionStale(submittedToken)) {
      return { kind: "aborted" };
    }
    return { kind: "ready", data };
  } catch (error: unknown) {
    if (options.signal?.aborted) {
      return { kind: "aborted" };
    }
    if (error instanceof ApiError && error.status === 401) {
      return { kind: "unauthorized" };
    }
    if (isSessionStale(submittedToken)) {
      return { kind: "aborted" };
    }
    if (error instanceof ApiError && error.status === 403) {
      return { kind: "forbidden", message: error.message };
    }
    if (error instanceof ApiError && (error.status === 404 || error.code === "PROOF_NOT_FOUND")) {
      return { kind: "not_found", message: "Bukti tidak ditemukan." };
    }
    if (error instanceof ApiError) {
      return { kind: "error", code: error.code, message: error.message };
    }
    return {
      kind: "error",
      code: "NETWORK_ERROR",
      message: "Detail bukti belum dapat dimuat. Pastikan layanan aktif lalu coba lagi.",
    };
  }
}

// Menggabungkan hasil konfirmasi pencabutan API-06 ke detail bukti tanpa mengarang reasonCode lokal.
export function mergeRevokeResultIntoProofDetail(
  current: ProofStatusResponse,
  revokeResult: RevokeProofResponse,
): ProofStatusResponse {
  return {
    ...current,
    lifecycleStatus: revokeResult.lifecycleStatus,
    revokedAt: revokeResult.revokedAt,
    revocationReasonCode: current.revocationReasonCode,
    revokeTransaction: revokeResult.transaction,
  };
}

// Menyusun pesan gagal muat ulang detail berbasis pembacaan agar tidak memakai pesan gagal tulis dari registry.
export function getProofDetailRefreshErrorMessage(
  error: Pick<Extract<ProofDetailLoadResult, { kind: "error" }>, "code" | "message">,
): string {
  if (error.code === "RATE_LIMITED") {
    return error.message;
  }
  return "Detail bukti terbaru dari registry belum dapat dimuat ulang. Data yang sudah tercatat tidak berubah; silakan coba muat ulang beberapa saat lagi.";
}

// Mengirim unggahan PDF ke API-04 POST /api/v1/proofs dengan header Idempotency-Key.
export async function submitIssueProof(options: {
  file: File;
  idempotencyKey: string;
  signal?: AbortSignal;
  onUnauthorized?: () => void;
}): Promise<IssueProofSubmitResult> {
  const session = readSession();
  if (!session) {
    options.onUnauthorized?.();
    return { kind: "unauthorized" };
  }
  const submittedToken = session.accessToken;

  const formData = new FormData();
  formData.append("file", options.file);

  try {
    const data = await apiFetch<IssueProofResponse>("/api/v1/proofs", {
      method: "POST",
      body: formData,
      headers: {
        "Idempotency-Key": options.idempotencyKey,
      },
      signal: options.signal,
      onUnauthorized: options.onUnauthorized,
    });
    if (options.signal?.aborted || isSessionStale(submittedToken)) {
      return { kind: "aborted" };
    }
    return { kind: "success", data };
  } catch (error: unknown) {
    if (options.signal?.aborted) {
      return { kind: "aborted" };
    }
    if (error instanceof ApiError && error.status === 401) {
      return { kind: "unauthorized" };
    }
    if (isSessionStale(submittedToken)) {
      return { kind: "aborted" };
    }
    if (error instanceof ApiError) {
      const canRetrySameKey =
        error.code === "REGISTRY_UNAVAILABLE" ||
        error.code === "REGISTRY_TRANSACTION_FAILED" ||
        error.status >= 500;
      const requiresResetKey = error.code === "IDEMPOTENCY_KEY_CONFLICT";
      return {
        kind: "error",
        status: error.status,
        code: error.code,
        message: error.message,
        canRetrySameKey,
        requiresResetKey,
      };
    }
    return {
      kind: "error",
      status: 0,
      code: "NETWORK_ERROR",
      message: "Tidak dapat menghubungi layanan backend. Pastikan layanan aktif lalu coba lagi.",
      canRetrySameKey: true,
      requiresResetKey: false,
    };
  }
}

// Mengirim permintaan pencabutan bukti ke API-06 POST /api/v1/proofs/{proofId}/revocations dengan Idempotency-Key.
export async function submitRevokeProof(options: {
  proofId: string;
  reasonCode: RevocationReasonCode;
  idempotencyKey: string;
  signal?: AbortSignal;
  onUnauthorized?: () => void;
}): Promise<RevokeProofSubmitResult> {
  const session = readSession();
  if (!session) {
    options.onUnauthorized?.();
    return { kind: "unauthorized" };
  }
  const submittedToken = session.accessToken;

  const payload: RevokeProofRequest = {
    reasonCode: options.reasonCode,
  };

  try {
    const data = await apiFetch<RevokeProofResponse>("/api/v1/proofs/{proofId}/revocations", {
      method: "POST",
      pathParams: { proofId: options.proofId },
      headers: {
        "Idempotency-Key": options.idempotencyKey,
      },
      body: payload,
      signal: options.signal,
      onUnauthorized: options.onUnauthorized,
    });
    if (options.signal?.aborted || isSessionStale(submittedToken)) {
      return { kind: "aborted" };
    }
    return { kind: "success", data };
  } catch (error: unknown) {
    if (options.signal?.aborted) {
      return { kind: "aborted" };
    }
    if (error instanceof ApiError && error.status === 401) {
      return { kind: "unauthorized" };
    }
    if (isSessionStale(submittedToken)) {
      return { kind: "aborted" };
    }
    if (error instanceof ApiError && error.code === "PROOF_ALREADY_REVOKED") {
      return { kind: "already_revoked", message: error.message };
    }
    if (error instanceof ApiError) {
      const canRetrySameKey =
        error.code === "REGISTRY_UNAVAILABLE" ||
        error.code === "REGISTRY_TRANSACTION_FAILED" ||
        error.status >= 500;
      const requiresResetKey = error.code === "IDEMPOTENCY_KEY_CONFLICT";
      return {
        kind: "error",
        status: error.status,
        code: error.code,
        message: error.message,
        canRetrySameKey,
        requiresResetKey,
      };
    }
    return {
      kind: "error",
      status: 0,
      code: "NETWORK_ERROR",
      message: "Tidak dapat menghubungi layanan backend. Pastikan layanan aktif lalu coba lagi.",
      canRetrySameKey: true,
      requiresResetKey: false,
    };
  }
}
