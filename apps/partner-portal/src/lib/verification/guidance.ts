// Owner: Pash (PIC 4) | Status: COMPLETE | Ref: PRD §9.7, FR-02.10; SA §11.3.3
import type { VerificationResponse } from "@/lib/api/types";

// Identitas aturan panduan PRD §9.7.
export type GuidanceId = "G-01" | "G-02" | "G-03" | "G-04" | "G-05" | "G-06" | "G-07" | "G-08" | "G-09" | "G-10";

// Satu butir panel Langkah yang Disarankan.
export type GuidanceItem = {
  id: GuidanceId;
  text: string;
};

// Menyusun panduan tindak lanjut dari kombinasi status hasil verifikasi.
export function buildGuidance(result: VerificationResponse): GuidanceItem[] {
  const { proofCheck, integrityCheck, riskAnalysis, mode } = result;
  const guidance: GuidanceItem[] = [
    { id: "G-01", text: "Jangan melakukan pembayaran atau memberikan data sensitif untuk proses rekrutmen sebelum memastikan melalui kanal resmi perusahaan." },
  ];

  if (riskAnalysis.state === "COMPLETED" && riskAnalysis.category === "HIGH") {
    guidance.push({ id: "G-02", text: "Hentikan proses dan konfirmasi langsung kepada perusahaan melalui situs atau kontak resmi yang Anda cari sendiri, bukan kontak di dalam surat." });
  }
  if (proofCheck.lifecycleStatus === "REVOKED") {
    guidance.push({ id: "G-03", text: "Penawaran ini telah dicabut oleh penerbit. Konfirmasikan status penawaran kepada perusahaan sebelum melanjutkan." });
  }
  if (integrityCheck.result === "MISMATCH") {
    guidance.push({ id: "G-04", text: "Mintalah salinan asli surat melalui kanal resmi perusahaan dan periksa kembali." });
  }
  if (proofCheck.lookup === "FOUND" && integrityCheck.result === "NOT_CHECKED" && integrityCheck.reason === "NO_FILE") {
    guidance.push({ id: "G-05", text: "Unggah berkas PDF surat Anda untuk memastikan berkas sama dengan yang dicatat, dan pastikan nama penerbit sama dengan nama perusahaan pada surat." });
  }
  if (proofCheck.lookup === "NOT_FOUND") {
    guidance.push({ id: "G-06", text: "Periksa kembali penulisan kode. Apabila kode sudah benar, konfirmasikan keaslian surat melalui kanal resmi perusahaan." });
  }
  if (proofCheck.lookup === "UNAVAILABLE" || riskAnalysis.state === "UNAVAILABLE") {
    guidance.push({ id: "G-07", text: "Sebagian pemeriksaan gagal karena gangguan. Coba lagi beberapa saat lagi." });
  }
  if (mode === "AI_ONLY") {
    guidance.push({ id: "G-08", text: "Hasil ini hanya menilai isi surat. Apabila perusahaan menyatakan menggunakan Lettrust, mintalah kode referensi untuk memeriksa bukti penerbitan." });
  }
  if (riskAnalysis.state === "COMPLETED" && riskAnalysis.category === "MEDIUM") {
    guidance.push({ id: "G-09", text: "Periksa hal yang ditandai dan konfirmasikan kepada perusahaan melalui kanal resmi." });
  }
  if (proofCheck.lookup === "FOUND" && proofCheck.lifecycleStatus === "ACTIVE" && integrityCheck.result === "MATCH" && riskAnalysis.state === "COMPLETED" && riskAnalysis.category === "LOW") {
    guidance.push({ id: "G-10", text: "Bukti tercatat dan berkas identik. Tetap waspada terhadap permintaan yang tidak wajar dan konfirmasikan bila ragu." });
  }
  if (proofCheck.lookup === "FOUND" && proofCheck.lifecycleStatus === "ACTIVE" && integrityCheck.result === "MATCH" && riskAnalysis.state === "NOT_REQUESTED") {
    guidance.push({ id: "G-10", text: "Bukti tercatat dan berkas identik. Tetap waspada terhadap permintaan yang tidak wajar dan konfirmasikan bila ragu." });
  }
  return guidance;
}
