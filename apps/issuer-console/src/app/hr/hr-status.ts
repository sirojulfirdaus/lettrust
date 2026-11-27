// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-01.04, §9.3.1, §9.5, §9.9.3; SA §10.5 (S-03), §10.6 (S-06)
import type { MeResponse, ProofListResponse } from "@/lib/api/client";

export { formatUtcTimestamp as formatProofTimestamp } from "@/lib/timestamp";

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

// Label dan nada tunggal status verifikasi penerbit untuk Beranda HR, badge Admin, dan pesan keputusan.
export function getIssuerStatusPresentation(status: IssuerMembership["issuerStatus"]): {
  label: string;
  tone: StatusTone;
} {
  switch (status) {
    case "VERIFIED":
      return { label: "Terverifikasi", tone: "positive" };
    case "PENDING":
      return { label: "Menunggu Verifikasi", tone: "warning" };
    case "REJECTED":
      return { label: "Ditolak", tone: "danger" };
  }
}

// Label dan nada status otorisasi HR; HR pada penerbit REJECTED tidak akan diotorisasi sehingga tidak ditampilkan sebagai menunggu.
export function getAuthorizationPresentation(
  status: IssuerMembership["authorizationStatus"],
  issuerStatus: IssuerMembership["issuerStatus"],
): {
  label: string;
  tone: StatusTone;
} {
  if (status === "AUTHORIZED") {
    return { label: "Diotorisasi", tone: "positive" };
  }
  return issuerStatus === "REJECTED"
    ? { label: "Tidak Diotorisasi", tone: "danger" }
    : { label: "Belum Diotorisasi", tone: "neutral" };
}

// Memetakan status penerbit dan otorisasi HR ke label, nada visual, serta hak penerbitan.
export function getHrStatusPresentation(membership: IssuerMembership): HrStatusPresentation {
  const issuer = getIssuerStatusPresentation(membership.issuerStatus);
  const authorization = getAuthorizationPresentation(
    membership.authorizationStatus,
    membership.issuerStatus,
  );
  const labels = {
    issuerStatusLabel: issuer.label,
    issuerTone: issuer.tone,
    authorizationLabel: authorization.label,
    authorizationTone: authorization.tone,
  };

  if (membership.issuerStatus === "PENDING") {
    return {
      ...labels,
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
      ...labels,
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
      ...labels,
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
    ...labels,
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
