// @vitest-environment jsdom
// Owner: Pash (PIC 4) | Status: COMPLETE | Ref: PRD FR-02.02, FR-02.06, NFR-06 (aksesibilitas); SA §11.3
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { createElement } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CONSENT_REQUIRED_MESSAGE } from "@/lib/verification/form";
import { VerifyForm } from "./verify-form";

const CODE_MESSAGE = "Format kode referensi tidak valid. Periksa kembali kode pada surat Anda.";

// jsdom tidak menyediakan ResizeObserver yang dipakai Radix Checkbox; stub kosong cukup untuk render.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}

// Merender formulir dan mengembalikan elemen yang dipakai berulang.
function renderForm() {
  const fetchSpy = vi.fn();
  vi.stubGlobal("fetch", fetchSpy);
  vi.stubGlobal("ResizeObserver", ResizeObserverStub);
  const view = render(createElement(VerifyForm));
  const form = view.container.querySelector("form") as HTMLFormElement;
  return { form, fetchSpy };
}

// Memastikan sebuah elemen adalah live region yang diumumkan utuh.
function expectLiveRegion(element: HTMLElement) {
  expect(element.getAttribute("aria-live")).toBe("polite");
  expect(element.getAttribute("aria-atomic")).toBe("true");
}

describe("aksesibilitas pesan error inline formulir portal", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  // Live region kode selalu ada sebelum error agar perubahan isinya diumumkan pembaca layar.
  it("wadah pesan kode selalu ada dan kosong sebelum error", () => {
    renderForm();
    const region = document.getElementById("reference-error") as HTMLElement;
    expect(region).not.toBeNull();
    expectLiveRegion(region);
    expect(region.textContent).toBe("");
    const input = screen.getByLabelText("Kode referensi");
    expect(input.getAttribute("aria-invalid")).toBe("false");
    expect(input.getAttribute("aria-describedby")).toBe("reference-help");
  });

  // Kode kosong atau salah: pesan masuk live region, kolom aria-invalid, describedby mengarah ke pesan.
  it.each(["", "ABC-123"])("submit dengan kode %j mengumumkan pesan format kode", (value) => {
    const { form, fetchSpy } = renderForm();
    const input = screen.getByLabelText("Kode referensi");
    fireEvent.change(input, { target: { value } });
    fireEvent.submit(form);
    const region = document.getElementById("reference-error") as HTMLElement;
    expectLiveRegion(region);
    expect(region.textContent).toBe(CODE_MESSAGE);
    expect(input.getAttribute("aria-invalid")).toBe("true");
    expect(input.getAttribute("aria-describedby")?.split(" ")).toEqual(["reference-help", "reference-error"]);
    // Satu pesan visual: teks yang sama tidak muncul lagi di banner.
    expect(screen.getAllByText(CODE_MESSAGE)).toHaveLength(1);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  // Berkas bukan PDF: pesan berkas di live region, input berkas aria-invalid dan terhubung ke pesan.
  it("berkas tidak valid diumumkan lewat live region berkas", () => {
    renderForm();
    const region = document.getElementById("file-error") as HTMLElement;
    expectLiveRegion(region);
    expect(region.textContent).toBe("");
    const input = document.getElementById("offer-letter") as HTMLInputElement;
    const notPdf = new File(["bukan pdf"], "catatan.txt", { type: "text/plain" });
    fireEvent.change(input, { target: { files: [notPdf] } });
    expect(region.textContent).not.toBe("");
    expect(input.getAttribute("aria-invalid")).toBe("true");
    expect(input.getAttribute("aria-describedby")?.split(" ")).toContain("file-error");
  });

  // Persetujuan AI belum diberikan: banner alert selalu ada, kotak persetujuan aria-invalid dan terhubung ke banner.
  it("persetujuan AI yang belum diberikan ditandai dan diumumkan", () => {
    const { form, fetchSpy } = renderForm();
    const banner = document.getElementById("form-error") as HTMLElement;
    expect(banner.getAttribute("role")).toBe("alert");
    expect(banner.textContent).toBe("");
    fireEvent.change(screen.getByLabelText("Kode referensi"), { target: { value: "LTR-7K3M-9QX2-H4TD" } });
    const pdf = new File(["%PDF-1.4\n"], "surat.pdf", { type: "application/pdf" });
    fireEvent.change(document.getElementById("offer-letter") as HTMLInputElement, { target: { files: [pdf] } });
    fireEvent.click(screen.getByRole("checkbox", { name: /Analisis indikasi risiko dengan AI/ }));
    fireEvent.submit(form);
    expect(banner.textContent).toBe(CONSENT_REQUIRED_MESSAGE);
    expect(banner.getAttribute("aria-atomic")).toBe("true");
    const consent = screen.getByRole("checkbox", { name: /Saya menyetujui pemrosesan AI/ });
    expect(consent.getAttribute("aria-invalid")).toBe("true");
    expect(consent.getAttribute("aria-describedby")).toBe("form-error");
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
