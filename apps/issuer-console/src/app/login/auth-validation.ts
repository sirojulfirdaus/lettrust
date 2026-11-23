// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-01.01, FR-01.02, §9.8; SA §10.5 (S-01, S-02)
import type { ErrorDetail } from "@/lib/api/client";

export type LoginFieldErrors = {
  email?: string;
  password?: string;
};

export type RegisterFieldErrors = {
  displayName?: string;
  email?: string;
  password?: string;
};

// Regex email dasar yang mengizinkan domain sintetis seperti .test (sesuai D-06).
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// Menghitung jumlah karakter Unicode (code points) agar selaras dengan len() Python di backend.
export function countCodePoints(value: string): number {
  return [...value].length;
}

// Memvalidasi input formulir login sebelum dikirim ke S-02.
export function validateLoginForm(email: string, password: string): LoginFieldErrors {
  const errors: LoginFieldErrors = {};
  const trimmedEmail = email.trim();

  if (!trimmedEmail) {
    errors.email = "Email wajib diisi.";
  } else if (!EMAIL_PATTERN.test(trimmedEmail)) {
    errors.email = "Format email tidak valid.";
  }

  if (!password) {
    errors.password = "Password wajib diisi.";
  }

  return errors;
}

// Memvalidasi input formulir registrasi akun HR sesuai aturan S-01 (SA §10.5).
export function validateRegisterForm(
  displayName: string,
  email: string,
  password: string,
): RegisterFieldErrors {
  const errors: RegisterFieldErrors = {};
  const trimmedName = displayName.trim();
  const trimmedEmail = email.trim();
  const nameLength = countCodePoints(trimmedName);
  const passwordLength = countCodePoints(password);

  if (nameLength < 2) {
    errors.displayName = "Nama lengkap minimal 2 karakter.";
  } else if (nameLength > 80) {
    errors.displayName = "Nama lengkap maksimal 80 karakter.";
  }

  if (!trimmedEmail) {
    errors.email = "Email wajib diisi.";
  } else if (!EMAIL_PATTERN.test(trimmedEmail)) {
    errors.email = "Format email tidak valid.";
  }

  if (passwordLength < 8) {
    errors.password = "Password minimal 8 karakter.";
  } else if (passwordLength > 128) {
    errors.password = "Password maksimal 128 karakter.";
  }

  return errors;
}

// Memetakan kode issue VALIDATION_ERROR dari backend ke pesan bahasa Indonesia yang mudah dipahami.
function formatIssueMessage(field: string, issue: string): string {
  if (field === "displayName") {
    if (issue.includes("short") || issue.includes("missing")) {
      return "Nama lengkap minimal 2 karakter.";
    }
    if (issue.includes("long")) {
      return "Nama lengkap maksimal 80 karakter.";
    }
    return "Nama lengkap tidak valid.";
  }
  if (field === "email") {
    return "Format email tidak valid.";
  }
  if (field === "password") {
    if (issue.includes("short") || issue.includes("missing")) {
      return "Password minimal 8 karakter.";
    }
    if (issue.includes("long")) {
      return "Password maksimal 128 karakter.";
    }
    return "Password tidak valid.";
  }
  return "Nilai field tidak valid.";
}

// Mengonversi daftar ErrorDetail backend menjadi peta error per field formulir registrasi/login.
export function mapValidationDetails(
  details: readonly ErrorDetail[],
): RegisterFieldErrors {
  const mapped: RegisterFieldErrors = {};
  for (const item of details) {
    if (item.field === "displayName" || item.field === "email" || item.field === "password") {
      mapped[item.field] = formatIssueMessage(item.field, item.issue);
    }
  }
  return mapped;
}
