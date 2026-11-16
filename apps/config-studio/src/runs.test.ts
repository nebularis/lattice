// SPDX-License-Identifier: MPL-2.0
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it, vi } from "vitest";
import { assemble, createRunController, DEADLINE_MS, GRACE_MS, type RunApi, type RunEvents, type RunFrame, type RunRequest, type StartRunResult } from "./runs";

const samples = join(__dirname, "../../../contracts/config-studio/samples");
const example = (name: string) => JSON.parse(readFileSync(join(samples, name), "utf-8")) as RunFrame[];
const RUN = "urn:lattice:studio:run:3f2b8c1e-5a47-4d0e-9b1a-6c7d8e9f0a1b";
const OTHER = "urn:lattice:studio:run:9d1c4e72-0b3a-4f6d-8a25-1e7f3c5b2d90";
const JOB = "00000000-0000-0000-0000-000000000001";

/** A small seeded generator (mulberry32), so a failure can be repeated. */
function seeded(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function shuffled<T>(items: readonly T[], random: () => number): T[] {
  const out = [...items];
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

/** A run of `parts` parts, each split into one to three frames, then a succeeded last frame. */
function generated(random: () => number, run = RUN): RunFrame[] {
  const frames: RunFrame[] = [];
  const parts = 1 + Math.floor(random() * 4);
  for (let p = 0; p < parts; p++) {
    const pieces = 1 + Math.floor(random() * 3);
    for (let k = 0; k < pieces; k++) {
      frames.push({
        run,
        seq: frames.length,
        last: false,
        ...(k === 0 ? { part: { index: p, role: p % 2 ? "artefact" : "report", mediaType: "text/turtle", ...(p % 2 ? { path: `${p}.ttl`, group: "g", step: p } : {}) } } : {}),
        text: `part ${p} piece ${k} é\u{1F600}\n`,
        ...(k < pieces - 1 ? { more: true } : {}),
      });
    }
  }
  frames.push({ run, seq: frames.length, last: true, status: "succeeded", conforms: random() < 0.5 });
  return frames;
}

describe("assemble", () => {
  it("assembles the contract's two example runs", () => {
    const ok = assemble(example("run-frames.example.json"));
    expect(ok.state).toBe("complete");
    if (ok.state !== "complete") return;
    expect(ok.status).toBe("succeeded");
    expect(ok.conforms).toBe(true);
    expect(ok.parts.map((p) => [p.index, p.role, p.mediaType, p.path, p.group, p.step])).toEqual([
      [0, "report", "text/turtle", undefined, undefined, undefined],
      [1, "artefact", "application/n-triples", "loan-intake.0.nt", "https://example.org/lattice/mapping/loan-intake", 0],
    ]);
    expect(ok.parts[0].text).toContain("sh:conforms true");
    // the artefact is the text of its two frames, joined
    expect(ok.parts[1].text).toBe(example("run-frames.example.json").slice(1, 3).map((f) => f.text).join(""));
    expect(ok.parts[1].text.split("\n").filter(Boolean)).toHaveLength(2);
  });

  it("gives a failed run for the example that could not start", () => {
    const failed = assemble(example("run-frames-failed.example.json"));
    expect(failed).toEqual({ state: "complete", run: "urn:lattice:studio:run:9d1c4e72-0b3a-4f6d-8a25-1e7f3c5b2d90", parts: [], status: "failed", message: "The compile job could not be read, so nothing was run." });
  });

  it("gives failed, with the whole parts before the gap as partial output, for the run that was cut at its deadline", () => {
    const frames = example("run-frames-deadline.example.json");
    const run = frames[0].run;
    expect(assemble(frames)).toEqual({
      state: "failed",
      run,
      parts: [{ index: 0, role: "report", mediaType: "text/turtle", text: frames[0].text }],
      message: "The run did not finish by its deadline.",
      partial: true,
    });
    // in any order, with any duplicates
    const random = seeded(17);
    for (let i = 0; i < 50; i++) expect(assemble(shuffled([...frames, ...frames.filter(() => random() < 0.5)], random))).toEqual(assemble(frames));
  });

  it("settles a failed last frame whatever is missing, and a succeeded one only with every frame", () => {
    const random = seeded(23);
    for (let i = 0; i < 100; i++) {
      const frames = generated(random);
      const removed = Math.floor(random() * (frames.length - 1));
      const gapped = frames.filter((f) => f.seq !== removed);
      const failedEnd: RunFrame = { run: RUN, seq: frames.length - 1, last: true, status: "failed", message: "stopped" };
      const failed = assemble(shuffled([...gapped.slice(0, -1), failedEnd], random), RUN);
      expect(failed.state).toBe("failed");
      if (failed.state !== "failed") continue;
      expect(failed.message).toBe("stopped");
      // only parts that a later part follows, before the gap, are whole
      const before = assemble(frames.slice(0, removed), RUN);
      const held = before.state === "partial" ? before.parts : [];
      expect(failed.parts).toEqual(held.slice(0, -1));
      expect(assemble(shuffled(gapped, random), RUN).state).toBe("partial");
    }
  });

  it("gives the same result for any order of a run's frames (permutation, 200 seeded runs)", () => {
    const random = seeded(7);
    for (let i = 0; i < 200; i++) {
      const frames = generated(random);
      const expected = assemble(frames, RUN);
      expect(expected.state).toBe("complete");
      const once = assemble(shuffled(frames, random), RUN);
      expect(once).toEqual(expected);
      // and with no run named, the run is the one the frames name
      expect(assemble(shuffled(frames, random))).toEqual(expected);
    }
  });

  it("gives the same result for any duplication of frames, in any order", () => {
    const random = seeded(11);
    for (let i = 0; i < 200; i++) {
      const frames = generated(random);
      const expected = assemble(frames, RUN);
      const repeated = shuffled([...frames, ...frames.filter(() => random() < 0.5), ...frames.filter(() => random() < 0.5)], random);
      expect(assemble(repeated, RUN)).toEqual(expected);
    }
  });

  it("keeps the first frame seen for a number and ignores a later one", () => {
    const frames = generated(seeded(3));
    const changed = { ...frames[0], text: "something else\n" };
    const first = assemble([frames[0], changed, ...frames.slice(1)], RUN);
    const second = assemble([changed, frames[0], ...frames.slice(1)], RUN);
    expect(first).toEqual(assemble(frames, RUN));
    expect(second).not.toEqual(first);
    expect(second.state === "complete" && second.parts[0].text.startsWith("something else")).toBe(true);
  });

  it("is partial, and names the number, for a run with any one frame removed", () => {
    const random = seeded(5);
    for (let i = 0; i < 100; i++) {
      const frames = generated(random);
      const removed = Math.floor(random() * frames.length);
      const result = assemble(shuffled(frames.filter((f) => f.seq !== removed), random), RUN);
      expect(result.state).toBe("partial");
      if (result.state !== "partial") continue;
      expect(result.next).toBe(removed);
      expect(result.received).toBe(frames.length - 1);
      // a number below the highest frame is named as missing, and the last frame itself is named by `next`
      expect(result.missing).toEqual(removed < frames.length - 1 ? [removed] : []);
      // the parts shown are those the frames before the gap hold, never one with a gap inside
      const before = assemble(frames.slice(0, removed), RUN);
      expect(result.parts).toEqual(before.state === "partial" ? before.parts : []);
      expect(result.end?.status).toBe(removed === frames.length - 1 ? undefined : "succeeded");
    }
  });

  it("names every missing number, and carries the outcome of a last frame that came without what it ends", () => {
    const frames = generated(seeded(9));
    const result = assemble([frames[0], frames[frames.length - 1]], RUN);
    expect(result.state).toBe("partial");
    if (result.state !== "partial") return;
    expect(result.missing).toEqual(Array.from({ length: frames.length - 2 }, (_, i) => i + 1));
    expect(result.end?.status).toBe("succeeded");
  });

  it("ignores a frame of another run", () => {
    const frames = generated(seeded(2));
    const strangers = generated(seeded(4), OTHER);
    const mixed = shuffled([...frames, ...strangers], seeded(1));
    expect(assemble(mixed, RUN)).toEqual(assemble(frames, RUN));
    expect(assemble(mixed, OTHER)).toEqual(assemble(strangers, OTHER));
  });

  it("concatenates a part's text exactly, whatever it holds", () => {
    const pieces = ["aé", "\u{1F600}\u{1F600}", "\r\n", "", " end"];
    const frames: RunFrame[] = pieces.map((text, seq) => ({ run: RUN, seq, last: false, ...(seq === 0 ? { part: { index: 0, role: "artefact" as const, mediaType: "text/plain" } } : {}), text, more: true }));
    frames.push({ run: RUN, seq: frames.length, last: true, status: "succeeded" });
    const result = assemble(frames, RUN);
    expect(result.state === "complete" && result.parts[0].text).toBe(pieces.join(""));
  });

  it("gives the same result again for the same frames, and does not change them", () => {
    const frames = generated(seeded(13));
    const copy = JSON.parse(JSON.stringify(frames));
    expect(assemble(frames, RUN)).toEqual(assemble(frames, RUN));
    expect(frames).toEqual(copy);
  });

  it("is invalid, with a reason and no throw, for a frame that breaks the contract", () => {
    const part = { index: 0, role: "report" as const, mediaType: "text/turtle" };
    const cases: [string, unknown[]][] = [
      ["a text with no part before it", [{ run: RUN, seq: 0, last: false, text: "x" }, { run: RUN, seq: 1, last: true, status: "succeeded" }]],
      ["a last frame with no status", [{ run: RUN, seq: 0, last: true }]],
      ["a failed last frame with no message", [{ run: RUN, seq: 0, last: true, status: "failed" }]],
      ["a status on a frame that is not last", [{ run: RUN, seq: 0, last: false, status: "succeeded" }]],
      ["a part with an unknown role", [{ run: RUN, seq: 0, last: false, part: { ...part, role: "banner" } }]],
      ["a part out of its place", [{ run: RUN, seq: 0, last: false, part: { ...part, index: 1 } }]],
      ["a seq past the limit", [{ run: RUN, seq: 129, last: false }]],
      ["two last frames", [{ run: RUN, seq: 0, last: true, status: "succeeded" }, { run: RUN, seq: 1, last: true, status: "succeeded" }]],
      ["a frame after the last", [{ run: RUN, seq: 0, last: true, status: "succeeded" }, { run: RUN, seq: 1, last: false }]],
      ["a frame that is not an object", [null]],
      ["a last frame that says its part continues", [{ run: RUN, seq: 0, last: true, status: "succeeded", more: true }]],
    ];
    for (const [name, frames] of cases) {
      const result = assemble(frames, RUN);
      expect(result.state, name).toBe("invalid");
      expect(result.state === "invalid" && result.reason, name).toMatch(/\S/);
    }
  });

  it("is invalid for no frames that name a run, and partial for none of a named run", () => {
    expect(assemble([]).state).toBe("invalid");
    expect(assemble([], RUN)).toEqual({ state: "partial", run: RUN, parts: [], received: 0, missing: [], next: 0 });
  });
});

// --- the controller ---

class FakeTimers {
  now = 1_000_000;
  private next = 1;
  private pending = new Map<number, { at: number; f: () => void }>();
  readonly clock = { now: () => this.now };
  readonly timers = {
    setTimeout: (f: () => void, ms: number) => {
      const id = this.next++;
      this.pending.set(id, { at: this.now + ms, f });
      return id;
    },
    clearTimeout: (h: unknown) => void this.pending.delete(h as number),
  };
  get open(): number {
    return this.pending.size;
  }
  advance(ms: number) {
    const to = this.now + ms;
    for (;;) {
      const due = [...this.pending.entries()].filter(([, t]) => t.at <= to).sort((a, b) => a[1].at - b[1].at)[0];
      if (!due) break;
      this.pending.delete(due[0]);
      this.now = due[1].at;
      due[1].f();
    }
    this.now = to;
  }
}

class FakeEvents implements RunEvents {
  up = true;
  listeners = new Set<(f: unknown) => void>();
  connected = () => this.up;
  tabId = () => "tab1";
  onRunFrame = (l: (f: unknown) => void) => {
    this.listeners.add(l);
    return () => void this.listeners.delete(l);
  };
  serve(frame: unknown) {
    for (const l of [...this.listeners]) l(frame);
  }
}

interface Call {
  workspace: string;
  query: Parameters<RunApi["startRun"]>[1];
  body: string;
  mediaType: string;
  signal?: AbortSignal;
  resolve: (r: StartRunResult) => void;
  reject: (e: unknown) => void;
}

/** An api whose every call waits for the test to answer it. */
function fakeApi() {
  const calls: Call[] = [];
  const api: RunApi = {
    startRun: (workspace, query, body, mediaType, signal) =>
      new Promise((resolve, reject) => {
        calls.push({ workspace, query, body, mediaType, signal, resolve, reject });
      }),
  };
  return { api, calls };
}

const request = (body = "<s> <p> <o> .", kind: RunRequest["kind"] = "sample"): RunRequest => ({ workspace: "ws1", kind, target: "mapping", job: JOB, body, mediaType: "text/turtle" });
const frame = (seq: number, extra: Partial<RunFrame> = {}, run = RUN): RunFrame => ({ run, seq, last: false, ...extra });
const first = (text = "x\n"): Partial<RunFrame> => ({ part: { index: 0, role: "report", mediaType: "text/turtle" }, text });
const end = (seq: number, run = RUN): RunFrame => ({ run, seq, last: true, status: "succeeded", conforms: true });
const settle = () => new Promise((r) => setTimeout(r, 0));

function setup() {
  const time = new FakeTimers();
  const events = new FakeEvents();
  const { api, calls } = fakeApi();
  const controller = createRunController({ api, events, clock: time.clock, timers: time.timers });
  const states: string[] = [];
  controller.subscribe(() => states.push(controller.getState().phase));
  return { time, events, api, calls, controller, states };
}

describe("the run controller", () => {
  it("starts idle, sends a run with the tab, no deadline and no wait, and shows running", async () => {
    const { controller, calls, time } = setup();
    expect(controller.getState()).toEqual({ phase: "idle" });
    controller.start(request());
    expect(controller.getState()).toMatchObject({ phase: "running", number: 1, job: JOB, parts: [], received: 0 });
    expect(calls).toHaveLength(1);
    expect(calls[0].query).toEqual({ kind: "sample", target: "mapping", job: JOB, tab: "tab1", wait: false });
    expect(calls[0].query).not.toHaveProperty("deadline");
    expect(calls[0].body).toBe("<s> <p> <o> .");
    expect(calls[0].mediaType).toBe("text/turtle");
    expect(time.open).toBe(1);
  });

  it("times a run by the kind's own default plus the grace", () => {
    const { controller, time } = setup();
    controller.start(request("t", "simulate"));
    expect(DEADLINE_MS).toEqual({ simulate: 15_000, sample: 120_000 });
    expect(GRACE_MS).toBe(2_000);
    time.advance(DEADLINE_MS.simulate + GRACE_MS - 1);
    expect(controller.getState().phase).toBe("running");
    time.advance(1);
    expect(controller.getState().phase).toBe("incomplete");
  });

  it("assembles the frames the events deliver for the run the 202 names, in order of arrival of the parts, and completes", async () => {
    const { controller, calls, events, time } = setup();
    controller.start(request());
    calls[0].resolve({ kind: "accepted", run: RUN });
    await settle();
    events.serve(frame(0, first("a")));
    expect(controller.getState()).toMatchObject({ phase: "running", received: 1, parts: [{ index: 0, text: "a" }] });
    // the last frame comes before the one between, and the run is not yet complete
    events.serve(end(2));
    expect(controller.getState()).toMatchObject({ phase: "running", received: 2 });
    events.serve(frame(1, { text: "b" }));
    expect(controller.getState()).toEqual({ phase: "complete", number: 1, job: JOB, parts: [{ index: 0, role: "report", mediaType: "text/turtle", text: "ab" }], conforms: true });
    expect(time.open).toBe(0);
  });

  it("keeps the frames that arrive before the 202 returns, and reads them once the run's IRI is known", async () => {
    const { controller, calls, events } = setup();
    controller.start(request());
    // the whole run arrives first, with a frame of an older run among it
    events.serve(frame(1, { text: "b" }));
    events.serve(frame(0, first("a"), OTHER));
    events.serve(frame(0, first("a")));
    events.serve(end(2));
    expect(controller.getState()).toMatchObject({ phase: "running", received: 0 });
    calls[0].resolve({ kind: "accepted", run: RUN });
    await settle();
    expect(controller.getState()).toMatchObject({ phase: "complete", parts: [{ text: "ab" }] });
  });

  it("holds early frames only up to a limit", async () => {
    const { controller, calls, events } = setup();
    controller.start(request());
    for (let i = 0; i < 2000; i++) events.serve(frame(i % 128, first("z"), OTHER));
    events.serve(frame(0, first("a")));
    events.serve(end(1));
    calls[0].resolve({ kind: "accepted", run: RUN });
    await settle();
    // the run's own frames came after the limit, so they were not kept, and the run ends at its deadline
    expect(controller.getState().phase).toBe("running");
  });

  it("ignores frames of a run that is not the one shown, and frames when no run is in flight", async () => {
    const { controller, calls, events } = setup();
    events.serve(frame(0, first(), OTHER));
    expect(controller.getState().phase).toBe("idle");
    controller.start(request());
    calls[0].resolve({ kind: "accepted", run: RUN });
    await settle();
    events.serve(frame(0, first("a"), OTHER));
    events.serve(end(1, OTHER));
    expect(controller.getState()).toMatchObject({ phase: "running", received: 0 });
    events.serve(frame(0, first("a")));
    events.serve(end(1));
    expect(controller.getState().phase).toBe("complete");
    // late frames after the run ended change nothing
    events.serve(frame(0, first("late")));
    expect(controller.getState()).toMatchObject({ phase: "complete", parts: [{ text: "a" }] });
  });

  it("keeps one run in flight, and of three quick starts sends the first and the newest, never the second", async () => {
    const { controller, calls, events, states } = setup();
    controller.start(request("one"));
    controller.start(request("two"));
    expect(controller.getState()).toEqual({ phase: "queued", number: 2, job: JOB });
    controller.start(request("three"));
    expect(controller.getState()).toEqual({ phase: "queued", number: 3, job: JOB });
    expect(calls).toHaveLength(1);
    calls[0].resolve({ kind: "accepted", run: RUN });
    await settle();
    expect(calls).toHaveLength(1);
    events.serve(frame(0, first("a")));
    events.serve(end(1));
    // the run in flight ended, so the waiting one is sent at once
    expect(calls).toHaveLength(2);
    expect(calls[1].body).toBe("three");
    expect(controller.getState()).toMatchObject({ phase: "running", number: 3 });
    expect(states).toContain("queued");
  });

  it("shows only the newest run: the late frames of the run before it are ignored", async () => {
    const { controller, calls, events, time } = setup();
    controller.start(request("one"));
    calls[0].resolve({ kind: "accepted", run: RUN });
    await settle();
    controller.start(request("two"));
    time.advance(DEADLINE_MS.sample + GRACE_MS);
    expect(calls).toHaveLength(2);
    calls[1].resolve({ kind: "accepted", run: OTHER });
    await settle();
    events.serve(frame(0, first("old")));
    events.serve(end(1));
    expect(controller.getState()).toMatchObject({ phase: "running", number: 2, received: 0 });
    events.serve(frame(0, first("new"), OTHER));
    events.serve(end(1, OTHER));
    expect(controller.getState()).toMatchObject({ phase: "complete", number: 2, parts: [{ text: "new" }] });
  });

  it("sends the waiting request when the run in flight fails, is refused or is incomplete", async () => {
    for (const ending of ["failed", "refused", "incomplete"] as const) {
      const { controller, calls, events, time } = setup();
      controller.start(request("one"));
      controller.start(request("two"));
      if (ending === "refused") calls[0].resolve({ kind: "refused", status: 503, message: "no broker" });
      else {
        calls[0].resolve({ kind: "accepted", run: RUN });
        await settle();
        if (ending === "failed") events.serve({ run: RUN, seq: 0, last: true, status: "failed", message: "boom" });
        else time.advance(DEADLINE_MS.sample + GRACE_MS);
      }
      await settle();
      expect(calls, ending).toHaveLength(2);
      expect(controller.getState(), ending).toMatchObject({ phase: "running", number: 2 });
    }
  });

  it("gives failed, with the run's message and what arrived, for a failed last frame", async () => {
    const { controller, calls, events } = setup();
    controller.start(request());
    calls[0].resolve({ kind: "accepted", run: RUN });
    await settle();
    events.serve(frame(0, first("a")));
    events.serve({ run: RUN, seq: 1, last: true, status: "failed", message: "The result is too large, narrow what is run." });
    expect(controller.getState()).toMatchObject({ phase: "failed", message: "The result is too large, narrow what is run.", parts: [{ text: "a" }] });
  });

  it("gives incomplete at the deadline, listing what arrived and what is missing, and ends the wait", async () => {
    const { controller, calls, events, time } = setup();
    controller.start(request());
    calls[0].resolve({ kind: "accepted", run: RUN });
    await settle();
    events.serve(frame(0, first("a")));
    events.serve(frame(2, { text: "c" }));
    time.advance(DEADLINE_MS.sample + GRACE_MS - 1);
    expect(controller.getState().phase).toBe("running");
    time.advance(1);
    expect(controller.getState()).toEqual({ phase: "incomplete", number: 1, job: JOB, parts: [{ index: 0, role: "report", mediaType: "text/turtle", text: "a" }], received: 2, missing: [1], next: 1 });
    expect(calls[0].signal?.aborted).toBe(true);
  });

  it("gives failed, with the service's own message, for a failed last frame that came without the frames before it", async () => {
    const { controller, calls, events, time } = setup();
    controller.start(request("t", "simulate"));
    calls[0].resolve({ kind: "accepted", run: RUN });
    await settle();
    events.serve({ run: RUN, seq: 3, last: true, status: "failed", message: "The run did not finish before its deadline." });
    expect(controller.getState()).toEqual({ phase: "failed", number: 1, job: JOB, parts: [], message: "The run did not finish before its deadline.", partial: true });
    expect(time.open).toBe(0);
  });

  it("gives failed, not incomplete, for the service's failed frame that arrives within the grace after the deadline", async () => {
    const { controller, calls, events, time } = setup();
    controller.start(request("t", "simulate"));
    calls[0].resolve({ kind: "accepted", run: RUN });
    await settle();
    events.serve(frame(0, first("a")));
    events.serve(frame(1, { part: { index: 1, role: "artefact", mediaType: "text/plain" }, text: "b" }));
    // frame 2 is lost, and the service sends its failed frame at the deadline
    time.advance(DEADLINE_MS.simulate + GRACE_MS - 1);
    expect(controller.getState().phase).toBe("running");
    events.serve({ run: RUN, seq: 3, last: true, status: "failed", message: "The run did not finish by its deadline." });
    expect(controller.getState()).toEqual({ phase: "failed", number: 1, job: JOB, parts: [{ index: 0, role: "report", mediaType: "text/turtle", text: "a" }], message: "The run did not finish by its deadline.", partial: true });
    time.advance(10_000);
    expect(controller.getState().phase).toBe("failed");
  });

  it("keeps a succeeded last frame with a gap before it as running, and gives incomplete after the grace", async () => {
    const { controller, calls, events, time } = setup();
    controller.start(request());
    calls[0].resolve({ kind: "accepted", run: RUN });
    await settle();
    events.serve(frame(0, first("a")));
    events.serve(end(2));
    time.advance(DEADLINE_MS.sample);
    expect(controller.getState()).toMatchObject({ phase: "running", received: 2 });
    time.advance(GRACE_MS - 1);
    expect(controller.getState().phase).toBe("running");
    time.advance(1);
    expect(controller.getState()).toMatchObject({ phase: "incomplete", received: 2, missing: [1], next: 1 });
  });

  it("times a run by a duration from the send, and reads no clock to compare with anything the service said", async () => {
    const time = new FakeTimers();
    const { api, calls } = fakeApi();
    const clock = { now: (): number => { throw new Error("the controller must not read a clock"); } };
    const controller = createRunController({ api, events: new FakeEvents(), clock, timers: time.timers });
    controller.start(request());
    expect(calls[0].query).not.toHaveProperty("deadline");
    calls[0].resolve({ kind: "accepted", run: RUN });
    await settle();
    // however far the page's clock is from the service's, the run ends a duration after the send
    time.now += 3_600_000;
    time.advance(DEADLINE_MS.sample + GRACE_MS);
    expect(controller.getState().phase).toBe("incomplete");
    const bare = createRunController({ api, events: new FakeEvents(), timers: time.timers });
    bare.start(request("again"));
    expect(bare.getState().phase).toBe("running");
    bare.dispose();
  });

  it("closes a waiting request when the timer ends and on dispose", async () => {
    const a = setup();
    a.events.up = false;
    a.controller.start(request());
    a.time.advance(DEADLINE_MS.sample + GRACE_MS);
    expect(a.calls[0].signal?.aborted).toBe(true);
    const b = setup();
    b.events.up = false;
    b.controller.start(request());
    b.controller.dispose();
    expect(b.calls[0].signal?.aborted).toBe(true);
  });

  it("gives incomplete when the connection drops, the run is not sent again, and the run ends at its deadline", async () => {
    const { controller, calls, events, time } = setup();
    controller.start(request());
    calls[0].resolve({ kind: "accepted", run: RUN });
    await settle();
    events.serve(frame(0, first("a")));
    events.up = false;
    time.advance(DEADLINE_MS.sample + GRACE_MS);
    expect(calls).toHaveLength(1);
    expect(controller.getState()).toMatchObject({ phase: "incomplete", received: 1 });
  });

  it("sends with wait where the events are not connected, and assembles the array the answer gives", async () => {
    const { controller, calls, events, time } = setup();
    events.up = false;
    controller.start(request());
    expect(calls[0].query.wait).toBe(true);
    // frames of the events are not read for a run that waits
    events.serve(end(0));
    expect(controller.getState().phase).toBe("running");
    calls[0].resolve({ kind: "frames", frames: [end(2), frame(1, { text: "b" }), frame(0, first("a")), frame(0, first("a"))] });
    await settle();
    expect(controller.getState()).toMatchObject({ phase: "complete", parts: [{ text: "ab" }] });
    expect(time.open).toBe(0);
  });

  it("gives the same state from frames over events and from the waiting answer", async () => {
    const frames = [frame(0, first("a")), frame(1, { text: "b" }), end(2)];
    const viaEvents = setup();
    viaEvents.controller.start(request());
    viaEvents.calls[0].resolve({ kind: "accepted", run: RUN });
    await settle();
    for (const f of [...frames].reverse()) viaEvents.events.serve(f);
    const waiting = setup();
    waiting.events.up = false;
    waiting.controller.start(request());
    waiting.calls[0].resolve({ kind: "frames", frames });
    await settle();
    expect(viaEvents.controller.getState()).toEqual(waiting.controller.getState());
  });

  it("gives incomplete for the service's 504, and failed for an answer that is not frames or breaks the contract", async () => {
    const a = setup();
    a.events.up = false;
    a.controller.start(request());
    a.calls[0].resolve({ kind: "deadline" });
    await settle();
    expect(a.controller.getState()).toMatchObject({ phase: "incomplete", received: 0 });
    const b = setup();
    b.events.up = false;
    b.controller.start(request());
    b.calls[0].resolve({ kind: "frames", frames: { not: "a list" } });
    await settle();
    expect(b.controller.getState()).toMatchObject({ phase: "failed", message: "The service's answer is not a list of frames." });
    const c = setup();
    c.events.up = false;
    c.controller.start(request());
    c.calls[0].resolve({ kind: "frames", frames: [{ run: RUN, seq: 0, last: false, text: "no part" }, end(1)] });
    await settle();
    expect(c.controller.getState()).toMatchObject({ phase: "failed", message: expect.stringContaining("text and no part before it") });
  });

  it("gives refused for each status the contract names, with its text, and the Retry-After of a 429", async () => {
    for (const status of [429, 409, 404, 400, 413, 415, 503]) {
      const { controller, calls, time } = setup();
      controller.start(request());
      calls[0].resolve({ kind: "refused", status, message: `text ${status}`, ...(status === 429 ? { retryAfter: 7 } : {}) });
      await settle();
      expect(controller.getState(), String(status)).toEqual({ phase: "refused", number: 1, job: JOB, status, message: `text ${status}`, ...(status === 429 ? { retryAfter: 7 } : {}) });
      expect(time.open).toBe(0);
    }
  });

  it("gives refused with status 0 when the request itself fails, and ends nothing twice", async () => {
    const { controller, calls, states } = setup();
    controller.start(request());
    calls[0].reject(new Error("Failed to fetch"));
    await settle();
    expect(controller.getState()).toMatchObject({ phase: "refused", status: 0, message: "Failed to fetch" });
    const seen = states.length;
    await settle();
    expect(states).toHaveLength(seen);
  });

  it("can run again after any end", async () => {
    const { controller, calls } = setup();
    controller.start(request());
    calls[0].resolve({ kind: "refused", status: 409, message: "x" });
    await settle();
    controller.start(request("again"));
    expect(calls).toHaveLength(2);
    expect(controller.getState()).toMatchObject({ phase: "running", number: 2 });
  });

  it("on dispose ends the timers and the wait, drops the queue, and ignores what arrives after", async () => {
    const { controller, calls, events, time, states } = setup();
    controller.start(request("one"));
    controller.start(request("two"));
    calls[0].resolve({ kind: "accepted", run: RUN });
    await settle();
    const seen = states.length;
    controller.dispose();
    expect(time.open).toBe(0);
    expect(calls[0].signal?.aborted).toBe(true);
    expect(events.listeners.size).toBe(0);
    events.serve(frame(0, first()));
    events.serve(end(1));
    time.advance(200_000);
    calls[0].resolve({ kind: "refused", status: 503, message: "late" });
    await settle();
    controller.start(request("three"));
    expect(calls).toHaveLength(1);
    expect(states).toHaveLength(seen);
    controller.dispose();
  });

  it("tells a subscriber of each change, and none after it has left", async () => {
    const { controller, calls } = setup();
    const listener = vi.fn();
    const off = controller.subscribe(listener);
    controller.start(request());
    expect(listener).toHaveBeenCalled();
    off();
    const seen = listener.mock.calls.length;
    calls[0].resolve({ kind: "refused", status: 503, message: "x" });
    await settle();
    expect(listener).toHaveBeenCalledTimes(seen);
  });
});
