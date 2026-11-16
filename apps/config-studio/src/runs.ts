// SPDX-License-Identifier: MPL-2.0
// A run's result from its frames, and the controller that keeps one run in flight a pane (ADR-A154 decisions 8, 9 and 10, contracts/config-studio
// README, "Runs"). Frames reach a tab at QoS 0, so one can be lost, repeated or late, and a run is never read again. The assembler is a pure
// function of the frames it is given, in any order, and the controller holds everything that depends on time, taking the clock and the timers
// as inputs.

export type RunKind = "sample" | "simulate";
export type PartRole = "check" | "request" | "report" | "artefact" | "delta" | "outcome";
const ROLES: readonly string[] = ["check", "request", "report", "artefact", "delta", "outcome"];

/** One frame of a run, as `run-frame.schema.json` states it. */
export interface RunFrame {
  run: string;
  seq: number;
  last: boolean;
  part?: { index: number; role: PartRole; mediaType: string; path?: string; group?: string; step?: number };
  text?: string;
  more?: boolean;
  status?: "succeeded" | "failed";
  message?: string;
  conforms?: boolean;
}

export interface RunPart {
  index: number;
  role: PartRole;
  mediaType: string;
  path?: string;
  group?: string;
  step?: number;
  /** The concatenation of the text of the part's frames in sequence order. */
  text: string;
}

export interface RunEnd {
  status: "succeeded" | "failed";
  message?: string;
  conforms?: boolean;
}

export type Assembly =
  /** Every sequence number from 0 to the last frame's is present. */
  | ({ state: "complete"; run: string; parts: RunPart[] } & RunEnd)
  /** `missing` holds each absent number below the highest one seen (or below the last frame's), `next` the lowest absent number, and `end` the last frame's outcome where that frame arrived. */
  | { state: "partial"; run: string; parts: RunPart[]; received: number; missing: number[]; next: number; end?: RunEnd }
  | { state: "invalid"; reason: string };

const MAX_SEQ = 128;
const RUN_IRI = /^urn:lattice:studio:run:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** What the schema states about one frame that matters to assembly. A reason is given for the first rule the frame breaks. */
function breaks(frame: Record<string, unknown>): string | undefined {
  const { seq, last, part, text, more, status, message, conforms } = frame;
  if (typeof seq !== "number" || !Number.isInteger(seq) || seq < 0 || seq > MAX_SEQ) return `a frame has a seq that is not a whole number from 0 to ${MAX_SEQ}`;
  const at = `frame ${seq}`;
  if (typeof last !== "boolean") return `${at} has no last`;
  if (part !== undefined) {
    if (!isObject(part)) return `${at} has a part that is not an object`;
    if (typeof part.index !== "number" || !Number.isInteger(part.index) || part.index < 0 || part.index > 127) return `${at} has a part with no index`;
    if (typeof part.role !== "string" || !ROLES.includes(part.role)) return `${at} has a part with no known role`;
    if (typeof part.mediaType !== "string" || part.mediaType === "") return `${at} has a part with no media type`;
    for (const key of ["path", "group"] as const) if (part[key] !== undefined && (typeof part[key] !== "string" || part[key] === "")) return `${at} has a part whose ${key} is empty`;
    if (part.step !== undefined && (typeof part.step !== "number" || !Number.isInteger(part.step) || part.step < 0)) return `${at} has a part whose step is not a whole number`;
  }
  if (text !== undefined && typeof text !== "string") return `${at} has a text that is not a string`;
  if (more !== undefined && typeof more !== "boolean") return `${at} has a more that is not a boolean`;
  if (status !== undefined && status !== "succeeded" && status !== "failed") return `${at} has a status that is neither succeeded nor failed`;
  if (message !== undefined && (typeof message !== "string" || message === "")) return `${at} has an empty message`;
  if (conforms !== undefined && typeof conforms !== "boolean") return `${at} has a conforms that is not a boolean`;
  if (last) {
    if (status === undefined) return `${at} is the last frame and has no status`;
    if (more === true) return `${at} is the last frame and says its part continues`;
  } else if (status !== undefined || message !== undefined || conforms !== undefined) {
    return `${at} is not the last frame and carries a status, a message or conforms`;
  }
  if (status === "failed" && (message === undefined || conforms !== undefined)) return `${at} failed and must give a message and no conforms`;
  if (status === "succeeded" && message !== undefined) return `${at} succeeded and gives a message`;
  return undefined;
}

/**
 * The state of a run from the frames received, in any order and with any repeats. The first frame seen for a sequence number is kept and a
 * later one for the same number ignored, a frame of another run is ignored, and a frame that breaks the contract makes the result invalid, never
 * a throw. `run` names the run, and where it is left out the lowest run IRI among the frames stands for it, so the result does not depend on
 * their order.
 */
export function assemble(frames: readonly unknown[], run?: string): Assembly {
  let wanted = run;
  if (wanted === undefined) {
    const named = frames.filter(isObject).map((f) => f.run).filter((r): r is string => typeof r === "string").sort();
    wanted = named[0];
  }
  const bySeq = new Map<number, RunFrame>();
  for (const candidate of frames) {
    if (!isObject(candidate)) return { state: "invalid", reason: "a frame is not an object" };
    if (candidate.run !== wanted) continue;
    const reason = breaks(candidate);
    if (reason) return { state: "invalid", reason };
    if (!bySeq.has(candidate.seq as number)) bySeq.set(candidate.seq as number, candidate as unknown as RunFrame);
  }
  if (wanted === undefined || !RUN_IRI.test(wanted)) return { state: "invalid", reason: "the frames name no run by its IRI" };
  const ends = [...bySeq.values()].filter((f) => f.last);
  if (ends.length > 1) return { state: "invalid", reason: `frames ${ends.map((f) => f.seq).sort((a, b) => a - b).join(" and ")} are each the last` };
  const end = ends[0];
  const highest = Math.max(-1, ...bySeq.keys());
  if (end && highest > end.seq) return { state: "invalid", reason: `frame ${highest} comes after the last frame, ${end.seq}` };
  const missing: number[] = [];
  for (let n = 0; n < highest; n++) if (!bySeq.has(n)) missing.push(n);
  const next = missing[0] ?? highest + 1;
  // The parts are read from the frames that follow one another from 0, so a part shown is never one with a gap inside it.
  const parts: RunPart[] = [];
  for (let n = 0; n < next; n++) {
    const frame = bySeq.get(n)!;
    if (frame.part) {
      if (frame.part.index !== parts.length) return { state: "invalid", reason: `frame ${n} starts part ${frame.part.index} where part ${parts.length} is due` };
      const { index, role, mediaType, path, group, step } = frame.part;
      parts.push({ index, role, mediaType, ...(path === undefined ? {} : { path }), ...(group === undefined ? {} : { group }), ...(step === undefined ? {} : { step }), text: "" });
    }
    if (frame.text) {
      const current = parts[parts.length - 1];
      if (!current) return { state: "invalid", reason: `frame ${n} has text and no part before it` };
      current.text += frame.text;
    }
  }
  const outcome = end && { status: end.status!, ...(end.message === undefined ? {} : { message: end.message }), ...(end.conforms === undefined ? {} : { conforms: end.conforms }) };
  if (end && missing.length === 0) return { state: "complete", run: wanted, parts, ...outcome! };
  return { state: "partial", run: wanted, parts, received: bySeq.size, missing, next, ...(outcome ? { end: outcome } : {}) };
}

// --- the controller ---

/** What a request for a run holds. */
export interface RunRequest {
  workspace: string;
  kind: RunKind;
  target: string;
  /** The finished compile job whose artefacts run. */
  job: string;
  body: string;
  mediaType: string;
}

export type StartRunResult =
  | { kind: "accepted"; run: string }
  | { kind: "frames"; frames: unknown }
  /** The service's `504`, which it gives at the deadline of a request that waits. */
  | { kind: "deadline" }
  | { kind: "refused"; status: number; message: string; retryAfter?: number };

export interface RunApi {
  startRun(
    workspace: string,
    query: { kind: RunKind; target: string; job: string; tab: string; deadline: string; wait: boolean },
    body: string,
    mediaType: string,
    signal?: AbortSignal,
  ): Promise<StartRunResult>;
}

export interface RunEvents {
  connected(): boolean;
  onRunFrame(listener: (frame: unknown) => void): () => void;
  tabId(): string;
}

export interface RunClock {
  now(): number;
}

export interface RunTimers {
  setTimeout(f: () => void, ms: number): unknown;
  clearTimeout(handle: unknown): void;
}

export const DEADLINE_MS: Record<RunKind, number> = { simulate: 15_000, sample: 120_000 };

/** The most frames held while a request waits for the run's IRI. A run sends at most 129, and other runs' frames are dropped once it is known. */
const BUFFER_LIMIT = 512;

export type RunState =
  | { phase: "idle" }
  | { phase: "queued"; number: number; job: string }
  | { phase: "running"; number: number; job: string; parts: RunPart[]; received: number }
  | { phase: "complete"; number: number; job: string; parts: RunPart[]; conforms?: boolean }
  | { phase: "failed"; number: number; job: string; parts: RunPart[]; message: string }
  | { phase: "incomplete"; number: number; job: string; parts: RunPart[]; received: number; missing: number[]; next: number; message?: string }
  | { phase: "refused"; number: number; job: string; status: number; message: string; retryAfter?: number };

export interface RunController {
  /** Sends the run now, or, behind one in flight, waits as the newest request. */
  start(request: RunRequest): void;
  getState(): RunState;
  /** For `useSyncExternalStore`. The listener is called after each change of state. */
  subscribe(listener: () => void): () => void;
  /** Ends the timers and the wait, and ignores anything that arrives later. */
  dispose(): void;
}

interface Flight {
  number: number;
  request: RunRequest;
  mode: "events" | "wait";
  timer: unknown;
  abort: AbortController;
  /** Known once the service has accepted the run. */
  run?: string;
  frames: unknown[];
  /** Run frames that arrived before the run's IRI was known. */
  early: unknown[];
}

/**
 * One controller a pane. A frame can arrive before the `202` that names its run, since the service forwards frames as soon as it reads them, so
 * a request that waits for its IRI keeps every run frame it is given, up to a limit, and reads them again once the IRI is known, keeping those
 * of that run and dropping the rest. Where the tab's events are not connected at the start, the request waits (`wait=true`) and its answer is
 * assembled the same way. A connection that drops in flight is not repaired and the run ends at its deadline.
 */
export function createRunController(deps: { api: RunApi; events: RunEvents; clock: RunClock; timers: RunTimers }): RunController {
  const { api, events, clock, timers } = deps;
  const listeners = new Set<() => void>();
  let state: RunState = { phase: "idle" };
  let flight: Flight | undefined;
  let waiting: { number: number; request: RunRequest } | undefined;
  let counter = 0;
  let disposed = false;

  const set = (next: RunState) => {
    state = next;
    for (const l of [...listeners]) l();
  };

  const finish = (entry: Flight, next: RunState) => {
    if (disposed || flight !== entry) return;
    timers.clearTimeout(entry.timer);
    entry.abort.abort();
    flight = undefined;
    set(next);
    if (waiting) {
      const { number, request } = waiting;
      waiting = undefined;
      begin(number, request);
    }
  };

  const read = (entry: Flight) => {
    const a = assemble(entry.frames, entry.run);
    const job = entry.request.job;
    if (a.state === "invalid") finish(entry, { phase: "failed", number: entry.number, job, parts: [], message: `The result broke the contract: ${a.reason}.` });
    else if (a.state === "complete") {
      if (a.status === "failed") finish(entry, { phase: "failed", number: entry.number, job, parts: a.parts, message: a.message ?? "The run failed." });
      else finish(entry, { phase: "complete", number: entry.number, job, parts: a.parts, ...(a.conforms === undefined ? {} : { conforms: a.conforms }) });
    } else set({ phase: "running", number: entry.number, job, parts: a.parts, received: a.received });
  };

  const incomplete = (entry: Flight) => {
    const a = assemble(entry.frames, entry.run);
    const job = entry.request.job;
    if (a.state === "partial") {
      finish(entry, { phase: "incomplete", number: entry.number, job, parts: a.parts, received: a.received, missing: a.missing, next: a.next, ...(a.end?.message ? { message: a.end.message } : {}) });
    } else finish(entry, { phase: "incomplete", number: entry.number, job, parts: [], received: 0, missing: [], next: 0 });
  };

  const onFrame = (frame: unknown) => {
    const entry = flight;
    if (disposed || !entry || entry.mode !== "events") return;
    if (entry.run === undefined) {
      if (entry.early.length < BUFFER_LIMIT) entry.early.push(frame);
      return;
    }
    // A frame of a run this pane no longer shows is not kept.
    if (!(typeof frame === "object" && frame !== null && (frame as { run?: unknown }).run === entry.run)) return;
    entry.frames.push(frame);
    read(entry);
  };

  const begin = (number: number, request: RunRequest) => {
    const length = DEADLINE_MS[request.kind];
    const deadline = clock.now() + length;
    const entry: Flight = { number, request, mode: events.connected() ? "events" : "wait", timer: undefined, abort: new AbortController(), frames: [], early: [] };
    flight = entry;
    set({ phase: "running", number, job: request.job, parts: [], received: 0 });
    entry.timer = timers.setTimeout(() => incomplete(entry), Math.max(0, deadline - clock.now()));
    const wait = entry.mode === "wait";
    api
      .startRun(request.workspace, { kind: request.kind, target: request.target, job: request.job, tab: events.tabId(), deadline: new Date(deadline).toISOString(), wait }, request.body, request.mediaType, entry.abort.signal)
      .then(
        (result) => {
          if (disposed || flight !== entry) return;
          if (result.kind === "refused") finish(entry, { phase: "refused", number, job: request.job, status: result.status, message: result.message, ...(result.retryAfter === undefined ? {} : { retryAfter: result.retryAfter }) });
          else if (result.kind === "deadline") incomplete(entry);
          else if (result.kind === "accepted") {
            entry.run = result.run;
            entry.frames = entry.early.filter((f) => typeof f === "object" && f !== null && (f as { run?: unknown }).run === result.run);
            entry.early = [];
            if (entry.frames.length) read(entry);
          } else if (!Array.isArray(result.frames)) {
            finish(entry, { phase: "failed", number, job: request.job, parts: [], message: "The service's answer is not a list of frames." });
          } else {
            entry.frames = result.frames;
            entry.run = (result.frames.find((f) => typeof f === "object" && f !== null) as { run?: string } | undefined)?.run;
            read(entry);
          }
        },
        (error: unknown) => {
          if (disposed || flight !== entry) return;
          finish(entry, { phase: "refused", number, job: request.job, status: 0, message: error instanceof Error ? error.message : String(error) });
        },
      );
  };

  const off = events.onRunFrame(onFrame);

  return {
    start(request) {
      if (disposed) return;
      const number = ++counter;
      if (flight) {
        waiting = { number, request };
        set({ phase: "queued", number, job: request.job });
      } else begin(number, request);
    },
    getState: () => state,
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    dispose() {
      if (disposed) return;
      disposed = true;
      off();
      if (flight) {
        timers.clearTimeout(flight.timer);
        flight.abort.abort();
      }
      flight = undefined;
      waiting = undefined;
      listeners.clear();
    },
  };
}

/** The clock and timers of the page. */
export const pageClock: RunClock = { now: () => Date.now() };
export const pageTimers: RunTimers = { setTimeout: (f, ms) => setTimeout(f, ms), clearTimeout: (h) => clearTimeout(h as ReturnType<typeof setTimeout>) };
