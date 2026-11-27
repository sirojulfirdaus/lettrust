// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD §9.9.3, FR-03.08, FR-04.01
"use client";

import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { LifecycleStatus, RevocationReasonCode } from "@/lib/api/client";

export { formatUtcTimestamp as formatProofTimestamp } from "@/lib/timestamp";

export type RevocationReasonOption = {
  code: RevocationReasonCode;
  label: string;
  description: string;
};

// Daftar alasan pencabutan yang diizinkan sesuai kontrak API-06 dan PRD FR-04.01.
export const REVOCATION_REASON_OPTIONS: readonly RevocationReasonOption[] = [
  {
    code: "OFFER_WITHDRAWN",
    label: "Penawaran dibatalkan",
    description: "Perusahaan menarik atau membatalkan offer letter yang sebelumnya diterbitkan.",
  },
  {
    code: "ISSUED_IN_ERROR",
    label: "Kesalahan penerbitan",
    description: "Bukti diterbitkan untuk berkas yang keliru atau tidak seharusnya diterbitkan.",
  },
  {
    code: "DOCUMENT_REPLACED",
    label: "Dokumen diganti versi baru",
    description: "Offer letter diperbarui dan akan digantikan oleh berkas final yang baru.",
  },
  {
    code: "OTHER",
    label: "Alasan lainnya",
    description: "Pencabutan dilakukan karena alasan operasional lain di luar kategori di atas.",
  },
];

// Mengembalikan label berbahasa Indonesia untuk kode alasan pencabutan bukti.
export function getRevocationReasonLabel(code: RevocationReasonCode): string {
  const match = REVOCATION_REASON_OPTIONS.find((item) => item.code === code);
  return match ? match.label : code;
}

// Menampilkan badge status siklus hidup bukti (ACTIVE/REVOKED) dengan warna, ikon, dan teks PRD §9.9.3.
export function ProofStatusBadge({ status }: { status: LifecycleStatus }) {
  if (status === "ACTIVE") {
    return (
      <Badge
        variant="outline"
        className="gap-1.5 border-status-positive/30 bg-status-positive/10 px-2.5 py-0.5 text-status-positive"
      >
        <CheckCircle2 className="size-3.5" aria-hidden="true" />
        <span>Aktif</span>
      </Badge>
    );
  }

  return (
    <Badge
      variant="outline"
      className="gap-1.5 border-status-warning/30 bg-status-warning/10 px-2.5 py-0.5 text-status-warning"
    >
      <AlertTriangle className="size-3.5" aria-hidden="true" />
      <span>Dicabut</span>
    </Badge>
  );
}
