import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// The dev server proxies the API to the service (LATTICE_STUDIO_PORT, default 8090).
const service = `http://127.0.0.1:${process.env.LATTICE_STUDIO_PORT ?? "8090"}`;

export default defineConfig({
  plugins: [react()],
  server: { host: "127.0.0.1", port: 4175, strictPort: true, proxy: { "/api": service } },
  preview: { host: "127.0.0.1", port: 4175, strictPort: true, proxy: { "/api": service } },
  test: { include: ["src/**/*.test.ts"], environment: "node" },
  // n3 and React make one 500 kB bundle, 150 kB compressed. Splitting it gains nothing for a studio.
  build: { outDir: "dist", sourcemap: true, chunkSizeWarningLimit: 600 },
});
