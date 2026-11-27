// Owner: Pash (PIC 4) | Status: COMPLETE | Ref: PRD FR-02.05, FR-02.06, FR-02.07, FR-02.11; SA §11.3.2, §10.2, TOI-03
import { getServerConfig, PortalConfigurationError } from "@/lib/server/config";

export const runtime = "nodejs";

// Margin overhead multipart (boundary dan header part), sama dengan batas body backend.
const MULTIPART_OVERHEAD_BYTES = 64 * 1024;
const UNAVAILABLE_MESSAGE = "Layanan pemeriksaan sedang tidak tersedia. Coba lagi beberapa saat lagi.";

// Membuat requestId lokal untuk panggilan upstream dan respons gangguan sebelum backend menjawab.
function newRequestId(): string {
  return `req_${crypto.randomUUID().replace(/-/g, "").slice(0, 16).toUpperCase()}`;
}

type FieldDetail = { field: string; issue: string };

// Membentuk error envelope portal tanpa menyertakan detail internal atau isi berkas.
function errorResponse(
  requestId: string,
  status: number,
  code: string,
  message: string,
  details: FieldDetail[] = [],
): Response {
  return Response.json(
    { requestId, error: { code, message, details } },
    { status, headers: { "X-Request-ID": requestId } },
  );
}

// Membaca field boolean secara ketat: absen = undefined, maksimal satu nilai, dan hanya "true"/"false" persis.
function readStrictBoolean(form: FormData, name: string): boolean | undefined | FieldDetail {
  const values = form.getAll(name);
  if (values.length === 0) return undefined;
  if (values.length > 1) return { field: name, issue: "multiple_values" };
  if (values[0] === "true") return true;
  if (values[0] === "false") return false;
  return { field: name, issue: "bool_parsing" };
}

// Membaca referenceCode sebagai satu nilai teks; duplikat atau kiriman berkas ditolak agar mode tidak ambigu.
function readReferenceCode(form: FormData): string | undefined | FieldDetail {
  const values = form.getAll("referenceCode");
  if (values.length === 0) return undefined;
  if (values.length > 1) return { field: "referenceCode", issue: "multiple_values" };
  return typeof values[0] === "string" ? values[0] : { field: "referenceCode", issue: "string_type" };
}

// Membedakan detail error field dari nilai hasil parsing.
function isFieldDetail(value: unknown): value is FieldDetail {
  return typeof value === "object" && value !== null && "issue" in value;
}

// Memvalidasi multipart dan field secara ketat, membatasi ukuran, mewajibkan persetujuan AI, lalu meneruskan API-07.
export async function POST(req: Request): Promise<Response> {
  const requestId = newRequestId();
  const contentType = req.headers.get("content-type") ?? "";
  if (!contentType.toLowerCase().startsWith("multipart/form-data;")) {
    return errorResponse(requestId, 400, "VALIDATION_ERROR", "Permintaan harus menggunakan multipart/form-data.");
  }

  let config: ReturnType<typeof getServerConfig>;
  try {
    config = getServerConfig();
  } catch (error) {
    if (!(error instanceof PortalConfigurationError)) throw error;
    return errorResponse(requestId, 503, "SERVICE_UNAVAILABLE", UNAVAILABLE_MESSAGE);
  }

  // Menolak body besar sebelum dibaca ke memori; ukuran per berkas tetap diperiksa setelah parsing.
  const contentLength = Number(req.headers.get("content-length"));
  if (Number.isFinite(contentLength) && contentLength > config.maxUploadBytes + MULTIPART_OVERHEAD_BYTES) {
    return errorResponse(requestId, 413, "FILE_TOO_LARGE", "Ukuran berkas melebihi batas yang diizinkan.");
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

  // Nilai kanonis dipakai untuk cek persetujuan dan diteruskan, sehingga entri mentah/duplikat tidak sampai ke backend.
  const includeRisk = readStrictBoolean(incoming, "includeRisk");
  const aiConsent = readStrictBoolean(incoming, "aiConsent");
  const referenceCode = readReferenceCode(incoming);
  const invalid = [includeRisk, aiConsent, referenceCode].filter(isFieldDetail);
  if (invalid.length > 0) {
    return errorResponse(requestId, 400, "VALIDATION_ERROR", "Periksa kembali isian yang dikirim.", invalid);
  }

  // Persetujuan diperiksa di server agar analisis AI tidak dapat diminta tanpa centang persetujuan.
  if (includeRisk === true && aiConsent !== true) {
    return errorResponse(
      requestId,
      400,
      "VALIDATION_ERROR",
      "Setujui pemrosesan AI sebelum mengirim surat untuk dianalisis.",
      [{ field: "aiConsent", issue: "consent_required" }],
    );
  }

  // aiConsent hanya untuk portal dan tidak diteruskan ke backend; berkas ganda tetap diteruskan agar backend menjawab MULTIPLE_FILES.
  const outgoing = new FormData();
  if (typeof referenceCode === "string") outgoing.append("referenceCode", referenceCode);
  if (typeof includeRisk === "boolean") outgoing.append("includeRisk", String(includeRisk));
  for (const value of incoming.getAll("file")) {
    if (!(value instanceof File)) continue;
    if (value.size > config.maxUploadBytes) {
      return errorResponse(requestId, 413, "FILE_TOO_LARGE", "Ukuran berkas melebihi batas yang diizinkan.");
    }
    outgoing.append("file", value, value.name);
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
      return errorResponse(requestId, 503, "SERVICE_UNAVAILABLE", UNAVAILABLE_MESSAGE);
    }
    throw error;
  }

  const upstreamRequestId = upstream.headers.get("X-Request-ID");
  if (upstream.status === 401) {
    return errorResponse(
      upstreamRequestId ?? requestId,
      503,
      "SERVICE_UNAVAILABLE",
      UNAVAILABLE_MESSAGE,
    );
  }

  const headers = new Headers();
  const upstreamContentType = upstream.headers.get("Content-Type");
  if (upstreamContentType) headers.set("Content-Type", upstreamContentType);
  if (upstreamRequestId) headers.set("X-Request-ID", upstreamRequestId);
  return new Response(upstream.body, { status: upstream.status, headers });
}
