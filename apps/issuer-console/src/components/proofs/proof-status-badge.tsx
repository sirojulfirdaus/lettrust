// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD §9.9.3, FR-03.08, FR-04.01
"use client";

import { Ban, CircleCheck } from "lucide-react";
import { StatusBadge } from "@/components/status-badge";
import { getProofLifecyclePresentation } from "@/app/hr/hr-status";
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

// Menampilkan badge status siklus hidup bukti (ACTIVE/REVOKED) dengan teks PRD §9.9.3, ikon, dan nada warna bersama.
export function ProofStatusBadge({ status }: { status: LifecycleStatus }) {
  const meta = getProofLifecyclePresentation(status);
  return (
    <StatusBadge label={meta.label} tone={meta.tone} icon={status === "ACTIVE" ? CircleCheck : Ban} />
  );
}
