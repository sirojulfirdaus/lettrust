// Owner: Van (PIC 2) | Status: COMPLETE | Ref: SA §11.1, §18.1
import { defineConfig } from "vitest/config";

// Konfigurasi Vitest untuk logika non-visual Console (alias @/* dari tsconfig).
export default defineConfig({
  resolve: { tsconfigPaths: true },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
});
