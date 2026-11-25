// Owner: Pash (PIC 4) | Status: COMPLETE | Ref: PRD FR-02.07, FR-02.11; SA §11.3.2, §10.2, TOI-03
import { getServerConfig, PortalConfigurationError } from "@/lib/server/config";

export const runtime = "nodejs";

const MAX_UPLOAD_BYTES = 5 * 1024 * 1024;

// Membuat requestId lokal untuk panggilan upstream dan respons gangguan sebelum backend menjawab.
function newRequestId(): string {
  return `req_${crypto.randomUUID().replace(/-/g, "").slice(0, 16).toUpperCase()}`;
}

// Membentuk error envelope portal tanpa menyertakan detail internal atau isi berkas.
function errorResponse(requestId: string, status: number, code: string, message: string): Response {
  return Response.json(
    { requestId, error: { code, message, details: [] } },
    { status, headers: { "X-Request-ID": requestId } },
  );
}

// Memvalidasi multipart, membatasi ukuran berkas, dan meneruskan API-07 dari server portal.
export async function POST(req: Request): Promise<Response> {
  const requestId = newRequestId();
  const contentType = req.headers.get("content-type") ?? "";
  if (!contentType.toLowerCase().startsWith("multipart/form-data;")) {
    return errorResponse(requestId, 400, "VALIDATION_ERROR", "Permintaan harus menggunakan multipart/form-data.");
  }

  let incoming: FormData;
  try {
    incoming = await req.formData();
  } catch (error) {
    if (error instanceof TypeError) {
      return errorResponse(requestId, 400, "VALIDATION_ERROR", "Format berkas yang dikirim tidak valid.");
    }
    throw error;
  }

  const outgoing = new FormData();
  for (const [name, value] of incoming.entries()) {
    if (name === "referenceCode" || name === "includeRisk") {
      if (typeof value === "string") outgoing.append(name, value);
    } else if (name === "file" && value instanceof File) {
      if (value.size > MAX_UPLOAD_BYTES) {
        return errorResponse(requestId, 413, "FILE_TOO_LARGE", "Ukuran berkas melebihi batas yang diizinkan.");
      }
      outgoing.append("file", value, value.name);
    }
  }

  let config: ReturnType<typeof getServerConfig>;
  try {
    config = getServerConfig();
  } catch (error) {
    if (!(error instanceof PortalConfigurationError)) throw error;
    return errorResponse(requestId, 503, "SERVICE_UNAVAILABLE", "Layanan pemeriksaan sedang tidak tersedia. Coba lagi beberapa saat lagi.");
  }
  let upstream: Response;
  try {
    upstream = await fetch(`${config.apiBaseUrl}/api/v1/verifications`, {
      method: "POST",
      body: outgoing,
      headers: {
        Authorization: `Bearer ${config.partnerToken}`,
        "X-Request-ID": requestId,
      },
      signal: AbortSignal.timeout(config.upstreamTimeoutMs),
    });
  } catch (error) {
    if (error instanceof TypeError || (error instanceof DOMException && error.name === "TimeoutError")) {
      return errorResponse(requestId, 503, "SERVICE_UNAVAILABLE", "Layanan pemeriksaan sedang tidak tersedia. Coba lagi beberapa saat lagi.");
    }
    throw error;
  }

  const upstreamRequestId = upstream.headers.get("X-Request-ID");
  if (upstream.status === 401) {
    return errorResponse(
      upstreamRequestId ?? requestId,
      503,
      "SERVICE_UNAVAILABLE",
      "Layanan pemeriksaan sedang tidak tersedia. Coba lagi beberapa saat lagi.",
    );
  }

  const headers = new Headers();
  const upstreamContentType = upstream.headers.get("Content-Type");
  if (upstreamContentType) headers.set("Content-Type", upstreamContentType);
  if (upstreamRequestId) headers.set("X-Request-ID", upstreamRequestId);
  return new Response(upstream.body, { status: upstream.status, headers });
}
