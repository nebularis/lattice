// SPDX-License-Identifier: MPL-2.0
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

/** An MQTT client that records what the page publishes, and lets a test play the broker. */
class FakeClient {
  static last: FakeClient | undefined;
  published: { topic: string; payload: string }[] = [];
  subscribed: string[] = [];
  handlers: Record<string, ((...a: unknown[]) => void)[]> = {};
  constructor(public url: string, public options: Record<string, unknown>) {
    FakeClient.last = this;
  }
  on(event: string, f: (...a: unknown[]) => void) {
    (this.handlers[event] ??= []).push(f);
    return this;
  }
  emit(event: string, ...a: unknown[]) {
    for (const f of this.handlers[event] ?? []) f(...a);
  }
  publish(topic: string, payload: string) {
    this.published.push({ topic, payload });
  }
  async subscribeAsync(topic: string) {
    this.subscribed.push(topic);
  }
  frames() {
    return this.published.map((p) => JSON.parse(p.payload));
  }
  serve(frame: object) {
    this.emit("message", "events", new TextEncoder().encode(JSON.stringify(frame)));
  }
}

const JOB = "urn:lattice:studio:job:00000000-0000-0000-0000-000000000001";
const settle = () => new Promise((r) => setTimeout(r, 0));

describe("events", () => {
  beforeEach(() => {
    vi.resetModules();
    FakeClient.last = undefined;
    vi.doMock("mqtt", () => ({ connect: (url: string, options: Record<string, unknown>) => new FakeClient(url, options) }));
    vi.doMock("./session", () => ({
      authHeaders: () => ({ "X-Lattice-Principal": "reviewer" }),
      loadSession: async () => ({ provider: "local", principal: "reviewer", events: "wss://broker.example:15676/ws", eventsPassword: "the-key" }),
    }));
    vi.stubGlobal("window", { addEventListener: () => undefined });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.doUnmock("mqtt");
    vi.doUnmock("./session");
  });

  async function connected() {
    const events = await import("./events");
    const w = events.watch(JOB);
    // The client is made once the session is read and the library loaded.
    while (!FakeClient.last) await settle();
    const c = FakeClient.last;
    c.emit("connect");
    await settle();
    return { events, w, c };
  }

  it("connects as the principal from a client id of its own, and watches only on its own topics", async () => {
    const { events, w, c } = await connected();
    const name = events.topicName("reviewer");
    expect(c.url).toBe("wss://broker.example:15676/ws");
    expect(c.options.username).toBe("reviewer");
    expect(c.options.password).toBe("the-key");
    expect(String(c.options.clientId)).toMatch(new RegExp(`^studio:${name}:[a-z0-9]{12}$`));
    const tab = String(c.options.clientId).split(":")[2];
    expect((c.options.will as { topic: string; payload: string }).topic).toBe(`studio/u/${name}/${tab}/watch`);
    expect(JSON.parse((c.options.will as { payload: string }).payload)).toEqual({ type: "gone" });
    expect(c.subscribed).toEqual([`studio/u/${name}/${tab}/events`]);
    expect(events.connected()).toBe(true);
    expect(c.published.every((p) => p.topic === `studio/u/${name}/${tab}/watch`)).toBe(true);
    expect(c.frames()[0]).toEqual({ type: "subscribe", subject: JOB, headers: { "X-Lattice-Principal": "reviewer" } });
    w.close();
    expect(c.frames()[1]).toEqual({ type: "unsubscribe", subject: JOB });
  });

  it("wakes a watcher on its subject's event, and keeps an event that came before it waited", async () => {
    const { w, c } = await connected();
    c.serve({ specversion: "1.0", subject: JOB, type: "org.nebularis.lattice.studio.job.updated" });
    const early = Date.now();
    await w.next(10_000);
    expect(Date.now() - early).toBeLessThan(1000);
    const waiting = w.next(10_000);
    c.serve({ type: "error", message: "no such subject" });
    c.serve({ specversion: "1.0", subject: "urn:lattice:studio:job:other" });
    c.serve({ specversion: "1.0", subject: JOB });
    await waiting;
    w.close();
  });

  it("wakes every watcher when the connection drops, and watches again when it is back", async () => {
    const { w, c } = await connected();
    const waiting = w.next(10_000);
    c.emit("close");
    await waiting;
    c.emit("connect");
    await settle();
    expect(c.frames().filter((f) => f.type === "subscribe")).toHaveLength(2);
    w.close();
  });

  it("falls back to reading again after a while when the studio offers no events", async () => {
    vi.doMock("./session", () => ({ authHeaders: () => ({}), loadSession: async () => ({ provider: "local", principal: "reviewer" }) }));
    const { watch, connected } = await import("./events");
    const w = watch(JOB);
    const started = Date.now();
    await w.next(50);
    expect(Date.now() - started).toBeGreaterThanOrEqual(45);
    expect(connected()).toBe(false);
    w.close();
  });

  it("finds the client library's connect in its browser build's one default export", async () => {
    vi.doMock("mqtt", () => ({ default: { connect: (url: string, options: Record<string, unknown>) => new FakeClient(url, options) } }));
    const { watch } = await import("./events");
    const w = watch(JOB);
    while (!FakeClient.last) await settle();
    expect(FakeClient.last.url).toBe("wss://broker.example:15676/ws");
    w.close();
  });

  it("names a principal in a topic with none of the characters a topic reserves", async () => {
    const { topicName } = await import("./events");
    expect(topicName("ana.lyst@example.org/a+b#")).toMatch(/^[A-Za-z0-9_-]+$/);
    expect(topicName("développeur")).toBe(Buffer.from("développeur").toString("base64url"));
  });
});
