// Owner: Pash (PIC 4) | Status: STUB | Ref: PRD §9.6, FR-02.09, FR-06.07; SA §11.3.3
// TODO: Petakan setiap enum hasil ke judul, penjelasan, ikon, dan nada persis sesuai PRD §9.6; nilai tidak dikenal -> kondisi tidak dikenal (FR-06.07/AC-04).
import type { IntegrityCheck, ProofCheck, RiskAnalysis } from "@/lib/api/types";

// Nada status sesuai PRD §9.9.3; selalu disertai teks dan ikon.
export type StatusTone = "positive" | "warning" | "danger" | "disruption" | "neutral";

// Label tampilan satu panel hasil.
export type StatusLabel = {
  title: string;
  explanation: string;
  icon: string;
  tone: StatusTone;
};

// Label panel Bukti Penerbitan & Status (PRD §9.6.1).
export function proofCheckLabel(_proofCheck: ProofCheck): StatusLabel {
  throw new Error("NOT_IMPLEMENTED");
}

// Label panel Keutuhan Berkas (PRD §9.6.2).
export function integrityCheckLabel(_integrityCheck: IntegrityCheck): StatusLabel {
  throw new Error("NOT_IMPLEMENTED");
}

// Label panel Indikasi Risiko (AI) (PRD §9.6.3).
export function riskAnalysisLabel(_riskAnalysis: RiskAnalysis): StatusLabel {
  throw new Error("NOT_IMPLEMENTED");
}

// Label bahasa Indonesia untuk kode indikator taksonomi (PRD §9.6.3).
export function indicatorLabel(_code: string): string {
  throw new Error("NOT_IMPLEMENTED");
}
