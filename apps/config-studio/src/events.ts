// SPDX-License-Identifier: MPL-2.0
// The service's completion events over one WebSocket for the tab (PM3, PM-Q11 (c), PM-Q12). The first frame authenticates with the
// headers an HTTP request carries, and a subscribe frame names each subject waited for. Polling stays the fallback: a watcher still
// reads again after a while, so an event lost while the socket was closed costs a delay, never a hang.

import { authHeaders } from "./session";

const RECONNECT_MS = 5000;

let socket: WebSocket | undefined;
let ready = false;
const waiters = new Map<string, Set<() => void>>();

function send(frame: object) {
  if (socket && ready) socket.send(JSON.stringify(frame));
}

function wake(subject: string) {
  for (const w of [...(waiters.get(subject) ?? [])]) w();
}

function connect() {
  if (socket || typeof WebSocket === "undefined" || typeof location === "undefined") return;
  try {
    socket = new WebSocket(`${location.origin.replace(/^http/, "ws")}/api/events`);
  } catch {
    return;
  }
  const open = socket;
  open.onopen = () => open.send(JSON.stringify({ type: "auth", headers: authHeaders() }));
  open.onmessage = (message) => {
    let frame: { type?: string; specversion?: string; subject?: string };
    try {
      frame = JSON.parse(String(message.data));
    } catch {
      return;
    }
    if (frame.type === "ready") {
      ready = true;
      for (const subject of waiters.keys()) send({ type: "subscribe", subject });
    } else if (frame.specversion && frame.subject) {
      wake(frame.subject);
    }
  };
  open.onclose = () => {
    socket = undefined;
    ready = false;
    // What was missed while closed is read again now, and the socket is opened again while anything waits.
    for (const subject of waiters.keys()) wake(subject);
    setTimeout(() => {
      if (waiters.size > 0) connect();
    }, RECONNECT_MS);
  };
}

/** Whether the socket is open and authenticated, so a watcher may wait long between reads. */
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
  connect();
  let fired = false;
  let resume: (() => void) | undefined;
  const waiter = () => {
    fired = true;
    resume?.();
  };
  const set = waiters.get(subject) ?? new Set();
  if (set.size === 0) send({ type: "subscribe", subject });
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
