// Owner: Pash (PIC 4) | Status: COMPLETE | Ref: PRD FR-02.02–FR-02.06, FR-02.08, §9.8
import { describe, expect, it } from "vitest";
import {
  afterSubmit,
  buildVerifyRequest,
  canToggleRisk,
  DEFAULT_MAX_UPLOAD_BYTES,
  initialFormState,
  shouldIncludeRisk,
  validatePdfFile,
  validateSubmission,
  withFile,
  withIncludeRisk,
  type VerifyFormState,
} from "./form";

const CODE = "LTR-7K3M-9QX2-H4TD";
const pdf = new File(["%PDF-test"], "offer.pdf", { type: "application/pdf" });

// Menyusun state formulir dengan nilai bawaan Mode Dengan Kode.
function state(overrides: Partial<VerifyFormState> = {}): VerifyFormState {
  return { ...initialFormState(), ...overrides };
}

describe("gating formulir verifikasi", () => {
  // FR-02.02 AC-02/AC-03: mode awal dengan kode; ganti mode mengosongkan input.
  it("memulai dari Mode Dengan Kode dan mengosongkan input saat ganti mode", () => {
    expect(initialFormState()).toEqual({ mode: "REFERENCE_CHECK", referenceCode: "", file: null, includeRisk: false, consent: false });
    expect(initialFormState("AI_ONLY")).toEqual({ mode: "AI_ONLY", referenceCode: "", file: null, includeRisk: true, consent: false });
  });

  // FR-02.04 AC-02: AI selalu aktif pada Mode Tanpa Kode dan tidak dapat dinonaktifkan.
  it("mengaktifkan AI permanen pada Mode Tanpa Kode", () => {
    const aiOnly = initialFormState("AI_ONLY");
    expect(shouldIncludeRisk(aiOnly)).toBe(true);
    expect(shouldIncludeRisk(withIncludeRisk(aiOnly, false))).toBe(true);
    expect(shouldIncludeRisk(withFile({ ...aiOnly, file: pdf }, null))).toBe(true);
  });

  // §9.5 Disabled: pilihan AI pada Mode Dengan Kode nonaktif tanpa berkas.
  it("menonaktifkan pilihan AI tanpa berkas dan meresetnya saat berkas dihapus", () => {
    expect(canToggleRisk(state())).toBe(false);
    expect(withIncludeRisk(state(), true).includeRisk).toBe(false);
    const withPdf = withIncludeRisk(withFile(state(), pdf), true);
    expect(canToggleRisk(withPdf)).toBe(true);
    expect(withPdf.includeRisk).toBe(true);
    const removed = withFile({ ...withPdf, consent: true }, null);
    expect(removed).toMatchObject({ file: null, includeRisk: false, consent: false });
  });

  // FR-02.06 AC-01/AC-03: persetujuan wajib dan direset setiap pengiriman atau perubahan pilihan.
  it("mewajibkan persetujuan dan mereset persetujuan setelah pengiriman", () => {
    const ready = state({ referenceCode: CODE, file: pdf, includeRisk: true });
    expect(validateSubmission(ready)).toBe("Setujui pemrosesan AI sebelum mengirim surat untuk dianalisis.");
    expect(validateSubmission({ ...ready, consent: true })).toBeNull();
    expect(withIncludeRisk({ ...ready, consent: true }, true).consent).toBe(false);
    expect(afterSubmit({ ...ready, consent: true }).consent).toBe(false);
  });

  // FR-02.08/§9.5: masukan tetap tersedia setelah error agar pemohon dapat memperbaiki dan mengirim ulang.
  it("mempertahankan kode dan berkas setelah pengiriman", () => {
    const submitted = afterSubmit(state({ referenceCode: CODE, file: pdf, includeRisk: true, consent: true }));
    expect(submitted).toMatchObject({ referenceCode: CODE, file: pdf, includeRisk: true });
  });

  // FR-02.03 AC-01 dan §9.8: pesan validasi sesuai PRD.
  it("memakai pesan PRD untuk kode tidak valid dan analisis AI tanpa berkas", () => {
    expect(validateSubmission(state())).toBe("Format kode referensi tidak valid. Periksa kembali kode pada surat Anda.");
    expect(validateSubmission(state({ referenceCode: "LTR-1234" }))).toBe("Format kode referensi tidak valid. Periksa kembali kode pada surat Anda.");
    expect(validateSubmission(state({ referenceCode: CODE }))).toBeNull();
    expect(validateSubmission({ ...initialFormState("AI_ONLY"), consent: true })).toBe("Masukkan kode referensi atau unggah berkas PDF untuk dianalisis.");
  });

  // FR-02.04/SA §10.7: kode referensi tidak dikirim pada AI_ONLY; aiConsent hanya ikut bila AI diminta.
  it("menyusun multipart tanpa kode referensi pada AI_ONLY", () => {
    const aiOnly = buildVerifyRequest({ ...initialFormState("AI_ONLY"), referenceCode: CODE, file: pdf, consent: true });
    expect(aiOnly.has("referenceCode")).toBe(false);
    expect(aiOnly.get("includeRisk")).toBe("true");
    expect(aiOnly.get("aiConsent")).toBe("true");
    expect((aiOnly.get("file") as File).name).toBe("offer.pdf");

    const codeOnly = buildVerifyRequest(state({ referenceCode: " ltr-7k3m-9qx2-h4td " }));
    expect([...codeOnly.keys()]).toEqual(["includeRisk", "referenceCode"]);
    expect(codeOnly.get("includeRisk")).toBe("false");
    expect(codeOnly.get("referenceCode")).toBe(CODE);
  });

  // FR-02.05: hanya satu PDF tidak kosong di bawah batas bersama yang diterima.
  it("memvalidasi tipe, isi, dan ukuran berkas dengan batas bersama", () => {
    expect(DEFAULT_MAX_UPLOAD_BYTES).toBe(5 * 1024 * 1024);
    expect(validatePdfFile(pdf)).toBeNull();
    expect(validatePdfFile(new File(["x"], "offer.docx", { type: "application/msword" }))).toBe("Berkas harus berformat PDF.");
    expect(validatePdfFile(new File([], "empty.pdf", { type: "application/pdf" }))).toBe("Berkas kosong tidak dapat diproses.");
    expect(validatePdfFile(new File([new Uint8Array(DEFAULT_MAX_UPLOAD_BYTES + 1)], "big.pdf", { type: "application/pdf" }))).toBe(
      "Ukuran berkas melebihi batas yang diizinkan.",
    );
    expect(validatePdfFile(new File([new Uint8Array(DEFAULT_MAX_UPLOAD_BYTES)], "max.pdf", { type: "application/pdf" }))).toBeNull();
  });
});
