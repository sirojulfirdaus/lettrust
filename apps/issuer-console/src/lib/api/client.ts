// Owner: Van (PIC 2) | Status: STUB | Ref: PRD FR-01.02/AC-04, §9.8; SA §10.1, §10.2, §11.1, §11.2.2
// TODO: Wrapper fetch tipis: Authorization Bearer dari sesi, X-Request-ID, parse error envelope; 401 -> clearSession() lalu redirect /login.
import type { paths } from "./schema";

// Base URL backend; disisipkan saat build dari NEXT_PUBLIC_API_BASE_URL (bukan secret).
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// Path API yang valid menurut kontrak OpenAPI hasil generate.
export type ApiPath = keyof paths;

// Error terstruktur dari envelope SA §10.2 untuk ditampilkan sesuai PRD §9.8.
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    readonly requestId: string | null,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// Memanggil endpoint backend dengan token sesi dan mengembalikan body JSON bertipe.
export async function apiFetch<T>(_path: ApiPath, _init?: RequestInit): Promise<T> {
  throw new Error("NOT_IMPLEMENTED");
}
