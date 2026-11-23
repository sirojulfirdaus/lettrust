// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-01.01, FR-01.02, §9.8; SA §10.5, §18.1
import { describe, expect, it } from "vitest";
import { errorValidationError } from "@/fixtures/api";
import {
  countCodePoints,
  mapValidationDetails,
  validateLoginForm,
  validateRegisterForm,
} from "./auth-validation";

describe("validasi formulir login dan registrasi", () => {
  it("menerima kredensial login valid termasuk domain .test", () => {
    expect(validateLoginForm("hr.sinar@lettrust.test", "rahasia-demo-123")).toEqual({});
  });

  it("menolak email kosong, format email salah, dan password kosong pada login", () => {
    expect(validateLoginForm("", "")).toEqual({
      email: "Email wajib diisi.",
      password: "Password wajib diisi.",
    });
    expect(validateLoginForm("bukan-email", "12345678")).toEqual({
      email: "Format email tidak valid.",
    });
  });

  it("memvalidasi panjang nama (2-80), email, dan password (8-128) pada registrasi", () => {
    expect(validateRegisterForm("Rina Demo", "rina@lettrust.test", "rahasia-demo-123")).toEqual({});
    expect(validateRegisterForm("A", "salah", "1234567")).toEqual({
      displayName: "Nama lengkap minimal 2 karakter.",
      email: "Format email tidak valid.",
      password: "Password minimal 8 karakter.",
    });
    expect(validateRegisterForm("A".repeat(81), "ok@lettrust.test", "x".repeat(129))).toEqual({
      displayName: "Nama lengkap maksimal 80 karakter.",
      password: "Password maksimal 128 karakter.",
    });
  });

  it("menghitung batas nama dan password dengan Unicode code points selaras backend Python", () => {
    // Empat emoji memiliki .length === 8 di UTF-16, tetapi hanya 4 code points.
    expect(countCodePoints("😀😀😀😀")).toBe(4);
    expect(validateRegisterForm("😀", "ok@lettrust.test", "😀😀😀😀")).toEqual({
      displayName: "Nama lengkap minimal 2 karakter.",
      password: "Password minimal 8 karakter.",
    });

    // Batas minimum dan maksimum tepat dengan karakter non-BMP harus diterima.
    expect(validateRegisterForm("😀😀", "ok@lettrust.test", "😀".repeat(8))).toEqual({});
    expect(
      validateRegisterForm(
        `${"a".repeat(79)}😀`,
        "ok@lettrust.test",
        `${"p".repeat(127)}😀`,
      ),
    ).toEqual({});

    // Melebihi batas maksimum tepat 1 code point harus ditolak.
    expect(
      validateRegisterForm(
        `${"a".repeat(80)}😀`,
        "ok@lettrust.test",
        `${"p".repeat(128)}😀`,
      ),
    ).toEqual({
      displayName: "Nama lengkap maksimal 80 karakter.",
      password: "Password maksimal 128 karakter.",
    });
  });

  it("memetakan details VALIDATION_ERROR dari fixture kontrak ke pesan per field", () => {
    const mapped = mapValidationDetails(errorValidationError.error.details ?? []);
    expect(mapped).toEqual({
      email: "Format email tidak valid.",
      password: "Password minimal 8 karakter.",
    });
  });
});
