// Owner: Pash (PIC 4) | Status: COMPLETE | Ref: PRD §9.7, FR-02.10
import { describe, expect, it } from "vitest";
import { api07AiOnly, api07AiOnlyMediumPartial, api07AiUnavailable, api07CodeOnly, api07NotFoundCodeOnly, api07ReferenceMatchAi, api07RegistryUnavailable, api07RevokedMismatch } from "@/fixtures/api";
import { buildGuidance } from "./guidance";

describe("guidance", () => {
  // Memastikan aturan umum dan tindak lanjut status parsial muncul berurutan.
  it("selalu memuat G-01 dan menampilkan seluruh aturan yang cocok berurutan", () => {
    expect(buildGuidance(api07RevokedMismatch).map(({ id }) => id)).toEqual(["G-01", "G-03", "G-04"]);
    expect(buildGuidance(api07NotFoundCodeOnly).map(({ id }) => id)).toEqual(["G-01", "G-06"]);
    expect(buildGuidance(api07RegistryUnavailable).map(({ id }) => id)).toEqual(["G-01", "G-07"]);
    expect(buildGuidance(api07AiUnavailable).map(({ id }) => id)).toContain("G-07");
    expect(buildGuidance(api07CodeOnly).map(({ id }) => id)).toContain("G-05");
  });

  // Memastikan hasil AI-only menyertakan panduan kategori dan tanpa vonis.
  it("menyertakan arahan AI-only dan hasil risiko tinggi tanpa vonis gabungan", () => {
    const guidance = buildGuidance(api07AiOnly);
    expect(guidance.map(({ id }) => id)).toEqual(["G-01", "G-02", "G-08"]);
    expect(guidance.every(({ text }) => !/asli|palsu|aman|penipuan/i.test(text))).toBe(true);
    expect(buildGuidance(api07AiOnlyMediumPartial).map(({ id }) => id)).toEqual(["G-01", "G-08", "G-09"]);
  });

  // Memastikan kombinasi bukti aktif, berkas cocok, dan risiko rendah mendapat G-10.
  it("memuat G-10 ketika bukti ACTIVE, berkas MATCH, dan risiko LOW", () => {
    expect(buildGuidance(api07ReferenceMatchAi).map(({ id }) => id)).toEqual(["G-01", "G-10"]);
  });
});
