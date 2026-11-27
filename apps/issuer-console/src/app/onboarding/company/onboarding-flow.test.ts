// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-01.03, §9.8; SA §10.5 (API-01, S-03)
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  api01RegisterIssuerRequest,
  api01RegisterIssuerResponse,
  errorAccountAlreadyAffiliated,
  errorInternalError,
  errorRegistrationNumberAlreadyExists,
  errorValidationError,
  s03SessionAdmin,
  s03SessionHrPending,
  s03SessionHrUnaffiliated,
} from "@/fixtures/api";
import { buildApiUrl } from "@/lib/api/client";
import { clearSession, createSession, saveSession, SESSION_CHANGE_EVENT } from "@/lib/session";
import { loadOnboardingGuard, submitCompanyRegistration } from "./onboarding-flow";

// Storage in-memory untuk meniru window.sessionStorage saat pengujian Vitest.
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

// Membuat objek Response JSON standar untuk mock fetch.
function jsonResponse(payload: unknown, status: number): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("alur halaman onboarding perusahaan", () => {
  beforeEach(() => {
    vi.stubGlobal("window", {
      sessionStorage: createMemoryStorage(),
      location: { pathname: "/onboarding/company", assign: vi.fn() },
      dispatchEvent: vi.fn(),
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("mengarahkan ke /login tanpa memanggil API bila belum ada sesi", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const result = await loadOnboardingGuard();

    expect(result).toEqual({ kind: "redirect", to: "/login" });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("mengarahkan akun ADMIN ke /admin/issuers", async () => {
    saveSession(createSession("jwt-admin", 3600));
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(s03SessionAdmin, 200));
    vi.stubGlobal("fetch", fetchMock);

    const result = await loadOnboardingGuard();

    expect(result).toEqual({ kind: "redirect", to: "/admin/issuers" });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("mengarahkan akun HR yang sudah terafiliasi ke /hr", async () => {
    saveSession(createSession("jwt-hr-pending", 3600));
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(s03SessionHrPending, 200));
    vi.stubGlobal("fetch", fetchMock);

    const result = await loadOnboardingGuard();

    expect(result).toEqual({ kind: "redirect", to: "/hr" });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("mengizinkan akun HR tanpa afiliasi mengisi formulir onboarding", async () => {
    saveSession(createSession("jwt-hr-unaffiliated", 3600));
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(s03SessionHrUnaffiliated, 200));
    vi.stubGlobal("fetch", fetchMock);

    const result = await loadOnboardingGuard();

    expect(result).toEqual({
      kind: "ready",
      displayName: s03SessionHrUnaffiliated.displayName,
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("mengembalikan error yang dapat diulang saat S-03 gagal non-401 lalu berhasil saat coba lagi", async () => {
    saveSession(createSession("jwt-hr-unaffiliated", 3600));
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(errorInternalError, 500))
      .mockResolvedValueOnce(jsonResponse(s03SessionHrUnaffiliated, 200));
    vi.stubGlobal("fetch", fetchMock);

    const failed = await loadOnboardingGuard();
    expect(failed.kind).toBe("error");
    if (failed.kind === "error") {
      expect(failed.message).toContain("Data profil sesi belum dapat dimuat");
    }

    const retried = await loadOnboardingGuard();
    expect(retried).toEqual({
      kind: "ready",
      displayName: s03SessionHrUnaffiliated.displayName,
    });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("mengirim api01RegisterIssuerRequest ke POST /api/v1/issuers dan mengembalikan 201 PENDING siap ke /hr", async () => {
    saveSession(createSession("jwt-hr-unaffiliated", 3600));
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(api01RegisterIssuerResponse, 201));
    vi.stubGlobal("fetch", fetchMock);

    const dispatchMock = vi.mocked(window.dispatchEvent);
    dispatchMock.mockClear();

    const result = await submitCompanyRegistration(api01RegisterIssuerRequest);

    expect(result).toEqual({
      kind: "success",
      data: api01RegisterIssuerResponse,
      redirectTo: "/hr",
    });
    // Afiliasi baru memicu event sesi agar header memuat ulang profil tanpa refetch per navigasi.
    expect(dispatchMock.mock.calls.map(([event]) => event.type)).toContain(SESSION_CHANGE_EVENT);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [calledUrl, calledInit] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(calledUrl).toBe(buildApiUrl("/api/v1/issuers"));
    expect(calledInit.method).toBe("POST");
    expect(JSON.parse(String(calledInit.body))).toEqual(api01RegisterIssuerRequest);
  });

  it("menangani kegagalan 409 ACCOUNT_ALREADY_AFFILIATED dengan tautan ke Beranda HR", async () => {
    saveSession(createSession("jwt-hr-affiliated", 3600));
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(errorAccountAlreadyAffiliated, 409)),
    );

    const result = await submitCompanyRegistration(api01RegisterIssuerRequest);

    expect(result).toEqual({
      kind: "error",
      submitError: {
        message: "Akun Anda sudah terhubung dengan perusahaan.",
        showHrLink: true,
      },
    });
  });

  it("menangani kegagalan 409 REGISTRATION_NUMBER_ALREADY_EXISTS dengan error pada field nomor registrasi", async () => {
    saveSession(createSession("jwt-hr-unaffiliated", 3600));
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(errorRegistrationNumberAlreadyExists, 409)),
    );

    const result = await submitCompanyRegistration(api01RegisterIssuerRequest);

    expect(result).toEqual({
      kind: "error",
      fieldErrors: {
        registrationNumber: "Nomor registrasi perusahaan sudah terdaftar.",
      },
      submitError: {
        message: "Nomor registrasi perusahaan sudah terdaftar.",
        showHrLink: false,
      },
    });
  });

  it("menangani kegagalan 400 VALIDATION_ERROR dari kontrak dan memetakan detail field", async () => {
    saveSession(createSession("jwt-hr-unaffiliated", 3600));
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(errorValidationError, 400))
      .mockResolvedValueOnce(
        jsonResponse(
          {
            ...errorValidationError,
            error: {
              ...errorValidationError.error,
              details: [{ field: "companyName", issue: "string_too_short" }],
            },
          },
          400,
        ),
      );
    vi.stubGlobal("fetch", fetchMock);

    const genericResult = await submitCompanyRegistration(api01RegisterIssuerRequest);
    expect(genericResult).toEqual({
      kind: "error",
      fieldErrors: {},
      submitError: {
        message: "Periksa kembali data yang Anda masukkan.",
        showHrLink: false,
      },
    });

    const mappedResult = await submitCompanyRegistration(api01RegisterIssuerRequest);
    expect(mappedResult).toEqual({
      kind: "error",
      fieldErrors: {
        companyName: "Nama perusahaan harus terdiri dari 3 hingga 120 karakter.",
      },
      submitError: {
        message: "Periksa kembali data perusahaan yang ditandai di bawah.",
        showHrLink: false,
      },
    });
  });

  it("mengabaikan respons 201 yang terlambat setelah logout atau abort agar tidak mengganggu halaman login", async () => {
    saveSession(createSession("jwt-hr-unaffiliated", 3600));

    let resolveLateResponse: ((value: Response) => void) | undefined;
    const fetchMock = vi.fn().mockReturnValue(
      new Promise<Response>((resolve) => {
        resolveLateResponse = resolve;
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const lateSubmitPromise = submitCompanyRegistration(api01RegisterIssuerRequest);

    clearSession();
    resolveLateResponse?.(jsonResponse(api01RegisterIssuerResponse, 201));

    expect(await lateSubmitPromise).toEqual({ kind: "aborted" });

    saveSession(createSession("jwt-hr-unaffiliated", 3600));
    const controller = new AbortController();
    const abortedSubmitPromise = submitCompanyRegistration(api01RegisterIssuerRequest, {
      signal: controller.signal,
    });
    controller.abort();
    resolveLateResponse?.(jsonResponse(api01RegisterIssuerResponse, 201));

    expect(await abortedSubmitPromise).toEqual({ kind: "aborted" });
  });
});
