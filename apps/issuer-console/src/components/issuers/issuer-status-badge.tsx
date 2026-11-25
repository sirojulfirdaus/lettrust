// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD §9.5, §9.9.3; SA §10.5
"use client";

import { CheckCircle2, Clock, ShieldAlert, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { components } from "@/lib/api/schema";

type IssuerStatus = components["schemas"]["IssuerStatus"];
type AuthorizationStatus = components["schemas"]["AuthorizationStatus"];
type StatusTone = "positive" | "warning" | "danger" | "neutral";

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

// Memetakan status verifikasi penerbit ke label bahasa Indonesia dan nada warna.
function getIssuerStatusMeta(status: IssuerStatus): { label: string; tone: StatusTone } {
  switch (status) {
    case "VERIFIED":
      return { label: "Terverifikasi", tone: "positive" };
    case "PENDING":
      return { label: "Menunggu Verifikasi", tone: "warning" };
    case "REJECTED":
      return { label: "Ditolak", tone: "danger" };
  }
}

// Memetakan status otorisasi HR ke label bahasa Indonesia dan nada warna.
function getAuthorizationStatusMeta(status: AuthorizationStatus): {
  label: string;
  tone: StatusTone;
} {
  switch (status) {
    case "AUTHORIZED":
      return { label: "Diotorisasi", tone: "positive" };
    case "NOT_AUTHORIZED":
      return { label: "Menunggu Otorisasi", tone: "neutral" };
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
  const meta = getIssuerStatusMeta(status);
  return <StatusPill label={meta.label} tone={meta.tone} />;
}

// Badge status otorisasi anggota HR (AUTHORIZED, NOT_AUTHORIZED).
export function HrAuthorizationBadge({ status }: { status: AuthorizationStatus }) {
  const meta = getAuthorizationStatusMeta(status);
  return <StatusPill label={meta.label} tone={meta.tone} />;
}

// Memformat stempel waktu ISO ke format lokal Indonesia yang mudah dibaca.
export function formatIssuerTimestamp(isoString: string | null): string {
  if (!isoString) {
    return "-";
  }
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) {
    return isoString;
  }
  return new Intl.DateTimeFormat("id-ID", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}
