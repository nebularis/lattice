/**
 * The Playwright/manual harness entry point (plan WA9 "Files"): the same `App`, over a
 * `FakeWordPort` instead of Office.js, with `window.__harness` for tests to drive and inspect the
 * in-memory model directly, bypassing React.
 */
import { createRoot } from "react-dom/client";
import { HttpApiClient } from "./api/client";
import { App } from "./app/App";
import "./app/app.css";
import { FakeWordPort } from "./word/fakePort";

const params = new URLSearchParams(window.location.search);
const pollTimeoutMs = Number(params.get("pollTimeoutMs") ?? "20000");

const port = new FakeWordPort();
const api = new HttpApiClient("/api");

declare global {
  interface Window {
    __harness: {
      model: () => ReturnType<FakeWordPort["model"]>;
      ooxml: () => Promise<string>;
      metadata: () => ReturnType<FakeWordPort["readMetadata"]>;
      select: (elementId: string, start: number, end: number) => void;
    };
  }
}

window.__harness = {
  model: () => port.model(),
  ooxml: () => port.readBodyOoxml(),
  metadata: () => port.readMetadata(),
  select: (elementId, start, end) => port.select(elementId, start, end),
};

const container = document.getElementById("root");
if (container) {
  createRoot(container).render(<App port={port} api={api} options={{ pollTimeoutMs }} />);
}
