// Owner: Van (PIC 2) | Status: COMPLETE | Ref: SA §11.2.1, §11.2.2, §18.1
import { describe, expect, it } from "vitest";
import { CONSOLE_ROUTES } from "./routes";
import { SESSION_STORAGE_KEY } from "./session";

describe("sanity Console", () => {
  it("memuat seluruh route SA §11.2.1", () => {
    expect(CONSOLE_ROUTES.map((r) => r.path)).toEqual([
      "/",
      "/login",
      "/register",
      "/onboarding/company",
      "/hr",
      "/hr/proofs",
      "/hr/proofs/new",
      "/hr/proofs/[proofId]",
      "/admin/issuers",
      "/admin/issuers/[issuerId]",
    ]);
  });

  it("memakai kunci sessionStorage dari SA §11.2.2", () => {
    expect(SESSION_STORAGE_KEY).toBe("lettrust.session");
  });
});
