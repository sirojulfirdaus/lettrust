// Owner: Pash (PIC 4) | Status: COMPLETE | Ref: SA §6.3.1; PRD FR-02.03/AC-02, AC-03

// Contoh format kode yang ditampilkan di form (SA §10.6).
export const REFERENCE_CODE_EXAMPLE = "LTR-7K3M-9QX2-H4TD";

// Regex kode setelah normalisasi (alfabet Crockford Base32, SA §6.3.1).
export const REFERENCE_CODE_PATTERN = /^LTR-[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{4}$/;

// Menormalisasi input kode; mengembalikan null bila input kosong atau hanya spasi.
export function normalizeReferenceCode(input: string): string | null {
  const trimmed = input.trim().toUpperCase();
  if (!trimmed) return null;
  let body = trimmed.replace(/[\s-]/g, "");
  if (body.startsWith("LTR")) body = body.slice(3);
  body = body.replace(/O/g, "0").replace(/[IL]/g, "1");
  return `LTR-${body.slice(0, 4)}-${body.slice(4, 8)}-${body.slice(8)}`;
}

// Memeriksa apakah kode hasil normalisasi sesuai format.
export function isValidReferenceCode(code: string): boolean {
  return REFERENCE_CODE_PATTERN.test(code);
}
