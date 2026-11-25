// Owner: Pash (PIC 4) | Status: COMPLETE | Ref: PRD FR-02.08, §9.5
type ProcessingStatusProps = { includeRisk: boolean };

// Menjelaskan pemeriksaan yang sedang berlangsung dan estimasi relatifnya.
export function ProcessingStatus({ includeRisk }: ProcessingStatusProps) {
  return (
    <div role="status" aria-live="polite" className="rounded-lg border bg-muted p-4">
      <p className="font-medium">Sedang memeriksa surat Anda…</p>
      <p className="text-sm text-muted-foreground">
        {includeRisk ? "Analisis AI dapat memerlukan waktu hingga puluhan detik. Jangan tutup halaman ini." : "Pemeriksaan bukti penerbitan sedang berlangsung."}
      </p>
    </div>
  );
}
