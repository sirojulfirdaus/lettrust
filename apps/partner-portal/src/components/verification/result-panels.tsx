// Owner: Pash (PIC 4) | Status: COMPLETE | Ref: PRD FR-02.09, §9.6, §9.9.3
import type { ReactNode } from "react";
import type { VerificationResponse } from "@/lib/api/types";
import { StatusBadge } from "@/components/verification/status-icon";
import {
  indicatorLabel,
  integrityCheckLabel,
  proofCheckLabel,
  proofDetailLines,
  riskAnalysisLabel,
  type DetailLine,
  type StatusLabel,
} from "@/lib/verification/labels";

type ResultPanelsProps = { result: VerificationResponse };

const SEVERITY_LABELS: Record<string, string> = { HIGH: "tinggi", MEDIUM: "sedang", LOW: "rendah" };

// Menyusun metadata ringkas tiap panel; sumber registry tidak ditampilkan saat registry tidak terbaca atau tidak diminta.
function panelMetadata(result: VerificationResponse): Record<"proof" | "integrity" | "risk", DetailLine[]> {
  const { proofCheck, integrityCheck, riskAnalysis } = result;
  const proof = proofDetailLines(proofCheck);
  if (proofCheck.lookup === "FOUND" || proofCheck.lookup === "NOT_FOUND") proof.push({ label: "Sumber status bukti", value: "registry" });

  const integrity: DetailLine[] = [];
  if (integrityCheck.result !== "NOT_CHECKED") {
    integrity.push({ label: "Perbandingan hash", value: `${integrityCheck.result === "MATCH" ? "cocok" : "berbeda"} (${integrityCheck.hashAlgorithm})` });
  }

  const risk: DetailLine[] = [];
  if (riskAnalysis.state === "COMPLETED" && riskAnalysis.extractionMethod) {
    risk.push({ label: "Metode pembacaan", value: riskAnalysis.extractionMethod === "OCR" ? "OCR" : "teks PDF" });
    const pages = `${riskAnalysis.pagesAnalyzed ?? "—"}${riskAnalysis.pagesTotal ? ` dari ${riskAnalysis.pagesTotal}` : ""}${riskAnalysis.contentTruncated ? "; isi yang dianalisis dibatasi" : ""}`;
    risk.push({ label: "Halaman dianalisis", value: pages });
  }
  return { proof, integrity, risk };
}

// Daftar metadata ringkas (label–nilai) di bagian bawah panel.
function MetadataList({ lines }: { lines: DetailLine[] }) {
  if (lines.length === 0) return null;
  return (
    <dl className="mt-4 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 border-t pt-3 text-sm">
      {lines.map(({ label, value }) => (
        <div key={label} className="contents">
          <dt className="text-muted-foreground">{label}</dt>
          <dd className="min-w-0 break-words">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

// Satu panel hasil: nama panel sebagai label kecil, status sebagai lencana, lalu penjelasan PRD.
function ResultPanel({ name, label, children, metadata }: { name: string; label: StatusLabel; children?: ReactNode; metadata: DetailLine[] }) {
  return (
    <article className="rounded-lg border bg-card p-5">
      <h3 className="text-sm font-semibold">{name}</h3>
      <div className="mt-2">
        <StatusBadge label={label} />
      </div>
      <p className="mt-2 text-sm text-muted-foreground">{label.explanation}</p>
      {children}
      <MetadataList lines={metadata} />
    </article>
  );
}

// Merender ketiga status secara terpisah tanpa menggabungkannya menjadi vonis.
export function ResultPanels({ result }: ResultPanelsProps) {
  const risk = result.riskAnalysis;
  const metadata = panelMetadata(result);

  return (
    <section aria-labelledby="results-title" className="space-y-4">
      <h2 id="results-title" className="text-xl font-semibold">Hasil pemeriksaan</h2>
      <div className="grid gap-4">
        <ResultPanel name="Bukti Penerbitan & Status" label={proofCheckLabel(result.proofCheck)} metadata={metadata.proof} />
        <ResultPanel name="Keutuhan Berkas" label={integrityCheckLabel(result.integrityCheck)} metadata={metadata.integrity} />
        <ResultPanel name="Indikasi Risiko (AI)" label={riskAnalysisLabel(risk)} metadata={metadata.risk}>
          {risk.state === "COMPLETED" && (
            <div className="mt-4 space-y-4">
              {risk.indicatorDetails.length > 0 && (
                <ul className="space-y-3">
                  {risk.indicatorDetails.map((indicator, index) => (
                    <li key={`${indicator.code}-${index}`}>
                      <p className="text-sm font-medium">
                        {indicatorLabel(indicator.code)}{" "}
                        <span className="font-normal text-muted-foreground">· Tingkat {SEVERITY_LABELS[indicator.severity] ?? "rendah"}</span>
                      </p>
                      {indicator.evidence.map((quote, quoteIndex) => (
                        <blockquote key={quoteIndex} className="mt-1.5 border-l-2 pl-3 text-sm text-muted-foreground italic">“{quote}”</blockquote>
                      ))}
                    </li>
                  ))}
                </ul>
              )}
              {risk.explanation && <p className="text-sm">{risk.explanation}</p>}
              {risk.recommendation && <p className="text-sm font-medium">{risk.recommendation}</p>}
              <p className="text-xs text-muted-foreground">Hasil analisis AI bersifat indikatif dan bukan penentu keaslian surat atau putusan hukum.</p>
            </div>
          )}
        </ResultPanel>
      </div>
    </section>
  );
}
