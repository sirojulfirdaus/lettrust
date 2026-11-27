// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-01.05, FR-01.06, §9.5, §9.8; SA §10.5 (S-04, S-05, API-02, API-03)
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  api02VerifyIssuerRequest,
  api02VerifyIssuerResponse,
  api03AuthorizeHrRequest,
  api03AuthorizeHrResponse,
  errorForbiddenOperation,
  errorHrAlreadyAuthorized,
  errorHrNotAffiliated,
  errorIssuerDecisionAlreadyMade,
  errorIssuerNotFound,
  errorIssuerNotVerified,
  s03SessionAdmin,
  s03SessionHrAuthorized,
  s04IssuerList,
  s04IssuerListEmpty,
  s04IssuerListPending,
  s05IssuerDetailAdmin,
  s05IssuerDetailPending,
} from "@/fixtures/api";
import { buildApiUrl } from "@/lib/api/client";
import { createSession, saveSession } from "@/lib/session";
import {
  buildVerificationDecisionNotice,
  buildVerificationDecisionSuccessMessage,
  getHrAuthorizationUnavailableMessage,
  loadIssuerDetail,
  loadIssuerList,
  submitHrAuthorization,
  submitVerificationDecision,
  validateAuthorizeHrId,
  validateVerificationDecisionInput,
} from "./admin-issuers-flow";

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

describe("alur admin penerbit (S-04, S-05, API-02, API-03)", () => {
  beforeEach(() => {
    vi.stubGlobal("window", {
      sessionStorage: createMemoryStorage(),
      location: { pathname: "/admin/issuers", assign: vi.fn() },
      dispatchEvent: vi.fn(),
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("menyusun pesan keputusan tersimpan dengan status baru dan waktu peninjauan UTC", () => {
    const message = buildVerificationDecisionSuccessMessage({
      ...api02VerifyIssuerResponse,
      reviewedAt: "2026-11-24T03:15:00Z",
    });
    expect(message).toMatch(/^Keputusan verifikasi tersimpan\. Status penerbit: Terverifikasi\./);
    expect(message).toMatch(/2026,? 03[.:]15 UTC\.$/);
    expect(
      buildVerificationDecisionSuccessMessage({ ...api02VerifyIssuerResponse, issuerStatus: "REJECTED" }),
    ).toContain("Status penerbit: Ditolak.");
  });

  it("menyusun satu notifikasi keputusan sehingga sukses dan konflik saling menggantikan", () => {
    const success = buildVerificationDecisionNotice({ kind: "saved", data: api02VerifyIssuerResponse });
    expect(success).toEqual({
      kind: "success",
      message: buildVerificationDecisionSuccessMessage(api02VerifyIssuerResponse),
    });
    const conflict = buildVerificationDecisionNotice({
      kind: "conflict",
      message: errorIssuerDecisionAlreadyMade.error.message,
    });
    expect(conflict).toEqual({ kind: "conflict", message: errorIssuerDecisionAlreadyMade.error.message });
  });

  it("membedakan alasan otorisasi HR tidak tersedia untuk penerbit PENDING dan REJECTED", () => {
    expect(getHrAuthorizationUnavailableMessage("VERIFIED")).toBeNull();
    expect(getHrAuthorizationUnavailableMessage("PENDING")).toBe(
      "Penerbit belum terverifikasi sehingga HR belum dapat diotorisasi.",
    );
    const rejected = getHrAuthorizationUnavailableMessage("REJECTED");
    expect(rejected).toContain("ditolak");
    expect(rejected).not.toContain("belum terverifikasi");
  });

  it("mengarahkan ke login dengan penanda sesi berakhir bila sesi kedaluwarsa sebelum memuat", async () => {
    saveSession(createSession("jwt-admin-lama", -1));
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    expect(await loadIssuerList({ status: "ALL", limit: 20, offset: 0 })).toEqual({
      kind: "redirect",
      to: "/login?reason=session_expired",
    });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("memvalidasi panjang Unicode evidenceRef (3-120) dan reviewNote (<= 500) serta hrId", () => {
    expect(
      validateVerificationDecisionInput({
        decision: "VERIFIED",
        evidenceRef: "ab",
        reviewNote: "",
      }).evidenceRefError,
    ).toBeTruthy();

    expect(
      validateVerificationDecisionInput({
        decision: "VERIFIED",
        evidenceRef: "😀".repeat(120),
        reviewNote: "😀".repeat(500),
      }),
    ).toEqual({});

    expect(
      validateVerificationDecisionInput({
        decision: "REJECTED",
        evidenceRef: "EVD-001",
        reviewNote: "😀".repeat(501),
      }).reviewNoteError,
    ).toBeTruthy();

    expect(validateAuthorizeHrId("   ")).toBeTruthy();
    expect(validateAuthorizeHrId("USR-9R4T6V8W")).toBeNull();
  });

  it("memuat daftar penerbit S-04 dengan filter status, empty state, dan 403 untuk HR", async () => {
    expect(await loadIssuerList({ status: "ALL", limit: 10, offset: 0 })).toEqual({
      kind: "redirect",
      to: "/login",
    });

    saveSession(createSession("jwt-admin", 3600));
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(s04IssuerList, 200))
      .mockResolvedValueOnce(jsonResponse(s04IssuerListPending, 200))
      .mockResolvedValueOnce(jsonResponse(s04IssuerListEmpty, 200))
      .mockResolvedValueOnce(jsonResponse(errorForbiddenOperation, 403));
    vi.stubGlobal("fetch", fetchMock);

    const allResult = await loadIssuerList({ status: "ALL", limit: 10, offset: 0 });
    expect(allResult).toEqual({ kind: "ready", data: s04IssuerList });
    expect(fetchMock.mock.calls[0][0]).toBe(
      buildApiUrl("/api/v1/issuers", undefined, { limit: 10, offset: 0 }),
    );

    const pendingResult = await loadIssuerList({ status: "PENDING", limit: 10, offset: 0 });
    expect(pendingResult).toEqual({ kind: "ready", data: s04IssuerListPending });
    expect(fetchMock.mock.calls[1][0]).toBe(
      buildApiUrl("/api/v1/issuers", undefined, { limit: 10, offset: 0, status: "PENDING" }),
    );

    const emptyResult = await loadIssuerList({ status: "REJECTED", limit: 10, offset: 0 });
    expect(emptyResult).toEqual({ kind: "ready", data: s04IssuerListEmpty });

    const forbiddenResult = await loadIssuerList({ status: "ALL", limit: 10, offset: 0 });
    expect(forbiddenResult).toEqual({
      kind: "forbidden",
      message: "Anda tidak memiliki izin untuk tindakan ini.",
    });
  });

  it("memuat detail penerbit S-05 setelah verifikasi peran ADMIN serta menangani 404 ISSUER_NOT_FOUND", async () => {
    saveSession(createSession("jwt-admin", 3600));
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(s03SessionAdmin, 200))
      .mockResolvedValueOnce(jsonResponse(s05IssuerDetailPending, 200))
      .mockResolvedValueOnce(jsonResponse(s03SessionAdmin, 200))
      .mockResolvedValueOnce(jsonResponse(errorIssuerNotFound, 404));
    vi.stubGlobal("fetch", fetchMock);

    const ready = await loadIssuerDetail({ issuerId: s05IssuerDetailPending.issuerId });
    expect(ready).toEqual({ kind: "ready", data: s05IssuerDetailPending });
    expect(fetchMock.mock.calls[0][0]).toBe(buildApiUrl("/api/v1/auth/me"));
    expect(fetchMock.mock.calls[1][0]).toBe(
      buildApiUrl("/api/v1/issuers/{issuerId}", {
        issuerId: s05IssuerDetailPending.issuerId,
      }),
    );

    const notFound = await loadIssuerDetail({ issuerId: "ISS-MISSING" });
    expect(notFound).toEqual({
      kind: "not_found",
      message: "Penerbit tidak ditemukan.",
    });
    expect(fetchMock.mock.calls[2][0]).toBe(buildApiUrl("/api/v1/auth/me"));
    expect(fetchMock.mock.calls[3][0]).toBe(
      buildApiUrl("/api/v1/issuers/{issuerId}", {
        issuerId: "ISS-MISSING",
      }),
    );
  });

  it("menolak akses HR di loadIssuerDetail sebelum memanggil S-05", async () => {
    saveSession(createSession("jwt-hr", 3600));
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(s03SessionHrAuthorized, 200));
    vi.stubGlobal("fetch", fetchMock);

    const result = await loadIssuerDetail({ issuerId: s05IssuerDetailPending.issuerId });
    expect(result).toEqual({
      kind: "forbidden",
      message: "Anda tidak memiliki izin untuk tindakan ini.",
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe(buildApiUrl("/api/v1/auth/me"));
  });

  it("menyimpan keputusan verifikasi API-02 dan menangani ISSUER_DECISION_ALREADY_MADE", async () => {
    saveSession(createSession("jwt-admin", 3600));
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(api02VerifyIssuerResponse, 200))
      .mockResolvedValueOnce(jsonResponse(errorIssuerDecisionAlreadyMade, 409));
    vi.stubGlobal("fetch", fetchMock);

    const ok = await submitVerificationDecision({
      issuerId: s05IssuerDetailPending.issuerId,
      decision: api02VerifyIssuerRequest.decision,
      evidenceRef: api02VerifyIssuerRequest.evidenceRef,
      reviewNote: api02VerifyIssuerRequest.reviewNote ?? "",
    });
    expect(ok).toEqual({ kind: "ready", data: api02VerifyIssuerResponse });

    const conflict = await submitVerificationDecision({
      issuerId: s05IssuerDetailAdmin.issuerId,
      decision: "VERIFIED",
      evidenceRef: "EVD-DEMO-003",
      reviewNote: "",
    });
    expect(conflict).toEqual({
      kind: "error",
      code: "ISSUER_DECISION_ALREADY_MADE",
      status: 409,
      message: "Penerbit ini sudah memiliki keputusan verifikasi.",
    });
  });

  it("mengotorisasi HR via API-03 serta menangani 422 HR_NOT_AFFILIATED, 409 ISSUER_NOT_VERIFIED, dan 409 HR_ALREADY_AUTHORIZED", async () => {
    saveSession(createSession("jwt-admin", 3600));
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(api03AuthorizeHrResponse, 201))
      .mockResolvedValueOnce(jsonResponse(errorHrNotAffiliated, 422))
      .mockResolvedValueOnce(jsonResponse(errorIssuerNotVerified, 409))
      .mockResolvedValueOnce(jsonResponse(errorHrAlreadyAuthorized, 409));
    vi.stubGlobal("fetch", fetchMock);

    const ok = await submitHrAuthorization({
      issuerId: s05IssuerDetailAdmin.issuerId,
      hrId: api03AuthorizeHrRequest.hrId,
    });
    expect(ok).toEqual({ kind: "ready", data: api03AuthorizeHrResponse });
    expect(fetchMock.mock.calls[0][0]).toBe(
      buildApiUrl("/api/v1/issuers/{issuerId}/hr-authorizations", {
        issuerId: s05IssuerDetailAdmin.issuerId,
      }),
    );

    const notAffiliated = await submitHrAuthorization({
      issuerId: s05IssuerDetailAdmin.issuerId,
      hrId: "USR-LAIN0000",
    });
    expect(notAffiliated).toEqual({
      kind: "error",
      code: "HR_NOT_AFFILIATED",
      status: 422,
      message: "Akun HR tidak terhubung dengan penerbit ini.",
    });

    const notVerified = await submitHrAuthorization({
      issuerId: s05IssuerDetailPending.issuerId,
      hrId: "USR-4G7H2J5K",
    });
    expect(notVerified).toEqual({
      kind: "error",
      code: "ISSUER_NOT_VERIFIED",
      status: 409,
      message: "Penerbit belum terverifikasi sehingga HR belum dapat diotorisasi.",
    });

    const alreadyAuthorized = await submitHrAuthorization({
      issuerId: s05IssuerDetailAdmin.issuerId,
      hrId: "USR-5H2K8M4P",
    });
    expect(alreadyAuthorized).toEqual({
      kind: "error",
      code: "HR_ALREADY_AUTHORIZED",
      status: 409,
      message: "Akun HR ini sudah diotorisasi.",
    });
  });
});
