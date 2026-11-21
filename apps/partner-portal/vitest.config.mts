// Owner: Pash (PIC 4) | Status: COMPLETE | Ref: SA §11.1, §11.3.3, §18.1
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

// Konfigurasi Vitest portal; "server-only" diarahkan ke modul kosong agar modul server dapat diuji di Node.
export default defineConfig({
  resolve: {
    tsconfigPaths: true,
    alias: {
      "server-only": fileURLToPath(new URL("./node_modules/server-only/empty.js", import.meta.url)),
    },
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
});
