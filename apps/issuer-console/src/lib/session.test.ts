// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-01.02, §9.8; SA §11.2.1, §11.2.2, §18.1
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  errorInvalidCredentials,
  errorUnauthenticated,
  errorValidationError,
  s03SessionAdmin,
  s03SessionHrAuthorized,
  s03SessionHrPending,
  s03SessionHrRejected,
  s03SessionHrUnaffiliated,
  s03SessionHrVerifiedNotAuthorized,
} from "@/fixtures/api";
import {
  ApiError,
  apiFetch,
  buildApiUrl,
  mapApiErrorMessage,
} from "@/lib/api/client";
import {
  canIssueProofs,
  getNavRoutesForUser,
  resolveLandingRoute,
} from "@/lib/routes";
import {
  clearSession,
  createSession,
  isSessionExpired,
  readSession,
  saveSession,
  SESSION_STORAGE_KEY,
} from "@/lib/session";

// Storage in-memory sederhana untuk meniru window.sessionStorage di lingkungan Node Vitest.
function createMemoryStorage(): Storage {
  const store = new Map<string, string>();
  return {
    get length() {
      return store.size;
    },
    clear: () => store.clear(),
    getItem: (key: string) => store.get(key) ?? null,
    key: (index: number) => Array.from(store.keys())[index] ?? null,
    removeItem: (key: string) => {
      store.delete(key);
    },
    setItem: (key: string, value: string) => {
      store.set(key, value);
    },
  };
}

describe("manajemen sesi Console", () => {
  let storage: Storage;
  let dispatchedEvents: string[];

  beforeEach(() => {
    storage = createMemoryStorage();
    dispatchedEvents = [];
    vi.stubGlobal("window", {
      sessionStorage: storage,
      location: { pathname: "/hr", assign: vi.fn() },
      dispatchEvent: (event: Event) => {
        dispatchedEvents.push(event.type);
        return true;
      },
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("menyimpan, membaca, dan menghapus sesi pada kunci lettrust.session", () => {
    const now = Date.parse("2026-11-22T10:00:00Z");
    const session = createSession("token-demo-123", 3600, now);

    saveSession(session);
    expect(storage.getItem(SESSION_STORAGE_KEY)).toBe(JSON.stringify(session));
    expect(readSession(now + 1000)).toEqual(session);

    clearSession();
    expect(storage.getItem(SESSION_STORAGE_KEY)).toBeNull();
    expect(readSession(now + 1000)).toBeNull();
    expect(dispatchedEvents.length).toBe(2);
  });

  it("mengembalikan null dan membersihkan sesi bila sudah kedaluwarsa atau rusak", () => {
    const now = Date.parse("2026-11-22T10:00:00Z");
    const expired = createSession("token-expired", -10, now);

    expect(isSessionExpired(expired, now)).toBe(true);
    saveSession(expired);
    expect(readSession(now)).toBeNull();
    expect(storage.getItem(SESSION_STORAGE_KEY)).toBeNull();

    storage.setItem(SESSION_STORAGE_KEY, "{bukan-json");
    expect(readSession(now)).toBeNull();
    expect(storage.getItem(SESSION_STORAGE_KEY)).toBeNull();
  });
});

describe("guard dan navigasi berbasis peran", () => {
  it("mengarahkan halaman akar sesuai role dan afiliasi S-03", () => {
    expect(resolveLandingRoute(s03SessionAdmin)).toBe("/admin/issuers");
    expect(resolveLandingRoute(s03SessionHrUnaffiliated)).toBe("/onboarding/company");
    expect(resolveLandingRoute(s03SessionHrPending)).toBe("/hr");
    expect(resolveLandingRoute(s03SessionHrRejected)).toBe("/hr");
    expect(resolveLandingRoute(s03SessionHrVerifiedNotAuthorized)).toBe("/hr");
    expect(resolveLandingRoute(s03SessionHrAuthorized)).toBe("/hr");
  });

  it("hanya mengaktifkan menu bukti untuk HR AUTHORIZED pada penerbit VERIFIED", () => {
    expect(canIssueProofs(s03SessionHrAuthorized)).toBe(true);
    expect(canIssueProofs(s03SessionHrPending)).toBe(false);
    expect(canIssueProofs(s03SessionHrVerifiedNotAuthorized)).toBe(false);
    expect(canIssueProofs(s03SessionAdmin)).toBe(false);

    expect(getNavRoutesForUser(s03SessionAdmin).map((r) => r.path)).toEqual(["/admin/issuers"]);
    expect(getNavRoutesForUser(s03SessionHrUnaffiliated).map((r) => r.path)).toEqual([
      "/onboarding/company",
    ]);
    expect(getNavRoutesForUser(s03SessionHrPending).map((r) => r.path)).toEqual(["/hr"]);
    expect(getNavRoutesForUser(s03SessionHrAuthorized).map((r) => r.path)).toEqual([
      "/hr",
      "/hr/proofs",
      "/hr/proofs/new",
    ]);
  });
});

describe("API client dan penanganan error envelope", () => {
  let storage: Storage;

  beforeEach(() => {
    storage = createMemoryStorage();
    vi.stubGlobal("window", {
      sessionStorage: storage,
      location: { pathname: "/hr", assign: vi.fn() },
      dispatchEvent: vi.fn(),
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("menyertakan Authorization Bearer dan X-Request-ID serta mem-parsing respons JSON", async () => {
    saveSession(createSession("jwt-valid", 3600));
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(s03SessionHrAuthorized), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const me = await apiFetch<typeof s03SessionHrAuthorized>("/api/v1/auth/me");
    expect(me.userId).toBe(s03SessionHrAuthorized.userId);

    const [calledUrl, calledInit] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(calledUrl).toBe(buildApiUrl("/api/v1/auth/me"));
    const headers = new Headers(calledInit.headers);
    expect(headers.get("Authorization")).toBe("Bearer jwt-valid");
    expect(headers.get("X-Request-ID")).toMatch(/^req_[A-Z0-9]{16}$/);
  });

  it("menghapus sesi dan memanggil redirect saat respons 401 pada endpoint terlindungi", async () => {
    saveSession(createSession("jwt-expired", 3600));
    const onUnauthorized = vi.fn();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify(errorUnauthenticated), {
          status: 401,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(
      apiFetch("/api/v1/auth/me", { onUnauthorized }),
    ).rejects.toMatchObject({
      status: 401,
      code: "UNAUTHENTICATED",
      message: "Sesi Anda telah berakhir. Silakan masuk kembali.",
    });

    expect(storage.getItem(SESSION_STORAGE_KEY)).toBeNull();
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
  });

  it("tidak menghapus sesi baru dan tidak redirect saat respons 401 lama untuk token A tiba setelah token B tersimpan", async () => {
    const sessionA = createSession("jwt-token-A", 3600);
    const sessionB = createSession("jwt-token-B", 3600);
    saveSession(sessionA);

    let resolveResponseA: ((response: Response) => void) | undefined;
    const fetchMock = vi.fn().mockImplementation(
      () =>
        new Promise<Response>((resolve) => {
          resolveResponseA = resolve;
        }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const onUnauthorized = vi.fn();
    const pendingRequestA = apiFetch("/api/v1/auth/me", { onUnauthorized });

    // Pengguna login ulang dan menyimpan sesi B sebelum respons 401 untuk token A tiba.
    saveSession(sessionB);
    expect(resolveResponseA).toBeDefined();
    resolveResponseA!(
      new Response(JSON.stringify(errorUnauthenticated), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(pendingRequestA).rejects.toMatchObject({
      status: 401,
      code: "UNAUTHENTICATED",
    });

    expect(readSession()).toEqual(sessionB);
    expect(onUnauthorized).not.toHaveBeenCalled();
  });

  it("tidak menghapus sesi baru saat request tanpa token mendapat 401 setelah pengguna login", async () => {
    let resolveResponse: ((response: Response) => void) | undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation(
        () =>
          new Promise<Response>((resolve) => {
            resolveResponse = resolve;
          }),
      ),
    );

    const onUnauthorized = vi.fn();
    const pending = apiFetch("/api/v1/auth/me", { onUnauthorized });

    const sessionB = createSession("jwt-token-baru", 3600);
    saveSession(sessionB);

    resolveResponse!(
      new Response(JSON.stringify(errorUnauthenticated), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(pending).rejects.toMatchObject({ status: 401 });
    expect(readSession()).toEqual(sessionB);
    expect(onUnauthorized).not.toHaveBeenCalled();
  });

  it("tidak memicu redirect saat respons 401 lama tiba setelah pengguna sudah keluar (logout)", async () => {
    saveSession(createSession("jwt-sebelum-logout", 3600));
    let resolveResponse: ((response: Response) => void) | undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation(
        () =>
          new Promise<Response>((resolve) => {
            resolveResponse = resolve;
          }),
      ),
    );

    const onUnauthorized = vi.fn();
    const pending = apiFetch("/api/v1/auth/me", { onUnauthorized });

    clearSession();
    resolveResponse!(
      new Response(JSON.stringify(errorUnauthenticated), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(pending).rejects.toMatchObject({ status: 401 });
    expect(readSession()).toBeNull();
    expect(onUnauthorized).not.toHaveBeenCalled();
  });

  it("tidak memicu redirect sesi saat 401 INVALID_CREDENTIALS pada login (auth: false)", async () => {
    const onUnauthorized = vi.fn();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify(errorInvalidCredentials), {
          status: 401,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(
      apiFetch("/api/v1/auth/login", {
        method: "POST",
        auth: false,
        body: { email: "salah@lettrust.test", password: "password-salah" },
        onUnauthorized,
      }),
    ).rejects.toMatchObject({
      status: 401,
      code: "INVALID_CREDENTIALS",
      message: "Email atau password tidak sesuai.",
    });

    expect(onUnauthorized).not.toHaveBeenCalled();
  });

  it("mem-parsing details VALIDATION_ERROR dari envelope error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify(errorValidationError), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    try {
      await apiFetch("/api/v1/auth/register", { method: "POST", auth: false, body: {} });
      expect.fail("seharusnya melempar ApiError");
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError);
      const apiErr = error as ApiError;
      expect(apiErr.code).toBe("VALIDATION_ERROR");
      expect(apiErr.requestId).toBe(errorValidationError.requestId);
      expect(apiErr.details).toHaveLength(2);
    }
  });

  it("memetakan kode error PRD §9.8 dengan tepat", () => {
    expect(mapApiErrorMessage("EMAIL_ALREADY_REGISTERED", 409)).toBe(
      "Email sudah terdaftar. Silakan masuk.",
    );
    expect(mapApiErrorMessage("ACCOUNT_ALREADY_AFFILIATED", 409)).toBe(
      "Akun Anda sudah terhubung dengan perusahaan.",
    );
    expect(mapApiErrorMessage("REGISTRATION_NUMBER_ALREADY_EXISTS", 409)).toBe(
      "Nomor registrasi perusahaan sudah terdaftar.",
    );
    expect(mapApiErrorMessage("FORBIDDEN_OPERATION", 403)).toBe(
      "Anda tidak memiliki izin untuk tindakan ini.",
    );
  });
});
