// SPDX-License-Identifier: MPL-2.0
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { Graph } from "@lattice/authoring-domain";
import type { Recorded, RecordedRun } from "../e2e/sampleRuns";
import { FIXTURE } from "../e2e/sampleRuns";
import { schemesOf } from "./rdf/mapping";
import type { Artefact } from "./rdf/report";
import { createRunController, type RunApi, type RunEvents, type StartRunResult } from "./runs";
import { createSampleSession, engineOf, formsOf, runResult, schemeReading, sourceFormats, WAITS, type Compiled, type SampleSession } from "./sample";

const recorded = JSON.parse(readFileSync(new URL(`../e2e/${FIXTURE}`, import.meta.url), "utf-8")) as Recorded;
const workspace = (id: string) => recorded.workspaces.find((w) => w.id === id)!;
const recordedRun = (id: string): RecordedRun => recorded.runs.find((r) => r.id === id)!;
const artefacts = (id: string): Artefact[] => workspace(id).compiled.map((a) => ({ ...a }));
const mappingOf = (id: string) => Graph.parse(workspace(id).compileBody);
const XML_SCHEME = "urn:example:mapping/xml#Scheme";
const JSON_SCHEME = "urn:example:mapping/json#Scheme";
const CATALOGUE = "http://example.org/mapping#Catalogue";

/** A session over the recorded compilations and runs, which counts what it was asked to do. A run is answered with the frames the workers gave for its sample. */
function harness(id: "policies" | "catalogue" = "policies") {
  const log = { compiled: [] as Graph[], forgotten: [] as string[], runs: [] as { job: string; body: string; mediaType: string }[] };
  const store = new Map<string, string>();
  let fail: string | undefined;
  const api: RunApi = {
    async startRun(_workspace, query, body, mediaType): Promise<StartRunResult> {
      log.runs.push({ job: query.job, body, mediaType });
      if (fail) return { kind: "frames", frames: [{ run: "urn:lattice:studio:run:3f2b8c1e-5a47-4d0e-9b1a-6c7d8e9f0a1b", seq: 0, last: true, status: "failed", message: fail }] };
      const found = recorded.runs.find((r) => r.workspace === id && r.sample === body && r.mediaType === mediaType);
      if (!found) throw new Error("no recorded run for this request");
      return { kind: "frames", frames: found.frames };
    },
  };
  const events: RunEvents = { connected: () => false, tabId: () => "tab1", onRunFrame: () => () => undefined };
  const controller = createRunController({ api, events, timers: { setTimeout: () => 0, clearTimeout: () => undefined } });
  const deps = {
    workspace: "ws1",
    async compile(graph: Graph): Promise<Compiled> {
      log.compiled.push(graph);
      return { job: `job-${log.compiled.length}`, artefacts: artefacts(id) };
    },
    async latest(): Promise<Compiled | undefined> {
      return { job: "found", artefacts: artefacts(id) };
    },
    forget: (job: string) => void log.forgotten.push(job),
    controller,
    storage: { get: (k: string) => store.get(k), set: (k: string, v?: string) => (v === undefined ? store.delete(k) : void store.set(k, v)) },
  };
  const session = createSampleSession(deps);
  const graph = mappingOf(id);
  /** What the workspace holds, given to the session as the view would give it. */
  const inputs = (over: Partial<{ graph: Graph; context: string; scheme: string }> = {}) => {
    session.setScheme(over.scheme ?? (id === "policies" ? XML_SCHEME : CATALOGUE));
    return { graph: over.graph ?? graph, context: over.context ?? "0" };
  };
  const finished = async () => {
    for (let i = 0; i < 50 && ["running", "queued"].includes(session.getState().run.phase); i++) await new Promise((r) => setTimeout(r, 0));
    await new Promise((r) => setTimeout(r, 0));
  };
  return { session, log, inputs, graph, finished, fail: (m?: string) => (fail = m) };
}

const XML = () => recordedRun("xml").sample;

async function ran(h: ReturnType<typeof harness>, session: SampleSession = h.session) {
  await session.run();
  await h.finished();
}

describe("the forms of a compilation", () => {
  it("lists the form each source is compiled to and whether a runtime exists, as the sketch's table says", () => {
    const policies = artefacts("policies");
    const xml = formsOf(policies, XML_SCHEME, sourceFormats(mappingOf("policies"), XML_SCHEME));
    expect(xml.map((f) => [f.kind, f.label, f.reads, f.runtime])).toEqual([["xslt", "XSLT 3.0", "application/xml", true]]);
    const json = formsOf(policies, JSON_SCHEME, sourceFormats(mappingOf("policies"), JSON_SCHEME));
    expect(json.map((f) => [f.kind, f.label, f.reads, f.runtime])).toEqual([
      ["jolt", "JOLT", "application/json", true],
      ["rml", "RML", undefined, false],
    ]);
    const rdf = formsOf(artefacts("catalogue"), CATALOGUE, sourceFormats(mappingOf("catalogue"), CATALOGUE));
    expect(rdf.map((f) => [f.kind, f.label, f.reads, f.runtime, f.path])).toEqual([["construct", "SPARQL CONSTRUCT", "text/turtle", true, "Catalogue.compiled.ttl"]]);
  });

  it("offers a scheme's compiled queries only where its source is RDF, and reads each scheme's source formats from the part", () => {
    const g = mappingOf("policies");
    expect([...sourceFormats(g, XML_SCHEME)]).toEqual(["XML"]);
    expect([...sourceFormats(g, JSON_SCHEME)]).toEqual(["JSON"]);
    expect([...sourceFormats(mappingOf("catalogue"), CATALOGUE)]).toEqual(["RDF"]);
    expect(formsOf(artefacts("policies"), XML_SCHEME, new Set()).map((f) => f.kind)).toEqual(["xslt"]);
    expect(formsOf(artefacts("catalogue"), CATALOGUE, new Set(["XML"])).map((f) => f.kind)).toEqual([]);
  });

  it("finds the scheme that reads an example source, and lists no template library, since none exist yet", () => {
    const g = mappingOf("policies");
    expect(schemeReading(g, "urn:example:source/xml#Source")).toBe(XML_SCHEME);
    expect(schemeReading(g, "urn:example:source/json#Source")).toBe(JSON_SCHEME);
    expect(schemeReading(g, "urn:example:none")).toBeUndefined();
    expect(schemesOf(g).map((s) => s.iri).sort()).toEqual([JSON_SCHEME, XML_SCHEME]);
    const h = harness();
    h.session.setInputs(h.inputs());
    expect(h.session.getState().libraries).toEqual([]);
  });
});

describe("the sample session", () => {
  it("runs nothing on an edit, a new sample, a new format or a new form, and compiles nothing", async () => {
    const h = harness();
    h.session.setInputs(h.inputs());
    h.session.setSample(XML());
    h.session.setInputs(h.inputs({ graph: Graph.parse(workspace("policies").compileBody), context: "1" }));
    h.session.setInputs(h.inputs({ scheme: JSON_SCHEME }));
    h.session.setFormat("application/json");
    h.session.chooseForm("rml");
    h.session.setSample(recordedRun("json").sample);
    await new Promise((r) => setTimeout(r, 20));
    expect(h.log.compiled).toHaveLength(0);
    expect(h.log.runs).toHaveLength(0);
    expect(h.session.getState().run).toEqual({ phase: "idle" });
  });

  it("compiles on Run only when the mapping part or another part has changed since the last compilation", async () => {
    const h = harness();
    h.session.setInputs(h.inputs());
    h.session.setSample(XML());
    await ran(h);
    expect(h.log.compiled).toHaveLength(1);
    expect(h.log.runs).toHaveLength(1);
    expect(h.log.runs[0]).toEqual({ job: "job-1", body: XML(), mediaType: "application/xml" });
    // the same inputs, a new sample of the same kind: run again over the same compilation
    await ran(h);
    expect(h.log.compiled).toHaveLength(1);
    expect(h.log.runs).toHaveLength(2);
    expect(h.log.runs[1].job).toBe("job-1");
    // the mapping part is edited
    h.session.setInputs(h.inputs({ graph: Graph.parse(workspace("policies").compileBody) }));
    expect(h.session.getState().compilationCurrent).toBe(false);
    await ran(h);
    expect(h.log.compiled).toHaveLength(2);
    expect(h.log.runs[2].job).toBe("job-2");
    expect(h.log.forgotten).toEqual(["job-1"]);
    expect(h.session.getState().compilationCurrent).toBe(true);
    // another part is saved
    h.session.setInputs({ ...h.inputs({ graph: h.log.compiled[1] }), context: "1" });
    await ran(h);
    expect(h.log.compiled).toHaveLength(3);
    expect(h.log.forgotten).toEqual(["job-1", "job-2"]);
  });

  it("leaves a compilation it did not make alone, lists its forms before it compiles, and compiles when Run is pressed", async () => {
    const h = harness();
    h.session.setInputs(h.inputs({ scheme: JSON_SCHEME }));
    await h.session.refresh();
    const before = h.session.getState();
    expect(before.forms.map((f) => f.kind)).toEqual(["jolt", "rml"]);
    expect(before.compilationCurrent).toBe(false);
    h.session.setSample(recordedRun("json").sample);
    await ran(h);
    expect(h.log.compiled).toHaveLength(1);
    expect(h.log.forgotten).toEqual([]);
  });

  it("offers no Run for an RML form, and says in words that it waits on a runtime", async () => {
    const h = harness();
    h.session.setInputs(h.inputs({ scheme: JSON_SCHEME }));
    h.session.setSample(recordedRun("json").sample);
    await ran(h);
    expect(h.session.getState().form?.kind).toBe("jolt");
    expect(h.session.getState().canRun).toBe(true);
    h.session.chooseForm("rml");
    const state = h.session.getState();
    expect(state.form?.kind).toBe("rml");
    expect(state.canRun).toBe(false);
    expect(state.blocked).toBe(WAITS);
    expect(state.blocked).toMatch(/waits on an RML runtime/i);
    expect(state.blocked).not.toMatch(/\b[A-Z]{2,}-\d+\b/);
    const runs = h.log.runs.length;
    await h.session.run();
    expect(h.log.runs).toHaveLength(runs);
    h.session.chooseForm("jolt");
    expect(h.session.getState().canRun).toBe(true);
  });

  it("says when the sample is not in the format the chosen form reads, and when there is no sample", async () => {
    const h = harness();
    h.session.setInputs(h.inputs());
    expect(h.session.getState().blocked).toBe("Give a sample to run.");
    h.session.setSample(XML());
    await ran(h);
    h.session.chooseForm("xslt");
    h.session.setFormat("text/turtle");
    // a new format forgets the choice, so the author chooses again
    expect(h.session.getState().blocked).toBeUndefined();
    h.session.chooseForm("xslt");
    expect(h.session.getState().blocked).toBe("XSLT 3.0 reads XML, and this sample is Turtle. Change the sample's format or pick another form.");
    expect(h.session.getState().canRun).toBe(false);
  });

  it("runs a sample no form of the chosen scheme reads, over the other schemes of the part, and says so", async () => {
    const h = harness();
    h.session.setInputs(h.inputs({ scheme: JSON_SCHEME }));
    h.session.setSample(XML());
    await ran(h);
    const state = h.session.getState();
    expect(state.form?.kind).toBe("jolt");
    expect(state.blocked).toBeUndefined();
    expect(state.note).toBe("No form of this scheme reads a XML sample. The run covers the schemes of the mapping part that do.");
    expect(state.run.phase).toBe("complete");
  });

  it("takes the form from the sample's format unless the author chose one, and forgets the choice when the scheme or the format changes", async () => {
    const h = harness();
    h.session.setInputs(h.inputs({ scheme: JSON_SCHEME }));
    h.session.setSample(recordedRun("json").sample);
    await ran(h);
    h.session.chooseForm("rml");
    h.session.setInputs(h.inputs({ scheme: XML_SCHEME }));
    expect(h.session.getState().form?.kind).toBe("xslt");
    h.session.setInputs(h.inputs({ scheme: JSON_SCHEME }));
    h.session.chooseForm("rml");
    h.session.setFormat("application/json");
    expect(h.session.getState().form?.kind).toBe("jolt");
  });

  it("keeps the counts of the last run and marks them out of date once the scheme, another part, the sample or its format changes", async () => {
    const h = harness();
    h.session.setInputs(h.inputs());
    h.session.setSample(XML());
    expect(h.session.getState().last).toBeUndefined();
    expect(h.session.getState().stale).toBe(false);
    await ran(h);
    const first = h.session.getState();
    expect(first.run.phase).toBe("complete");
    expect(first.last?.parts.length).toBeGreaterThan(0);
    expect(first.stale).toBe(false);
    // each kind of edit marks them, and putting the thing back makes them current again, since they are the counts of that content
    h.session.setInputs(h.inputs({ graph: Graph.parse(workspace("policies").compileBody) }));
    expect(h.session.getState().stale).toBe(true);
    expect(h.session.getState().last).toBe(first.last);
    h.session.setInputs(h.inputs());
    expect(h.session.getState().stale).toBe(false);
    h.session.setInputs(h.inputs({ context: "2" }));
    expect(h.session.getState().stale).toBe(true);
    h.session.setInputs(h.inputs());
    h.session.setSample(`${XML()}\n`);
    expect(h.session.getState().stale).toBe(true);
    h.session.setSample(XML());
    expect(h.session.getState().stale).toBe(false);
    h.session.setFormat("text/turtle");
    expect(h.session.getState().stale).toBe(true);
    // a new run makes the counts current
    h.session.setFormat("application/xml");
    h.session.setInputs(h.inputs({ context: "3" }));
    expect(h.session.getState().stale).toBe(true);
    await ran(h);
    expect(h.session.getState().stale).toBe(false);
    expect(h.session.getState().last).not.toBe(first.last);
  });

  it("keeps the last run's counts when a later run fails, and says why", async () => {
    const h = harness();
    h.session.setInputs(h.inputs());
    h.session.setSample(XML());
    await ran(h);
    const last = h.session.getState().last;
    h.fail("The compile job could not be read, so nothing was run.");
    await ran(h);
    expect(h.session.getState().run).toMatchObject({ phase: "failed", message: "The compile job could not be read, so nothing was run." });
    expect(h.session.getState().last).toBe(last);
  });

  it("gives a run's frames to the output explorer as parts, the report first and an artefact for each mapping, with the engine the report names", async () => {
    const x = harness();
    x.session.setInputs(x.inputs());
    x.session.setSample(XML());
    await ran(x);
    const state = x.session.getState();
    const parts = state.run.phase === "complete" ? state.run.parts : [];
    expect(parts.map((p) => p.role)).toEqual(["report", "artefact", "artefact", "artefact", "artefact", "artefact", "artefact"]);
    expect(state.last?.parts).toEqual(parts);
    expect(parts[1]).toMatchObject({ mediaType: "application/n-triples", path: "0/Cover.nt", group: "urn:example:mapping/xml#Cover", step: 0 });
    expect(engineOf(parts, Graph.parse)).toBe("Saxon-HE 12.5, XSLT 3.0");
    const result = runResult(parts);
    expect(result.strata).toBe(1);
    expect([...result.lines.keys()]).toContain("urn:example:mapping/xml#Policy");
    expect(result.lines.get("urn:example:mapping/xml#Policy")![0].lines.length).toBeGreaterThan(0);

    const t = harness("catalogue");
    t.session.setInputs(t.inputs());
    t.session.setSample(recordedRun("turtle").sample);
    expect(t.session.getState().format).toBe("text/turtle");
    await ran(t);
    const turtle = t.session.getState();
    expect(turtle.run.phase).toBe("complete");
    const rdf = turtle.last!.parts;
    expect(rdf[0].role).toBe("report");
    expect(engineOf(rdf, Graph.parse)).toMatch(/^mork_rdf .* on Oxigraph /);
    expect(t.log.runs[0].mediaType).toBe("text/turtle");
  });

  it("keeps the sample and its format in the browser's storage for the workspace, and a new session reads them", () => {
    const h = harness();
    h.session.setSample(XML(), "policies.xml");
    expect(h.session.getState()).toMatchObject({ sample: XML(), format: "application/xml" });
    h.session.setFormat("application/json");
    expect(h.session.getState().format).toBe("application/json");
  });

  it("reads a sample's format when it first has text and when an edit makes it another kind of document, and typing in it never undoes the author's choice", () => {
    const h = harness();
    h.session.setSample("<a>");
    expect(h.session.getState().format).toBe("application/xml");
    h.session.setFormat("text/turtle");
    h.session.setSample("<a><b/>");
    expect(h.session.getState().format).toBe("text/turtle");
    h.session.setSample('{"a": 1}');
    expect(h.session.getState().format).toBe("application/json");
    h.session.setSample(undefined);
    h.session.setSample("@prefix a: <urn:a#> . a:s a:p a:o .");
    expect(h.session.getState().format).toBe("text/turtle");
  });
});
