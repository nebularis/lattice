// SPDX-License-Identifier: MPL-2.0
// The persistence simulator's pure part (SVA-P4, ADR-A154 decisions 9 and 11). The sample world is the tab's, a set of quads kept as lines of N-Triples
// in each graph, and a step is built from it, the object and the operation as the contract's section "A persistence step" says. The worker holds
// nothing between steps, so the TriG built here is the whole of the step. Every function is a pure function of its arguments and never reads a clock.
// The browser does not judge a write. It builds the request, and the checks, the delta and the outcome are the worker's, read back from its parts.

import { Parser } from "n3";
import type { LandingPlaces, LandingTarget, Place, TargetOperation } from "./landing";

const PAT = "https://www.nebularis.org/neuro-semantic/lattice/persistence-store#";
const CST = "https://www.nebularis.org/neuro-semantic/lattice/config-studio#";
const XSD = "http://www.w3.org/2001/XMLSchema#";

export const STEP_GRAPH = "urn:lattice:studio:step";
export const PAYLOAD_GRAPH = `${STEP_GRAPH}/payload`;

/** The service's limit on a request body, `StudioApi.MAX_BODY_BYTES`, which holds the sample world and the step together. */
export const REQUEST_LIMIT_BYTES = 5 * 1024 * 1024;

const compare = (a: string, b: string) => (a < b ? -1 : a > b ? 1 : 0);

// --- terms as lines of N-Triples ------------------------------------------------------------------------------------------------

function escapeString(text: string): string {
  return text.replace(/[\\"\n\r\t]/g, (c) => (c === "\\" ? "\\\\" : c === '"' ? '\\"' : c === "\n" ? "\\n" : c === "\r" ? "\\r" : "\\t"));
}

/** A term as N-Triples writes it. A string literal carries no datatype and a language literal no datatype but its tag, as RDF 1.1 writes them. */
export function ntTerm(term: { termType: string; value: string; datatype?: { value: string }; language?: string }): string {
  if (term.termType === "NamedNode") return `<${term.value}>`;
  if (term.termType === "BlankNode") return `_:${term.value}`;
  const lexical = `"${escapeString(term.value)}"`;
  if (term.language) return `${lexical}@${term.language}`;
  if (term.datatype && term.datatype.value !== `${XSD}string`) return `${lexical}^^<${term.datatype.value}>`;
  return lexical;
}

export function ntLine(s: string, p: string, o: string): string {
  return `<${s}> <${p}> ${o} .`;
}

/**
 * The line a statement of N-Triples is in the form this module writes, so that two lines of the same triple are the same text whoever wrote
 * them. Lines that are not N-Triples are returned as they are, and the worker refuses them.
 */
export function normaliseLine(line: string): string {
  try {
    const quads = new Parser({ format: "N-Triples" }).parse(line);
    if (quads.length === 1) {
      const q = quads[0];
      return `${ntTerm(q.subject)} ${ntTerm(q.predicate)} ${ntTerm(q.object)} .`;
    }
  } catch {
    // left as written
  }
  return line;
}

/** The parts of a line of N-Triples, for following an edge. Null for a line that is not one. */
export function splitLine(line: string): { s: string; p: string; o: string } | null {
  try {
    const quads = new Parser({ format: "N-Triples" }).parse(line);
    if (quads.length !== 1) return null;
    const q = quads[0];
    return { s: ntTerm(q.subject), p: ntTerm(q.predicate), o: ntTerm(q.object) };
  } catch {
    return null;
  }
}

const bytes = (text: string) => new TextEncoder().encode(text);

/** The lines in the order of their UTF-8 bytes, as the worker orders them, with none twice. */
export function sortedLines(lines: Iterable<string>): string[] {
  const unique = [...new Set(lines)];
  return unique
    .map((line) => ({ line, key: bytes(line) }))
    .sort((a, b) => {
      const n = Math.min(a.key.length, b.key.length);
      for (let i = 0; i < n; i++) if (a.key[i] !== b.key[i]) return a.key[i] - b.key[i];
      return a.key.length - b.key.length;
    })
    .map((e) => e.line);
}

// --- the sample world ----------------------------------------------------------------------------------------------------------

/** The sample world, each graph by its IRI, the empty string for the default graph, holding its triples as sorted lines of N-Triples. */
export interface World {
  graphs: Record<string, string[]>;
}

export const EMPTY_WORLD: World = { graphs: {} };

function graphBlock(graph: string, lines: string[]): string {
  const body = lines.join("\n");
  return graph === "" ? body : `GRAPH <${graph}> {\n${body}\n}`;
}

/** The world as TriG, the graphs in the order of their IRIs and the lines in the order of their bytes, so one world is always the same text. */
export function worldTrig(world: World): string {
  const names = Object.keys(world.graphs).filter((g) => world.graphs[g].length > 0).sort(compare);
  return names.map((g) => graphBlock(g, world.graphs[g])).join("\n");
}

export function worldQuadCount(world: World): number {
  return Object.values(world.graphs).reduce((n, lines) => n + lines.length, 0);
}

/** How large the world is as the request carries it, in bytes of UTF-8, against the service's limit. */
export function worldSize(world: World): { bytes: number; quads: number; limit: number; fraction: number } {
  const size = bytes(worldTrig(world)).length;
  return { bytes: size, quads: worldQuadCount(world), limit: REQUEST_LIMIT_BYTES, fraction: size / REQUEST_LIMIT_BYTES };
}

function withGraph(world: World, graph: string, lines: string[]): World {
  return { graphs: { ...world.graphs, [graph]: sortedLines(lines) } };
}

/** A world with `lines` added to `graph`. */
export function addLines(world: World, graph: string, lines: readonly string[]): World {
  return withGraph(world, graph, [...(world.graphs[graph] ?? []), ...lines.map(normaliseLine)]);
}

const strip = (value: string | undefined): string | undefined => (value !== undefined && /^<.*>$/.test(value) ? value.slice(1, -1) : value);

/**
 * The world a target starts from, the dataset's epoch at 1 in the dataset graph the operations of its compiled profile bind, so that a template
 * that guards on the dataset's epoch finds it. A target whose operations bind no dataset starts empty.
 */
export function initialWorld(target: LandingTarget | undefined): World {
  const bindings = target?.operations.map((o) => o.bindings).find((b) => b.datasetGraph !== undefined);
  const graph = strip(bindings?.datasetGraph);
  if (!graph) return EMPTY_WORLD;
  const node = strip(bindings?.datasetNode) ?? graph;
  return addLines(EMPTY_WORLD, graph, [ntLine(node, `${PAT}epoch`, `"1"^^<${XSD}long>`)]);
}

/** The percent-encoding `ENCODE_FOR_URI` gives, which the worker renders `{root}` with. */
export function encodeForUri(text: string): string {
  let out = "";
  for (const b of bytes(text)) {
    const c = String.fromCharCode(b);
    out += b < 128 && /[A-Za-z0-9\-_.~]/.test(c) ? c : `%${b.toString(16).toUpperCase().padStart(2, "0")}`;
  }
  return out;
}

export interface Values {
  root?: string;
  newRev?: string;
  month?: string;
}

/** The graph a place names for these values, the template of the closed placeholders rendered as the worker renders it. Null where the template needs a value that is not given. */
export function renderGraph(place: Pick<Place, "graph" | "named">, values: Values): string | null {
  if (!place.named) return place.graph;
  let missing = false;
  const out = place.graph.replace(/\{[^}]*\}/g, (hole) => {
    const value = hole === "{root}" ? (values.root === undefined ? undefined : encodeForUri(values.root)) : hole === "{newRev}" ? values.newRev : hole === "{month}" ? values.month : undefined;
    if (value === undefined) missing = true;
    return value ?? "";
  });
  return missing ? null : out;
}

function placeOfKind(target: LandingTarget, kind: Place["kind"]): Place | undefined {
  return target.places.find((p) => p.kind === kind);
}

/** The graph that holds the root's data, and the graph that holds its version row, as the target's compiled profile places them. Null where the profile has none. */
export function graphsOf(target: LandingTarget, root: string): { data: string | null; meta: string | null } {
  const data = placeOfKind(target, "data-graph");
  const meta = placeOfKind(target, "version-row");
  return { data: data ? renderGraph(data, { root }) : null, meta: meta ? renderGraph(meta, { root }) : null };
}

const lastOf = (iri: string) => iri.slice(Math.max(iri.lastIndexOf("#"), iri.lastIndexOf("/")) + 1);

function numberIn(lines: readonly string[] | undefined, subject: string, predicate: string): number | undefined {
  const start = `<${subject}> <${predicate}> `;
  for (const line of lines ?? []) {
    if (!line.startsWith(start)) continue;
    const m = /^"(-?\d+)"\^\^<[^>]*>/.exec(line.slice(start.length)) ?? /^"(-?\d+)"/.exec(line.slice(start.length));
    if (m) return Number(m[1]);
  }
  return undefined;
}

/** The position of the root's version row in the world, its `pat:seq`, or undefined where the world has none, so that nothing is stored. */
export function positionOf(world: World, target: LandingTarget, root: string): number | undefined {
  const { meta } = graphsOf(target, root);
  return meta === null ? undefined : numberIn(world.graphs[meta], root, `${PAT}seq`);
}

/** The epoch a step is written at, the dataset's where the profile binds a dataset and the world holds its epoch, else the root's row's, else 1. */
export function epochOf(world: World, target: LandingTarget, root: string): number {
  const bindings = target.operations.map((o) => o.bindings).find((b) => b.datasetGraph !== undefined);
  const graph = strip(bindings?.datasetGraph);
  if (graph) {
    const found = numberIn(world.graphs[graph], strip(bindings?.datasetNode) ?? graph, `${PAT}epoch`);
    if (found !== undefined) return found;
  }
  const { meta } = graphsOf(target, root);
  return (meta === null ? undefined : numberIn(world.graphs[meta], root, `${PAT}epoch`)) ?? 1;
}

// --- the aggregate in the world ------------------------------------------------------------------------------------------------

interface OwnedEdgeLike {
  property: string;
  inverse: boolean;
  owned: OwnedEdgeLike[];
}

/**
 * The lines of the aggregate that is stored for `root` in the graph that holds its data. They are the root's own, and those of each node reached
 * through an owned edge of the compiled profile, nested as the shape nests them, and never a node the aggregate only references.
 */
export function aggregateLines(world: World, graph: string | null, root: string, owned: readonly OwnedEdgeLike[]): string[] {
  if (graph === null) return [];
  const lines = world.graphs[graph] ?? [];
  const parsed = lines.map((line) => ({ line, parts: splitLine(line) })).filter((e): e is { line: string; parts: { s: string; p: string; o: string } } => e.parts !== null);
  const out = new Set<string>();
  const take = (node: string, edges: readonly OwnedEdgeLike[]) => {
    for (const e of parsed) if (e.parts.s === `<${node}>`) out.add(e.line);
    for (const edge of edges) {
      const members = edge.inverse
        ? parsed.filter((e) => e.parts.p === `<${edge.property}>` && e.parts.o === `<${node}>`).map((e) => e.parts.s)
        : parsed.filter((e) => e.parts.s === `<${node}>` && e.parts.p === `<${edge.property}>`).map((e) => e.parts.o);
      for (const member of members) if (member.startsWith("<")) take(member.slice(1, -1), edge.owned);
    }
  };
  take(root, owned);
  return sortedLines(out);
}

// --- the step ------------------------------------------------------------------------------------------------------------------

/** The kind of write each operation of the simulator is, and the kinds of the compiled profile a step runs (the contract's section "A persistence step"). */
export type WriteKind = "create" | "replace" | "delete" | "append";

export const WRITES: { write: WriteKind; label: string; kinds: string[] }[] = [
  { write: "create", label: "Create", kinds: ["Create"] },
  { write: "replace", label: "Replace", kinds: ["DeltaReplace", "Replace"] },
  { write: "delete", label: "Delete", kinds: ["Tombstone"] },
  { write: "append", label: "Append", kinds: ["AppendVersion"] },
];

/** The kinds a step can run. A step of another kind is a failed step, so the pane offers none. */
export const RUNNABLE_KINDS = ["Create", "Replace", "DeltaReplace", "Tombstone"];

/** The operation a write runs on a target, among those whose kind a step runs. Where two serve one write, the delta replace is the one the profile guards on a position and keeps a log for, so it comes first. */
export function operationsFor(target: LandingTarget, write: WriteKind): TargetOperation[] {
  const kinds = WRITES.find((w) => w.write === write)!.kinds;
  return target.operations
    .filter((o) => kinds.includes(o.kind) && RUNNABLE_KINDS.includes(o.kind))
    .sort((a, b) => kinds.indexOf(a.kind) - kinds.indexOf(b.kind) || compare(a.operation, b.operation));
}

export const TIME = /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?(Z|[+-]\d\d:\d\d)$/;

/**
 * The identifiers a step mints from the tab's step count, the number of steps the world holds plus one. The revision is `urn:rev:` and the root's
 * local name, a slash and the number. The transaction is `urn:txn:`, the local name, a hyphen and the number, and any other IRI the operation
 * declares, such as a tombstone's cause and actor, is `urn:simulator:`, the parameter's name, a slash and the number. The local name is what
 * follows the root's last `#` or `/`, percent-encoded. A step that is sent twice has the same count, so it has the same identifiers and the same
 * request digest, and a step the world applied moves the count on.
 */
export function mint(root: string, step: number): { newRev: string; txnId: string; other: (name: string) => string } {
  const local = encodeURIComponent(lastOf(root) || root);
  return { newRev: `urn:rev:${local}/${step}`, txnId: `urn:txn:${local}-${step}`, other: (name) => `urn:simulator:${encodeURIComponent(name)}/${step}` };
}

export interface StepInput {
  target: LandingTarget;
  operation: TargetOperation;
  root: string;
  /** The object, as lines of N-Triples, for a create or a replace. */
  object: readonly string[];
  world: World;
  /** The steps the world holds. This step is the next. */
  steps: number;
  /** The transaction time the step is stated at, an `xsd:dateTime` with a time zone. */
  time: string;
  /** Sends the step from the position before the world's, so the guard refuses it. */
  asAnotherWriter?: boolean;
}

export type Built = { trig: string; parameters: Record<string, string>; bytes: number } | { problem: string };

const turtleString = (text: string) => `"${escapeString(text)}"`;

/**
 * The body of a `simulate` run for a step, TriG. It holds the world, the graph `urn:lattice:studio:step` and the payload graphs, in an order that
 * is the same for the same arguments. Each declared parameter is given by its name and kind. The root, the epoch, the position expected and the
 * next one are read from the world, the identifiers are minted (`mint`), a payload parameter is the object (`payloadTriples`), what it adds
 * (`assertTriples`) or what it removes (`retractTriples`) against the aggregate the world holds, and the request digest is never given.
 */
export function buildStep(input: StepInput): Built {
  const { target, operation, root, world } = input;
  if (!RUNNABLE_KINDS.includes(operation.kind)) return { problem: `The operation ${operation.operation} is of kind ${operation.kind}, and a step runs only a Create, Replace, DeltaReplace or Tombstone.` };
  if (!TIME.test(input.time)) return { problem: "The transaction time is not an xsd:dateTime with a time zone, for example 2026-01-15T09:00:00Z." };
  if (!/^[A-Za-z][A-Za-z0-9+.\-]*:[^\s<>"{}|\\^`]*$/.test(root)) return { problem: "The root is not an IRI." };
  const n = input.steps + 1;
  const ids = mint(root, n);
  const positioned = operation.parameters.some((p) => p.name === "expectedSeq");
  const stored = positionOf(world, target, root);
  if (positioned && stored === undefined) return { problem: "The sample world holds no version row for the root, so there is no position to expect. Create it first." };
  if (input.asAnotherWriter && !positioned) return { problem: "This operation has no position to expect, so a lost race cannot be shown with it." };
  if (input.asAnotherWriter && (stored ?? 0) < 1) return { problem: "There is no earlier position than the world's to send from." };
  const expected = (stored ?? 0) - (input.asAnotherWriter ? 1 : 0);
  const { data } = graphsOf(target, root);
  const current = aggregateLines(world, data, root, target.aggregate.owned);
  const object = sortedLines(input.object.map(normaliseLine));
  const have = new Set(current);
  const added = object.filter((l) => !have.has(l));
  const wanted = new Set(object);
  const removed = current.filter((l) => !wanted.has(l));
  const parameters: Record<string, string> = {};
  const payloads: Record<string, string[]> = {};
  for (const p of operation.parameters) {
    if (p.kind === "DigestKind") continue;
    if (p.kind === "PayloadKind") {
      const lines = p.name === "payloadTriples" ? object : p.name === "assertTriples" ? added : p.name === "retractTriples" ? removed : undefined;
      if (lines === undefined) return { problem: `The operation declares the payload parameter ${p.name}, and the simulator fills only payloadTriples, assertTriples and retractTriples.` };
      if (lines.some((l) => /^_:|\s_:/.test(l))) return { problem: "The object holds a blank node, and a payload holds none. Give each node an IRI." };
      payloads[p.name] = lines;
      continue;
    }
    const value =
      p.name === "root" ? root
      : p.name === "epoch" ? String(epochOf(world, target, root))
      : p.name === "expectedSeq" ? String(expected)
      : p.name === "nextSeq" ? String(expected + 1)
      : p.name === "newRev" ? ids.newRev
      : p.name === "txnId" ? ids.txnId
      : p.kind === "IriKind" ? ids.other(p.name)
      : undefined;
    if (value === undefined) {
      if (p.required) return { problem: `The operation declares the parameter ${p.name}, of kind ${p.kind}, and the simulator does not fill one like it.` };
      continue;
    }
    parameters[p.name] = value;
  }
  const names = Object.keys(parameters).sort(compare);
  const step = [
    `<${STEP_GRAPH}> a cst:SimulationStepRequest ;`,
    `    cst:forClass <${target.class}> ;`,
    ...(target.deployment === null ? [] : [`    cst:forDeployment <${target.deployment}> ;`]),
    `    cst:operation ${turtleString(operation.operation)} ;`,
    `    cst:transactionTime "${input.time}"^^xsd:dateTime ;`,
    `    cst:parameter ${names.map((name) => `[ cst:parameterName ${turtleString(name)} ; cst:parameterValue ${turtleString(parameters[name])} ]`).join(" ,\n        ")} .`,
  ];
  const blocks: string[] = [`@prefix cst: <${CST}> .\n@prefix xsd: <${XSD}> .`];
  const stored_ = worldTrig(world);
  if (stored_) blocks.push(stored_);
  blocks.push(graphBlock(STEP_GRAPH, step));
  for (const name of Object.keys(payloads).sort(compare)) {
    if (payloads[name].length === 0) continue;
    blocks.push(graphBlock(name === (operation.payload ?? "payloadTriples") ? PAYLOAD_GRAPH : `${PAYLOAD_GRAPH}/${name}`, payloads[name]));
  }
  const trig = `${blocks.join("\n")}\n`;
  return { trig, parameters, bytes: bytes(trig).length };
}

// --- reading the worker's parts ------------------------------------------------------------------------------------------------

export interface DeltaGraph {
  graph: string | null;
  added: string[];
  removed: string[];
}

export interface Delta {
  places: { place: string; role: string; graphs: DeltaGraph[] }[];
  unplaced: DeltaGraph[];
}

export interface StepOutcome {
  outcome: string;
  classification: string;
  reason: string;
  revision?: string;
  engine?: string;
}

function parseObject(text: string | undefined): Record<string, unknown> | undefined {
  if (text === undefined) return undefined;
  try {
    const value: unknown = JSON.parse(text);
    return typeof value === "object" && value !== null && !Array.isArray(value) ? (value as Record<string, unknown>) : undefined;
  } catch {
    return undefined;
  }
}

const strings = (value: unknown): string[] => (Array.isArray(value) ? value.filter((v): v is string => typeof v === "string") : []);

function graphsOfDelta(value: unknown): DeltaGraph[] {
  if (!Array.isArray(value)) return [];
  const out: DeltaGraph[] = [];
  for (const g of value) {
    if (typeof g !== "object" || g === null) continue;
    const e = g as Record<string, unknown>;
    out.push({ graph: typeof e.graph === "string" ? e.graph : null, added: strings(e.added), removed: strings(e.removed) });
  }
  return out;
}

/** The delta part of a step, or undefined when its text is not the JSON the contract states. */
export function readDelta(text: string | undefined): Delta | undefined {
  const o = parseObject(text);
  if (!o || !Array.isArray(o.places) || !Array.isArray(o.unplaced)) return undefined;
  const places: Delta["places"] = [];
  for (const p of o.places) {
    if (typeof p !== "object" || p === null) continue;
    const e = p as Record<string, unknown>;
    if (typeof e.place === "string") places.push({ place: e.place, role: typeof e.role === "string" ? e.role : "", graphs: graphsOfDelta(e.graphs) });
  }
  return { places, unplaced: graphsOfDelta(o.unplaced) };
}

/** The outcome part of a step, or undefined when its text is not the JSON the contract states. */
export function readOutcome(text: string | undefined): StepOutcome | undefined {
  const o = parseObject(text);
  if (!o || typeof o.outcome !== "string" || typeof o.classification !== "string") return undefined;
  return {
    outcome: o.outcome,
    classification: o.classification,
    reason: typeof o.reason === "string" ? o.reason : "",
    ...(typeof o.revision === "string" ? { revision: o.revision } : {}),
    ...(typeof o.engine === "string" ? { engine: o.engine } : {}),
  };
}

/** Every changed graph of a delta once, whichever places it is listed under, and the unplaced ones. */
export function changedGraphs(delta: Delta): DeltaGraph[] {
  const byGraph = new Map<string, DeltaGraph>();
  for (const g of [...delta.places.flatMap((p) => p.graphs), ...delta.unplaced]) byGraph.set(g.graph ?? "", g);
  return [...byGraph.values()].sort((a, b) => compare(a.graph ?? "", b.graph ?? ""));
}

/** The world after a delta, the removed lines taken out of each changed graph and the added ones put in. */
export function applyDelta(world: World, delta: Delta): World {
  let next = world;
  for (const g of changedGraphs(delta)) {
    const key = g.graph ?? "";
    const gone = new Set(g.removed.map(normaliseLine));
    next = withGraph(next, key, [...(next.graphs[key] ?? []).filter((l) => !gone.has(l)), ...g.added.map(normaliseLine)]);
  }
  const graphs: Record<string, string[]> = {};
  for (const [name, lines] of Object.entries(next.graphs)) if (lines.length > 0) graphs[name] = lines;
  return { graphs };
}

/** What a step lights on the canvas, the places the delta names by the IRI the compiled profile gives them and by their role. */
export interface Lit {
  place: string;
  role: string;
}

export function litOf(delta: Delta): Lit[] {
  return delta.places.map((p) => ({ place: p.place, role: p.role })).sort((a, b) => compare(a.place, b.place));
}

/**
 * Whether a place of the canvas, which merges the places of each target that writes it, is one a step wrote. A place is matched by the IRI the
 * compiled profile gives it and by its role, and never by a pattern in an IRI or by the name of its graph.
 */
export function isLit(place: Pick<Place, "iris" | "role">, lit: readonly Lit[]): boolean {
  return lit.some((l) => l.role === place.role && place.iris.includes(l.place));
}

/** The places of a compiled profile by their IRI, for the delta to say what each is. */
export function placesByIri(doc: LandingPlaces): Map<string, { place: Place; target: LandingTarget }> {
  const out = new Map<string, { place: Place; target: LandingTarget }>();
  for (const target of doc.targets) for (const place of target.places) for (const iri of place.iris) if (!out.has(iri)) out.set(iri, { place, target });
  return out;
}

/** A step the world keeps, with the world before it, so that stepping back restores it. */
export interface StepRecord {
  number: number;
  write: WriteKind;
  operation: string;
  root: string;
  time: string;
  revision?: string;
  before: World;
}
