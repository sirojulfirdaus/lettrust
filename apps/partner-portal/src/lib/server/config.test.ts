// Owner: Pash (PIC 4) | Status: COMPLETE | Ref: SA §11.3.2, §14.2, §18.1
import { describe, expect, it } from "vitest";
import { getServerConfig, readMaxUploadBytes } from "./config";

const VALID_ENV = {
  LETTRUST_API_BASE_URL: "http://backend:8000/",
  LETTRUST_PARTNER_TOKEN: "test-token",
  PORTAL_UPSTREAM_TIMEOUT_MS: "120000",
};

describe("getServerConfig", () => {
  it("membaca env valid dan membuang garis miring di akhir URL", () => {
    expect(getServerConfig(VALID_ENV)).toEqual({
      apiBaseUrl: "http://backend:8000",
      partnerToken: "test-token",
      upstreamTimeoutMs: 120000,
      maxUploadBytes: 5 * 1024 * 1024,
    });
  });

  it("memakai timeout default 120000 bila tidak diisi", () => {
    const env = { ...VALID_ENV, PORTAL_UPSTREAM_TIMEOUT_MS: undefined };
    expect(getServerConfig(env).upstreamTimeoutMs).toBe(120000);
  });

  it("menolak token kosong tanpa membocorkan nilai env", () => {
    expect(() => getServerConfig({ ...VALID_ENV, LETTRUST_PARTNER_TOKEN: "  " })).toThrow(/LETTRUST_PARTNER_TOKEN/);
  });

  it("menolak URL dan timeout tidak valid", () => {
    expect(() => getServerConfig({ ...VALID_ENV, LETTRUST_API_BASE_URL: "bukan url" })).toThrow(/LETTRUST_API_BASE_URL/);
    expect(() => getServerConfig({ ...VALID_ENV, PORTAL_UPSTREAM_TIMEOUT_MS: "-5" })).toThrow(/PORTAL_UPSTREAM_TIMEOUT_MS/);
  });

  // Batas unggah memakai nama env backend dan menolak nilai bukan bilangan bulat positif.
  it("membaca MAX_UPLOAD_BYTES dan menolak nilai tidak valid", () => {
    expect(getServerConfig({ ...VALID_ENV, MAX_UPLOAD_BYTES: "1048576" }).maxUploadBytes).toBe(1048576);
    expect(() => getServerConfig({ ...VALID_ENV, MAX_UPLOAD_BYTES: "0" })).toThrow(/MAX_UPLOAD_BYTES/);
    expect(() => getServerConfig({ ...VALID_ENV, MAX_UPLOAD_BYTES: "5MB" })).toThrow(/MAX_UPLOAD_BYTES/);
  });

  // Halaman membaca batas unggah tanpa memerlukan token partner.
  it("readMaxUploadBytes tidak bergantung pada token dan memakai default", () => {
    expect(readMaxUploadBytes({})).toBe(5 * 1024 * 1024);
    expect(readMaxUploadBytes({ MAX_UPLOAD_BYTES: "2097152" })).toBe(2097152);
    expect(() => readMaxUploadBytes({ MAX_UPLOAD_BYTES: "-1" })).toThrow(/MAX_UPLOAD_BYTES/);
  });
});
