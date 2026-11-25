// Owner: Pash (PIC 4) | Status: COMPLETE | Ref: SA §6.3.1, PRD FR-02.03
import { describe, expect, it } from "vitest";
import { isValidReferenceCode, normalizeReferenceCode } from "./reference-code";

describe("reference code", () => {
  // Memastikan input yang dapat diperbaiki dinormalisasi ke format konsisten.
  it("menormalisasi variasi spasi, tanda hubung, prefiks, dan alfabet Crockford", () => {
    expect(normalizeReferenceCode(" ltr o7k3 m-9qx2 h4td ")).toBe("LTR-07K3-M9QX-2H4TD");
    expect(normalizeReferenceCode("7K3M9QX2H4TD")).toBe("LTR-7K3M-9QX2-H4TD");
  });

  // Memastikan input kosong, format akhir, dan kode di luar alfabet ditolak.
  it("mengembalikan null untuk input kosong dan memvalidasi format hasil normalisasi", () => {
    expect(normalizeReferenceCode("  ")).toBeNull();
    expect(isValidReferenceCode("LTR-7K3M-9QX2-H4TD")).toBe(true);
    expect(isValidReferenceCode("LTR-7K3I-9QX2-H4TD")).toBe(false);
    expect(isValidReferenceCode("7K3M-9QX2-H4TD")).toBe(false);
    expect(isValidReferenceCode(normalizeReferenceCode("7K3M9QX2H4TDgarbage") ?? "")).toBe(false);
  });
});
