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

  it("menerima berkas 5 MiB dan menolak berkas yang melebihi batas", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const acceptedFile = new File([new Uint8Array(5 * 1024 * 1024)], "five-mib.pdf", { type: "application/pdf" });
    const accepted = await POST(makeRequest([["file", acceptedFile], ["includeRisk", "true"]]));
    expect(accepted.status).toBe(200);

    const tooLargeFile = new File([new Uint8Array(5 * 1024 * 1024 + 1)], "too-large.pdf", { type: "application/pdf" });
    const rejected = await POST(makeRequest([["file", tooLargeFile], ["includeRisk", "true"]]));
    expect(rejected.status).toBe(413);
    expect((await rejected.json()).error.code).toBe("FILE_TOO_LARGE");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
