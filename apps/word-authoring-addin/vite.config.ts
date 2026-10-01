import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "/addin/",
  plugins: [react()],
  server: {
    port: 4175,
    strictPort: true,
    proxy: {
      "/api": "http://127.0.0.1:8088",
    },
  },
  build: {
    rollupOptions: {
      input: {
        taskpane: "taskpane.html",
        harness: "harness.html",
      },
    },
  },
});
