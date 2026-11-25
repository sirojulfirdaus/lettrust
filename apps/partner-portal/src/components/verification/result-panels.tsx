// Owner: Pash (PIC 4) | Status: COMPLETE | Ref: PRD FR-02.09, §9.6, §9.9.3
import type { VerificationResponse } from "@/lib/api/types";
import { indicatorLabel, integrityCheckLabel, proofCheckLabel, riskAnalysisLabel } from "@/lib/verification/labels";

type ResultPanelsProps = { result: VerificationResponse };

const toneClasses = {
  positive: "border-l-green-700",
  warning: "border-l-amber-700",
  danger: "border-l-red-700",
  disruption: "border-l-violet-700",
  neutral: "border-l-slate-600",
} as const;

// Merender ketiga status secara terpisah tanpa menggabungkannya menjadi vonis.
export function ResultPanels({ result }: ResultPanelsProps) {
  const proof = proofCheckLabel(result.proofCheck);
  const integrity = integrityCheckLabel(result.integrityCheck);
  const risk = riskAnalysisLabel(result.riskAnalysis);
  const panels = [
    { id: "proof", title: "Bukti Penerbitan & Status", label: proof },
    { id: "integrity", title: "Keutuhan Berkas", label: integrity },
    { id: "risk", title: "Indikasi Risiko (AI)", label: risk },
  ];

  return (
    <section aria-labelledby="results-title" className="space-y-4">
      <h2 id="results-title" className="text-xl font-semibold">Hasil pemeriksaan</h2>
      <div className="grid gap-4">
        {panels.map(({ id, title, label }) => (
          <article key={id} className={`rounded-xl border border-l-4 bg-card p-5 ${toneClasses[label.tone]}`}>
            <div className="flex items-start gap-3">
              <span aria-hidden="true" className="text-xl font-bold">{label.icon}</span>
              <div className="min-w-0">
                <h3 className="font-semibold">{title}: {label.title}</h3>
                <p className="mt-1 text-sm text-muted-foreground">{label.explanation}</p>
              </div>
            </div>
            {id === "proof" && result.proofCheck.issuer?.companyName && (
              <p className="mt-3 text-sm">Penerbit: <span className="font-medium">{result.proofCheck.issuer.companyName}</span></p>
            )}
            {id === "proof" && result.proofCheck.lookup !== "NOT_REQUESTED" && (
              <p className="mt-3 text-xs text-muted-foreground">Sumber status bukti: registry.</p>
            )}
            {id === "integrity" && result.integrityCheck.result !== "NOT_CHECKED" && (
              <p className="mt-3 text-xs text-muted-foreground">Hasil perbandingan hash: {result.integrityCheck.result === "MATCH" ? "cocok" : "berbeda"} ({result.integrityCheck.hashAlgorithm}).</p>
            )}
            {id === "risk" && result.riskAnalysis.state === "COMPLETED" && (
              <div className="mt-4 space-y-3">
                {result.riskAnalysis.indicatorDetails.map((indicator, index) => (
                  <div key={`${indicator.code}-${index}`} className="rounded-lg bg-muted p-3">
                    <p className="font-medium">{indicatorLabel(indicator.code)} <span className="text-xs">· Tingkat {indicator.severity === "HIGH" ? "tinggi" : indicator.severity === "MEDIUM" ? "sedang" : "rendah"}</span></p>
                    {indicator.evidence.map((quote, quoteIndex) => <blockquote key={quoteIndex} className="mt-2 border-l-2 pl-3 text-sm">“{quote}”</blockquote>)}
                  </div>
                ))}
                {result.riskAnalysis.explanation && <p className="text-sm">{result.riskAnalysis.explanation}</p>}
                {result.riskAnalysis.recommendation && <p className="text-sm font-medium">{result.riskAnalysis.recommendation}</p>}
                <p className="text-xs text-muted-foreground">Hasil analisis AI bersifat indikatif dan bukan penentu keaslian surat atau putusan hukum.</p>
                {result.riskAnalysis.extractionMethod && <p className="text-xs text-muted-foreground">Metode pembacaan: {result.riskAnalysis.extractionMethod === "OCR" ? "OCR" : "teks PDF"}. Halaman dianalisis: {result.riskAnalysis.pagesAnalyzed ?? "—"}{result.riskAnalysis.pagesTotal ? ` dari ${result.riskAnalysis.pagesTotal}` : ""}{result.riskAnalysis.contentTruncated ? "; isi yang dianalisis dibatasi" : ""}.</p>}
              </div>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}
