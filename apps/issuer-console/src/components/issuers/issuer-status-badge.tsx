// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD §9.5, §9.9.3; SA §10.5
"use client";

import { CircleCheck, CircleMinus, CircleX, Clock, type LucideIcon } from "lucide-react";
import { StatusBadge } from "@/components/status-badge";
import type { components } from "@/lib/api/schema";
import {
  getAuthorizationPresentation,
  getIssuerStatusPresentation,
  type StatusTone,
} from "@/app/hr/hr-status";

type IssuerStatus = components["schemas"]["IssuerStatus"];
type AuthorizationStatus = components["schemas"]["AuthorizationStatus"];

export { formatUtcTimestamp as formatIssuerTimestamp } from "@/lib/timestamp";

// Ikon per nada status penerbit/otorisasi; nada netral berarti belum berjalan (belum diotorisasi).
const TONE_ICONS: Record<StatusTone, LucideIcon> = {
  positive: CircleCheck,
  warning: Clock,
  danger: CircleX,
  neutral: CircleMinus,
};

// Badge status verifikasi penerbit (PENDING, VERIFIED, REJECTED).
export function IssuerStatusBadge({ status }: { status: IssuerStatus }) {
  const meta = getIssuerStatusPresentation(status);
  return <StatusBadge label={meta.label} tone={meta.tone} icon={TONE_ICONS[meta.tone]} />;
}

// Badge status otorisasi anggota HR; status penerbit menentukan label NOT_AUTHORIZED (menunggu atau ditolak).
export function HrAuthorizationBadge({
  status,
  issuerStatus,
}: {
  status: AuthorizationStatus;
  issuerStatus: IssuerStatus;
}) {
  const meta = getAuthorizationPresentation(status, issuerStatus);
  return <StatusBadge label={meta.label} tone={meta.tone} icon={TONE_ICONS[meta.tone]} />;
}
