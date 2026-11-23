// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-01.02/AC-04, §9.8; SA §10.1, §10.2, §11.1, §11.2.2
import type { components, paths } from "./schema";
import { consumeUnauthorizedSession, readSession } from "@/lib/session";

// Base URL backend; disisipkan saat build dari NEXT_PUBLIC_API_BASE_URL (bukan secret).
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// Path API yang valid menurut kontrak OpenAPI hasil generate.
export type ApiPath = keyof paths;

export type ErrorCode = components["schemas"]["ErrorCode"];
export type ErrorDetail = components["schemas"]["ErrorDetail"];
export type ErrorEnvelope = components["schemas"]["ErrorEnvelope"];
export type MeResponse = components["schemas"]["MeResponse"];
export type LoginRequest = components["schemas"]["LoginRequest"];
export type LoginResponse = components["schemas"]["LoginResponse"];
export type RegisterAccountRequest = components["schemas"]["RegisterAccountRequest"];
export type UserSummary = components["schemas"]["UserSummary"];
export type RegisterIssuerRequest = components["schemas"]["RegisterIssuerRequest"];
export type RegisterIssuerResponse = components["schemas"]["RegisterIssuerResponse"];
export type IssuerDetailResponse = components["schemas"]["IssuerDetailResponse"];
export type ProofListResponse = components["schemas"]["ProofListResponse"];

// Pesan kesalahan Console sesuai PRD §9.8.
const ERROR_MESSAGES: Record<string, string> = {
  EMAIL_ALREADY_REGISTERED: "Email sudah terdaftar. Silakan masuk.",
  INVALID_CREDENTIALS: "Email atau password tidak sesuai.",
  ACCOUNT_ALREADY_AFFILIATED: "Akun Anda sudah terhubung dengan perusahaan.",
  REGISTRATION_NUMBER_ALREADY_EXISTS: "Nomor registrasi perusahaan sudah terdaftar.",
  ISSUER_DECISION_ALREADY_MADE: "Penerbit ini sudah memiliki keputusan verifikasi.",
  ISSUER_NOT_VERIFIED: "Penerbit belum terverifikasi sehingga HR belum dapat diotorisasi.",
  HR_NOT_AFFILIATED: "Akun HR tidak terhubung dengan penerbit ini.",
  HR_ALREADY_AUTHORIZED: "Akun HR ini sudah diotorisasi.",
  PROOF_ALREADY_REVOKED: "Bukti ini sudah dicabut sebelumnya.",
  DUPLICATE_ACTIVE_DOCUMENT: "Berkas yang sama sudah memiliki bukti aktif.",
  IDEMPOTENCY_KEY_CONFLICT:
    "Permintaan bertentangan dengan permintaan sebelumnya. Mulai ulang proses penerbitan.",
  REGISTRY_UNAVAILABLE:
    "Pencatatan ke registry gagal. Tidak ada perubahan yang tersimpan. Coba lagi.",
  REGISTRY_TRANSACTION_FAILED:
    "Pencatatan ke registry gagal. Tidak ada perubahan yang tersimpan. Coba lagi.",
  UNSUPPORTED_MEDIA_TYPE: "Berkas harus berformat PDF.",
  FILE_TOO_LARGE: "Ukuran berkas melebihi batas yang diizinkan.",
  EMPTY_FILE: "Berkas kosong tidak dapat diproses.",
  RATE_LIMITED: "Terlalu banyak permintaan. Coba lagi beberapa saat lagi.",
  UNAUTHENTICATED: "Sesi Anda telah berakhir. Silakan masuk kembali.",
  FORBIDDEN_OPERATION: "Anda tidak memiliki izin untuk tindakan ini.",
};

// Memetakan kode error dan status HTTP ke pesan aman berbahasa Indonesia (PRD §9.8).
export function mapApiErrorMessage(
  code: string,
  status: number,
  fallbackMessage?: string,
): string {
  if (Object.hasOwn(ERROR_MESSAGES, code)) {
    return ERROR_MESSAGES[code];
  }
  if (status === 401) {
    return "Sesi Anda telah berakhir. Silakan masuk kembali.";
  }
  if (status === 403) {
    return "Anda tidak memiliki izin untuk tindakan ini.";
  }
  if (code === "VALIDATION_ERROR") {
    return "Periksa kembali data yang Anda masukkan.";
  }
  if (fallbackMessage && fallbackMessage.trim().length > 0 && status < 500) {
    return fallbackMessage;
  }
  return "Layanan sedang tidak tersedia. Coba lagi beberapa saat lagi.";
}

// Error terstruktur dari envelope SA §10.2 untuk ditampilkan sesuai PRD §9.8.
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    readonly requestId: string | null,
    message: string,
    readonly details: readonly ErrorDetail[] = [],
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export type ApiFetchOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  pathParams?: Record<string, string>;
  query?: Record<string, string | number | undefined>;
  // Default true; set false untuk endpoint publik seperti login/register agar 401 tidak memicu redirect sesi.
  auth?: boolean;
  // Override redirect saat 401 (berguna untuk pengujian unit).
  onUnauthorized?: () => void;
};

// Membuat X-Request-ID format req_<16 karakter> sesuai konvensi SA §10.2.
function generateRequestId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    const compact = crypto.randomUUID().replace(/-/g, "").slice(0, 16).toUpperCase();
    return `req_${compact}`;
  }
  return `req_${Date.now().toString(36).toUpperCase().padStart(16, "0").slice(-16)}`;
}

// Menyusun URL lengkap dengan substitusi parameter path dan query string opsional.
export function buildApiUrl(
  path: ApiPath,
  pathParams?: Record<string, string>,
  query?: Record<string, string | number | undefined>,
): string {
  let resolvedPath: string = path;
  if (pathParams) {
    for (const [key, value] of Object.entries(pathParams)) {
      resolvedPath = resolvedPath.replace(`{${key}}`, encodeURIComponent(value));
    }
  }

  const base = API_BASE_URL.replace(/\/+$/, "");
  const url = new URL(`${base}${resolvedPath}`);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== "") {
        url.searchParams.set(key, String(value));
      }
    }
  }
  return url.toString();
}

// Handler default yang dapat didaftarkan oleh komponen klien (mis. Next.js router) untuk redirect 401.
let registeredUnauthorizedHandler: (() => void) | null = null;

// Mendaftarkan handler redirect 401 berbasis router klien; mengembalikan fungsi cleanup.
export function registerUnauthorizedHandler(handler: () => void): () => void {
  registeredUnauthorizedHandler = handler;
  return () => {
    if (registeredUnauthorizedHandler === handler) {
      registeredUnauthorizedHandler = null;
    }
  };
}

// Mengarahkan browser ke halaman login dengan penanda sesi berakhir.
function defaultRedirectToLogin(): void {
  if (registeredUnauthorizedHandler) {
    registeredUnauthorizedHandler();
    return;
  }
  if (typeof window === "undefined") {
    return;
  }
  if (window.location.pathname !== "/login") {
    const loginUrl = new URL("/login?reason=session_expired", window.location.origin);
    window.location.href = loginUrl.toString();
  }
}

// Membaca envelope error SA §10.2 secara aman bila respons gagal bukan JSON standar.
function parseErrorEnvelope(payload: unknown): ErrorEnvelope | null {
  if (typeof payload !== "object" || payload === null) {
    return null;
  }
  const candidate = payload as Partial<ErrorEnvelope>;
  if (
    typeof candidate.error === "object" &&
    candidate.error !== null &&
    typeof candidate.error.code === "string" &&
    typeof candidate.error.message === "string"
  ) {
    return {
      requestId: typeof candidate.requestId === "string" ? candidate.requestId : "",
      error: {
        code: candidate.error.code as ErrorCode,
        message: candidate.error.message,
        details: Array.isArray(candidate.error.details) ? candidate.error.details : [],
      },
    };
  }
  return null;
}

// Mengekstrak token Bearer dari header Authorization bila sudah disetel pemanggil.
function extractBearerToken(headers: Headers): string | null {
  const value = headers.get("Authorization");
  if (!value) {
    return null;
  }
  const match = /^Bearer\s+(.+)$/i.exec(value.trim());
  return match ? match[1].trim() : null;
}

// Memanggil endpoint backend dengan token sesi dan mengembalikan body JSON bertipe.
export async function apiFetch<T>(path: ApiPath, options: ApiFetchOptions = {}): Promise<T> {
  const {
    body,
    pathParams,
    query,
    auth = true,
    onUnauthorized,
    headers: initHeaders,
    ...restInit
  } = options;

  const headers = new Headers(initHeaders);
  headers.set("Accept", "application/json");
  if (!headers.has("X-Request-ID")) {
    headers.set("X-Request-ID", generateRequestId());
  }

  let sentToken: string | null = null;
  if (auth) {
    const existingHeaderToken = extractBearerToken(headers);
    if (existingHeaderToken !== null) {
      sentToken = existingHeaderToken;
    } else {
      const session = readSession();
      if (session) {
        sentToken = session.accessToken;
        headers.set("Authorization", `Bearer ${session.accessToken}`);
      }
    }
  }

  let encodedBody: BodyInit | undefined;
  if (body instanceof FormData) {
    encodedBody = body;
  } else if (body !== undefined) {
    if (!headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    encodedBody = typeof body === "string" ? body : JSON.stringify(body);
  }

  const url = buildApiUrl(path, pathParams, query);
  const response = await fetch(url, {
    ...restInit,
    headers,
    body: encodedBody,
  });

  const text = await response.text();
  let payload: unknown = null;
  if (text.length > 0) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = null;
    }
  }

  if (!response.ok) {
    const envelope = parseErrorEnvelope(payload);
    const code = envelope?.error.code ?? (response.status === 401 ? "UNAUTHENTICATED" : "INTERNAL_ERROR");
    const requestId = envelope?.requestId || response.headers.get("X-Request-ID") || null;
    const details = envelope?.error.details ?? [];
    const message = mapApiErrorMessage(code, response.status, envelope?.error.message);

    if (response.status === 401 && auth) {
      if (consumeUnauthorizedSession(sentToken)) {
        (onUnauthorized ?? defaultRedirectToLogin)();
      }
    }

    throw new ApiError(response.status, code, requestId, message, details);
  }

  return payload as T;
}

// Memanggil S-03 GET /api/v1/auth/me untuk memperoleh profil sesi aktif atau memverifikasi token baru sebelum disimpan.
export async function fetchSessionProfile(
  options?: Pick<ApiFetchOptions, "signal" | "onUnauthorized"> & { accessToken?: string },
): Promise<MeResponse> {
  const { accessToken, ...rest } = options ?? {};
  if (accessToken !== undefined) {
    return apiFetch<MeResponse>("/api/v1/auth/me", {
      method: "GET",
      auth: false,
      headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
      ...rest,
    });
  }
  return apiFetch<MeResponse>("/api/v1/auth/me", {
    method: "GET",
    ...rest,
  });
}
