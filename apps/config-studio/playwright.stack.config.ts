import { defineConfig } from "@playwright/test";

// Against the running stack: the service on 8090 behind the dev server on 4175 (`mise run
// studio:service`, `studio:worker`, `studio:web`, with Fuseki and RabbitMQ up).
export default defineConfig({
  testDir: "./e2e-stack",
  outputDir: "../../.build/config-studio-stack-results",
  timeout: 120_000,
  use: { baseURL: "http://127.0.0.1:4175", viewport: { width: 1600, height: 1000 } },
});
