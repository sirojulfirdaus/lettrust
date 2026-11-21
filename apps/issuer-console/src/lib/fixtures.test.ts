// Owner: Dws (PIC 1) | Status: COMPLETE | Ref: SA §10, §11.1; contracts/README.md
import { describe, expect, it } from "vitest";

import * as fixtures from "@/fixtures/api";

// Sanity: indeks fixture console dapat diimpor dan memuat contoh sesi serta error envelope.
describe("fixture API console", () => {
  it("memuat contoh hasil generate dari contracts/examples", () => {
    expect(Object.keys(fixtures).length).toBeGreaterThan(0);
    expect(fixtures.s03SessionAdmin.membership).toBeNull();
    expect(fixtures.errorUnauthenticated.error.code).toBe("UNAUTHENTICATED");
  });
});
