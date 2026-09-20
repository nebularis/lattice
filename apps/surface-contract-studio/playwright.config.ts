import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  outputDir: "../../.build/surface-contract-studio-test-results",
  use: { baseURL: "http://127.0.0.1:4173" },
  webServer: { command: "yarn dev --host 127.0.0.1", port: 4173, reuseExistingServer: !process.env.CI },
});
