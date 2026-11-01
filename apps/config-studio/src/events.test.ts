// SPDX-License-Identifier: MPL-2.0
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

/** A WebSocket that records what the page sends, and lets a test play the service's frames. */
class FakeSocket {
  static last: FakeSocket | undefined;
  sent: string[] = [];
  onopen?: () => void;
  onmessage?: (m: { data: string }) => void;
  onclose?: () => void;
  constructor(public url: string) {
    FakeSocket.last = this;
  }
  send(text: string) {
    this.sent.push(text);
  }
  frames() {
    return this.sent.map((t) => JSON.parse(t));
  }
  serve(frame: object) {
    this.onmessage?.({ data: JSON.stringify(frame) });
  }
}

const JOB = "urn:lattice:studio:job:00000000-0000-0000-0000-000000000001";

describe("events", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.stubGlobal("WebSocket", FakeSocket);
    vi.stubGlobal("location", { origin: "http://127.0.0.1:8090" });
    vi.stubGlobal("sessionStorage", { getItem: () => null });
    vi.stubGlobal("localStorage", { getItem: () => "reviewer" });
  });
  afterEach(() => vi.unstubAllGlobals());

  it("authenticates first with the request headers, then subscribes what it waits for", async () => {
    const { watch, connected } = await import("./events");
    const w = watch(JOB);
    const s = FakeSocket.last!;
    expect(s.url).toBe("ws://127.0.0.1:8090/api/events");
    s.onopen?.();
    expect(s.frames()[0].type).toBe("auth");
    expect(connected()).toBe(false);
    s.serve({ type: "ready", principal: "reviewer" });
    expect(connected()).toBe(true);
    expect(s.frames()[1]).toEqual({ type: "subscribe", subject: JOB });
    w.close();
    expect(s.frames()[2]).toEqual({ type: "unsubscribe", subject: JOB });
  });

  it("wakes a watcher on its subject's event, and keeps an event that came before it waited", async () => {
    const { watch } = await import("./events");
    const w = watch(JOB);
    const s = FakeSocket.last!;
    s.onopen?.();
    s.serve({ type: "ready", principal: "reviewer" });
    s.serve({ specversion: "1.0", subject: JOB, type: "org.nebularis.lattice.studio.job.updated" });
    const early = Date.now();
    await w.next(10_000);
    expect(Date.now() - early).toBeLessThan(1000);
    const waiting = w.next(10_000);
    s.serve({ specversion: "1.0", subject: "urn:lattice:studio:job:other" });
    s.serve({ specversion: "1.0", subject: JOB });
    await waiting;
    w.close();
  });

  it("falls back to reading again after a while when no event comes", async () => {
    const { watch } = await import("./events");
    const w = watch(JOB);
    const started = Date.now();
    await w.next(50);
    expect(Date.now() - started).toBeGreaterThanOrEqual(45);
    w.close();
  });
});
