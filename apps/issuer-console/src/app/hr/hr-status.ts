// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-01.04, §9.3.1, §9.5, §9.9.3; SA §10.5 (S-03), §10.6 (S-06)
import type { MeResponse, ProofListResponse } from "@/lib/api/client";

// Data afiliasi perusahaan milik pengguna HR dari S-03 GET /api/v1/auth/me.
export type IssuerMembership = NonNullable<MeResponse["membership"]>;

// Item ringkas bukti penerbitan dari S-06 GET /api/v1/proofs.
export type ProofListItem = ProofListResponse["items"][number];

// Nada warna status sesuai token PRD §9.9.3 (selalu dipasangkan dengan teks dan ikon).
export type StatusTone = "positive" | "warning" | "danger" | "neutral";

// Presentasi status perusahaan dan otorisasi HR pada Beranda HR.
export type HrStatusPresentation = {
  issuerStatusLabel: string;
  issuerTone: StatusTone;
  authorizationLabel: string;
  authorizationTone: StatusTone;
  summaryTitle: string;
  summaryDescription: string;
  canIssueProof: boolean;
  disabledReason: string | null;
  reviewNote: string | null;
};

// Memetakan status penerbit dan otorisasi HR ke label, nada visual, serta hak penerbitan.
export function getHrStatusPresentation(membership: IssuerMembership): HrStatusPresentation {
  if (membership.issuerStatus === "PENDING") {
    return {
      issuerStatusLabel: "Menunggu Verifikasi",
      issuerTone: "warning",
      authorizationLabel:
        membership.authorizationStatus === "AUTHORIZED" ? "Diotorisasi" : "Belum Diotorisasi",
      authorizationTone:
        membership.authorizationStatus === "AUTHORIZED" ? "positive" : "neutral",
      summaryTitle: "Perusahaan sedang menunggu verifikasi",
      summaryDescription:
        "Pendaftaran perusahaan Anda sedang ditinjau oleh Administrator. Fitur penerbitan bukti baru dapat digunakan setelah perusahaan terverifikasi dan akun HR Anda diotorisasi.",
      canIssueProof: false,
      disabledReason:
        "Penerbitan bukti dinonaktifkan karena perusahaan masih menunggu verifikasi Administrator.",
      reviewNote: null,
    };
  }

  if (membership.issuerStatus === "REJECTED") {
    const trimmedNote = membership.reviewNote?.trim() ?? "";
    return {
      issuerStatusLabel: "Ditolak",
      issuerTone: "danger",
      authorizationLabel: "Tidak Diotorisasi",
      authorizationTone: "danger",
      summaryTitle: "Verifikasi perusahaan ditolak",
      summaryDescription:
        "Pengajuan verifikasi perusahaan Anda ditolak oleh Administrator. Fitur penerbitan bukti tidak tersedia untuk status ini.",
      canIssueProof: false,
      disabledReason:
        "Penerbitan bukti tidak tersedia karena verifikasi perusahaan ditolak oleh Administrator.",
      reviewNote: trimmedNote.length > 0 ? trimmedNote : null,
    };
  }

  if (membership.authorizationStatus !== "AUTHORIZED") {
    return {
      issuerStatusLabel: "Terverifikasi",
      issuerTone: "positive",
      authorizationLabel: "Menunggu Otorisasi",
      authorizationTone: "warning",
      summaryTitle: "Perusahaan terverifikasi, akun HR belum diotorisasi",
      summaryDescription:
        "Perusahaan Anda sudah terverifikasi, tetapi akun HR Anda masih memerlukan otorisasi dari Administrator sebelum dapat menerbitkan bukti.",
      canIssueProof: false,
      disabledReason:
        "Penerbitan bukti dinonaktifkan karena akun HR Anda belum diotorisasi oleh Administrator.",
      reviewNote: null,
    };
  }

  return {
    issuerStatusLabel: "Terverifikasi",
    issuerTone: "positive",
    authorizationLabel: "Diotorisasi",
    authorizationTone: "positive",
    summaryTitle: "Siap menerbitkan bukti",
    summaryDescription:
      "Perusahaan Anda telah terverifikasi dan akun HR Anda sudah diotorisasi. Anda dapat menerbitkan bukti baru serta memantau riwayat penerbitan.",
    canIssueProof: true,
    disabledReason: null,
    reviewNote: null,
  };
}

// Memetakan status siklus hidup bukti (ACTIVE/REVOKED) ke label dan nada warna PRD §9.9.3.
export function getProofLifecyclePresentation(status: ProofListItem["lifecycleStatus"]): {
  label: string;
  tone: StatusTone;
} {
  if (status === "ACTIVE") {
    return { label: "Aktif", tone: "positive" };
  }
  return { label: "Dicabut", tone: "warning" };
}

// Memformat stempel waktu ISO-8601 ke tampilan tanggal dan waktu yang mudah dibaca.
export function formatProofTimestamp(isoValue: string): string {
  const parsed = new Date(isoValue);
  if (Number.isNaN(parsed.getTime())) {
    return isoValue;
  }
  return new Intl.DateTimeFormat("id-ID", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
  }).format(parsed) + " UTC";
}
