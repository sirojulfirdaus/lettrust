// Owner: Pash (PIC 4) | Status: STUB | Ref: PRD FR-02.07, FR-02.11; SA §11.3.2, §10.2, TOI-03
// TODO: Teruskan multipart ke API-07 dengan token partner dari getServerConfig(); timeout/jaringan/401 upstream -> 503 SERVICE_UNAVAILABLE.
// Import efek samping memastikan rantai modul server-only ikut dibundel; token belum dibaca pada stub ini.
import "@/lib/server/config";

export const runtime = "nodejs";

// Membuat requestId berformat SA §6.3 (req_ + 16 karakter).
function newRequestId(): string {
  return `req_${crypto.randomUUID().replace(/-/g, "").slice(0, 16).toUpperCase()}`;
}

// Meneruskan permintaan pemeriksaan pelamar ke API-07 menggunakan token partner di sisi server.
export async function POST(_req: Request): Promise<Response> {
  // 1. Pastikan multipart; ambil hanya field referenceCode, file, includeRisk.
  // 2. Susun FormData baru (field lain dibuang).
  // 3. fetch(`${apiBaseUrl}/api/v1/verifications`, {
  //      method: "POST", body, headers: { Authorization: `Bearer ${partnerToken}`, "X-Request-ID": id },
  //      signal: AbortSignal.timeout(upstreamTimeoutMs) })
  // 4. Teruskan status dan body JSON apa adanya.
  // 5. Error jaringan/timeout/401 dari upstream -> 503 { error: { code: "SERVICE_UNAVAILABLE" } }.
  // BFF tidak menyimpan berkas dan tidak mencatat isi permintaan.
  const requestId = newRequestId();
  return Response.json(
    {
      requestId,
      error: {
        code: "NOT_IMPLEMENTED",
        message: "Fitur pemeriksaan belum diimplementasikan.",
        details: [],
      },
    },
    { status: 501, headers: { "X-Request-ID": requestId } },
  );
}
