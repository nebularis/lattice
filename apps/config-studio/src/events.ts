// SPDX-License-Identifier: MPL-2.0
// The service's completion events over the broker's MQTT, one connection for the tab (PM3, PM-Q20 (d)). The broker lets the tab in
// with the principal's name and the app's own credential, and lets it write only its watch topic and read only its events topic. The
// service's relay reads the watch frames, each carrying the headers an HTTP request carries, and sends each event to the tabs whose
// principal may read it, checked as it is delivered. Polling stays the fallback: a watcher still reads again after a while, so an
// event lost while the connection was down, or a studio that offers no events, costs a delay, never a hang.

import type { MqttClient } from "mqtt";
import { authHeaders, loadSession, type Session } from "./session";

const RECONNECT_MS = 5000;
const GONE = JSON.stringify({ type: "gone" });

let client: MqttClient | undefined;
let starting = false;
let ready = false;
let watchTopic = "";
const tab = Array.from({ length: 12 }, () => "abcdefghijklmnopqrstuvwxyz0123456789"[Math.floor(Math.random() * 36)]).join("");
const waiters = new Map<string, Set<() => void>>();

/** A principal's name as a topic carries it, unpadded base64url of its UTF-8, so it holds no `.`, `/`, `+` or `#`. */
export function topicName(principal: string): string {
  const bytes = new TextEncoder().encode(principal);
  return btoa(String.fromCharCode(...bytes)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

/** The CONNECT password: the bearer token, or with local sign-in the key only a page of the studio's own origin reads from the session. */
function password(session: Session): string {
  const auth = authHeaders().Authorization;
  return auth?.startsWith("Bearer ") ? auth.slice(7) : (session.eventsPassword ?? "");
}

function send(frame: object) {
  if (client && ready) client.publish(watchTopic, JSON.stringify(frame));
}

function subscribe(subject: string) {
  send({ type: "subscribe", subject, headers: authHeaders() });
}

function wake(subject: string) {
  for (const w of [...(waiters.get(subject) ?? [])]) w();
}

async function connect() {
  if (client || starting || typeof window === "undefined") return;
  starting = true;
  try {
    const session = await loadSession();
    if (!session.events || !session.principal) return;
    // The library's browser build exports one default object, and its Node build the functions by name.
    const library: { connect?: typeof import("mqtt").connect; default?: { connect: typeof import("mqtt").connect } } = await import("mqtt");
    const open = "connect" in library && library.connect ? library.connect : library.default!.connect;
    const base = `studio/u/${topicName(session.principal)}/${tab}`;
    watchTopic = `${base}/watch`;
    const c = open(session.events, {
      username: session.principal,
      password: password(session),
      clientId: `studio:${topicName(session.principal)}:${tab}`,
      clean: true,
      reconnectPeriod: RECONNECT_MS,
      // The library's default timers run in a worker made from a blob URL, which the page's policy refuses.
      timerVariant: "native",
      // The broker sends this when the connection drops uncleanly, so the relay forgets the tab's watches.
      will: { topic: watchTopic, payload: GONE, qos: 0, retain: false },
    });
    client = c;
    c.on("reconnect", () => {
      // A token may have been renewed since the last connection.
      c.options.password = password(session);
    });
    c.on("connect", async () => {
      try {
        await c.subscribeAsync(`${base}/events`);
      } catch {
        return;
      }
      ready = true;
      for (const subject of waiters.keys()) subscribe(subject);
    });
    c.on("message", (_topic, payload) => {
      let frame: { specversion?: string; subject?: string };
      try {
        frame = JSON.parse(new TextDecoder().decode(payload));
      } catch {
        return;
      }
      if (frame.specversion && frame.subject) wake(frame.subject);
    });
    c.on("close", () => {
      if (!ready) return;
      ready = false;
      // What was missed while down is read again now, and the client connects again while anything waits.
      for (const subject of waiters.keys()) wake(subject);
    });
    window.addEventListener("pagehide", () => c.publish(watchTopic, GONE));
  } catch {
    // No broker reachable, or no client library: the watchers poll.
  } finally {
    starting = false;
  }
}

/** Whether the tab's connection is up, so a watcher may wait long between reads. */
export function connected(): boolean {
  return ready;
}

export interface Watch {
  /** Resolves when an event for the subject arrives, or after `fallbackMs`, whichever is first. An event that came before is kept. */
  next(fallbackMs: number): Promise<void>;
  close(): void;
}

/** Waits for events about one subject, such as a job's IRI. Open it before reading the subject, so no event falls between the two. */
export function watch(subject: string): Watch {
  void connect();
  let fired = false;
  let resume: (() => void) | undefined;
  const waiter = () => {
    fired = true;
    resume?.();
  };
  const set = waiters.get(subject) ?? new Set();
  if (set.size === 0) subscribe(subject);
  set.add(waiter);
  waiters.set(subject, set);
  return {
    next(fallbackMs) {
      if (fired) {
        fired = false;
        return Promise.resolve();
      }
      return new Promise<void>((resolve) => {
        const timer = setTimeout(done, fallbackMs);
        function done() {
          clearTimeout(timer);
          resume = undefined;
          fired = false;
          resolve();
        }
        resume = done;
      });
    },
    close() {
      set.delete(waiter);
      if (set.size === 0) {
        waiters.delete(subject);
        send({ type: "unsubscribe", subject });
      }
    },
  };
}
