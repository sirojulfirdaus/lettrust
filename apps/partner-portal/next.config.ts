// Owner: Pash (PIC 4) | Status: COMPLETE | Ref: SA §11.1, §11.3, §15.1
import type { NextConfig } from "next";

// Konfigurasi Next.js portal; output standalone dipakai image Docker.
const nextConfig: NextConfig = {
  output: "standalone",
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
