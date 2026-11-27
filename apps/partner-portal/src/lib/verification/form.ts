// Owner: Pash (PIC 4) | Status: COMPLETE | Ref: PRD FR-02.02–FR-02.06, FR-02.08, §9.8; SA §11.3
import type { VerificationMode } from "@/components/verification/mode-selector";
import { isValidReferenceCode, normalizeReferenceCode } from "@/lib/verification/reference-code";

// Batas default ukuran berkas (5 MiB, sama dengan backend); modul ini aman dipakai browser maupun server.
export const DEFAULT_MAX_UPLOAD_BYTES = 5 * 1024 * 1024;

const PDF_MIME = "application/pdf";

// Masukan formulir pemeriksaan yang memengaruhi validasi dan isi permintaan.
export type VerifyFormState = {
  mode: VerificationMode;
  referenceCode: string;
  file: File | null;
  includeRisk: boolean;
  consent: boolean;
};

// Membuat masukan kosong untuk sebuah mode; dipakai saat awal, ganti mode, dan "Periksa surat lain".
export function initialFormState(mode: VerificationMode = "REFERENCE_CHECK"): VerifyFormState {
  return { mode, referenceCode: "", file: null, includeRisk: mode === "AI_ONLY", consent: false };
}

// Menentukan apakah analisis AI diminta; selalu aktif pada Mode Tanpa Kode.
export function shouldIncludeRisk(state: VerifyFormState): boolean {
  return state.mode === "AI_ONLY" || state.includeRisk;
}

// Pilihan analisis AI pada Mode Dengan Kode hanya dapat diaktifkan setelah PDF dipilih.
export function canToggleRisk(state: VerifyFormState): boolean {
  return state.file !== null;
}

// Mengganti atau menghapus berkas; pilihan AI dan persetujuan direset karena berkas berubah.
export function withFile(state: VerifyFormState, file: File | null): VerifyFormState {
  return { ...state, file, includeRisk: state.mode === "AI_ONLY", consent: false };
}

// Mengubah pilihan AI; persetujuan harus diberikan ulang dan pilihan ditolak bila belum ada berkas.
export function withIncludeRisk(state: VerifyFormState, includeRisk: boolean): VerifyFormState {
  if (state.mode === "AI_ONLY") return state;
  return { ...state, includeRisk: includeRisk && canToggleRisk(state), consent: false };
}

// Menyiapkan state setelah satu pengiriman: masukan dipertahankan, persetujuan direset.
export function afterSubmit(state: VerifyFormState): VerifyFormState {
  return { ...state, consent: false };
}

// Memvalidasi satu berkas PDF di browser; mengembalikan pesan alasan penolakan atau null.
export function validatePdfFile(file: File, maxBytes: number = DEFAULT_MAX_UPLOAD_BYTES): string | null {
  if (!file.name.toLowerCase().endsWith(".pdf") || (file.type && file.type !== PDF_MIME)) return "Berkas harus berformat PDF.";
  if (file.size === 0) return "Berkas kosong tidak dapat diproses.";
  if (file.size > maxBytes) return "Ukuran berkas melebihi batas yang diizinkan.";
  return null;
}

// Memeriksa kelengkapan masukan sebelum dikirim; mengembalikan pesan kesalahan atau null.
export function validateSubmission(state: VerifyFormState): string | null {
  const normalizedCode = normalizeReferenceCode(state.referenceCode);
  if (state.mode === "REFERENCE_CHECK" && (!normalizedCode || !isValidReferenceCode(normalizedCode))) {
    return "Format kode referensi tidak valid. Periksa kembali kode pada surat Anda.";
  }
  if (shouldIncludeRisk(state) && !state.file) return "Masukkan kode referensi atau unggah berkas PDF untuk dianalisis.";
  if (shouldIncludeRisk(state) && !state.consent) return "Setujui pemrosesan AI sebelum mengirim surat untuk dianalisis.";
  return null;
}

// Menyusun multipart untuk BFF portal; kode referensi tidak pernah dikirim pada Mode Tanpa Kode.
export function buildVerifyRequest(state: VerifyFormState): FormData {
  const formData = new FormData();
  const includeRisk = shouldIncludeRisk(state);
  formData.set("includeRisk", String(includeRisk));
  if (includeRisk) formData.set("aiConsent", String(state.consent));
  const normalizedCode = normalizeReferenceCode(state.referenceCode);
  if (state.mode === "REFERENCE_CHECK" && normalizedCode) formData.set("referenceCode", normalizedCode);
  if (state.file) formData.set("file", state.file, state.file.name);
  return formData;
}
