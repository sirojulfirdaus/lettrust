// Owner: Pash (PIC 4) | Status: COMPLETE | Ref: PRD §9.6, FR-02.09, FR-06.07
import { describe, expect, it } from "vitest";
import * as fixtures from "@/fixtures/api";
import { api07AiNotPerformed, api07AiOnly, api07NotFoundCodeOnly, api07ReferenceMatchAi, api07RegistryUnavailable, api07RevokedMismatch } from "@/fixtures/api";
import type { VerificationResponse } from "@/lib/api/types";
import { buildGuidance } from "./guidance";
import { indicatorLabel, integrityCheckLabel, proofCheckLabel, proofDetailLines, riskAnalysisLabel } from "./labels";

// Kalimat vonis afirmatif (mis. "surat ini asli"); kalimat bernegasi PRD seperti "tidak berarti surat palsu" dikecualikan.
const VERDICT = /\b(?:surat|penawaran|hasil|berkas)\s+(?:ini\s+)?(?:asli|palsu|aman|penipuan)\b/i;
const NEGATION = /\b(?:tidak|bukan)\b/i;

// Mengembalikan kalimat yang memuat vonis tanpa negasi.
function verdictSentences(texts: string[]): string[] {
  return texts
    .flatMap((text) => text.split(/(?<=[.!?])\s+/))
    .filter((sentence) => VERDICT.test(sentence) && !NEGATION.test(sentence));
}

const API07_FIXTURES = Object.entries(fixtures).filter(([name]) => name.startsWith("api07")) as [string, VerificationResponse][];

describe("verification labels", () => {
  // Memastikan fixture API-07 normal menghasilkan label untuk tiga panel.
  it("memetakan hasil API-07 sukses ke label tiap komponen", () => {
    expect(proofCheckLabel(api07ReferenceMatchAi.proofCheck).title).toBe("Tercatat dan aktif");
    expect(integrityCheckLabel(api07ReferenceMatchAi.integrityCheck).title).toBe("Berkas identik dengan yang dicatat");
    expect(riskAnalysisLabel(api07ReferenceMatchAi.riskAnalysis).title).toBe("Indikasi risiko rendah");
  });

  // Memastikan alasan hasil parsial tidak berubah menjadi status positif.
  it("memetakan hasil API-07 parsial dan status tidak diminta sesuai alasan", () => {
    expect(proofCheckLabel(api07NotFoundCodeOnly.proofCheck).title).toBe("Tidak ditemukan di Lettrust");
    expect(integrityCheckLabel(api07NotFoundCodeOnly.integrityCheck).title).toBe("Tidak dapat diperiksa");
    expect(riskAnalysisLabel(api07NotFoundCodeOnly.riskAnalysis).title).toBe("Tidak diminta");
    expect(proofCheckLabel(api07RegistryUnavailable.proofCheck).tone).toBe("disruption");
    expect(integrityCheckLabel(api07RegistryUnavailable.integrityCheck).tone).toBe("disruption");
    expect(riskAnalysisLabel(api07AiNotPerformed.riskAnalysis).title).toBe("Tidak dapat dianalisis");
    expect(integrityCheckLabel(api07RevokedMismatch.integrityCheck).title).toBe("Berkas berbeda dari yang dicatat");
    expect(proofCheckLabel(api07RevokedMismatch.proofCheck).title).toBe("Tercatat, tetapi telah dicabut");
  });

  // Menampilkan redaksi PRD, nama perusahaan biasa, dan waktu yang mudah dibaca.
  it("memformat keterangan penerbit dan tanggal tanpa markup literal", () => {
    const revoked = proofCheckLabel(api07RevokedMismatch.proofCheck);
    expect(revoked.explanation).toContain(api07RevokedMismatch.proofCheck.issuer?.companyName);
    expect(revoked.explanation).not.toContain("**");
    if (api07RevokedMismatch.proofCheck.revokedAt) {
      expect(revoked.explanation).not.toContain(api07RevokedMismatch.proofCheck.revokedAt);
    }

    const unverified = proofCheckLabel({
      ...api07ReferenceMatchAi.proofCheck,
      issuerVerified: false,
    });
    expect(unverified.explanation).toContain("(penerbit belum/tidak berstatus terverifikasi)");
    expect(unverified.explanation).not.toContain("terverifikasi.)");
  });

  // Mempertahankan disclaimer dan penjelasan hasil sesuai teks PRD.
  it("menggunakan redaksi label sesuai PRD", () => {
    expect(proofCheckLabel(api07NotFoundCodeOnly.proofCheck).explanation).toContain("Ini tidak berarti surat palsu:");
    expect(riskAnalysisLabel(api07AiOnly.riskAnalysis).explanation).toContain("pola yang sering muncul pada penipuan rekrutmen");
    expect(riskAnalysisLabel(api07ReferenceMatchAi.riskAnalysis).explanation).toContain("Risiko rendah tidak menjamin surat aman.");
    expect(integrityCheckLabel(api07ReferenceMatchAi.integrityCheck).explanation).toBe(
      "Berkas Anda sama persis dengan berkas yang dicatat penerbit. Ini tidak menilai apakah isi surat aman.",
    );
  });

  // Memastikan tidak ada vonis gabungan pada label, panduan, dan teks risiko di seluruh fixture API-07.
  it("tidak memuat kalimat vonis pada semua fixture API-07", () => {
    expect(API07_FIXTURES.length).toBeGreaterThanOrEqual(13);
    expect(verdictSentences(["Surat ini asli."])).toHaveLength(1);
    for (const [name, response] of API07_FIXTURES) {
      const labels = [
        proofCheckLabel(response.proofCheck),
        integrityCheckLabel(response.integrityCheck),
        riskAnalysisLabel(response.riskAnalysis),
      ];
      const texts = [
        ...labels.flatMap(({ title, explanation }) => [title, explanation]),
        ...buildGuidance(response).map(({ text }) => text),
        response.riskAnalysis.explanation ?? "",
        response.riskAnalysis.recommendation ?? "",
      ];
      expect(verdictSentences(texts), name).toEqual([]);
    }
  });

  // Memastikan enum baru ditangani netral dan taksonomi indikator diterjemahkan.
  it("tidak menafsirkan nilai dan kode indikator yang tidak dikenal sebagai hasil positif", () => {
    expect(proofCheckLabel({ ...api07ReferenceMatchAi.proofCheck, lookup: "FUTURE" } as never).title).toBe("Status tidak dikenal");
    expect(indicatorLabel("FUTURE_CODE")).toBe("Indikator tidak dikenal");
    expect(indicatorLabel("PAYMENT_REQUEST")).toBe("Permintaan pembayaran kepada pelamar");
  });

  // FR-02.09 AC-02: rincian status penerbit dan waktu terbit hanya ditambahkan untuk REVOKED.
  it("menyusun rincian status penerbit dan waktu penerbitan untuk bukti REVOKED", () => {
    const revoked = proofDetailLines(api07RevokedMismatch.proofCheck);
    expect(revoked[0]).toBe("Status verifikasi penerbit: terverifikasi");
    expect(revoked[1]).toMatch(/^Waktu penerbitan: 23 November 2026/);
    expect(proofDetailLines({ ...api07RevokedMismatch.proofCheck, issuerVerified: false })[0]).toBe(
      "Status verifikasi penerbit: belum/tidak berstatus terverifikasi",
    );
    expect(proofDetailLines(api07ReferenceMatchAi.proofCheck)).toEqual([]);
    expect(proofDetailLines(api07NotFoundCodeOnly.proofCheck)).toEqual([]);
  });
});
