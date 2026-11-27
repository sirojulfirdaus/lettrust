// Owner: Pash (PIC 4) | Status: COMPLETE | Ref: PRD §9.6, FR-02.09, FR-06.07; SA §11.3.3
import type { IntegrityCheck, ProofCheck, RiskAnalysis } from "@/lib/api/types";

// Nada status sesuai PRD §9.9.3; selalu disertai teks dan ikon.
export type StatusTone = "positive" | "warning" | "danger" | "disruption" | "neutral";

// Kunci ikon status (presentasi saja); dipetakan ke ikon lucide-react di StatusIcon.
export type StatusIconKey =
  | "circle-check"
  | "circle-x"
  | "circle-help"
  | "triangle-alert"
  | "ban"
  | "circle-minus"
  | "circle-dot"
  | "circle-alert"
  | "octagon-alert";

// Label tampilan satu panel hasil.
export type StatusLabel = {
  title: string;
  explanation: string;
  icon: StatusIconKey;
  tone: StatusTone;
};

const UNKNOWN_LABEL: StatusLabel = {
  title: "Status tidak dikenal",
  explanation: "Lettrust menerima status yang belum dikenali. Periksa kembali nanti atau konfirmasikan melalui kanal resmi perusahaan.",
  icon: "circle-help",
  tone: "neutral",
};

// Memformat waktu API (ISO 8601 UTC) dalam UTC berlabel "UTC", sama dengan format Console (mis. "27 Nov 2026, 04.30 UTC").
export function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("id-ID", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
  }).format(date) + " UTC";
}

// Label panel Bukti Penerbitan & Status (PRD §9.6.1).
export function proofCheckLabel(proofCheck: ProofCheck): StatusLabel {
  const lookup = proofCheck.lookup as string;
  if (lookup === "FOUND" && proofCheck.lifecycleStatus === "ACTIVE") {
    const company = proofCheck.issuer?.companyName;
    const issuerStatus = proofCheck.issuerVerified === false
      ? "penerbit belum/tidak berstatus terverifikasi"
      : "penerbit terverifikasi";
    const issuedAt = proofCheck.issuedAt ? ` pada ${formatTimestamp(proofCheck.issuedAt)}` : "";
    return {
      title: "Tercatat dan aktif",
      explanation: `Surat dengan kode ini dicatat oleh ${company ? `${company} (${issuerStatus})` : issuerStatus}${issuedAt}, dan statusnya masih aktif. Pastikan nama perusahaan sesuai dengan surat Anda. Status ini tidak menjamin isi surat aman.`,
      icon: "circle-check",
      tone: "positive",
    };
  }
  if (lookup === "FOUND" && proofCheck.lifecycleStatus === "REVOKED") {
    const company = proofCheck.issuer?.companyName;
    const revokedAt = proofCheck.revokedAt ? ` pada ${formatTimestamp(proofCheck.revokedAt)}` : "";
    return {
      title: "Tercatat, tetapi telah dicabut",
      explanation: `Surat dengan kode ini pernah dicatat oleh ${company ?? "penerbit"}, tetapi telah dicabut oleh penerbit${revokedAt}. Konfirmasikan status penawaran kepada perusahaan melalui kanal resminya.`,
      icon: "ban",
      tone: "warning",
    };
  }
  switch (lookup) {
    case "NOT_FOUND":
      return { title: "Tidak ditemukan di Lettrust", explanation: "Kode ini tidak tercatat dalam registry Lettrust. Ini tidak berarti surat palsu: perusahaan mungkin tidak menggunakan Lettrust atau kode salah ketik. Periksa kembali kode dan konfirmasikan melalui kanal resmi perusahaan.", icon: "circle-help", tone: "neutral" };
    case "UNAVAILABLE":
      return { title: "Pemeriksaan bukti sedang tidak dapat dilakukan", explanation: "Terjadi gangguan saat memeriksa registry. Ini bukan berarti kode tidak terdaftar. Coba lagi beberapa saat lagi.", icon: "triangle-alert", tone: "disruption" };
    case "NOT_REQUESTED":
      return { title: "Tidak diperiksa", explanation: "Bukti penerbitan tidak diperiksa karena Anda tidak memasukkan kode referensi.", icon: "circle-minus", tone: "neutral" };
    default:
      return UNKNOWN_LABEL;
  }
}

// Satu baris metadata panel: label dan nilai ditampilkan sebagai pasangan dt/dd.
export type DetailLine = { label: string; value: string };

// Rincian bukti untuk FOUND (ACTIVE dan REVOKED) sesuai FR-02.09 AC-02: penerbit, status verifikasi penerbit, waktu penerbitan.
export function proofDetailLines(proofCheck: ProofCheck): DetailLine[] {
  if ((proofCheck.lookup as string) !== "FOUND") return [];
  const lines: DetailLine[] = [];
  if (proofCheck.issuer?.companyName) lines.push({ label: "Penerbit", value: proofCheck.issuer.companyName });
  if (proofCheck.issuerVerified === true) lines.push({ label: "Status verifikasi penerbit", value: "terverifikasi" });
  if (proofCheck.issuerVerified === false) lines.push({ label: "Status verifikasi penerbit", value: "belum/tidak berstatus terverifikasi" });
  if (proofCheck.issuedAt) lines.push({ label: "Waktu penerbitan", value: formatTimestamp(proofCheck.issuedAt) });
  return lines;
}

// Label panel Keutuhan Berkas (PRD §9.6.2).
export function integrityCheckLabel(integrityCheck: IntegrityCheck): StatusLabel {
  const result = integrityCheck.result as string;
  if (result === "MATCH") return { title: "Berkas identik dengan yang dicatat", explanation: "Berkas Anda sama persis dengan berkas yang dicatat penerbit. Ini tidak menilai apakah isi surat aman.", icon: "circle-check", tone: "positive" };
  if (result === "MISMATCH") return { title: "Berkas berbeda dari yang dicatat", explanation: "Berkas Anda tidak sama dengan berkas yang dicatat penerbit untuk kode ini. Berkas mungkin telah diubah atau disimpan ulang. Mintalah salinan asli melalui kanal resmi perusahaan.", icon: "circle-x", tone: "warning" };
  if (result !== "NOT_CHECKED") return UNKNOWN_LABEL;
  switch (integrityCheck.reason as string | null) {
    case "NO_FILE": return { title: "Tidak diperiksa", explanation: "Unggah berkas PDF surat Anda untuk memastikan berkas sama dengan yang dicatat penerbit.", icon: "circle-minus", tone: "neutral" };
    case "PROOF_NOT_FOUND": return { title: "Tidak dapat diperiksa", explanation: "Tidak ada catatan rujukan karena kode tidak ditemukan.", icon: "circle-minus", tone: "neutral" };
    case "REGISTRY_UNAVAILABLE": return { title: "Tidak dapat diperiksa saat ini", explanation: "Catatan rujukan tidak dapat dibaca karena gangguan. Coba lagi beberapa saat lagi.", icon: "circle-minus", tone: "disruption" };
    case "NO_REFERENCE_CODE": return { title: "Tidak diperiksa", explanation: "Keutuhan berkas hanya dapat diperiksa dengan kode referensi.", icon: "circle-minus", tone: "neutral" };
    default: return UNKNOWN_LABEL;
  }
}

// Label panel Indikasi Risiko (AI) (PRD §9.6.3).
export function riskAnalysisLabel(riskAnalysis: RiskAnalysis): StatusLabel {
  const state = riskAnalysis.state as string;
  if (state === "COMPLETED") {
    switch (riskAnalysis.category as string | null) {
      case "HIGH": return { title: "Indikasi risiko tinggi", explanation: "Ditemukan pola yang sering muncul pada penipuan rekrutmen. Lihat indikator dan kutipan di bawah.", icon: "octagon-alert", tone: "danger" };
      case "MEDIUM": return { title: "Indikasi risiko sedang", explanation: "Ditemukan hal yang perlu diperiksa lebih lanjut.", icon: "circle-alert", tone: "warning" };
      case "LOW": return { title: "Indikasi risiko rendah", explanation: "Tidak ditemukan pola yang termasuk dalam daftar indikator. Risiko rendah tidak menjamin surat aman.", icon: "circle-dot", tone: "neutral" };
      default: return UNKNOWN_LABEL;
    }
  }
  if (state === "NOT_REQUESTED") return { title: "Tidak diminta", explanation: "Analisis isi surat tidak dipilih.", icon: "circle-minus", tone: "neutral" };
  if (state === "NOT_PERFORMED") {
    if (riskAnalysis.reason === "DOCUMENT_CONTENT_UNAVAILABLE") return { title: "Tidak dapat dianalisis", explanation: "Isi surat tidak dapat dibaca dari berkas (misalnya berkas tidak memuat teks yang dapat dikenali).", icon: "circle-minus", tone: "neutral" };
    return UNKNOWN_LABEL;
  }
  if (state === "UNAVAILABLE") {
    switch (riskAnalysis.reason as string | null) {
      case "AI_SERVICE_UNAVAILABLE":
      case "AI_TIMEOUT":
      case "AI_OUTPUT_INVALID":
        return { title: "Analisis sedang tidak tersedia", explanation: "Analisis AI gagal dijalankan. Ini bukan berarti risiko rendah. Coba lagi beberapa saat lagi.", icon: "triangle-alert", tone: "disruption" };
      case "AI_QUOTA_EXCEEDED":
        return { title: "Analisis sedang tidak tersedia", explanation: "Kapasitas layanan analisis sedang habis. Ini bukan berarti risiko rendah. Coba lagi nanti.", icon: "triangle-alert", tone: "disruption" };
      default: return UNKNOWN_LABEL;
    }
  }
  return UNKNOWN_LABEL;
}

// Label bahasa Indonesia untuk kode indikator taksonomi (PRD §9.6.3).
export function indicatorLabel(code: string): string {
  switch (code) {
    case "PAYMENT_REQUEST": return "Permintaan pembayaran kepada pelamar";
    case "SENSITIVE_DATA_REQUEST": return "Permintaan data atau akses sensitif";
    case "UNOFFICIAL_CONTACT": return "Kontak melalui kanal tidak resmi";
    case "URGENCY_PRESSURE": return "Tekanan waktu atau ancaman";
    case "IDENTITY_INCONSISTENCY": return "Informasi perusahaan atau penawaran tidak konsisten";
    case "UNREALISTIC_COMPENSATION": return "Kompensasi tidak wajar";
    case "VAGUE_JOB_DETAILS": return "Rincian pekerjaan tidak jelas";
    default: return "Indikator tidak dikenal";
  }
}
