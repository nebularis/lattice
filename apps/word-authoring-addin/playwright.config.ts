import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  outputDir: "../../.build/word-authoring-addin-test-results",
  use: {
    baseURL: "http://127.0.0.1:4175/addin/",
    channel: process.platform === "win32" ? "msedge" : undefined,
  },
  webServer: { command: "yarn dev --host 127.0.0.1", port: 4175, reuseExistingServer: !process.env.CI },
});
