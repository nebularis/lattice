// SPDX-License-Identifier: MPL-2.0
// The persistence simulator's pure part (SVA-P4) over the facility sample. The steps it builds are held against the contract's two sample steps and
// against what the run worker's own test, PersistenceStepTest, sends for each kind of write.

import { readFileSync } from "node:fs";
import { Parser } from "n3";
import { describe, expect, it } from "vitest";
import { readLanding, drawing, placeId, type LandingPlaces, type LandingTarget, type TargetOperation } from "./landing";
import {
  EMPTY_WORLD, REQUEST_LIMIT_BYTES, STEP_GRAPH, WRITES, addLines, aggregateLines, applyDelta, buildStep, changedGraphs, encodeForUri, epochOf, graphsOf, initialWorld, isLit, litOf,
  mint, normaliseLine, ntLine, ntTerm, operationsFor, placesByIri, positionOf, readDelta, readOutcome, renderGraph, worldSize, worldTrig,
  type Built, type Delta, type World,
} from "./simulator";
import { INITIAL, forgetSims, getSim, setSim, stepBack } from "./simulatorStore";

const fixture = (name: string) => readFileSync(new URL(`../../e2e/fixtures/${name}`, import.meta.url), "utf-8");
const sample = (name: string) => readFileSync(new URL(`../../../../contracts/config-studio/samples/${name}`, import.meta.url), "utf-8");
const reading = readLanding(fixture("compiled-profile-facility.ttl"));
if (reading.state !== "ready") throw new Error("predates");
const doc: LandingPlaces = reading.doc;
const facility = doc.targets.find((t) => t.id === "Facility")!;
const borrower = doc.targets.find((t) => t.id === "Borrower")!;
const operation = (target: LandingTarget, name: string): TargetOperation => target.operations.find((o) => o.operation === name)!;

const EX = "https://example.org/lending#";
const ROOT = `${EX}facility-1`;
const PAT = "https://www.nebularis.org/neuro-semantic/lattice/persistence-store#";
const CST = "https://www.nebularis.org/neuro-semantic/lattice/config-studio#";

// --- reading a TriG as a set of statements ------------------------------------------------------------------------------------

interface Read {
  /** The sample world, each graph with its lines. */
  world: World;
  /** Every statement of the graphs the step uses, a parameter's blank node written as the name it gives, so two steps compare by what they say. */
  step: string[];
}

function readTrig(trig: string): Read {
  const quads = new Parser({ format: "application/trig" }).parse(trig);
  const nameOf = new Map<string, string>();
  for (const q of quads) if (q.predicate.value === `${CST}parameterName`) nameOf.set(q.subject.value, q.object.value);
  const term = (t: { termType: string; value: string; datatype?: { value: string }; language?: string }) => (t.termType === "BlankNode" ? `_:param-${nameOf.get(t.value) ?? t.value}` : ntTerm(t));
  const graphs: Record<string, string[]> = {};
  const step: string[] = [];
  for (const q of quads) {
    const graph = q.graph.value;
    const line = `${term(q.subject)} ${term(q.predicate)} ${term(q.object)} .`;
    if (graph === STEP_GRAPH || graph.startsWith(`${STEP_GRAPH}/`)) step.push(`${graph === STEP_GRAPH ? "" : graph.slice(STEP_GRAPH.length)} ${line}`);
    else (graphs[graph] ??= []).push(line);
  }
  const world: World = { graphs: Object.fromEntries(Object.entries(graphs).map(([g, lines]) => [g, [...lines].sort()])) };
  return { world, step: step.sort() };
}

const lines = (read: Read, graph: string) => read.world.graphs[graph] ?? [];
const SAMPLE_CREATE = readTrig(sample("facility-step-create.trig"));
const SAMPLE_REPLACE = readTrig(sample("facility-step-replace.trig"));

function worldOf(read: Read): World {
  let world = EMPTY_WORLD;
  for (const [graph, ls] of Object.entries(read.world.graphs)) world = addLines(world, graph, ls);
  return world;
}

/** The lines the sample step holds in a payload graph, `""` for `step/payload`. */
const payloadOf = (read: Read, name: string): string[] => {
  const prefix = name === "" ? "/payload " : `/payload/${name} `;
  return read.step.filter((s) => s.startsWith(prefix)).map((s) => s.slice(prefix.length));
};

function built(b: Built): { trig: string; parameters: Record<string, string>; bytes: number } {
  if ("problem" in b) throw new Error(b.problem);
  return b;
}

/** The statements of the step a body holds, with the identifiers the simulator mints put where a sample states its own. */
function stepOf(b: Built, substitutions: Record<string, string> = {}): string[] {
  let trig = built(b).trig;
  for (const [from, to] of Object.entries(substitutions)) trig = trig.split(from).join(to);
  return readTrig(trig).step;
}

describe("the sample world", () => {
  it("starts with the dataset's epoch where the compiled profile binds a dataset", () => {
    const world = initialWorld(facility);
    expect(world.graphs).toEqual({ "urn:g:dataset": [ntLine("urn:g:dataset", `${PAT}epoch`, `"1"^^<http://www.w3.org/2001/XMLSchema#long>`)] });
    expect(epochOf(world, facility, ROOT)).toBe(1);
    expect(initialWorld(undefined)).toEqual(EMPTY_WORLD);
  });

  it("is one text of TriG for one world, whatever order its lines were put in", () => {
    const a = ntLine(`${EX}a`, `${EX}p`, `"1"`);
    const b = ntLine(`${EX}b`, `${EX}p`, `"2"`);
    const forward = addLines(addLines(EMPTY_WORLD, "urn:g:two", [a, b]), "urn:g:one", [b]);
    const backward = addLines(addLines(EMPTY_WORLD, "urn:g:one", [b]), "urn:g:two", [b, a, a]);
    expect(worldTrig(forward)).toBe(worldTrig(backward));
    expect(worldTrig(forward)).toBe(`GRAPH <urn:g:one> {\n${b}\n}\nGRAPH <urn:g:two> {\n${a}\n${b}\n}`);
    expect(worldTrig(EMPTY_WORLD)).toBe("");
  });

  it("counts its size in the bytes of the TriG a request carries, against the service's 5 MiB", () => {
    const world = addLines(initialWorld(facility), "urn:g:facilities", [ntLine(ROOT, `${EX}facilityReference`, `"FAC-é"`)]);
    const size = worldSize(world);
    expect(size.quads).toBe(2);
    expect(size.bytes).toBe(new TextEncoder().encode(worldTrig(world)).length);
    expect(size.bytes).toBeGreaterThan(worldTrig(world).length);
    expect(size.limit).toBe(5 * 1024 * 1024);
    expect(size.limit).toBe(REQUEST_LIMIT_BYTES);
    expect(size.fraction).toBeCloseTo(size.bytes / (5 * 1024 * 1024), 12);
    expect(worldSize(EMPTY_WORLD)).toEqual({ bytes: 0, quads: 0, limit: REQUEST_LIMIT_BYTES, fraction: 0 });
  });

  it("holds each triple in one form whoever wrote it, so a line from the worker and a line from the form are the same", () => {
    expect(normaliseLine(`<${ROOT}> <${EX}margin> "3.25"^^<http://www.w3.org/2001/XMLSchema#decimal> .`)).toBe(`<${ROOT}> <${EX}margin> "3.25"^^<http://www.w3.org/2001/XMLSchema#decimal> .`);
    expect(normaliseLine(`<${ROOT}> <${EX}name> "x"^^<http://www.w3.org/2001/XMLSchema#string> .`)).toBe(`<${ROOT}> <${EX}name> "x" .`);
    expect(normaliseLine("not a triple")).toBe("not a triple");
  });

  it("reads the position and the graphs of a root as the compiled profile places them", () => {
    const world = worldOf(SAMPLE_REPLACE);
    expect(graphsOf(facility, ROOT)).toEqual({ data: "urn:g:facilities", meta: "urn:g:meta/6" });
    expect(graphsOf(borrower, `${EX}acme`)).toEqual({ data: `urn:g:borrower/${encodeForUri(`${EX}acme`)}`, meta: "urn:g:meta/52" });
    expect(positionOf(world, facility, ROOT)).toBe(2);
    expect(positionOf(initialWorld(facility), facility, ROOT)).toBeUndefined();
    expect(renderGraph({ graph: "urn:g:txlog/{month}", named: true }, { root: ROOT })).toBeNull();
    expect(renderGraph({ graph: "urn:g:txlog/{month}", named: true }, { month: "2026-03" })).toBe("urn:g:txlog/2026-03");
    expect(encodeForUri("https://a/b#c d")).toBe("https%3A%2F%2Fa%2Fb%23c%20d");
  });

  it("finds the aggregate stored for a root through its owned edges and not the facility beside it or a node it only references", () => {
    const world = worldOf(SAMPLE_REPLACE);
    const stored = aggregateLines(addLines(world, "urn:g:facilities", [ntLine(`${EX}facility-2`, `${EX}margin`, `"4.0"^^<http://www.w3.org/2001/XMLSchema#decimal>`), ntLine(`${EX}acme-foods`, `${EX}legalName`, `"Acme"`)]), "urn:g:facilities", ROOT, facility.aggregate.owned);
    expect(stored.length).toBe(lines(SAMPLE_REPLACE, "urn:g:facilities").length);
    expect(stored.some((l) => l.includes("facility-2") || l.includes("acme-foods> <"))).toBe(false);
    expect(stored.some((l) => l.startsWith(`<${EX}drawdown-1> `))).toBe(true);
  });
});

describe("minting", () => {
  it("makes the revision and the transaction from the root's local name and the step's number", () => {
    expect(mint(ROOT, 1)).toMatchObject({ newRev: "urn:rev:facility-1/1", txnId: "urn:txn:facility-1-1" });
    expect(mint(ROOT, 12).other("cause")).toBe("urn:simulator:cause/12");
    expect(mint("https://example.org/a b/c d", 2).newRev).toBe("urn:rev:c%20d/2");
  });
});

describe("a step's TriG", () => {
  const object = (read: Read) => lines(read, "urn:g:facilities");
  const create = (time = "2026-03-31T23:59:58Z") => buildStep({ target: facility, operation: operation(facility, "create-if-absent"), root: ROOT, object: payloadOf(SAMPLE_CREATE, ""), world: initialWorld(facility), steps: 0, time });
  const replaceWith = (margin: string, extra: Partial<Parameters<typeof buildStep>[0]> = {}) => {
    const next = object(SAMPLE_REPLACE).map((l) => l.replace(`"3.25"`, `"${margin}"`));
    return buildStep({ target: facility, operation: operation(facility, "cas-replace"), root: ROOT, object: next, world: worldOf(SAMPLE_REPLACE), steps: 2, time: "2026-04-02T09:30:00Z", ...extra });
  };

  it("for a create is the contract's sample, the identifiers the sample states itself being the ones minted", () => {
    expect(stepOf(create(), { "urn:rev:facility-1/1": "urn:rev:facility-1/1", "urn:txn:facility-1-1": "urn:txn:facility-1-create" })).toEqual(SAMPLE_CREATE.step);
    expect(readTrig(built(create()).trig).world).toEqual(SAMPLE_CREATE.world);
  });

  it("for a delta replace is the contract's sample, with what it asserts and what it retracts computed from the object against the world", () => {
    expect(stepOf(replaceWith("3.5"), { "urn:txn:facility-1-3": "urn:txn:facility-1-margin" })).toEqual(SAMPLE_REPLACE.step);
    expect(readTrig(built(replaceWith("3.5")).trig).world).toEqual(SAMPLE_REPLACE.world);
  });

  it("sends, for each kind of write, the parameters PersistenceStepTest sends and the payload graphs its operation reads", () => {
    const sentCreate = built(create());
    expect(sentCreate.parameters).toEqual({ epoch: "1", newRev: "urn:rev:facility-1/1", root: ROOT, txnId: "urn:txn:facility-1-1" });
    const delta = built(replaceWith("3.5"));
    expect(delta.parameters).toEqual({ epoch: "1", expectedSeq: "2", newRev: "urn:rev:facility-1/3", nextSeq: "3", root: ROOT, txnId: "urn:txn:facility-1-3" });
    const tombstone = built(buildStep({ target: facility, operation: operation(facility, "tombstone-delete"), root: ROOT, object: [], world: worldOf(SAMPLE_REPLACE), steps: 2, time: "2026-04-02T09:30:00Z" }));
    expect(tombstone.parameters).toEqual({
      actor: "urn:simulator:actor/3", cause: "urn:simulator:cause/3", epoch: "1", expectedSeq: "2", newRev: "urn:rev:facility-1/3", nextSeq: "3", root: ROOT, txnId: "urn:txn:facility-1-3",
    });
    expect(readTrig(tombstone.trig).step.filter((s) => s.startsWith("/payload"))).toEqual([]);
    // A whole replace reads its triples from step/payload and what it adds and removes from the graphs its parameters name.
    const whole = readTrig(built(replaceWith("3.5", { operation: operation(facility, "replace-whole") })).trig).step.filter((s) => s.startsWith("/payload"));
    expect(whole.filter((s) => s.startsWith("/payload ")).length).toBe(lines(SAMPLE_REPLACE, "urn:g:facilities").length);
    expect(whole.filter((s) => s.startsWith("/payload/assertTriples ")).length).toBe(1);
    expect(whole.filter((s) => s.startsWith("/payload/retractTriples ")).length).toBe(1);
    // A create reads only its payload, and a delta replace reads what it asserts there and what it retracts from its own graph.
    const kinds = (t: string) => new Set(readTrig(t).step.filter((s) => s.startsWith("/payload")).map((s) => s.split(" ")[0]));
    expect(kinds(sentCreate.trig)).toEqual(new Set(["/payload"]));
    expect(kinds(delta.trig)).toEqual(new Set(["/payload", "/payload/retractTriples"]));
  });

  it("never gives the request digest, since the caller library computes it", () => {
    for (const t of [create(), replaceWith("3.5")]) expect(Object.keys(built(t).parameters)).not.toContain("requestDigest");
  });

  it("sends as another writer from the position before the world's, so the guard has something to refuse", () => {
    const other = built(replaceWith("3.5", { asAnotherWriter: true }));
    expect(other.parameters).toMatchObject({ expectedSeq: "1", nextSeq: "2" });
    const expected = readTrig(sample("facility-step-replace.trig").replace('parameterValue "2"', 'parameterValue "1"')).step.find((s) => s.includes("_:param-expectedSeq"));
    expect(readTrig(other.trig).step.some((s) => s === expected)).toBe(true);
  });

  it("is the same on a repeat and with the world's lines added in another order, so a step sent twice is the same step", () => {
    expect(built(replaceWith("3.5")).trig).toBe(built(replaceWith("3.5")).trig);
    expect(built(create()).trig).toBe(built(create()).trig);
    const reversed = Object.entries(SAMPLE_REPLACE.world.graphs).reverse().reduce((w, [g, ls]) => addLines(w, g, [...ls].reverse()), EMPTY_WORLD);
    expect(built(replaceWith("3.5", { world: reversed })).trig).toBe(built(replaceWith("3.5")).trig);
  });

  it("is a step of the next number once a step has been taken, and the same number while none is", () => {
    expect(built(create()).parameters.txnId).toBe("urn:txn:facility-1-1");
    expect(built(replaceWith("3.5", { steps: 5 })).parameters).toMatchObject({ newRev: "urn:rev:facility-1/6", txnId: "urn:txn:facility-1-6" });
  });

  it("says why a step cannot be built, rather than sending one the worker would refuse", () => {
    const problem = (b: Built) => ("problem" in b ? b.problem : "");
    expect(problem(buildStep({ target: facility, operation: operation(facility, "cas-replace"), root: ROOT, object: [], world: initialWorld(facility), steps: 0, time: "2026-01-15T09:00:00Z" }))).toMatch(/no version row/);
    expect(problem(create("yesterday"))).toMatch(/xsd:dateTime/);
    expect(problem(buildStep({ target: facility, operation: operation(facility, "create-if-absent"), root: "not an iri", object: [], world: EMPTY_WORLD, steps: 0, time: "2026-01-15T09:00:00Z" }))).toMatch(/not an IRI/);
    expect(problem(buildStep({ target: facility, operation: operation(facility, "gap-scan-audit"), root: ROOT, object: [], world: EMPTY_WORLD, steps: 0, time: "2026-01-15T09:00:00Z" }))).toMatch(/Audit/);
    expect(problem(buildStep({ target: facility, operation: operation(facility, "create-if-absent"), root: ROOT, object: [], world: EMPTY_WORLD, steps: 0, time: "2026-01-15T09:00:00Z", asAnotherWriter: true }))).toMatch(/no position/);
    expect(problem(create())).toBe("");
    const blank = buildStep({ target: facility, operation: operation(facility, "create-if-absent"), root: ROOT, object: [`<${ROOT}> <${EX}margin> _:b .`], world: EMPTY_WORLD, steps: 0, time: "2026-01-15T09:00:00Z" });
    expect(problem(blank)).toMatch(/blank node/);
  });

  it("measures the request it builds, the world and the step together", () => {
    const b = built(create());
    expect(b.bytes).toBe(new TextEncoder().encode(b.trig).length);
    expect(b.bytes).toBeGreaterThan(worldSize(initialWorld(facility)).bytes);
  });

  it("offers a write only where the profile has an operation of a kind a step runs, the delta replace before the whole one, and no append", () => {
    expect(operationsFor(facility, "create").map((o) => o.operation)).toEqual(["create-if-absent"]);
    expect(operationsFor(facility, "replace").map((o) => o.operation)).toEqual(["cas-replace", "replace-whole"]);
    expect(operationsFor(facility, "delete").map((o) => o.operation)).toEqual(["tombstone-delete"]);
    expect(operationsFor(facility, "append")).toEqual([]);
    expect(WRITES.map((w) => w.write)).toEqual(["create", "replace", "delete", "append"]);
    const audits = facility.operations.filter((o) => o.kind === "Audit");
    expect(audits.length).toBeGreaterThan(0);
    for (const a of audits) for (const w of WRITES) expect(operationsFor(facility, w.write)).not.toContain(a);
  });
});

// --- reading the parts and moving the world -----------------------------------------------------------------------------------------

const place = (target: string, local: string) => `https://example.org/lending/${target}/compiled/profile#place-${local}`;
const FACILITY_CREATE: Delta = {
  places: [
    { place: place("Facility", "data-urn%3Ag%3Afacilities"), role: "DataRole", graphs: [{ graph: "urn:g:facilities", added: [ntLine(ROOT, `${EX}margin`, `"3.25"^^<http://www.w3.org/2001/XMLSchema#decimal>`)], removed: [] }] },
    { place: place("Facility", "meta-urn%3Ag%3Ameta%2F6"), role: "MetaRole", graphs: [{ graph: "urn:g:meta/6", added: [ntLine(ROOT, `${PAT}seq`, `"1"^^<http://www.w3.org/2001/XMLSchema#long>`)], removed: [] }] },
    { place: place("Facility", "txn-urn%3Ag%3Atxn"), role: "TxnRole", graphs: [{ graph: "urn:g:txn", added: [ntLine("urn:txn:facility-1-1", `${PAT}rev`, "<urn:rev:facility-1/1>")], removed: [] }] },
    { place: place("Facility", "log-urn%3Ag%3Atxlog%2F%7Bmonth%7D"), role: "LogRole", graphs: [{ graph: "urn:g:txlog/2026-01", added: [ntLine("urn:rev:facility-1/1", `${PAT}x`, `"1"`)], removed: [] }] },
    { place: place("Facility", "patch-%7BnewRev%7D%2Fadd"), role: "PatchRole", graphs: [{ graph: "urn:rev:facility-1/1/add", added: [ntLine(ROOT, `${EX}margin`, `"3.25"^^<http://www.w3.org/2001/XMLSchema#decimal>`)], removed: [] }] },
  ],
  unplaced: [],
};

describe("the delta", () => {
  it("is read from the part's JSON, and nothing is read from text that is not the contract's", () => {
    expect(readDelta(JSON.stringify(FACILITY_CREATE))).toEqual(FACILITY_CREATE);
    expect(readDelta("not json")).toBeUndefined();
    expect(readDelta(JSON.stringify({ places: [] }))).toBeUndefined();
    expect(readDelta(undefined)).toBeUndefined();
    expect(readOutcome(JSON.stringify({ outcome: "lostRace", classification: "PreconditionFailed", reason: "r", engine: "Jena" }))).toEqual({ outcome: "lostRace", classification: "PreconditionFailed", reason: "r", engine: "Jena" });
    expect(readOutcome("{}")).toBeUndefined();
  });

  it("moves the world forward by what it removes and what it adds, in each graph it changed once", () => {
    const before = initialWorld(facility);
    const after = applyDelta(before, FACILITY_CREATE);
    expect(Object.keys(after.graphs).sort()).toEqual(["urn:g:dataset", "urn:g:facilities", "urn:g:meta/6", "urn:g:txlog/2026-01", "urn:g:txn", "urn:rev:facility-1/1/add"]);
    expect(positionOf(after, facility, ROOT)).toBe(1);
    const undone = applyDelta(after, { places: [{ place: "p", role: "DataRole", graphs: [{ graph: "urn:g:facilities", added: [], removed: FACILITY_CREATE.places[0].graphs[0].added }] }], unplaced: [] });
    expect(undone.graphs["urn:g:facilities"]).toBeUndefined();
    // a graph listed under two places is applied once
    const twice: Delta = { places: [FACILITY_CREATE.places[0], { ...FACILITY_CREATE.places[0], place: "another" }], unplaced: [] };
    expect(changedGraphs(twice)).toHaveLength(1);
    expect(applyDelta(before, twice).graphs["urn:g:facilities"]).toHaveLength(1);
    // the graphs no place states are applied as well
    expect(applyDelta(before, { places: [], unplaced: [{ graph: "urn:g:stray", added: [ntLine(ROOT, `${EX}p`, `"1"`)], removed: [] }] }).graphs["urn:g:stray"]).toHaveLength(1);
  });
});

describe("lighting the canvas", () => {
  const drawn = drawing(doc, "aggregate", "Facility");
  const lit = (delta: Delta) => drawn.nodes.filter((n) => n.kind === "place" && isLit(n.place!, litOf(delta))).map((n) => n.place!.kind).sort();

  it("lights the place of each graph the step changed by the place's IRI and role, and none of the others", () => {
    expect(lit(FACILITY_CREATE)).toEqual(["data-graph", "patch-log-add", "receipt", "transaction-claim", "version-row"]);
    expect(drawn.nodes.filter((n) => n.kind === "place")).toHaveLength(7);
  });

  it("lights a place a target shares by either target's IRI for it, since the canvas draws it once", () => {
    const both = structuredClone(doc);
    for (const t of both.targets) t.profiles.push("urn:p:both");
    const together = drawing(both, "profile", "urn:p:both");
    const shared = together.nodes.find((n) => n.kind === "place" && n.place!.kind === "transaction-claim")!;
    expect(shared.targets).toEqual(["Borrower", "Facility"]);
    expect(shared.place!.iris).toEqual([place("Borrower", "txn-urn%3Ag%3Atxn"), place("Facility", "txn-urn%3Ag%3Atxn")]);
    for (const iri of shared.place!.iris) {
      const via: Delta = { places: [{ place: iri, role: "TxnRole", graphs: [] }], unplaced: [] };
      expect(together.nodes.filter((n) => n.kind === "place" && isLit(n.place!, litOf(via))).map((n) => n.place!.kind)).toEqual(["transaction-claim"]);
    }
  });

  it("does not light a place by a graph's name, by a likeness of an IRI, or by a role the place does not have", () => {
    const named: Delta = { places: [], unplaced: [{ graph: "urn:g:facilities", added: [], removed: [] }] };
    expect(lit(named)).toEqual([]);
    const near: Delta = { places: [{ place: `${place("Facility", "data-urn%3Ag%3Afacilities")}-copy`, role: "DataRole", graphs: [] }], unplaced: [] };
    expect(lit(near)).toEqual([]);
    const wrongRole: Delta = { places: [{ place: place("Facility", "data-urn%3Ag%3Afacilities"), role: "MetaRole", graphs: [] }], unplaced: [] };
    expect(lit(wrongRole)).toEqual([]);
    expect(lit({ places: [], unplaced: [] })).toEqual([]);
  });

  it("names the place an IRI is, for the delta to group by", () => {
    const index = placesByIri(doc);
    expect(index.get(place("Facility", "patch-%7BnewRev%7D%2Fadd"))?.place.label).toBe("Patch log, the triples added");
    expect(placeId(index.get(place("Facility", "patch-%7BnewRev%7D%2Fadd"))!.place)).toBe(drawn.nodes.find((n) => n.place?.kind === "patch-log-add")!.id);
  });
});

describe("stepping back", () => {
  it("removes the last step and restores the world before it, and does nothing where there is no step", () => {
    forgetSims();
    const ws = "w";
    const start = initialWorld(facility);
    stepBack(ws);
    expect(getSim(ws)).toEqual(INITIAL);
    const one = applyDelta(start, FACILITY_CREATE);
    const two = addLines(one, "urn:g:facilities", [ntLine(ROOT, `${EX}more`, `"1"`)]);
    setSim(ws, {
      world: two,
      lit: litOf(FACILITY_CREATE),
      steps: [
        { number: 1, write: "create", operation: "create-if-absent", root: ROOT, time: "t", before: start },
        { number: 2, write: "replace", operation: "cas-replace", root: ROOT, time: "t", before: one },
      ],
    });
    stepBack(ws);
    expect(getSim(ws).world).toBe(one);
    expect(getSim(ws).steps.map((s) => s.number)).toEqual([1]);
    expect(getSim(ws).lit).toEqual([]);
    stepBack(ws);
    expect(getSim(ws).world).toBe(start);
    expect(getSim(ws).steps).toEqual([]);
    stepBack(ws);
    expect(getSim(ws).world).toBe(start);
    forgetSims();
  });

  it("keeps a world for each workspace", () => {
    forgetSims();
    setSim("a", { world: initialWorld(facility) });
    expect(getSim("b").world).toBeUndefined();
    forgetSims();
  });
});
