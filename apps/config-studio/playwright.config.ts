import { defineConfig } from "@playwright/test";

// The tests intercept /api with a fake service (e2e/fake-service.ts), so only the dev server runs.
export default defineConfig({
  testDir: "./e2e",
  outputDir: "../../.build/config-studio-test-results",
  use: { baseURL: "http://127.0.0.1:4176", viewport: { width: 1600, height: 1000 } },
  webServer: { command: "yarn vite --port 4176", port: 4176, reuseExistingServer: !process.env.CI },
});
