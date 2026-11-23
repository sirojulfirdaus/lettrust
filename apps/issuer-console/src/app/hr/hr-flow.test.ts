// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-01.04, §9.3.1, §9.5, §9.9.3; SA §10.5 (S-03), §10.6 (S-06)
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  errorInternalError,
  s03SessionAdmin,
  s03SessionHrAuthorized,
  s03SessionHrPending,
  s03SessionHrRejected,
  s03SessionHrUnaffiliated,
  s03SessionHrVerifiedNotAuthorized,
  s06ProofList,
  s06ProofListEmpty,
} from "@/fixtures/api";
import { buildApiUrl } from "@/lib/api/client";
import { createSession, saveSession } from "@/lib/session";
import { loadHrHomeData, loadHrProofSummary } from "./hr-flow";

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

describe("alur halaman Beranda HR", () => {
  beforeEach(() => {
    vi.stubGlobal("window", {
      sessionStorage: createMemoryStorage(),
      location: { pathname: "/hr", assign: vi.fn() },
      dispatchEvent: vi.fn(),
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("mengarahkan sesuai guard untuk tanpa sesi, ADMIN, dan HR tanpa afiliasi", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(s03SessionAdmin, 200))
      .mockResolvedValueOnce(jsonResponse(s03SessionHrUnaffiliated, 200));
    vi.stubGlobal("fetch", fetchMock);

    expect(await loadHrHomeData()).toEqual({ kind: "redirect", to: "/login" });
    expect(fetchMock).not.toHaveBeenCalled();

    saveSession(createSession("jwt-admin", 3600));
    expect(await loadHrHomeData()).toEqual({ kind: "redirect", to: "/admin/issuers" });

    saveSession(createSession("jwt-hr-unaffiliated", 3600));
    expect(await loadHrHomeData()).toEqual({ kind: "redirect", to: "/onboarding/company" });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("memuat /auth/me untuk PENDING, menampilkan status menunggu verifikasi, dan tidak memanggil /api/v1/proofs", async () => {
    saveSession(createSession("jwt-hr-pending", 3600));
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(s03SessionHrPending, 200));
    vi.stubGlobal("fetch", fetchMock);

    const result = await loadHrHomeData();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe(buildApiUrl("/api/v1/auth/me"));
    expect(result.kind).toBe("ready");
    if (result.kind === "ready") {
      expect(result.status.issuerStatusLabel).toBe("Menunggu Verifikasi");
      expect(result.status.canIssueProof).toBe(false);
      expect(result.proofs).toBeNull();
      expect(result.proofsError).toBeNull();
    }
  });

  it("memuat /auth/me untuk REJECTED, menampilkan reviewNote, dan tidak memanggil /api/v1/proofs", async () => {
    saveSession(createSession("jwt-hr-rejected", 3600));
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(s03SessionHrRejected, 200));
    vi.stubGlobal("fetch", fetchMock);

    const result = await loadHrHomeData();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe(buildApiUrl("/api/v1/auth/me"));
    expect(result.kind).toBe("ready");
    if (result.kind === "ready") {
      expect(result.status.issuerStatusLabel).toBe("Ditolak");
      expect(result.status.reviewNote).toBe(s03SessionHrRejected.membership.reviewNote);
      expect(result.status.canIssueProof).toBe(false);
      expect(result.proofs).toBeNull();
    }
  });

  it("memuat /auth/me untuk VERIFIED + NOT_AUTHORIZED dan tidak memanggil /api/v1/proofs", async () => {
    saveSession(createSession("jwt-hr-not-authorized", 3600));
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse(s03SessionHrVerifiedNotAuthorized, 200));
    vi.stubGlobal("fetch", fetchMock);

    const result = await loadHrHomeData();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe(buildApiUrl("/api/v1/auth/me"));
    expect(result.kind).toBe("ready");
    if (result.kind === "ready") {
      expect(result.status.issuerStatusLabel).toBe("Terverifikasi");
      expect(result.status.authorizationLabel).toBe("Menunggu Otorisasi");
      expect(result.status.canIssueProof).toBe(false);
      expect(result.proofs).toBeNull();
    }
  });

  it("memuat /auth/me lalu GET /api/v1/proofs?limit=5&offset=0 untuk VERIFIED + AUTHORIZED", async () => {
    saveSession(createSession("jwt-hr-authorized", 3600));
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(s03SessionHrAuthorized, 200))
      .mockResolvedValueOnce(jsonResponse(s06ProofList, 200));
    vi.stubGlobal("fetch", fetchMock);

    const result = await loadHrHomeData();

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[0][0]).toBe(buildApiUrl("/api/v1/auth/me"));
    expect(fetchMock.mock.calls[1][0]).toBe(
      buildApiUrl("/api/v1/proofs", undefined, { limit: 5, offset: 0 }),
    );
    expect(result.kind).toBe("ready");
    if (result.kind === "ready") {
      expect(result.status.canIssueProof).toBe(true);
      expect(result.proofs).toEqual(s06ProofList);
      expect(result.proofs?.items).toHaveLength(2);
      expect(result.proofsError).toBeNull();
    }
  });

  it("menangani daftar bukti kosong (s06ProofListEmpty) untuk VERIFIED + AUTHORIZED", async () => {
    saveSession(createSession("jwt-hr-authorized", 3600));
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(s03SessionHrAuthorized, 200))
      .mockResolvedValueOnce(jsonResponse(s06ProofListEmpty, 200));
    vi.stubGlobal("fetch", fetchMock);

    const result = await loadHrHomeData();

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(result.kind).toBe("ready");
    if (result.kind === "ready") {
      expect(result.proofs).toEqual({ items: [], total: 0 });
      expect(result.proofsError).toBeNull();
    }
  });

  it("tetap menampilkan kartu status saat GET /api/v1/proofs gagal 500 lalu berhasil saat coba lagi", async () => {
    saveSession(createSession("jwt-hr-authorized", 3600));
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(s03SessionHrAuthorized, 200))
      .mockResolvedValueOnce(jsonResponse(errorInternalError, 500))
      .mockResolvedValueOnce(jsonResponse(s06ProofList, 200));
    vi.stubGlobal("fetch", fetchMock);

    const initial = await loadHrHomeData();
    expect(initial.kind).toBe("ready");
    if (initial.kind === "ready") {
      expect(initial.profile).toEqual(s03SessionHrAuthorized);
      expect(initial.proofs).toBeNull();
      expect(initial.proofsError).toBeTruthy();
    }

    const retriedProofs = await loadHrProofSummary();
    expect(retriedProofs).toEqual({ kind: "ready", data: s06ProofList });
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("mengembalikan error profil saat /auth/me gagal 500 lalu berhasil saat coba lagi", async () => {
    saveSession(createSession("jwt-hr-pending", 3600));
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(errorInternalError, 500))
      .mockResolvedValueOnce(jsonResponse(s03SessionHrPending, 200));
    vi.stubGlobal("fetch", fetchMock);

    const failed = await loadHrHomeData();
    expect(failed.kind).toBe("profile_error");
    if (failed.kind === "profile_error") {
      expect(failed.message).toBeTruthy();
    }

    const retried = await loadHrHomeData();
    expect(retried.kind).toBe("ready");
    if (retried.kind === "ready") {
      expect(retried.profile).toEqual(s03SessionHrPending);
    }
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
