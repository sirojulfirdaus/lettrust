// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-03.01–FR-03.09, FR-04.01–FR-04.07, §9.8; SA §10.6
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  api04IssueProof,
  api05ProofStatusActive,
  api05ProofStatusRevoked,
  api06RevokeRequest,
  api06RevokeResponse,
  errorDuplicateActiveDocument,
  errorEmptyFile,
  errorFileTooLarge,
  errorForbiddenOperation,
  errorIdempotencyKeyConflict,
  errorMultipleFiles,
  errorProofAlreadyRevoked,
  errorProofNotFound,
  errorRegistryTransactionFailed,
  errorRegistryUnavailable,
  errorUnauthenticated,
  errorUnsupportedMediaType,
  s03SessionAdmin,
  s03SessionHrAuthorized,
  s03SessionHrPending,
  s03SessionHrUnaffiliated,
  s03SessionHrVerifiedNotAuthorized,
  s06ProofList,
  s06ProofListEmpty,
} from "@/fixtures/api";
import { buildApiUrl } from "@/lib/api/client";
import { clearSession, createSession, saveSession } from "@/lib/session";
import {
  MAX_PROOF_FILE_BYTES,
  formatFileSize,
  generateIdempotencyKey,
  getProofDetailRefreshErrorMessage,
  isValidRevocationReasonCode,
  loadHrProofsGuard,
  loadProofDetail,
  loadProofList,
  mergeRevokeResultIntoProofDetail,
  submitIssueProof,
  submitRevokeProof,
  validateProofPdfFile,
} from "./proofs-flow";

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

// Membuat objek File sintetis dengan ukuran tertentu untuk pengujian validasi unggahan.
function createSyntheticFile(name: string, size: number, type: string): File {
  const bytes = new Uint8Array(size);
  return new File([bytes], name, { type });
}

describe("validasi berkas PDF dan helper penerbitan/pencabutan bukti", () => {
  it("menolak pilihan kosong, multi-berkas, bukan PDF, kosong 0 byte, dan melebihi 5 MB", () => {
    expect(validateProofPdfFile(null)).toEqual({
      valid: false,
      code: "EMPTY_SELECTION",
      message: "Pilih satu berkas PDF terlebih dahulu.",
    });

    const pdfA = createSyntheticFile("a.pdf", 128, "application/pdf");
    const pdfB = createSyntheticFile("b.pdf", 128, "application/pdf");
    expect(validateProofPdfFile([pdfA, pdfB])).toEqual({
      valid: false,
      code: "MULTIPLE_FILES",
      message: "Unggah hanya satu berkas PDF.",
    });

    const txtFile = createSyntheticFile("offer.txt", 128, "text/plain");
    expect(validateProofPdfFile([txtFile])).toEqual({
      valid: false,
      code: "UNSUPPORTED_MEDIA_TYPE",
      message: "Berkas harus berformat PDF.",
    });

    const spoofedPdf = createSyntheticFile("fake.pdf", 128, "image/png");
    expect(validateProofPdfFile([spoofedPdf])).toEqual({
      valid: false,
      code: "UNSUPPORTED_MEDIA_TYPE",
      message: "Berkas harus berformat PDF.",
    });

    const emptyPdf = createSyntheticFile("empty.pdf", 0, "application/pdf");
    expect(validateProofPdfFile([emptyPdf])).toEqual({
      valid: false,
      code: "EMPTY_FILE",
      message: "Berkas kosong tidak dapat diproses.",
    });

    const tooLargePdf = createSyntheticFile(
      "huge.pdf",
      MAX_PROOF_FILE_BYTES + 1,
      "application/pdf",
    );
    expect(validateProofPdfFile([tooLargePdf])).toEqual({
      valid: false,
      code: "FILE_TOO_LARGE",
      message: "Ukuran berkas melebihi batas maksimum 5 MB.",
    });
  });

  it("menerima satu berkas PDF hingga tepat 5 MB termasuk saat MIME browser kosong", () => {
    const exactLimitPdf = createSyntheticFile("offer-final.pdf", MAX_PROOF_FILE_BYTES, "application/pdf");
    expect(validateProofPdfFile([exactLimitPdf])).toEqual({ valid: true, file: exactLimitPdf });

    const noMimePdf = createSyntheticFile("OFFER.PDF", 2048, "");
    expect(validateProofPdfFile([noMimePdf])).toEqual({ valid: true, file: noMimePdf });
  });

  it("memvalidasi reasonCode, memformat ukuran berkas, dan membuat Idempotency-Key unik", () => {
    expect(isValidRevocationReasonCode("OFFER_WITHDRAWN")).toBe(true);
    expect(isValidRevocationReasonCode("ISSUED_IN_ERROR")).toBe(true);
    expect(isValidRevocationReasonCode("DOCUMENT_REPLACED")).toBe(true);
    expect(isValidRevocationReasonCode("OTHER")).toBe(true);
    expect(isValidRevocationReasonCode("UNKNOWN_REASON")).toBe(false);

    expect(formatFileSize(512)).toBe("512 B");
    expect(formatFileSize(2048)).toBe("2.0 KB");
    expect(formatFileSize(2 * 1024 * 1024)).toBe("2.00 MB");

    const keyA = generateIdempotencyKey();
    const keyB = generateIdempotencyKey();
    expect(keyA.length).toBeGreaterThan(8);
    expect(keyA).not.toBe(keyB);
  });
});

describe("alur API halaman bukti HR (S-06, API-04, API-05, API-06)", () => {
  beforeEach(() => {
    vi.stubGlobal("window", {
      sessionStorage: createMemoryStorage(),
      location: { pathname: "/hr/proofs", origin: "http://localhost:3000", href: "http://localhost:3000/hr/proofs" },
      dispatchEvent: vi.fn(),
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("menjalankan guard penerbitan bukti S-03 untuk tanpa sesi, ADMIN, belum afiliasi, belum otorisasi, dan HR berwenang", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(s03SessionAdmin, 200))
      .mockResolvedValueOnce(jsonResponse(s03SessionHrUnaffiliated, 200))
      .mockResolvedValueOnce(jsonResponse(s03SessionHrPending, 200))
      .mockResolvedValueOnce(jsonResponse(s03SessionHrVerifiedNotAuthorized, 200))
      .mockResolvedValueOnce(jsonResponse(s03SessionHrAuthorized, 200));
    vi.stubGlobal("fetch", fetchMock);

    expect(await loadHrProofsGuard()).toEqual({ kind: "redirect", to: "/login" });

    saveSession(createSession("jwt-admin", 3600));
    expect(await loadHrProofsGuard()).toEqual({ kind: "redirect", to: "/admin/issuers" });

    saveSession(createSession("jwt-hr-unaffiliated", 3600));
    expect(await loadHrProofsGuard()).toEqual({ kind: "redirect", to: "/onboarding/company" });

    saveSession(createSession("jwt-hr-pending", 3600));
    const pendingRes = await loadHrProofsGuard();
    expect(pendingRes.kind).toBe("forbidden");

    saveSession(createSession("jwt-hr-not-auth", 3600));
    const notAuthRes = await loadHrProofsGuard();
    expect(notAuthRes.kind).toBe("forbidden");

    saveSession(createSession("jwt-hr-auth", 3600));
    expect(await loadHrProofsGuard()).toEqual({ kind: "ready", profile: s03SessionHrAuthorized });
  });

  it("memuat daftar bukti S-06 dengan filter status, paginasi, empty state, dan 403", async () => {
    saveSession(createSession("jwt-hr-auth", 3600));
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(s06ProofList, 200))
      .mockResolvedValueOnce(jsonResponse(s06ProofListEmpty, 200))
      .mockResolvedValueOnce(jsonResponse(errorForbiddenOperation, 403));
    vi.stubGlobal("fetch", fetchMock);

    const listResult = await loadProofList({ status: "ALL", limit: 20, offset: 0 });
    expect(listResult).toEqual({ kind: "ready", data: s06ProofList });
    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      buildApiUrl("/api/v1/proofs", undefined, { limit: 20, offset: 0 }),
    );

    const filteredEmpty = await loadProofList({ status: "ACTIVE", limit: 20, offset: 20 });
    expect(filteredEmpty).toEqual({ kind: "ready", data: s06ProofListEmpty });
    expect(fetchMock.mock.calls[1]?.[0]).toBe(
      buildApiUrl("/api/v1/proofs", undefined, { status: "ACTIVE", limit: 20, offset: 20 }),
    );

    const forbiddenRes = await loadProofList({ status: "REVOKED" });
    expect(forbiddenRes).toEqual({
      kind: "forbidden",
      message: "Anda tidak memiliki izin untuk tindakan ini.",
    });
  });

  it("memuat detail bukti API-05 (ACTIVE, REVOKED, 404 PROOF_NOT_FOUND, 403, 503)", async () => {
    saveSession(createSession("jwt-hr-auth", 3600));
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(api05ProofStatusActive, 200))
      .mockResolvedValueOnce(jsonResponse(api05ProofStatusRevoked, 200))
      .mockResolvedValueOnce(jsonResponse(errorProofNotFound, 404))
      .mockResolvedValueOnce(jsonResponse(errorForbiddenOperation, 403))
      .mockResolvedValueOnce(jsonResponse(errorRegistryUnavailable, 503));
    vi.stubGlobal("fetch", fetchMock);

    expect(await loadProofDetail({ proofId: api05ProofStatusActive.proofId })).toEqual({
      kind: "ready",
      data: api05ProofStatusActive,
    });
    expect(await loadProofDetail({ proofId: api05ProofStatusRevoked.proofId })).toEqual({
      kind: "ready",
      data: api05ProofStatusRevoked,
    });
    expect(await loadProofDetail({ proofId: "0xmissing" })).toEqual({
      kind: "not_found",
      message: "Bukti tidak ditemukan.",
    });
    expect(await loadProofDetail({ proofId: "0xforbidden" })).toEqual({
      kind: "forbidden",
      message: "Anda tidak memiliki izin untuk tindakan ini.",
    });
    expect(await loadProofDetail({ proofId: "0xdown" })).toEqual({
      kind: "error",
      code: "REGISTRY_UNAVAILABLE",
      message: "Pencatatan ke registry gagal. Tidak ada perubahan yang tersimpan. Coba lagi.",
    });
  });

  it("mengirim API-04 POST /api/v1/proofs dengan FormData dan Idempotency-Key lalu memetakan semua error PRD §9.8", async () => {
    saveSession(createSession("jwt-hr-auth", 3600));
    const file = createSyntheticFile("offer.pdf", 1024, "application/pdf");
    const idemKey = "550e8400-e29b-41d4-a716-446655440000";

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(api04IssueProof, 201))
      .mockResolvedValueOnce(jsonResponse(errorDuplicateActiveDocument, 409))
      .mockResolvedValueOnce(jsonResponse(errorIdempotencyKeyConflict, 409))
      .mockResolvedValueOnce(jsonResponse(errorRegistryUnavailable, 503))
      .mockResolvedValueOnce(jsonResponse(errorRegistryTransactionFailed, 502))
      .mockResolvedValueOnce(jsonResponse(errorUnsupportedMediaType, 415))
      .mockResolvedValueOnce(jsonResponse(errorFileTooLarge, 413))
      .mockResolvedValueOnce(jsonResponse(errorEmptyFile, 400))
      .mockResolvedValueOnce(jsonResponse(errorMultipleFiles, 400))
      .mockResolvedValueOnce(jsonResponse(errorForbiddenOperation, 403));
    vi.stubGlobal("fetch", fetchMock);

    const okResult = await submitIssueProof({ file, idempotencyKey: idemKey });
    expect(okResult).toEqual({ kind: "success", data: api04IssueProof });

    const [firstUrl, firstInit] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(firstUrl).toBe(buildApiUrl("/api/v1/proofs"));
    expect(firstInit.method).toBe("POST");
    expect(firstInit.body).toBeInstanceOf(FormData);
    const firstHeaders = new Headers(firstInit.headers);
    expect(firstHeaders.get("Idempotency-Key")).toBe(idemKey);
    expect(firstHeaders.get("Content-Type")).toBeNull();

    expect(await submitIssueProof({ file, idempotencyKey: idemKey })).toEqual({
      kind: "error",
      status: 409,
      code: "DUPLICATE_ACTIVE_DOCUMENT",
      message: "Berkas yang sama sudah memiliki bukti aktif.",
      canRetrySameKey: false,
      requiresResetKey: false,
    });

    expect(await submitIssueProof({ file, idempotencyKey: idemKey })).toEqual({
      kind: "error",
      status: 409,
      code: "IDEMPOTENCY_KEY_CONFLICT",
      message: "Permintaan bertentangan dengan permintaan sebelumnya. Mulai ulang proses penerbitan.",
      canRetrySameKey: false,
      requiresResetKey: true,
    });

    expect(await submitIssueProof({ file, idempotencyKey: idemKey })).toEqual({
      kind: "error",
      status: 503,
      code: "REGISTRY_UNAVAILABLE",
      message: "Pencatatan ke registry gagal. Tidak ada perubahan yang tersimpan. Coba lagi.",
      canRetrySameKey: true,
      requiresResetKey: false,
    });

    expect(await submitIssueProof({ file, idempotencyKey: idemKey })).toEqual({
      kind: "error",
      status: 502,
      code: "REGISTRY_TRANSACTION_FAILED",
      message: "Pencatatan ke registry gagal. Tidak ada perubahan yang tersimpan. Coba lagi.",
      canRetrySameKey: true,
      requiresResetKey: false,
    });

    expect(await submitIssueProof({ file, idempotencyKey: idemKey })).toMatchObject({
      kind: "error",
      status: 415,
      code: "UNSUPPORTED_MEDIA_TYPE",
      message: "Berkas harus berformat PDF.",
    });

    expect(await submitIssueProof({ file, idempotencyKey: idemKey })).toMatchObject({
      kind: "error",
      status: 413,
      code: "FILE_TOO_LARGE",
      message: "Ukuran berkas melebihi batas yang diizinkan.",
    });

    expect(await submitIssueProof({ file, idempotencyKey: idemKey })).toMatchObject({
      kind: "error",
      status: 400,
      code: "EMPTY_FILE",
      message: "Berkas kosong tidak dapat diproses.",
    });

    expect(await submitIssueProof({ file, idempotencyKey: idemKey })).toMatchObject({
      kind: "error",
      status: 400,
      code: "MULTIPLE_FILES",
      message: "Unggah hanya satu berkas PDF.",
    });

    expect(await submitIssueProof({ file, idempotencyKey: idemKey })).toMatchObject({
      kind: "error",
      status: 403,
      code: "FORBIDDEN_OPERATION",
      message: "Anda tidak memiliki izin untuk tindakan ini.",
    });
  });

  it("mengirim API-06 POST /api/v1/proofs/{proofId}/revocations dengan Idempotency-Key dan menangani 409/503", async () => {
    saveSession(createSession("jwt-hr-auth", 3600));
    const proofId = api05ProofStatusActive.proofId;
    const idemKey = "660e8400-e29b-41d4-a716-446655440001";

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(api06RevokeResponse, 200))
      .mockResolvedValueOnce(jsonResponse(errorProofAlreadyRevoked, 409))
      .mockResolvedValueOnce(jsonResponse(errorRegistryTransactionFailed, 502))
      .mockResolvedValueOnce(jsonResponse(errorIdempotencyKeyConflict, 409));
    vi.stubGlobal("fetch", fetchMock);

    const okRes = await submitRevokeProof({
      proofId,
      reasonCode: api06RevokeRequest.reasonCode,
      idempotencyKey: idemKey,
    });
    expect(okRes).toEqual({ kind: "success", data: api06RevokeResponse });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe(buildApiUrl("/api/v1/proofs/{proofId}/revocations", { proofId }));
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual(api06RevokeRequest);
    expect(new Headers(init.headers).get("Idempotency-Key")).toBe(idemKey);

    expect(
      await submitRevokeProof({ proofId, reasonCode: "OFFER_WITHDRAWN", idempotencyKey: idemKey }),
    ).toEqual({
      kind: "already_revoked",
      message: "Bukti ini sudah dicabut sebelumnya.",
    });

    expect(
      await submitRevokeProof({ proofId, reasonCode: "OFFER_WITHDRAWN", idempotencyKey: idemKey }),
    ).toEqual({
      kind: "error",
      status: 502,
      code: "REGISTRY_TRANSACTION_FAILED",
      message: "Pencatatan ke registry gagal. Tidak ada perubahan yang tersimpan. Coba lagi.",
      canRetrySameKey: true,
      requiresResetKey: false,
    });

    expect(
      await submitRevokeProof({ proofId, reasonCode: "OFFER_WITHDRAWN", idempotencyKey: idemKey }),
    ).toEqual({
      kind: "error",
      status: 409,
      code: "IDEMPOTENCY_KEY_CONFLICT",
      message: "Permintaan bertentangan dengan permintaan sebelumnya. Mulai ulang proses penerbitan.",
      canRetrySameKey: false,
      requiresResetKey: true,
    });
  });

  it("mengabaikan respons terlambat setelah logout atau pembatalan AbortSignal", async () => {
    saveSession(createSession("jwt-hr-auth", 3600));
    const file = createSyntheticFile("offer.pdf", 256, "application/pdf");

    const fetchMock = vi.fn().mockImplementation(async () => {
      clearSession();
      return jsonResponse(api04IssueProof, 201);
    });
    vi.stubGlobal("fetch", fetchMock);

    const staleIssue = await submitIssueProof({ file, idempotencyKey: "idem-stale-1" });
    expect(staleIssue).toEqual({ kind: "aborted" });

    saveSession(createSession("jwt-hr-auth-2", 3600));
    const controller = new AbortController();
    const fetchAbortMock = vi.fn().mockImplementation(async () => {
      controller.abort();
      return jsonResponse(api06RevokeResponse, 200);
    });
    vi.stubGlobal("fetch", fetchAbortMock);

    const abortedRevoke = await submitRevokeProof({
      proofId: api05ProofStatusActive.proofId,
      reasonCode: "ISSUED_IN_ERROR",
      idempotencyKey: "idem-abort-1",
      signal: controller.signal,
    });
    expect(abortedRevoke).toEqual({ kind: "aborted" });

    saveSession(createSession("jwt-expired", 3600));
    const onUnauthorized = vi.fn();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce(jsonResponse(errorUnauthenticated, 401)),
    );
    const unauthRes = await loadProofList({ onUnauthorized });
    expect(unauthRes).toEqual({ kind: "unauthorized" });
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
  });

  it("memanggil onUnauthorized dan mengembalikan unauthorized saat sesi sudah kosong sebelum submit issue/revoke", async () => {
    clearSession();
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const onIssueUnauthorized = vi.fn();
    const file = createSyntheticFile("offer.pdf", 256, "application/pdf");
    const issueRes = await submitIssueProof({
      file,
      idempotencyKey: "idem-no-session-issue",
      onUnauthorized: onIssueUnauthorized,
    });
    expect(issueRes).toEqual({ kind: "unauthorized" });
    expect(onIssueUnauthorized).toHaveBeenCalledTimes(1);

    const onRevokeUnauthorized = vi.fn();
    const revokeRes = await submitRevokeProof({
      proofId: api05ProofStatusActive.proofId,
      reasonCode: "OFFER_WITHDRAWN",
      idempotencyKey: "idem-no-session-revoke",
      onUnauthorized: onRevokeUnauthorized,
    });
    expect(revokeRes).toEqual({ kind: "unauthorized" });
    expect(onRevokeUnauthorized).toHaveBeenCalledTimes(1);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("menggabungkan RevokeProofResponse ke detail bukti tanpa mengarang reasonCode lokal", () => {
    const mergedFromActive = mergeRevokeResultIntoProofDetail(
      api05ProofStatusActive,
      api06RevokeResponse,
    );
    expect(mergedFromActive.lifecycleStatus).toBe("REVOKED");
    expect(mergedFromActive.revokedAt).toBe(api06RevokeResponse.revokedAt);
    expect(mergedFromActive.revokeTransaction).toEqual(api06RevokeResponse.transaction);
    expect(mergedFromActive.revocationReasonCode).toBeNull();
    expect(mergedFromActive.documentHash).toBe(api05ProofStatusActive.documentHash);

    const mergedFromRevoked = mergeRevokeResultIntoProofDetail(
      api05ProofStatusRevoked,
      api06RevokeResponse,
    );
    expect(mergedFromRevoked.revocationReasonCode).toBe(
      api05ProofStatusRevoked.revocationReasonCode,
    );
  });

  it("memakai pesan gagal baca saat refresh detail latar belakang gagal dengan REGISTRY_UNAVAILABLE", () => {
    const refreshMessage = getProofDetailRefreshErrorMessage({
      code: "REGISTRY_UNAVAILABLE",
      message: "Pencatatan ke registry gagal. Tidak ada perubahan yang tersimpan. Coba lagi.",
    });
    expect(refreshMessage).toBe(
      "Detail bukti terbaru dari registry belum dapat dimuat ulang. Data yang sudah tercatat tidak berubah; silakan coba muat ulang beberapa saat lagi.",
    );
    expect(refreshMessage).not.toContain("Pencatatan ke registry gagal");

    expect(
      getProofDetailRefreshErrorMessage({
        code: "RATE_LIMITED",
        message: "Terlalu banyak permintaan. Coba lagi beberapa saat lagi.",
      }),
    ).toBe("Terlalu banyak permintaan. Coba lagi beberapa saat lagi.");
  });
});
