// Owner: Van (PIC 2) | Status: COMPLETE | Ref: SA §11.1, §15.1
import type { NextConfig } from "next";

// Konfigurasi Next.js Console; output standalone dipakai image Docker.
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
