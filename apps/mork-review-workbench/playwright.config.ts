import { defineConfig } from "@playwright/test";

export default defineConfig({ testDir: "./e2e", outputDir: "../../.build/mork-review-workbench-test-results", use: { baseURL: "http://127.0.0.1:4174" }, webServer: { command: "yarn dev --host 127.0.0.1", port: 4174, reuseExistingServer: !process.env.CI } });