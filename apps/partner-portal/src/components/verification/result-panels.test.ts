// Owner: Pash (PIC 4) | Status: COMPLETE | Ref: T4-04; PRD FR-02.09–FR-02.10, §9.6, §9.8
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import * as fixtures from "@/fixtures/api";
import type { VerificationResponse } from "@/lib/api/types";
import { buildGuidance } from "@/lib/verification/guidance";
import { indicatorLabel, integrityCheckLabel, proofCheckLabel, riskAnalysisLabel } from "@/lib/verification/labels";
import { ResultPanels } from "./result-panels";
import { verificationErrorMessage } from "./verify-form";

// Judul panel yang diharapkan per fixture API-07 (PRD §9.6): [bukti, keutuhan, risiko].
const EXPECTED_TITLES: Record<string, [string, string, string]> = {
  api07AiNotPerformed: ["Tercatat dan aktif", "Tidak diperiksa", "Tidak dapat dianalisis"],
  api07AiOnly: ["Tidak diperiksa", "Tidak diperiksa", "Indikasi risiko tinggi"],
  api07AiOnlyMediumPartial: ["Tidak diperiksa", "Tidak diperiksa", "Indikasi risiko sedang"],
  api07AiQuotaExceeded: ["Tidak diperiksa", "Tidak diperiksa", "Analisis sedang tidak tersedia"],
  api07AiUnavailable: ["Tercatat dan aktif", "Berkas identik dengan yang dicatat", "Analisis sedang tidak tersedia"],
  api07CodeOnly: ["Tercatat dan aktif", "Tidak diperiksa", "Tidak diminta"],
  api07DoubleOutage: ["Pemeriksaan bukti sedang tidak dapat dilakukan", "Tidak dapat diperiksa saat ini", "Analisis sedang tidak tersedia"],
  api07IssuerNotVerified: ["Tercatat dan aktif", "Berkas identik dengan yang dicatat", "Tidak diminta"],
  api07NotFoundCodeOnly: ["Tidak ditemukan di Lettrust", "Tidak dapat diperiksa", "Tidak diminta"],
  api07NotFoundWithAi: ["Tidak ditemukan di Lettrust", "Tidak dapat diperiksa", "Indikasi risiko tinggi"],
  api07ReferenceMatchAi: ["Tercatat dan aktif", "Berkas identik dengan yang dicatat", "Indikasi risiko rendah"],
  api07RegistryUnavailable: ["Pemeriksaan bukti sedang tidak dapat dilakukan", "Tidak dapat diperiksa saat ini", "Indikasi risiko rendah"],
  api07RevokedMismatch: ["Tercatat, tetapi telah dicabut", "Berkas berbeda dari yang dicatat", "Tidak diminta"],
};

const CATEGORY_TITLES = ["Indikasi risiko tinggi", "Indikasi risiko sedang", "Indikasi risiko rendah"];
const INDICATOR_LABELS = ["PAYMENT_REQUEST", "SENSITIVE_DATA_REQUEST", "UNOFFICIAL_CONTACT", "URGENCY_PRESSURE", "IDENTITY_INCONSISTENCY", "UNREALISTIC_COMPENSATION", "VAGUE_JOB_DETAILS"].map(indicatorLabel);

// Merender panel hasil ke HTML statis untuk diperiksa tanpa DOM.
function renderPanels(result: VerificationResponse): string {
  return renderToStaticMarkup(createElement(ResultPanels, { result }));
}

const apiFixtures = Object.entries(fixtures).filter(([name]) => name.startsWith("api07"));
const errorFixtures = Object.entries(fixtures).filter(([name]) => name.startsWith("error"));

describe("portal verification fixtures", () => {
  // Setiap fixture API-07 dipetakan ke judul PRD yang spesifik, bukan sekadar tidak kosong.
  it("memetakan judul tiga panel sesuai PRD untuk setiap fixture API-07", () => {
    expect(apiFixtures.map(([name]) => name).sort()).toEqual(Object.keys(EXPECTED_TITLES).sort());
    for (const [name, fixture] of apiFixtures) {
      const response = fixture as VerificationResponse;
      const titles = [
        proofCheckLabel(response.proofCheck).title,
        integrityCheckLabel(response.integrityCheck).title,
        riskAnalysisLabel(response.riskAnalysis).title,
      ];
      expect(titles, name).toEqual(EXPECTED_TITLES[name]);
      expect(buildGuidance(response).length, name).toBeGreaterThan(0);
    }
  });

  // Risiko UNAVAILABLE/NOT_PERFORMED tidak boleh menampilkan kategori atau indikator (AGENTS §7).
  it("tidak merender kategori dan indikator saat analisis AI gagal atau tidak dilakukan", () => {
    const cases = { api07AiUnavailable: fixtures.api07AiUnavailable, api07AiQuotaExceeded: fixtures.api07AiQuotaExceeded, api07DoubleOutage: fixtures.api07DoubleOutage, api07AiNotPerformed: fixtures.api07AiNotPerformed };
    for (const [name, fixture] of Object.entries(cases)) {
      const html = renderPanels(fixture as VerificationResponse);
      expect(html, name).toContain(riskAnalysisLabel(fixture.riskAnalysis).title);
      for (const text of [...CATEGORY_TITLES, ...INDICATOR_LABELS, "Tingkat ", "<blockquote"]) {
        expect(html, `${name}: ${text}`).not.toContain(text);
      }
    }
  });

  // Kontrol positif: hasil COMPLETED merender kategori dan indikator dari indicatorDetails.
  it("merender kategori dan indikator saat analisis AI COMPLETED", () => {
    const html = renderPanels(fixtures.api07AiOnly as VerificationResponse);
    expect(html).toContain("Indikasi risiko tinggi");
    expect(html).toContain(indicatorLabel(fixtures.api07AiOnly.riskAnalysis.indicatorDetails[0].code));
  });

  // FR-02.09 AC-02: bukti REVOKED tetap menampilkan status verifikasi penerbit dan waktu penerbitan.
  it("merender status penerbit dan waktu penerbitan untuk bukti REVOKED tanpa duplikasi pada ACTIVE", () => {
    const revoked = renderPanels(fixtures.api07RevokedMismatch as VerificationResponse);
    expect(revoked).toContain("Status verifikasi penerbit: terverifikasi");
    expect(revoked).toContain("Waktu penerbitan: 23 November 2026");
    const active = renderPanels(fixtures.api07CodeOnly as VerificationResponse);
    expect(active).not.toContain("Waktu penerbitan:");
    expect(active).toContain("(penerbit terverifikasi) pada 23 November 2026");
  });

  it("memberi pesan statis yang dapat ditindaklanjuti untuk semua fixture error", () => {
    expect(errorFixtures.length).toBeGreaterThan(0);
    for (const [, fixture] of errorFixtures) {
      const envelope = fixture as { error: { code: string } };
      expect(verificationErrorMessage(0, envelope.error.code).length).toBeGreaterThan(0);
    }
  });
  // Memastikan kode kesalahan khusus dipetakan sebelum status HTTP umum.
  it("memakai pesan PRD untuk validasi dan pembatasan permintaan", () => {
    expect(verificationErrorMessage(400, "INVALID_REFERENCE_CODE_FORMAT")).toBe("Format kode referensi tidak valid. Periksa kembali kode pada surat Anda.");
    expect(verificationErrorMessage(400, "INVALID_INPUT_COMBINATION")).toBe("Masukkan kode referensi atau unggah berkas PDF untuk dianalisis.");
    expect(verificationErrorMessage(400, "AI_ONLY_REQUIRES_INCLUDE_RISK")).toBe("Tanpa kode referensi, pemeriksaan hanya dapat dilakukan dengan analisis AI. Setujui pemrosesan AI untuk melanjutkan.");
    expect(verificationErrorMessage(400, "EMPTY_FILE")).toBe("Berkas kosong tidak dapat diproses.");
    expect(verificationErrorMessage(400, "MULTIPLE_FILES")).toBe("Hanya satu berkas yang dapat diproses per permintaan.");
    expect(verificationErrorMessage(429, "RATE_LIMITED")).toBe("Terlalu banyak permintaan. Coba lagi beberapa saat lagi.");
  });

  // Penolakan persetujuan dari BFF diberi pesan khusus, bukan pesan validasi umum.
  it("memetakan VALIDATION_ERROR dengan detail aiConsent ke pesan persetujuan", () => {
    expect(verificationErrorMessage(400, "VALIDATION_ERROR", [{ field: "aiConsent" }])).toBe("Setujui pemrosesan AI sebelum mengirim surat untuk dianalisis.");
    expect(verificationErrorMessage(400, "VALIDATION_ERROR", [{ field: "includeRisk" }])).toBe("Periksa kembali kode referensi, pilihan mode, dan berkas yang Anda masukkan.");
  });
});
