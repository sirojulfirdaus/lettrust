// Owner: Pash (PIC 4) | Status: STUB | Ref: SA §6.3.1; PRD FR-02.03/AC-02, AC-03
// TODO: Normalisasi (trim, kapital, hapus spasi/tanda hubung, pisah prefiks LTR, O->0, I/L->1, susun LTR-XXXX-XXXX-XXXX) dan validasi regex untuk umpan balik cepat; backend tetap memvalidasi.

// Contoh format kode yang ditampilkan di form (SA §10.6).
export const REFERENCE_CODE_EXAMPLE = "LTR-7K3M-9QX2-H4TD";

// Regex kode setelah normalisasi (alfabet Crockford Base32, SA §6.3.1).
export const REFERENCE_CODE_PATTERN = /^LTR-[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{4}$/;

// Menormalisasi input kode; mengembalikan null bila input kosong atau hanya spasi.
export function normalizeReferenceCode(_input: string): string | null {
  throw new Error("NOT_IMPLEMENTED");
}

// Memeriksa apakah kode hasil normalisasi sesuai format.
export function isValidReferenceCode(_code: string): boolean {
  throw new Error("NOT_IMPLEMENTED");
}
