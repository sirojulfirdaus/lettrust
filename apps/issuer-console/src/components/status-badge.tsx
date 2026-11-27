// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD §9.9.3
import type { LucideIcon } from "lucide-react";
import type { StatusTone } from "@/app/hr/hr-status";

// Kelas warna per nada; nada positif sengaja netral agar status aktif/terverifikasi tidak tampil hijau mencolok.
const TONE_CLASS_NAMES: Record<StatusTone, string> = {
  positive: "border-border bg-card text-foreground",
  warning: "border-amber-200 bg-amber-50 text-amber-700",
  danger: "border-red-200 bg-red-50 text-red-700",
  neutral: "border-border bg-muted text-muted-foreground",
};

// Badge status tunggal Console: selalu memasangkan teks, ikon, dan warna nada (tidak pernah warna saja).
export function StatusBadge({
  label,
  tone,
  icon: Icon,
}: {
  label: string;
  tone: StatusTone;
  icon: LucideIcon;
}) {
  return (
    <span
      className={`inline-flex w-fit shrink-0 items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs font-medium whitespace-nowrap ${TONE_CLASS_NAMES[tone]}`}
    >
      <Icon className="size-3.5" strokeWidth={2} aria-hidden="true" />
      <span>{label}</span>
    </span>
  );
}
