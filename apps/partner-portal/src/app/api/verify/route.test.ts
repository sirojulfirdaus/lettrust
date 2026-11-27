// Owner: Pash (PIC 4) | Status: COMPLETE | Ref: PRD FR-02.07, FR-02.11; SA §11.3.2, TOI-03
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { POST } from "./route";

const UPSTREAM_REQUEST_ID = "req_BACKEND1234567";

// Menyusun request multipart portal yang menyerupai kiriman browser.
function makeRequest(fields: Array<[string, string | File]>): Request {
  const form = new FormData();
  for (const [name, value] of fields) form.append(name, value);
  return new Request("http://localhost:3001/api/verify", { method: "POST", body: form });
}

describe("POST /api/verify", () => {
  beforeEach(() => {
    vi.stubEnv("LETTRUST_API_BASE_URL", "http://backend:8000");
    vi.stubEnv("LETTRUST_PARTNER_TOKEN", "server-only-token");
    vi.stubEnv("PORTAL_UPSTREAM_TIMEOUT_MS", "120000");
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it("meneruskan hanya field API-07 dengan token server dan requestId backend", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response('{"requestId":"backend-body-id","proofCheck":{}}', {
      status: 200,
      headers: { "Content-Type": "application/json", "X-Request-ID": UPSTREAM_REQUEST_ID },
    }));
    vi.stubGlobal("fetch", fetchMock);
    const request = makeRequest([
      ["referenceCode", "LTR-7K3M-9QX2-H4TD"],
      ["includeRisk", "true"],
      ["aiConsent", "true"],
      ["file", new File(["%PDF-test"], "offer.pdf", { type: "application/pdf" })],
      ["ignored", "jangan diteruskan"],
    ]);

    const response = await POST(request);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const forwarded = init.body as FormData;

    expect(url).toBe("http://backend:8000/api/v1/verifications");
    expect(init.method).toBe("POST");
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer server-only-token");
    expect(new Headers(init.headers).get("X-Request-ID")).toMatch(/^req_[A-F0-9]{16}$/);
    expect([...forwarded.keys()]).toEqual(["referenceCode", "includeRisk", "file"]);
    expect(response.status).toBe(200);
    expect(response.headers.get("X-Request-ID")).toBe(UPSTREAM_REQUEST_ID);
    expect(await response.text()).toBe('{"requestId":"backend-body-id","proofCheck":{}}');
  });

  it("mengubah 401 upstream menjadi 503 tanpa meneruskan status autentikasi", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", {
      status: 401,
      headers: { "X-Request-ID": UPSTREAM_REQUEST_ID },
    })));

    const response = await POST(makeRequest([["referenceCode", "LTR-7K3M-9QX2-H4TD"]]));
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(response.headers.get("X-Request-ID")).toBe(UPSTREAM_REQUEST_ID);
    expect(body).toMatchObject({ requestId: UPSTREAM_REQUEST_ID, error: { code: "SERVICE_UNAVAILABLE", details: [] } });
  });

  it("memetakan kegagalan jaringan dan timeout ke 503", async () => {
    for (const failure of [new TypeError("fetch failed"), new DOMException("timed out", "TimeoutError")]) {
      vi.stubGlobal("fetch", vi.fn().mockRejectedValue(failure));
      const response = await POST(makeRequest([["referenceCode", "LTR-7K3M-9QX2-H4TD"]]));
      expect(response.status).toBe(503);
      expect((await response.json()).error.code).toBe("SERVICE_UNAVAILABLE");
    }
  });

  // Menyamarkan konfigurasi server yang tidak lengkap sebagai gangguan layanan.
  it("mengembalikan envelope 503 saat konfigurasi server hilang", async () => {
    vi.stubEnv("LETTRUST_API_BASE_URL", "");
    vi.stubEnv("LETTRUST_PARTNER_TOKEN", "");
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const response = await POST(makeRequest([["referenceCode", "LTR-7K3M-9QX2-H4TD"]]));
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(response.headers.get("X-Request-ID")).toMatch(/^req_[A-F0-9]{16}$/);
    expect(body.error.code).toBe("SERVICE_UNAVAILABLE");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("menerima berkas 5 MiB dan menolak berkas yang melebihi batas", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const acceptedFile = new File([new Uint8Array(5 * 1024 * 1024)], "five-mib.pdf", { type: "application/pdf" });
    const accepted = await POST(makeRequest([["file", acceptedFile], ["includeRisk", "true"], ["aiConsent", "true"]]));
    expect(accepted.status).toBe(200);

    const tooLargeFile = new File([new Uint8Array(5 * 1024 * 1024 + 1)], "too-large.pdf", { type: "application/pdf" });
    const rejected = await POST(makeRequest([["file", tooLargeFile], ["includeRisk", "true"], ["aiConsent", "true"]]));
    expect(rejected.status).toBe(413);
    expect((await rejected.json()).error.code).toBe("FILE_TOO_LARGE");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  // Body yang jelas melebihi batas + margin multipart ditolak tanpa membaca formData.
  it("menolak 413 berdasarkan content-length sebelum membaca body", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const formData = vi.fn();
    const oversized = {
      headers: new Headers({
        "content-type": "multipart/form-data; boundary=x",
        "content-length": String(5 * 1024 * 1024 + 64 * 1024 + 1),
      }),
      formData,
    } as unknown as Request;

    const response = await POST(oversized);

    expect(response.status).toBe(413);
    expect((await response.json()).error.code).toBe("FILE_TOO_LARGE");
    expect(formData).not.toHaveBeenCalled();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  // Batas ukuran dibaca dari MAX_UPLOAD_BYTES, sama dengan nama env backend.
  it("memakai MAX_UPLOAD_BYTES dari konfigurasi server", async () => {
    vi.stubEnv("MAX_UPLOAD_BYTES", "10");
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const file = new File([new Uint8Array(11)], "offer.pdf", { type: "application/pdf" });

    const response = await POST(makeRequest([["referenceCode", "LTR-7K3M-9QX2-H4TD"], ["file", file]]));

    expect(response.status).toBe(413);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  // Analisis AI tanpa persetujuan ditolak di server walaupun browser melewati validasi form.
  it("menolak includeRisk=true tanpa aiConsent=true dan tidak meneruskan aiConsent", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const file = new File(["%PDF-test"], "offer.pdf", { type: "application/pdf" });

    for (const consent of [[], [["aiConsent", "false"]]] as Array<Array<[string, string]>>) {
      const response = await POST(makeRequest([["includeRisk", "true"], ...consent, ["file", file]]));
      const body = await response.json();
      expect(response.status).toBe(400);
      expect(body.error).toMatchObject({ code: "VALIDATION_ERROR", message: "Setujui pemrosesan AI sebelum mengirim surat untuk dianalisis." });
    }
    expect(fetchMock).not.toHaveBeenCalled();

    const accepted = await POST(makeRequest([["referenceCode", "LTR-7K3M-9QX2-H4TD"], ["includeRisk", "false"]]));
    expect(accepted.status).toBe(200);
    const forwarded = (fetchMock.mock.calls[0] as [string, RequestInit])[1].body as FormData;
    expect(forwarded.has("aiConsent")).toBe(false);
  });

  // Field boolean dan referenceCode harus satu nilai persis; penolakan terjadi sebelum panggilan upstream.
  it("menolak nilai boolean tidak kanonis dan field ganda tanpa memanggil upstream", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const file = new File(["%PDF-test"], "offer.pdf", { type: "application/pdf" });
    const cases: Array<[Array<[string, string]>, string, string]> = [
      [[["includeRisk", "1"], ["aiConsent", "true"]], "includeRisk", "bool_parsing"],
      [[["includeRisk", "True"], ["aiConsent", "true"]], "includeRisk", "bool_parsing"],
      [[["includeRisk", "true"], ["includeRisk", "false"], ["aiConsent", "true"]], "includeRisk", "multiple_values"],
      [[["includeRisk", "true"], ["aiConsent", "yes"]], "aiConsent", "bool_parsing"],
      [[["includeRisk", "true"], ["aiConsent", "true"], ["aiConsent", "true"]], "aiConsent", "multiple_values"],
      [[["referenceCode", "LTR-7K3M-9QX2-H4TD"], ["referenceCode", "LTR-AAAA-BBBB-CCCC"]], "referenceCode", "multiple_values"],
    ];

    for (const [fields, field, issue] of cases) {
      const response = await POST(makeRequest([...fields, ["file", file]]));
      const body = await response.json();
      expect(response.status).toBe(400);
      expect(body.error).toMatchObject({ code: "VALIDATION_ERROR", details: [{ field, issue }] });
    }
    expect(fetchMock).not.toHaveBeenCalled();
  });

  // Penolakan persetujuan dapat dibedakan klien lewat details[].field "aiConsent".
  it("menandai penolakan persetujuan dengan detail field aiConsent", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const response = await POST(makeRequest([["includeRisk", "true"], ["file", new File(["%PDF"], "a.pdf")]]));
    const body = await response.json();

    expect(response.status).toBe(400);
    expect(body.error.details).toEqual([{ field: "aiConsent", issue: "consent_required" }]);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  // Backend hanya menerima satu includeRisk kanonis; aiConsent tidak pernah diteruskan.
  it("meneruskan tepat satu includeRisk kanonis dan mempertahankan semantik saat absen", async () => {
    const fetchMock = vi.fn().mockImplementation(async () => new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const file = new File(["%PDF-test"], "offer.pdf", { type: "application/pdf" });

    await POST(makeRequest([["includeRisk", "true"], ["aiConsent", "true"], ["file", file]]));
    await POST(makeRequest([["referenceCode", "LTR-7K3M-9QX2-H4TD"]]));

    const withRisk = (fetchMock.mock.calls[0] as [string, RequestInit])[1].body as FormData;
    expect(withRisk.getAll("includeRisk")).toEqual(["true"]);
    expect(withRisk.has("aiConsent")).toBe(false);
    const withoutRisk = (fetchMock.mock.calls[1] as [string, RequestInit])[1].body as FormData;
    expect(withoutRisk.has("includeRisk")).toBe(false);
    expect(withoutRisk.getAll("referenceCode")).toEqual(["LTR-7K3M-9QX2-H4TD"]);
  });

  // Berkas ganda tetap diteruskan apa adanya agar backend menjawab MULTIPLE_FILES.
  it("tetap meneruskan berkas ganda ke backend", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 400 }));
    vi.stubGlobal("fetch", fetchMock);
    const file = new File(["%PDF-test"], "offer.pdf", { type: "application/pdf" });

    await POST(makeRequest([["includeRisk", "true"], ["aiConsent", "true"], ["file", file], ["file", file]]));

    const forwarded = (fetchMock.mock.calls[0] as [string, RequestInit])[1].body as FormData;
    expect(forwarded.getAll("file")).toHaveLength(2);
  });
});
