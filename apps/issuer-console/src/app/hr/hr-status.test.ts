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
import {
  formatProofTimestamp,
  getHrStatusPresentation,
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
    expect(presentation.authorizationLabel).toBe("Menunggu Otorisasi");
    expect(presentation.authorizationTone).toBe("warning");
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
});
