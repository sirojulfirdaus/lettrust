// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PLAN T2-07; SA §11.2; PRD §12.7.1
import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { API_BASE_URL, buildApiUrl } from "./api/client";

const SRC_ROOT = path.resolve(__dirname, "..");

// Mengumpulkan seluruh berkas sumber produksi (.ts/.tsx) di luar direktori fixture dan file uji.
function collectProductionSourceFiles(dir: string): string[] {
  const results: string[] = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === "fixtures") {
        continue;
      }
      results.push(...collectProductionSourceFiles(fullPath));
      continue;
    }
    if (!/\.(ts|tsx)$/.test(entry.name) || /\.test\.(ts|tsx)$/.test(entry.name)) {
      continue;
    }
    results.push(fullPath);
  }
  return results;
}

describe("keterhubungan Console ke API nyata (T2-07)", () => {
  it("tidak mengimpor fixture kontrak pada jalur kode produksi", () => {
    const prodFiles = collectProductionSourceFiles(SRC_ROOT);
    expect(prodFiles.length).toBeGreaterThan(0);

    const violations: string[] = [];
    for (const filePath of prodFiles) {
      const content = readFileSync(filePath, "utf8");
      if (/from\s+["']@\/fixtures\/api/.test(content) || /from\s+["']\.\.?\/.*fixtures\/api/.test(content)) {
        violations.push(path.relative(SRC_ROOT, filePath));
      }
    }

    expect(violations).toEqual([]);
  });

  it("membentuk URL endpoint Console live dengan base URL backend tanpa garis miring ganda", () => {
    expect(API_BASE_URL.length).toBeGreaterThan(0);
    expect(buildApiUrl("/api/v1/auth/me")).toBe(`${API_BASE_URL.replace(/\/+$/, "")}/api/v1/auth/me`);
    expect(buildApiUrl("/api/v1/proofs", undefined, { limit: 10, offset: 0 })).toBe(
      `${API_BASE_URL.replace(/\/+$/, "")}/api/v1/proofs?limit=10&offset=0`,
    );
  });
});
