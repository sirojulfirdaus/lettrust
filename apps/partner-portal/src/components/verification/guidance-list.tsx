// Owner: Pash (PIC 4) | Status: COMPLETE | Ref: PRD FR-02.10, §9.7
import type { VerificationResponse } from "@/lib/api/types";
import { buildGuidance } from "@/lib/verification/guidance";

type GuidanceListProps = { result: VerificationResponse };

// Menampilkan rekomendasi tindak lanjut yang sesuai dengan kombinasi hasil.
export function GuidanceList({ result }: GuidanceListProps) {
  const guidance = buildGuidance(result);
  return (
    <section aria-labelledby="guidance-title" className="rounded-xl border bg-card p-5">
      <h2 id="guidance-title" className="text-lg font-semibold">Langkah yang Disarankan</h2>
      <ul className="mt-3 list-disc space-y-2 pl-5">
        {guidance.map((item) => <li key={item.id}>{item.text}</li>)}
      </ul>
    </section>
  );
}
