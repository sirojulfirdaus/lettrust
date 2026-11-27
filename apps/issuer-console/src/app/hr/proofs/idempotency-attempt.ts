// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-03.05, FR-04.05, §9.8; SA §10.3, §10.6 (API-04, API-06)
import { generateIdempotencyKey } from "./proofs-flow";

// Satu upaya penerbitan/pencabutan: kunci idempotensi aktif dan apakah input dikunci demi retry aman.
export type IdempotencyAttempt = { key: string; locked: boolean };

// Ringkasan error submit yang memengaruhi nasib kunci idempotensi.
export type AttemptError = { status: number; code: string; canRetrySameKey: boolean; requiresResetKey: boolean };

// Kegagalan tulis registry yang hasilnya bisa sudah tercatat (mis. timeout receipt); hanya aman diulang dengan kunci sama.
const REGISTRY_WRITE_FAILURE_CODES: ReadonlySet<string> = new Set([
  "REGISTRY_UNAVAILABLE",
  "REGISTRY_TRANSACTION_FAILED",
]);

// Upaya kosong sebelum berkas dipilih.
export const EMPTY_ATTEMPT: IdempotencyAttempt = { key: "", locked: false };

// Membuat upaya baru dengan kunci unik (dipakai saat berkas baru dipilih, reset konflik, atau dialog cabut dibuka).
export function startAttempt(generate: () => string = generateIdempotencyKey): IdempotencyAttempt {
  return { key: generate(), locked: false };
}

// Kunci yang dikirim: memakai ulang kunci upaya aktif, membuat baru hanya bila belum ada.
export function resolveSubmitKey(
  attempt: IdempotencyAttempt,
  generate: () => string = generateIdempotencyKey,
): string {
  return attempt.key || generate();
}

// Memperbarui upaya setelah hasil submit: error yang boleh diulang mengunci input dengan kunci yang sama.
export function applySubmitOutcome(key: string, error: AttemptError | null): IdempotencyAttempt {
  return { key, locked: error?.canRetrySameKey ?? false };
}

// Input upaya (berkas atau alasan) hanya boleh diubah saat tidak ada request berjalan dan upaya tidak terkunci.
export function isAttemptInputLocked(attempt: IdempotencyAttempt, isSubmitting: boolean): boolean {
  return isSubmitting || attempt.locked;
}

// Apakah kegagalan ini adalah gagal tulis registry yang perlu panduan "coba lagi dengan permintaan yang sama".
export function isRegistryWriteFailure(code: string): boolean {
  return REGISTRY_WRITE_FAILURE_CODES.has(code);
}

// Permintaan yang mungkin sudah tercatat walau respons gagal: gangguan jaringan (status 0), semua 5xx, dan gagal tulis
// registry. Satu-satunya jalan aman adalah "Coba lagi" dengan permintaan dan kunci idempotensi yang sama.
export function mayHaveBeenRecorded(error: Pick<AttemptError, "status" | "code">): boolean {
  return error.code === "NETWORK_ERROR" || error.status === 0 || error.status >= 500 || isRegistryWriteFailure(error.code);
}

// "Mulai ulang upaya baru" hanya untuk penolakan 4xx yang pasti (mis. validasi berkas, duplikat aktif); konflik kunci
// punya tombol reset sendiri. Kunci baru setelah kegagalan yang mungkin tercatat bisa menghasilkan bukti ganda.
export function canStartNewAttempt(error: AttemptError): boolean {
  return error.status >= 400 && error.status < 500 && !error.requiresResetKey && !mayHaveBeenRecorded(error);
}
