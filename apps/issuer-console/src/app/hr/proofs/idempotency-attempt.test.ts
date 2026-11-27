// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-03.05, FR-04.05, §9.8; SA §10.3, §10.6 (API-04, API-06)
import { describe, expect, it } from "vitest";
import {
  EMPTY_ATTEMPT,
  UNCERTAIN_ISSUE_MESSAGE,
  UNCERTAIN_REVOKE_MESSAGE,
  applySubmitOutcome,
  attemptErrorMessage,
  canStartNewAttempt,
  isAttemptInputLocked,
  isRegistryWriteFailure,
  mayHaveBeenRecorded,
  resolveSubmitKey,
  startAttempt,
} from "./idempotency-attempt";

// Generator kunci deterministik agar urutan kunci dapat diperiksa.
function sequentialKeys(): () => string {
  let n = 0;
  return () => `key-${++n}`;
}

describe("logika Idempotency-Key upaya penerbitan/pencabutan", () => {
  it("membuat kunci baru saat berkas dipilih dan memakainya ulang saat retry", () => {
    const generate = sequentialKeys();
    const attempt = startAttempt(generate);
    expect(attempt).toEqual({ key: "key-1", locked: false });

    const firstKey = resolveSubmitKey(attempt, generate);
    const afterFailure = applySubmitOutcome(firstKey, {
      status: 503,
      code: "REGISTRY_UNAVAILABLE",
      canRetrySameKey: true,
      requiresResetKey: false,
    });
    expect(afterFailure).toEqual({ key: "key-1", locked: true });
    expect(resolveSubmitKey(afterFailure, generate)).toBe("key-1");

    expect(resolveSubmitKey(EMPTY_ATTEMPT, generate)).toBe("key-2");
  });

  it("membuka kunci input setelah sukses atau IDEMPOTENCY_KEY_CONFLICT lalu reset memberi kunci baru", () => {
    const generate = sequentialKeys();
    const previous = startAttempt(generate);
    expect(applySubmitOutcome(previous.key, null)).toEqual({ key: previous.key, locked: false });

    const conflict = applySubmitOutcome(previous.key, {
      status: 409,
      code: "IDEMPOTENCY_KEY_CONFLICT",
      canRetrySameKey: false,
      requiresResetKey: true,
    });
    expect(conflict.locked).toBe(false);
    expect(startAttempt(generate).key).not.toBe(previous.key);
  });

  it("mengunci input selama request berjalan atau upaya menunggu retry", () => {
    expect(isAttemptInputLocked({ key: "k", locked: false }, false)).toBe(false);
    expect(isAttemptInputLocked({ key: "k", locked: false }, true)).toBe(true);
    expect(isAttemptInputLocked({ key: "k", locked: true }, false)).toBe(true);
  });

  it("hanya menawarkan 'Mulai ulang upaya baru' untuk penolakan 4xx yang pasti", () => {
    // Mungkin sudah tercatat: gangguan jaringan, semua 5xx, dan gagal tulis registry → hanya "Coba lagi".
    const uncertain = [
      { status: 0, code: "NETWORK_ERROR" },
      { status: 503, code: "REGISTRY_UNAVAILABLE" },
      { status: 503, code: "REGISTRY_TRANSACTION_FAILED" },
      { status: 500, code: "INTERNAL_ERROR" },
      { status: 502, code: "UNKNOWN_UPSTREAM" },
    ];
    for (const error of uncertain) {
      expect(mayHaveBeenRecorded(error)).toBe(true);
      expect(canStartNewAttempt({ ...error, canRetrySameKey: true, requiresResetKey: false })).toBe(false);
    }
    // Penolakan pasti 4xx (validasi berkas, duplikat aktif): upaya baru aman.
    for (const error of [
      { status: 400, code: "UNSUPPORTED_MEDIA_TYPE" },
      { status: 413, code: "FILE_TOO_LARGE" },
      { status: 409, code: "DUPLICATE_ACTIVE_DOCUMENT" },
    ]) {
      expect(mayHaveBeenRecorded(error)).toBe(false);
      expect(canStartNewAttempt({ ...error, canRetrySameKey: false, requiresResetKey: false })).toBe(true);
    }
    // Konflik kunci punya tombol reset sendiri.
    expect(
      canStartNewAttempt({
        status: 409,
        code: "IDEMPOTENCY_KEY_CONFLICT",
        canRetrySameKey: false,
        requiresResetKey: true,
      }),
    ).toBe(false);
    expect(isRegistryWriteFailure("REGISTRY_UNAVAILABLE")).toBe(true);
    expect(isRegistryWriteFailure("DUPLICATE_ACTIVE_DOCUMENT")).toBe(false);
  });

  it("menampilkan satu pesan netral untuk hasil yang belum pasti, selain itu pesan API", () => {
    const registryFailure = {
      status: 503,
      code: "REGISTRY_TRANSACTION_FAILED",
      message: "Pencatatan ke registry gagal. Tidak ada perubahan yang tersimpan. Coba lagi.",
    };
    expect(attemptErrorMessage(registryFailure, UNCERTAIN_ISSUE_MESSAGE)).toBe(UNCERTAIN_ISSUE_MESSAGE);
    expect(attemptErrorMessage(registryFailure, UNCERTAIN_REVOKE_MESSAGE)).toBe(UNCERTAIN_REVOKE_MESSAGE);
    expect(attemptErrorMessage({ status: 0, code: "NETWORK_ERROR", message: "x" }, UNCERTAIN_ISSUE_MESSAGE)).toBe(
      UNCERTAIN_ISSUE_MESSAGE,
    );
    // Pesan netral tidak menyatakan "tidak ada perubahan" sehingga tidak bertentangan dengan kemungkinan tercatat.
    expect(UNCERTAIN_ISSUE_MESSAGE).not.toMatch(/tidak ada perubahan/i);
    expect(UNCERTAIN_REVOKE_MESSAGE).not.toMatch(/tidak ada perubahan/i);
    const definite = { status: 409, code: "DUPLICATE_ACTIVE_DOCUMENT", message: "Berkas yang sama sudah memiliki bukti aktif." };
    expect(attemptErrorMessage(definite, UNCERTAIN_ISSUE_MESSAGE)).toBe(definite.message);
  });
});
