// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD §9.5, §9.9.3; SA §10.5
"use client";

import { CheckCircle2, Clock, ShieldAlert, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { components } from "@/lib/api/schema";
import {
  getAuthorizationPresentation,
  getIssuerStatusPresentation,
  type StatusTone,
} from "@/app/hr/hr-status";

type IssuerStatus = components["schemas"]["IssuerStatus"];
type AuthorizationStatus = components["schemas"]["AuthorizationStatus"];

export { formatUtcTimestamp as formatIssuerTimestamp } from "@/lib/timestamp";

// Mengembalikan kelas warna badge sesuai token status PRD §9.9.3.
function getToneClassName(tone: StatusTone): string {
  switch (tone) {
    case "positive":
      return "border-status-positive/30 bg-status-positive/10 text-status-positive";
    case "warning":
      return "border-status-warning/30 bg-status-warning/10 text-status-warning";
    case "danger":
      return "border-status-danger/30 bg-status-danger/10 text-status-danger";
    case "neutral":
      return "border-status-neutral/30 bg-status-neutral/10 text-status-neutral";
  }
}

function StatusPill({ label, tone }: { label: string; tone: StatusTone }) {
  const Icon =
    tone === "positive"
      ? CheckCircle2
      : tone === "warning"
        ? Clock
        : tone === "danger"
          ? XCircle
          : ShieldAlert;

  return (
    <Badge variant="outline" className={`gap-1.5 px-2.5 py-0.5 ${getToneClassName(tone)}`}>
      <Icon className="size-3.5" aria-hidden="true" />
      <span>{label}</span>
    </Badge>
  );
}

// Badge status verifikasi penerbit (PENDING, VERIFIED, REJECTED).
export function IssuerStatusBadge({ status }: { status: IssuerStatus }) {
  const meta = getIssuerStatusPresentation(status);
  return <StatusPill label={meta.label} tone={meta.tone} />;
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
  return <StatusPill label={meta.label} tone={meta.tone} />;
}
