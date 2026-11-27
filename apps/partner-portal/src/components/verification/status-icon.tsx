// Owner: Pash (PIC 4) | Status: COMPLETE | Ref: PRD §9.6, §9.9.3
import {
  Ban,
  CircleAlert,
  CircleCheck,
  CircleDot,
  CircleHelp,
  CircleMinus,
  CircleX,
  OctagonAlert,
  TriangleAlert,
  type LucideIcon,
} from "lucide-react";
import type { StatusIconKey, StatusLabel, StatusTone } from "@/lib/verification/labels";

const ICONS: Record<StatusIconKey, LucideIcon> = {
  "circle-check": CircleCheck,
  "circle-x": CircleX,
  "circle-help": CircleHelp,
  "triangle-alert": TriangleAlert,
  ban: Ban,
  "circle-minus": CircleMinus,
  "circle-dot": CircleDot,
  "circle-alert": CircleAlert,
  "octagon-alert": OctagonAlert,
};

// Positif terbatas sengaja netral (bukan hijau); gangguan abu-abu seperti netral dan dibedakan lewat ikon.
const TONE_BADGE: Record<StatusTone, string> = {
  positive: "border-border bg-card text-foreground",
  warning: "border-amber-200 bg-amber-50 text-amber-700",
  danger: "border-red-200 bg-red-50 text-red-700",
  neutral: "border-border bg-muted text-muted-foreground",
  disruption: "border-border bg-muted text-muted-foreground",
};

// Ikon status dekoratif; makna selalu dibawa oleh teks di sebelahnya, warna mengikuti teks induk.
export function StatusIcon({ icon }: { icon: StatusIconKey }) {
  const Icon = ICONS[icon] ?? CircleHelp;
  return <Icon aria-hidden="true" focusable="false" size={16} strokeWidth={2} className="size-4 shrink-0" />;
}

// Lencana status kecil (ikon + judul PRD §9.6) dengan warna nada; dipakai sama seperti di Console.
export function StatusBadge({ label }: { label: Pick<StatusLabel, "icon" | "tone" | "title"> }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs font-medium ${TONE_BADGE[label.tone]}`}>
      <StatusIcon icon={label.icon} />
      {label.title}
    </span>
  );
}
