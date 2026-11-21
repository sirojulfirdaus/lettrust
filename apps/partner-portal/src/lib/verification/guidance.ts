// Owner: Pash (PIC 4) | Status: STUB | Ref: PRD §9.7, FR-02.10; SA §11.3.3
// TODO: Terapkan aturan G-01–G-10 sebagai fungsi murni; tampilkan seluruh aturan yang berlaku urut prioritas; tanpa kata asli/palsu/aman/penipuan.
import type { VerificationResponse } from "@/lib/api/types";

// Identitas aturan panduan PRD §9.7.
export type GuidanceId = "G-01" | "G-02" | "G-03" | "G-04" | "G-05" | "G-06" | "G-07" | "G-08" | "G-09" | "G-10";

// Satu butir panel Langkah yang Disarankan.
export type GuidanceItem = {
  id: GuidanceId;
  text: string;
};

// Menyusun panduan tindak lanjut dari kombinasi status hasil verifikasi.
export function buildGuidance(_result: VerificationResponse): GuidanceItem[] {
  throw new Error("NOT_IMPLEMENTED");
}
