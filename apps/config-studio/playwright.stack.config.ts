import { defineConfig } from "@playwright/test";

// Against the running stack from `mise run studio:up`: the service on 8090, which serves the built
// application. LATTICE_STUDIO_URL=http://127.0.0.1:4175 tests the dev server of `studio:up -- --dev` instead.
export default defineConfig({
  testDir: "./e2e-stack",
  outputDir: "../../.build/config-studio-stack-results",
  timeout: 120_000,
  use: { baseURL: process.env.LATTICE_STUDIO_URL ?? "http://127.0.0.1:8090", viewport: { width: 1600, height: 1000 } },
});
