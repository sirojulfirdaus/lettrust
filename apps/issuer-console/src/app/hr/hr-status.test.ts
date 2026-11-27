// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-01.04, §9.3.1, §9.5, §9.9.3; SA §10.5 (S-03), §10.6 (S-06)
import { describe, expect, it } from "vitest";
import {
  s03SessionHrAuthorized,
  s03SessionHrPending,
  s03SessionHrRejected,
  s03SessionHrVerifiedNotAuthorized,
  s06ProofList,
  s06ProofListEmpty,
} from "@/fixtures/api";
import { formatIssuerTimestamp } from "@/components/issuers/issuer-status-badge";
import { formatProofTimestamp as formatProofBadgeTimestamp } from "@/components/proofs/proof-status-badge";
import {
  formatProofTimestamp,
  getAuthorizationPresentation,
  getHrStatusPresentation,
  getIssuerStatusPresentation,
  getProofLifecyclePresentation,
} from "./hr-status";

describe("pemetaan status Beranda HR", () => {
  it("memetakan status PENDING dengan tombol penerbitan nonaktif dan alasan jelas", () => {
    const presentation = getHrStatusPresentation(s03SessionHrPending.membership);
    expect(presentation.issuerStatusLabel).toBe("Menunggu Verifikasi");
    expect(presentation.issuerTone).toBe("warning");
    expect(presentation.canIssueProof).toBe(false);
    expect(presentation.disabledReason).toContain("menunggu verifikasi");
    expect(presentation.reviewNote).toBeNull();
  });

  it("memetakan status REJECTED beserta reviewNote teks biasa dan penerbitan nonaktif", () => {
    const presentation = getHrStatusPresentation(s03SessionHrRejected.membership);
    expect(presentation.issuerStatusLabel).toBe("Ditolak");
    expect(presentation.issuerTone).toBe("danger");
    expect(presentation.canIssueProof).toBe(false);
    expect(presentation.disabledReason).toContain("ditolak");
    expect(presentation.reviewNote).toBe(s03SessionHrRejected.membership.reviewNote);
  });

  it("memetakan VERIFIED + NOT_AUTHORIZED dengan penjelasan otorisasi Administrator", () => {
    const presentation = getHrStatusPresentation(s03SessionHrVerifiedNotAuthorized.membership);
    expect(presentation.issuerStatusLabel).toBe("Terverifikasi");
    expect(presentation.issuerTone).toBe("positive");
    expect(presentation.authorizationLabel).toBe("Belum Diotorisasi");
    expect(presentation.authorizationTone).toBe("neutral");
    expect(presentation.canIssueProof).toBe(false);
    expect(presentation.disabledReason).toContain("belum diotorisasi");
  });

  it("memetakan VERIFIED + AUTHORIZED dengan hak penerbitan aktif", () => {
    const presentation = getHrStatusPresentation(s03SessionHrAuthorized.membership);
    expect(presentation.issuerStatusLabel).toBe("Terverifikasi");
    expect(presentation.issuerTone).toBe("positive");
    expect(presentation.authorizationLabel).toBe("Diotorisasi");
    expect(presentation.authorizationTone).toBe("positive");
    expect(presentation.canIssueProof).toBe(true);
    expect(presentation.disabledReason).toBeNull();
  });

  it("memetakan status siklus hidup bukti dari fixture S-06", () => {
    expect(s06ProofList.total).toBe(2);
    expect(s06ProofListEmpty.items).toHaveLength(0);

    const active = getProofLifecyclePresentation(s06ProofList.items[0].lifecycleStatus);
    const revoked = getProofLifecyclePresentation(s06ProofList.items[1].lifecycleStatus);

    expect(active).toEqual({ label: "Aktif", tone: "positive" });
    expect(revoked).toEqual({ label: "Dicabut", tone: "warning" });
  });

  it("memformat stempel waktu ISO bukti dengan aman", () => {
    const formatted = formatProofTimestamp(s06ProofList.items[0].issuedAt);
    expect(formatted).toContain("2026");
    expect(formatted).toContain("UTC");
    expect(formatProofTimestamp("tidak-valid")).toBe("tidak-valid");
  });

  it("membedakan NOT_AUTHORIZED yang menunggu (PENDING/VERIFIED) dari penerbit REJECTED", () => {
    const waiting = { label: "Belum Diotorisasi", tone: "neutral" };
    const rejected = { label: "Tidak Diotorisasi", tone: "danger" };
    expect(getAuthorizationPresentation("NOT_AUTHORIZED", "PENDING")).toEqual(waiting);
    expect(getAuthorizationPresentation("NOT_AUTHORIZED", "VERIFIED")).toEqual(waiting);
    expect(getAuthorizationPresentation("NOT_AUTHORIZED", "REJECTED")).toEqual(rejected);
    expect(getAuthorizationPresentation("AUTHORIZED", "VERIFIED")).toEqual({
      label: "Diotorisasi",
      tone: "positive",
    });

    const cases = [
      { fixture: s03SessionHrPending, expected: waiting },
      { fixture: s03SessionHrVerifiedNotAuthorized, expected: waiting },
      { fixture: s03SessionHrRejected, expected: rejected },
    ];
    for (const { fixture, expected } of cases) {
      const presentation = getHrStatusPresentation({
        ...fixture.membership,
        authorizationStatus: "NOT_AUTHORIZED",
      });
      expect({ label: presentation.authorizationLabel, tone: presentation.authorizationTone }).toEqual(
        expected,
      );
    }
    expect(getIssuerStatusPresentation("REJECTED")).toEqual({ label: "Ditolak", tone: "danger" });
  });

  it("memformat waktu penerbit dan bukti dengan formatter UTC yang sama", () => {
    const iso = "2026-11-24T03:15:00Z";
    const formatted = formatProofTimestamp(iso);
    expect(formatted).toMatch(/UTC$/);
    expect(formatted).toMatch(/03[.:]15/);
    expect(formatIssuerTimestamp(iso)).toBe(formatted);
    expect(formatProofBadgeTimestamp(iso)).toBe(formatted);
    expect(formatIssuerTimestamp(null)).toBe("-");
  });
});
