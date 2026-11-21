// Owner: Dws (PIC 1) | Status: COMPLETE | Ref: SA §10.7, §11.1; contracts/README.md
import { describe, expect, it } from "vitest";

import * as fixtures from "@/fixtures/api";

// Sanity: indeks fixture portal memuat contoh API-07 dan error envelope.
describe("fixture API portal", () => {
  it("memuat contoh hasil generate dari contracts/examples", () => {
    expect(Object.keys(fixtures).length).toBeGreaterThan(0);
    expect(fixtures.api07AiOnly.mode).toBe("AI_ONLY");
    expect(fixtures.errorInvalidInputCombination.error.code).toBe("INVALID_INPUT_COMBINATION");
  });
});
