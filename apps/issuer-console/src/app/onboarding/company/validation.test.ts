// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-01.03, §9.8; SA §10.5 (API-01)
import { describe, expect, it } from "vitest";
import { api01RegisterIssuerRequest } from "@/fixtures/api";
import {
  mapValidationDetailsToFieldErrors,
  normalizeCompanyPayload,
  validateCompanyForm,
} from "./validation";

describe("validasi formulir registrasi perusahaan", () => {
  it("menerima payload valid dari fixture API-01 termasuk email domain .test", () => {
    const errors = validateCompanyForm(api01RegisterIssuerRequest);
    expect(errors).toEqual({});
  });

  it("menolak seluruh field kosong", () => {
    const errors = validateCompanyForm({
      companyName: "   ",
      registrationNumber: "",
      contactEmail: " ",
    });
    expect(errors.companyName).toBeDefined();
    expect(errors.registrationNumber).toBeDefined();
    expect(errors.contactEmail).toBeDefined();
  });

  it("menolak panjang companyName di luar rentang 3-120 karakter", () => {
    expect(
      validateCompanyForm({
        ...api01RegisterIssuerRequest,
        companyName: "PT",
      }).companyName,
    ).toBeDefined();

    expect(
      validateCompanyForm({
        ...api01RegisterIssuerRequest,
        companyName: "A".repeat(121),
      }).companyName,
    ).toBeDefined();
  });

  it("menghitung panjang companyName berdasarkan Unicode codepoint untuk karakter non-BMP", () => {
    const exact120WithEmoji = `${"A".repeat(119)}🏢`;
    expect(exact120WithEmoji.length).toBe(121);
    expect([...exact120WithEmoji].length).toBe(120);
    expect(
      validateCompanyForm({
        ...api01RegisterIssuerRequest,
        companyName: exact120WithEmoji,
      }).companyName,
    ).toBeUndefined();

    const over120WithEmoji = `${"A".repeat(120)}🏢`;
    expect([...over120WithEmoji].length).toBe(121);
    expect(
      validateCompanyForm({
        ...api01RegisterIssuerRequest,
        companyName: over120WithEmoji,
      }).companyName,
    ).toBeDefined();

    const twoCodepointsWithEmoji = "A🏢";
    expect(twoCodepointsWithEmoji.length).toBe(3);
    expect([...twoCodepointsWithEmoji].length).toBe(2);
    expect(
      validateCompanyForm({
        ...api01RegisterIssuerRequest,
        companyName: twoCodepointsWithEmoji,
      }).companyName,
    ).toBeDefined();
  });

  it("menolak registrationNumber dengan panjang tidak valid atau karakter terlarang", () => {
    expect(
      validateCompanyForm({
        ...api01RegisterIssuerRequest,
        registrationNumber: "AB",
      }).registrationNumber,
    ).toBeDefined();

    expect(
      validateCompanyForm({
        ...api01RegisterIssuerRequest,
        registrationNumber: "R".repeat(41),
      }).registrationNumber,
    ).toBeDefined();

    expect(
      validateCompanyForm({
        ...api01RegisterIssuerRequest,
        registrationNumber: "REG DEMO@101",
      }).registrationNumber,
    ).toBeDefined();

    expect(
      validateCompanyForm({
        ...api01RegisterIssuerRequest,
        registrationNumber: "REG.2026/DEMO-101",
      }).registrationNumber,
    ).toBeUndefined();
  });

  it("menolak format contactEmail yang tidak valid", () => {
    expect(
      validateCompanyForm({
        ...api01RegisterIssuerRequest,
        contactEmail: "bukan-email",
      }).contactEmail,
    ).toBeDefined();

    expect(
      validateCompanyForm({
        ...api01RegisterIssuerRequest,
        contactEmail: "hr@contoh",
      }).contactEmail,
    ).toBeDefined();
  });

  it("menormalisasi spasi berlebih pada payload sebelum dikirim", () => {
    expect(
      normalizeCompanyPayload({
        companyName: "  PT Contoh Rekrutmen  ",
        registrationNumber: "  REG-DEMO-101 ",
        contactEmail: " hr@contoh.test ",
      }),
    ).toEqual(api01RegisterIssuerRequest);
  });

  it("memetakan detail VALIDATION_ERROR ke pesan per field", () => {
    const mapped = mapValidationDetailsToFieldErrors([
      { field: "companyName", issue: "string_too_short" },
      { field: "registrationNumber", issue: "string_pattern_mismatch" },
      { field: "contactEmail", issue: "value_error" },
      { field: "unknownField", issue: "value_error" },
    ]);

    expect(mapped.companyName).toContain("3 hingga 120");
    expect(mapped.registrationNumber).toContain("huruf, angka");
    expect(mapped.contactEmail).toContain("email");
    expect(Object.keys(mapped)).toHaveLength(3);
  });
});
