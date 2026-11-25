// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-01.03, §9.8; SA §10.5 (API-01)
import type { ErrorDetail, RegisterIssuerRequest } from "@/lib/api/client";

// Nilai formulir pendaftaran perusahaan pada halaman onboarding.
export type CompanyFormValues = {
  companyName: string;
  registrationNumber: string;
  contactEmail: string;
};

// Peta pesan kesalahan validasi per field formulir perusahaan.
export type CompanyFieldErrors = Partial<Record<keyof CompanyFormValues, string>>;

// Pola karakter yang diizinkan untuk nomor registrasi perusahaan (PRD FR-01.03).
const REGISTRATION_NUMBER_PATTERN = /^[A-Za-z0-9./-]+$/;

// Pola email dasar yang tetap mengizinkan domain sintetis seperti .test.
const CONTACT_EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// Menormalisasi input formulir sebelum dikirim ke API-01 POST /api/v1/issuers.
export function normalizeCompanyPayload(values: CompanyFormValues): RegisterIssuerRequest {
  return {
    companyName: values.companyName.trim(),
    registrationNumber: values.registrationNumber.trim(),
    contactEmail: values.contactEmail.trim(),
  };
}

// Menghitung panjang string berdasarkan jumlah Unicode codepoint agar selaras dengan len() Python/Pydantic.
function unicodeLength(value: string): number {
  return [...value].length;
}

// Memvalidasi seluruh field formulir registrasi perusahaan di sisi klien.
export function validateCompanyForm(values: CompanyFormValues): CompanyFieldErrors {
  const errors: CompanyFieldErrors = {};
  const companyName = values.companyName.trim();
  const registrationNumber = values.registrationNumber.trim();
  const contactEmail = values.contactEmail.trim();
  const companyNameLength = unicodeLength(companyName);
  const registrationNumberLength = unicodeLength(registrationNumber);

  if (companyNameLength === 0) {
    errors.companyName = "Nama perusahaan wajib diisi.";
  } else if (companyNameLength < 3 || companyNameLength > 120) {
    errors.companyName = "Nama perusahaan harus terdiri dari 3 hingga 120 karakter.";
  }

  if (registrationNumberLength === 0) {
    errors.registrationNumber = "Nomor registrasi perusahaan wajib diisi.";
  } else if (registrationNumberLength < 3 || registrationNumberLength > 40) {
    errors.registrationNumber = "Nomor registrasi harus terdiri dari 3 hingga 40 karakter.";
  } else if (!REGISTRATION_NUMBER_PATTERN.test(registrationNumber)) {
    errors.registrationNumber =
      "Nomor registrasi hanya boleh berisi huruf, angka, titik (.), garis miring (/), atau tanda hubung (-).";
  }

  if (contactEmail.length === 0) {
    errors.contactEmail = "Email kontak perusahaan wajib diisi.";
  } else if (!CONTACT_EMAIL_PATTERN.test(contactEmail)) {
    errors.contactEmail = "Format email kontak tidak valid.";
  }

  return errors;
}

// Menerjemahkan nama field dari detail error backend ke key formulir lokal.
function resolveFormField(rawField: string): keyof CompanyFormValues | null {
  const normalized = rawField.replace(/^body\./, "").trim();
  if (normalized === "companyName" || normalized === "company_name") {
    return "companyName";
  }
  if (normalized === "registrationNumber" || normalized === "registration_number") {
    return "registrationNumber";
  }
  if (normalized === "contactEmail" || normalized === "contact_email") {
    return "contactEmail";
  }
  return null;
}

// Menerjemahkan kode issue validasi backend menjadi pesan berbahasa Indonesia per field.
function formatFieldIssue(field: keyof CompanyFormValues, issue: string): string {
  const lowerIssue = issue.toLowerCase();
  if (field === "companyName") {
    if (lowerIssue.includes("short") || lowerIssue.includes("long")) {
      return "Nama perusahaan harus terdiri dari 3 hingga 120 karakter.";
    }
    if (lowerIssue.includes("missing")) {
      return "Nama perusahaan wajib diisi.";
    }
    return "Nama perusahaan tidak valid.";
  }

  if (field === "registrationNumber") {
    if (lowerIssue.includes("short") || lowerIssue.includes("long")) {
      return "Nomor registrasi harus terdiri dari 3 hingga 40 karakter.";
    }
    if (lowerIssue.includes("pattern")) {
      return "Nomor registrasi hanya boleh berisi huruf, angka, titik (.), garis miring (/), atau tanda hubung (-).";
    }
    if (lowerIssue.includes("missing")) {
      return "Nomor registrasi perusahaan wajib diisi.";
    }
    return "Nomor registrasi perusahaan tidak valid.";
  }

  if (lowerIssue.includes("missing")) {
    return "Email kontak perusahaan wajib diisi.";
  }
  return "Format email kontak tidak valid.";
}

// Memetakan array error.details dari respons VALIDATION_ERROR ke pesan per field.
export function mapValidationDetailsToFieldErrors(
  details: readonly ErrorDetail[],
): CompanyFieldErrors {
  const fieldErrors: CompanyFieldErrors = {};
  for (const detail of details) {
    const field = resolveFormField(detail.field);
    if (field && !fieldErrors[field]) {
      fieldErrors[field] = formatFieldIssue(field, detail.issue);
    }
  }
  return fieldErrors;
}
