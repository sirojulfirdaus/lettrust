// Owner: Pash (PIC 4) | Status: COMPLETE | Ref: SA §11.3.2, §14.2, §18.1
import { describe, expect, it } from "vitest";
import { getServerConfig } from "./config";

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
});
