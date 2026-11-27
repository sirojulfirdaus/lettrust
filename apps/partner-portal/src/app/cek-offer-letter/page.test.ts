// Owner: Pash (PIC 4) | Status: COMPLETE | Ref: PRD FR-02.07; SA §11.3.2, §14.2
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { DEFAULT_MAX_UPLOAD_BYTES } from "@/lib/verification/form";
import CheckOfferLetterPage, { dynamic } from "./page";

describe("CheckOfferLetterPage", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  // Label batas unggah mengikuti MAX_UPLOAD_BYTES server dan token tidak ikut ter-render.
  it("meneruskan batas unggah server ke formulir tanpa membocorkan token", () => {
    vi.stubEnv("MAX_UPLOAD_BYTES", String(10 * 1024 * 1024));
    vi.stubEnv("LETTRUST_PARTNER_TOKEN", "server-only-token");

    const html = renderToStaticMarkup(createElement(CheckOfferLetterPage));

    expect(html).toContain("PDF maksimal 10 MB");
    expect(html).not.toContain("server-only-token");
    expect(dynamic).toBe("force-dynamic");
  });

  // Tanpa MAX_UPLOAD_BYTES (kosong atau tidak di-set sama sekali), halaman tetap tampil dengan default yang sama dengan
  // backend (5.242.880 byte), bukan gagal render.
  it("memakai batas default backend saat env kosong atau tidak di-set", () => {
    expect(DEFAULT_MAX_UPLOAD_BYTES).toBe(5_242_880);
    vi.stubEnv("MAX_UPLOAD_BYTES", "");
    expect(renderToStaticMarkup(createElement(CheckOfferLetterPage))).toContain("PDF maksimal 5 MB");
    vi.stubEnv("MAX_UPLOAD_BYTES", undefined);
    expect(process.env.MAX_UPLOAD_BYTES).toBeUndefined();
    expect(renderToStaticMarkup(createElement(CheckOfferLetterPage))).toContain("PDF maksimal 5 MB");
  });

  // Hanya nilai yang di-set tetapi tidak valid yang menggagalkan render (tanpa fallback diam-diam).
  it.each(["0", "-1", "5MB", "1.5"])("gagal render bila MAX_UPLOAD_BYTES=%s", (value) => {
    vi.stubEnv("MAX_UPLOAD_BYTES", value);
    expect(() => renderToStaticMarkup(createElement(CheckOfferLetterPage))).toThrow(/MAX_UPLOAD_BYTES/);
  });
});
