import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e-stack",
  outputDir: "../../.build/word-authoring-addin-test-results",
  timeout: 90000,
  workers: 1,
  use: {
    baseURL: "https://localhost:3443",
    ignoreHTTPSErrors: true,
    channel: process.platform === "win32" ? "msedge" : undefined,
  },
});
