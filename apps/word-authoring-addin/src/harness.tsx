/**
 * The Playwright/manual harness entry point (plan WA9 "Files", extended WA9a): the same `App`,
 * over a `FakeWordPort` instead of Office.js, with `window.__harness` for tests to drive and
 * inspect the in-memory model directly, bypassing React, and to run a ribbon/right-click command
 * by id without a real Word host.
 */
import { createRoot } from "react-dom/client";
import { HttpApiClient } from "./api/client";
import { App } from "./app/App";
import "./app/app.css";
import { UiBridge } from "./app/uiBridge";
import { createHandlers, type CommandEvent, type Handlers } from "./commands/handlers";
import type { CommandId } from "./commands/ids";
import { newUuid } from "./domain/uuid";
import { FakeWordPort } from "./word/fakePort";

const params = new URLSearchParams(window.location.search);
const pollTimeoutMs = Number(params.get("pollTimeoutMs") ?? "20000");

const port = new FakeWordPort();
const api = new HttpApiClient("");
const bridge = new UiBridge();
const showPaneCalls: number[] = [];
const handlers: Handlers = createHandlers({
  port,
  bridge,
  showPane: () => {
    showPaneCalls.push(Date.now());
  },
  newUuid,
});

declare global {
  interface Window {
    __harness: {
      model: () => ReturnType<FakeWordPort["model"]>;
      ooxml: () => Promise<string>;
      metadata: () => ReturnType<FakeWordPort["readMetadata"]>;
      select: (elementId: string, start: number, end: number) => void;
      command: (id: Exclude<CommandId, "showPane">) => Promise<void>;
      showPaneCallCount: () => number;
    };
  }
}

window.__harness = {
  model: () => port.model(),
  ooxml: () => port.readBodyOoxml(),
  metadata: () => port.readMetadata(),
  select: (elementId, start, end) => port.select(elementId, start, end),
  command: (id) =>
    new Promise<void>((resolve, reject) => {
      const handler = handlers[id];
      if (!handler) {
        reject(new Error(`no such command: ${id}`));
        return;
      }
      const event: CommandEvent = { completed: () => resolve() };
      void handler(event);
    }),
  showPaneCallCount: () => showPaneCalls.length,
};

const container = document.getElementById("root");
if (container) {
  createRoot(container).render(<App port={port} api={api} bridge={bridge} options={{ pollTimeoutMs }} />);
}

