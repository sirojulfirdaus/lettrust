// Owner: Pash (PIC 4) | Status: COMPLETE | Ref: T4-04; PRD FR-02.09–FR-02.10
import { describe, expect, it } from "vitest";
import * as fixtures from "@/fixtures/api";
import type { VerificationResponse } from "@/lib/api/types";
import { buildGuidance } from "@/lib/verification/guidance";
import { integrityCheckLabel, proofCheckLabel, riskAnalysisLabel } from "@/lib/verification/labels";
import { verificationErrorMessage } from "./verify-form";

const apiFixtures = Object.entries(fixtures).filter(([name]) => name.startsWith("api07"));
const errorFixtures = Object.entries(fixtures).filter(([name]) => name.startsWith("error"));

describe("portal verification fixtures", () => {
  it("dapat memetakan tiga panel dan panduan untuk semua fixture API-07", () => {
    expect(apiFixtures.length).toBeGreaterThan(0);
    for (const [, fixture] of apiFixtures) {
      const response = fixture as VerificationResponse;
      expect(proofCheckLabel(response.proofCheck).title).toBeTruthy();
      expect(integrityCheckLabel(response.integrityCheck).title).toBeTruthy();
      expect(riskAnalysisLabel(response.riskAnalysis).title).toBeTruthy();
      expect(buildGuidance(response).length).toBeGreaterThan(0);
    }
  });

  it("memberi pesan statis yang dapat ditindaklanjuti untuk semua fixture error", () => {
    expect(errorFixtures.length).toBeGreaterThan(0);
    for (const [, fixture] of errorFixtures) {
      const envelope = fixture as { error: { code: string } };
      expect(verificationErrorMessage(0, envelope.error.code).length).toBeGreaterThan(0);
    }
  });
});
