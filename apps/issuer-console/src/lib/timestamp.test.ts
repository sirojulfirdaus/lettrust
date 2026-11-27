// Owner: Van (PIC 2) | Status: COMPLETE | Ref: SA §6.3, §10.1; PRD §9.10
import { describe, expect, it } from "vitest";
import { formatProofTimestamp } from "@/app/hr/hr-status";
import { formatIssuerTimestamp } from "@/components/issuers/issuer-status-badge";
import { formatUtcTimestamp } from "./timestamp";

describe("formatUtcTimestamp", () => {
  // Waktu ditampilkan dalam UTC (bukan zona lokal peramban) dan selalu berlabel "UTC".
  it("memformat waktu API dalam UTC dengan label UTC", () => {
    const formatted = formatUtcTimestamp("2026-11-26T23:30:00Z");
    expect(formatted.endsWith(" UTC")).toBe(true);
    expect(formatted).toContain("26");
    expect(formatted).toContain("23.30");
  });

  // Penerbit dan bukti memakai formatter yang sama sehingga konvensi zona waktunya identik.
  it("dipakai bersama oleh tampilan penerbit dan bukti", () => {
    const value = "2026-11-27T01:02:00+07:00";
    expect(formatIssuerTimestamp(value)).toBe(formatUtcTimestamp(value));
    expect(formatProofTimestamp(value)).toBe(formatUtcTimestamp(value));
    expect(formatUtcTimestamp(value)).toContain("18.02");
  });

  // Nilai kosong menjadi tanda strip, bukan waktu palsu.
  it("mengembalikan '-' untuk nilai kosong", () => {
    expect(formatUtcTimestamp(null)).toBe("-");
  });
});
