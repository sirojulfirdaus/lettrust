// Owner: Pash (PIC 4) | Status: COMPLETE | Ref: PRD FR-02.07, BR-01.14; SA §11.3.2, §14.2
import "server-only";

// Konfigurasi server portal; token partner tidak pernah dikirim ke browser.
export type PortalServerConfig = {
  apiBaseUrl: string;
  partnerToken: string;
  upstreamTimeoutMs: number;
};

const DEFAULT_UPSTREAM_TIMEOUT_MS = 120000;

// Membaca dan memvalidasi env server portal saat dipanggil (bukan saat import) agar next build tidak butuh env.
export function getServerConfig(env: Record<string, string | undefined> = process.env): PortalServerConfig {
  const apiBaseUrl = env.LETTRUST_API_BASE_URL?.trim().replace(/\/+$/, "");
  if (!apiBaseUrl || !URL.canParse(apiBaseUrl)) {
    throw new Error("Konfigurasi portal tidak valid: LETTRUST_API_BASE_URL wajib berupa URL.");
  }

  const partnerToken = env.LETTRUST_PARTNER_TOKEN?.trim();
  if (!partnerToken) {
    throw new Error("Konfigurasi portal tidak valid: LETTRUST_PARTNER_TOKEN wajib diisi.");
  }

  const timeoutRaw = env.PORTAL_UPSTREAM_TIMEOUT_MS?.trim();
  const upstreamTimeoutMs = timeoutRaw ? Number(timeoutRaw) : DEFAULT_UPSTREAM_TIMEOUT_MS;
  if (!Number.isInteger(upstreamTimeoutMs) || upstreamTimeoutMs <= 0) {
    throw new Error("Konfigurasi portal tidak valid: PORTAL_UPSTREAM_TIMEOUT_MS wajib bilangan bulat positif (ms).");
  }

  return { apiBaseUrl, partnerToken, upstreamTimeoutMs };
}
