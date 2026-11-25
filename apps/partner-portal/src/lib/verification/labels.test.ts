// Owner: Pash (PIC 4) | Status: COMPLETE | Ref: PRD §9.6, FR-02.09, FR-06.07
import { describe, expect, it } from "vitest";
import { api07AiOnly, api07AiNotPerformed, api07NotFoundCodeOnly, api07ReferenceMatchAi, api07RegistryUnavailable, api07RevokedMismatch } from "@/fixtures/api";
import { indicatorLabel, integrityCheckLabel, proofCheckLabel, riskAnalysisLabel } from "./labels";

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

  // Memastikan enum baru ditangani netral dan taksonomi indikator diterjemahkan.
  it("tidak menafsirkan nilai dan kode indikator yang tidak dikenal sebagai hasil positif", () => {
    expect(proofCheckLabel({ ...api07ReferenceMatchAi.proofCheck, lookup: "FUTURE" } as never).title).toBe("Status tidak dikenal");
    expect(indicatorLabel("FUTURE_CODE")).toBe("Indikator tidak dikenal");
    expect(indicatorLabel("PAYMENT_REQUEST")).toBe("Permintaan pembayaran kepada pelamar");
  });
});
