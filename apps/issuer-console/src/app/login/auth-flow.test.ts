// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-01.01, FR-01.02, §9.8; SA §10.5 (S-01, S-02, S-03), §11.2.2, §18.1
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  errorEmailAlreadyRegistered,
  errorInternalError,
  errorInvalidCredentials,
  errorValidationError,
  s01RegisterRequest,
  s01RegisterResponse,
  s02LoginRequest,
  s02LoginResponse,
  s03SessionAdmin,
  s03SessionHrAuthorized,
  s03SessionHrUnaffiliated,
} from "@/fixtures/api";
import { ApiError } from "@/lib/api/client";
import { readSession, SESSION_STORAGE_KEY } from "@/lib/session";
import { submitLoginFlow, submitRegisterFlow } from "./auth-flow";
import { mapValidationDetails } from "./auth-validation";

// Storage in-memory sederhana untuk meniru sessionStorage di Vitest.
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

function jsonResponse(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("alur login dan registrasi dengan fixture kontrak", () => {
  let storage: Storage;

  beforeEach(() => {
    storage = createMemoryStorage();
    vi.stubGlobal("window", {
      sessionStorage: storage,
      location: { pathname: "/login", assign: vi.fn() },
      dispatchEvent: vi.fn(),
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("tidak menyimpan sesi setengah jadi saat login 200 tetapi GET /auth/me gagal 500", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(s02LoginResponse, 200))
      .mockResolvedValueOnce(jsonResponse(errorInternalError, 500));
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      submitLoginFlow(s02LoginRequest.email, s02LoginRequest.password),
    ).rejects.toMatchObject({
      status: 500,
      code: "INTERNAL_ERROR",
    });

    expect(storage.getItem(SESSION_STORAGE_KEY)).toBeNull();
    expect(readSession()).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("tidak menyimpan sesi saat login 200 tetapi GET /auth/me gagal jaringan", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(s02LoginResponse, 200))
      .mockRejectedValueOnce(new TypeError("Failed to fetch"));
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      submitLoginFlow(s02LoginRequest.email, s02LoginRequest.password),
    ).rejects.toThrow("Failed to fetch");

    expect(readSession()).toBeNull();
  });

  it("mengembalikan pesan PRD §9.8 untuk kredensial salah tanpa menyimpan sesi", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(jsonResponse(errorInvalidCredentials, 401)));

    await expect(submitLoginFlow("hr@lettrust.test", "salah-123")).rejects.toMatchObject({
      status: 401,
      code: "INVALID_CREDENTIALS",
      message: "Email atau password tidak sesuai.",
    });

    expect(readSession()).toBeNull();
  });

  it("menyimpan sesi dan mengarahkan Administrator ke /admin/issuers", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(s02LoginResponse, 200))
      .mockResolvedValueOnce(jsonResponse(s03SessionAdmin, 200));
    vi.stubGlobal("fetch", fetchMock);

    const result = await submitLoginFlow("ADMIN@lettrust.test", "rahasia-demo-123");

    expect(result.redirectTo).toBe("/admin/issuers");
    expect(result.profile.role).toBe("ADMIN");
    expect(readSession()?.accessToken).toBe(s02LoginResponse.accessToken);

    const [, secondInit] = fetchMock.mock.calls[1] as [string, RequestInit];
    expect(new Headers(secondInit.headers).get("Authorization")).toBe(
      `Bearer ${s02LoginResponse.accessToken}`,
    );
  });

  it("menyimpan sesi dan mengarahkan HR tidak terafiliasi ke /onboarding/company", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(jsonResponse(s02LoginResponse, 200))
        .mockResolvedValueOnce(jsonResponse(s03SessionHrUnaffiliated, 200)),
    );

    const result = await submitLoginFlow(s02LoginRequest.email, s02LoginRequest.password);
    expect(result.redirectTo).toBe("/onboarding/company");
    expect(readSession()?.accessToken).toBe(s02LoginResponse.accessToken);
  });

  it("menyimpan sesi dan mengarahkan HR terafiliasi ke /hr", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(jsonResponse(s02LoginResponse, 200))
        .mockResolvedValueOnce(jsonResponse(s03SessionHrAuthorized, 200)),
    );

    const result = await submitLoginFlow(s02LoginRequest.email, s02LoginRequest.password);
    expect(result.redirectTo).toBe("/hr");
    expect(readSession()?.accessToken).toBe(s02LoginResponse.accessToken);
  });

  it("mendaftarkan akun HR tanpa mengirim field role dan menormalisasi email lowercase", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(jsonResponse(s01RegisterResponse, 201));
    vi.stubGlobal("fetch", fetchMock);

    const created = await submitRegisterFlow(
      `  ${s01RegisterRequest.displayName}  `,
      s01RegisterRequest.email.toUpperCase(),
      s01RegisterRequest.password,
    );

    expect(created).toEqual(s01RegisterResponse);
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const sentBody = JSON.parse(String(init.body)) as Record<string, unknown>;
    expect(sentBody).toEqual({
      displayName: s01RegisterRequest.displayName,
      email: s01RegisterRequest.email.toLowerCase(),
      password: s01RegisterRequest.password,
    });
    expect("role" in sentBody).toBe(false);
  });

  it("menangani email duplikat (409) dan VALIDATION_ERROR (400) pada registrasi", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce(jsonResponse(errorEmailAlreadyRegistered, 409)),
    );

    await expect(
      submitRegisterFlow(
        s01RegisterRequest.displayName,
        s01RegisterRequest.email,
        s01RegisterRequest.password,
      ),
    ).rejects.toMatchObject({
      status: 409,
      code: "EMAIL_ALREADY_REGISTERED",
      message: "Email sudah terdaftar. Silakan masuk.",
    });

    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(jsonResponse(errorValidationError, 400)));

    try {
      await submitRegisterFlow("Rina", "salah", "123");
      expect.fail("seharusnya melempar ApiError");
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError);
      const apiErr = error as ApiError;
      expect(apiErr.code).toBe("VALIDATION_ERROR");
      expect(mapValidationDetails(apiErr.details)).toEqual({
        email: "Format email tidak valid.",
        password: "Password minimal 8 karakter.",
      });
    }
  });
});
