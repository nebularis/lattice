// SPDX-License-Identifier: MPL-2.0
// The persistence canvas's pure part (SVA-P1, SVA-P1b). It reads the `compiled-profile.ttl` artefact of a persistence compile job into
// the targets, boundaries and places each lens draws, and says whether the picture is out of date. The compiled profile states where a
// target's data lands, as `dal:GraphPlace` nodes that each write access reaches by `dal:landsIn`, so nothing here reads the
// configuration, guesses from an IRI pattern or reads a template's SPARQL for it. The canvas draws what the latest compilation says.

import { DAL, Graph, TYPE, TurtleError, type Term } from "@lattice/authoring-domain";

export type PlaceKind =
  | "data-graph" | "version" | "events" | "version-row" | "receipt" | "transaction-claim" | "patch-log-add" | "patch-log-del"
  | "key-claim" | "merge-record" | "key-quarantine" | "retention-mark" | "dataset-epoch";

export type ReferenceMode = "ByIdentity" | "Pinned";

export interface ReferenceEdge {
  property: string;
  inverse: boolean;
  class: string | null;
  ownership: "Reference" | "Vocabulary";
  mode: ReferenceMode;
}

export interface OwnedEdge {
  property: string;
  inverse: boolean;
  class: string | null;
  shape: string | null;
  owned: OwnedEdge[];
  references: ReferenceEdge[];
}

export interface Aggregate {
  strategy: string | null;
  rootClass: string;
  rootShape: string | null;
  owned: OwnedEdge[];
  references: ReferenceEdge[];
}

export interface Place {
  kind: PlaceKind;
  label: string;
  /** The graph, or the template that names it when an operation runs, as the compiled profile states it. */
  graph: string;
  /** Whether `graph` is a template of the closed placeholders `{root}`, `{newRev}` and `{month}` (`dal:inGraphNamed`), and not a graph (`dal:inGraph`). */
  named: boolean;
  /** The local name of the place's `dal:inGraphRole`, for example `DataRole`. */
  role: string;
  /** The IRIs of the `dal:GraphPlace` nodes the compiled profile gives this place, sorted. A simulator step's delta names a place by its IRI. */
  iris: string[];
  from: string[];
  operations: string[];
}

/** A parameter an operation declares, `dal:ParameterDeclaration`, with the local name of its `dal:parameterKind` such as `IriKind` or `PayloadKind`. */
export interface OperationParameter {
  name: string;
  kind: string;
  required: boolean;
}

export interface TargetOperation {
  operation: string;
  templateId: string;
  kind: string;
  path: string;
  parameters: OperationParameter[];
  /** The name of the parameter that holds the payload the operation's payload contract names, or null where it has none. */
  payload: string | null;
  /** The values the compiled profile binds, such as `datasetGraph`, by name, as it writes them (an IRI in angle brackets, a whole number as digits). */
  bindings: Record<string, string>;
}

export interface LandingTarget {
  id: string;
  class: string;
  deployment: string | null;
  profiles: string[];
  scopes: string[];
  matchedScopes: string[];
  aggregate: Aggregate;
  places: Place[];
  operations: TargetOperation[];
}

export interface LandingPlaces {
  targets: LandingTarget[];
}

/** The artefact of a persistence compile job the canvas draws, in the group `profile`. */
export const COMPILED_PROFILE = "compiled-profile.ttl";

/** What reading a compiled profile gives. `predates` is a profile with targets and no `dal:GraphPlace`, compiled before the profile stated where data lands. */
export type Reading = { state: "ready"; doc: LandingPlaces } | { state: "predates" };

/** The kinds of place, in the order the canvas lists them. */
export const PLACE_KINDS: PlaceKind[] = [
  "data-graph", "version", "events", "version-row", "receipt", "transaction-claim", "patch-log-add", "patch-log-del",
  "key-claim", "merge-record", "key-quarantine", "retention-mark", "dataset-epoch",
];

const LABELS: Record<PlaceKind, string> = {
  "data-graph": "Data graph, the aggregate's triples",
  version: "The new version's triples",
  events: "Events of the stream",
  "version-row": "Version row, with the head and the sequence",
  receipt: "Receipt of each write",
  "transaction-claim": "Transaction claim, for a retry",
  "patch-log-add": "Patch log, the triples added",
  "patch-log-del": "Patch log, the triples removed",
  "key-claim": "Key claim",
  "merge-record": "Key merge record",
  "key-quarantine": "Key quarantine",
  "retention-mark": "Retention mark",
  "dataset-epoch": "Dataset epoch",
};

/** The kind of a place the roles that need nothing else decide. A pinned graph is the SPARQL realisation of receipt retention, so it is a receipt as the log is. */
const ROLE_KINDS: Record<string, PlaceKind> = {
  MetaRole: "version-row", TxnRole: "transaction-claim", LogRole: "receipt", PinnedRole: "receipt", EventRole: "events",
  QuarantineRole: "key-quarantine", RetentionRole: "retention-mark", DatasetRole: "dataset-epoch",
};

const compare = (a: string, b: string) => (a < b ? -1 : a > b ? 1 : 0);
const after = (iri: string) => iri.slice(iri.lastIndexOf("#") + 1);

/** The name of a target in the job, its class's local name followed by its deployment's where it has one, as the worker's `instantiate_by_target` names it. */
function groupOf(cls: string, deployment: string | null): string {
  const local = (iri: string) => {
    const trimmed = iri.replace(/[/#]+$/, "");
    const hash = trimmed.slice(trimmed.lastIndexOf("#") + 1);
    return hash.slice(hash.lastIndexOf("/") + 1);
  };
  return deployment === null ? local(cls) : `${local(cls)}.${local(deployment)}`;
}

/**
 * The path of an operation's SPARQL among a compile job's artefacts. The compiled profile does not state it, since it is where the job
 * writes the file, so the rule is restated here from `_compile_persistence` in workers/src/lattice_workers/config_studio_jobs.py, the
 * group being `groupOf`'s name for the target and the file the operation's name with each `:` and `/` written as `_`, and `.rq`. The unit
 * test holds it against every path the facility sample's job holds.
 */
export function artefactPath(group: string, operation: string): string {
  return `${group}/${operation.replace(/[:/]/g, "_")}.rq`;
}

/** A compiled profile that cannot be drawn, with what to do about it in plain words. */
export class LandingError extends Error {}

export function readLanding(turtle: string): Reading {
  let graph: Graph;
  try {
    graph = Graph.parse(turtle);
  } catch (e) {
    if (e instanceof TurtleError) throw new LandingError("The compiled profile is not Turtle the studio can read. Compile again.");
    throw e;
  }
  return landingOf(graph);
}

/** The targets of a compiled profile, in an order that never depends on the order its triples came in. */
export function landingOf(g: Graph): Reading {
  const profiles = g.subjects(TYPE, DAL("CompiledProfile"));
  if (profiles.length > 0 && g.subjects(TYPE, DAL("GraphPlace")).length === 0) return { state: "predates" };
  const targets = profiles.map((node) => targetOf(g, node));
  targets.sort((a, b) => compare(a.class, b.class) || compare(a.deployment ?? "", b.deployment ?? ""));
  return { state: "ready", doc: { targets } };
}

const one = (g: Graph, s: Term, p: string): string | undefined => g.value(s, DAL(p));
const many = (g: Graph, s: Term, p: string): Term[] => g.objects(s, DAL(p));
const sortedSet = (items: Iterable<string>): string[] => [...new Set(items)].sort(compare);

function targetOf(g: Graph, node: Term): LandingTarget {
  const cls = one(g, node, "forTarget");
  if (cls === undefined) throw new LandingError("A compiled profile names no target. Compile again.");
  const deployment = one(g, node, "forDeployment") ?? null;
  const id = groupOf(cls, deployment);
  const dimensions = many(g, node, "resolvedDimension");
  const profiles = sortedSet(dimensions.flatMap((d) => many(g, d, "wonBy").map((t) => t.value)));
  const scopes = sortedSet(dimensions.flatMap((d) => many(g, d, "wonThrough").map((t) => t.value)));
  const matchedScopes = sortedSet(many(g, node, "matchedScope").map((t) => t.value));
  const strategy = dimensions.find((d) => one(g, d, "dimension") === "aggregateBoundary" && one(g, d, "resolvedValue") !== undefined);
  const operations = many(g, node, "generatedOperation");
  const places = new Map<string, PlaceDraft>();
  const listed: TargetOperation[] = [];
  for (const op of operations) {
    const name = one(g, op, "forOperation");
    if (name === undefined) continue;
    const template = many(g, op, "usesTemplate")[0];
    const templateId = (template && one(g, template, "templateId")) || "";
    const kind = after(one(g, op, "operationKind") ?? "");
    listed.push({ operation: name, templateId, kind, path: artefactPath(id, name), ...contractOf(g, op) });
    for (const access of many(g, op, "access")) land(g, access, name, templateId, kind, places);
  }
  return {
    id, class: cls, deployment, profiles, scopes, matchedScopes,
    aggregate: aggregateOf(g, node, cls, strategy ? after(one(g, strategy, "resolvedValue")!) : null, operations),
    places: [...places.values()]
      .sort((a, b) => PLACE_KINDS.indexOf(a.kind) - PLACE_KINDS.indexOf(b.kind) || compare(a.graph, b.graph) || compare(a.constraint, b.constraint))
      .map((p) => ({ kind: p.kind, label: p.label, graph: p.graph, named: p.named, role: p.role, iris: sortedSet(p.iris), from: sortedSet(p.from), operations: sortedSet(p.operations) })),
    operations: listed.sort((a, b) => compare(a.operation, b.operation)),
  };
}

interface PlaceDraft extends Omit<Place, "from" | "operations" | "iris"> {
  constraint: string;
  iris: Set<string>;
  from: Set<string>;
  operations: Set<string>;
}

/** What a step of the simulator needs of an operation: its declared parameters, which one holds the payload, and the values the profile binds. */
function contractOf(g: Graph, op: Term): Pick<TargetOperation, "parameters" | "payload" | "bindings"> {
  const parameters = many(g, op, "parameter")
    .map((p) => ({ name: one(g, p, "parameterName") ?? "", kind: after(one(g, p, "parameterKind") ?? ""), required: one(g, p, "required") === "true" }))
    .filter((p) => p.name !== "")
    .sort((a, b) => compare(a.name, b.name));
  const contract = many(g, op, "payloadContract")[0];
  const payloadParameter = contract ? many(g, contract, "payloadParameter")[0] : undefined;
  const bound: [string, string][] = [];
  for (const b of many(g, op, "hasParameterBinding")) {
    const name = one(g, b, "paramName");
    const value = one(g, b, "paramValue");
    if (name !== undefined && value !== undefined) bound.push([name, value]);
  }
  const bindings = Object.fromEntries(bound.sort((a, b) => compare(a[0], b[0]) || compare(a[1], b[1])));
  return { parameters, payload: payloadParameter ? one(g, payloadParameter, "parameterName") ?? null : null, bindings };
}

/**
 * The kind of place a write access lands in, from what the compiled profile states of it. The role of the place decides it where it
 * can. The data graph is `version` where the operation's kind is `AppendVersion` and the aggregate's triples otherwise. A patch log's
 * graph is the triples added or removed as the access's `dal:patchDirection` says. The keys graph holds a key claim or a merge record, as
 * the access's `dal:resourceKind` says.
 */
function kindOf(role: string, resource: string, direction: string, operationKind: string): PlaceKind {
  if (role === "DataRole") return operationKind === "AppendVersion" ? "version" : "data-graph";
  if (role === "PatchRole") {
    if (direction === "Added") return "patch-log-add";
    if (direction === "Removed") return "patch-log-del";
    throw new LandingError("A patch log write of the compiled profile states no direction. Compile again.");
  }
  if (role === "KeysRole") {
    if (resource === "KeyClaim") return "key-claim";
    if (resource === "MergeRecord") return "merge-record";
    throw new LandingError("A write to the keys graph of the compiled profile is neither a key claim nor a merge record. Compile again.");
  }
  const kind = ROLE_KINDS[role];
  if (!kind) throw new LandingError(`The compiled profile names a graph role the canvas does not know, ${role || "none"}. Compile again.`);
  return kind;
}

/** Notes where a write access lands, and says nothing of a read, which lands nowhere. A key claim is a place for each constraint it serves. */
function land(g: Graph, access: Term, operation: string, templateId: string, operationKind: string, places: Map<string, PlaceDraft>): void {
  const place = many(g, access, "landsIn")[0];
  if (!place) return;
  const graph = one(g, place, "inGraph") ?? one(g, place, "inGraphNamed");
  if (graph === undefined) return;
  const kind = kindOf(after(one(g, place, "inGraphRole") ?? ""), after(one(g, access, "resourceKind") ?? ""), after(one(g, access, "patchDirection") ?? ""), operationKind);
  const constraint = kind === "key-claim" || kind === "merge-record" ? one(g, access, "forConstraint") ?? "" : "";
  const key = `${kind}|${graph}|${constraint}`;
  let draft = places.get(key);
  if (!draft) {
    draft = {
      kind, label: LABELS[kind] + (constraint ? `, ${localName(constraint)}` : ""), graph, named: one(g, place, "inGraph") === undefined,
      role: after(one(g, place, "inGraphRole") ?? ""), constraint, iris: new Set(), from: new Set(), operations: new Set(),
    };
    places.set(key, draft);
  }
  if (place.termType === "NamedNode") draft.iris.add(place.value);
  draft.from.add(templateId);
  draft.operations.add(operation);
}

// --- the boundary, from the edges the compiled profile states ------------------------------------------------------------------

interface Edge {
  source: string;
  property: string;
  inverse: boolean;
  ownership: string;
  class: string | null;
  shape: string | null;
  mode: ReferenceMode;
}

function edgeOf(g: Graph, node: Term): Edge {
  return {
    source: one(g, node, "edgeSource") ?? "",
    property: one(g, node, "edgePredicate") ?? "",
    inverse: one(g, node, "edgeInverse") === "true",
    ownership: after(one(g, node, "edgeOwnership") ?? ""),
    class: one(g, node, "edgeTargetClass") ?? null,
    shape: one(g, node, "edgeTargetShape") ?? null,
    mode: after(one(g, node, "referenceMode") ?? "") === "Pinned" ? "Pinned" : "ByIdentity",
  };
}

/** The aggregate as the profile's edges give it, each owned edge nested as its shape nests. The root's shape is the one the operations' payload contracts declare, or else the one source no edge leads to. */
function aggregateOf(g: Graph, node: Term, rootClass: string, strategy: string | null, operations: Term[]): Aggregate {
  const edges = many(g, node, "referenceEdge").map((e) => edgeOf(g, e)).sort(
    (a, b) => compare(a.source, b.source) || compare(a.property, b.property) || Number(a.inverse) - Number(b.inverse) || compare(a.shape ?? "", b.shape ?? ""),
  );
  const declared = sortedSet(
    operations.flatMap((op) => many(g, op, "payloadContract").flatMap((c) => many(g, c, "boundaryShape").map((s) => s.value))).filter((s) => s !== DAL("NoBoundaryShape")),
  );
  const targets = new Set(edges.flatMap((e) => (e.shape ? [e.shape] : [])));
  const sources = sortedSet(edges.map((e) => e.source).filter((s) => !targets.has(s)));
  const rootShape = declared[0] ?? sources[0] ?? null;

  const reference = (e: Edge): ReferenceEdge => ({
    property: e.property, inverse: e.inverse, class: e.class, ownership: e.ownership === "Vocabulary" ? "Vocabulary" : "Reference", mode: e.mode,
  });
  const level = (shape: string | null, path: Set<string | null>): { owned: OwnedEdge[]; references: ReferenceEdge[] } => {
    const owned: OwnedEdge[] = [];
    const references: ReferenceEdge[] = [];
    for (const e of edges.filter((x) => x.source === shape)) {
      if (e.ownership === "Owned") {
        const inner = e.shape && !path.has(e.shape) && e.shape !== shape ? level(e.shape, new Set([...path, shape])) : { owned: [], references: [] };
        owned.push({ property: e.property, inverse: e.inverse, class: e.class, shape: e.shape, owned: inner.owned, references: inner.references });
      } else references.push(reference(e));
    }
    return { owned, references };
  };
  return { strategy, rootClass, rootShape, ...level(rootShape, new Set()) };
}

export type Lens = "aggregate" | "profile" | "scope";

export const LENSES: { lens: Lens; title: string; picker: string; what: string }[] = [
  { lens: "aggregate", title: "Aggregate", picker: "Target", what: "one target, with its boundary and every place its data lands" },
  { lens: "profile", title: "Profile", picker: "Profile", what: "every target that resolves to one profile, with the places they share drawn once" },
  { lens: "scope", title: "Scope node", picker: "Scope node", what: "every target one scope node matches" },
];

/** The part of an IRI after its last `#` or `/`. */
export function localName(iri: string): string {
  const cut = Math.max(iri.lastIndexOf("#"), iri.lastIndexOf("/"));
  return cut < 0 ? iri : iri.slice(cut + 1) || iri;
}

export interface Choice {
  id: string;
  label: string;
}

export function targetLabel(t: LandingTarget): string {
  return t.deployment ? `${localName(t.class)} in ${localName(t.deployment)}` : localName(t.class);
}

/** What the picker lists for a lens, and only what the compile job holds. */
export function choices(doc: LandingPlaces, lens: Lens): Choice[] {
  if (lens === "aggregate") return doc.targets.map((t) => ({ id: t.id, label: targetLabel(t) })).sort((a, b) => compare(a.label, b.label) || compare(a.id, b.id));
  const iris = new Set(doc.targets.flatMap((t) => (lens === "profile" ? t.profiles : t.matchedScopes)));
  return [...iris].sort(compare).map((iri) => ({ id: iri, label: localName(iri) }));
}

/** The targets a choice of a lens draws. */
export function targetsOf(doc: LandingPlaces, lens: Lens, choice: string): LandingTarget[] {
  if (lens === "aggregate") return doc.targets.filter((t) => t.id === choice);
  return doc.targets.filter((t) => (lens === "profile" ? t.profiles : t.matchedScopes).includes(choice));
}

export type NodeKind = "root" | "owned" | "reference" | "target" | "place";

export interface CanvasNode {
  id: string;
  kind: NodeKind;
  label: string;
  /** The second line: the IRI of a class, the graph of a place, the deployment of a target. */
  sub: string;
  /** The rank the layout keeps. The boundary is to the left of the root and the places to its right. */
  rank: number;
  /** For a place, the place with the id of each target that writes it. */
  place?: Place;
  targets?: string[];
  /** For a node of the boundary, what the edge to it says. */
  edge?: { property: string; inverse: boolean; ownership: string; mode?: ReferenceMode };
  /** For a root or a target, the compiled target. */
  target?: LandingTarget;
}

export interface CanvasEdge {
  id: string;
  source: string;
  target: string;
  kind: "owned" | "reference" | "lands";
  label?: string;
  title: string;
  dashed: boolean;
  mode?: ReferenceMode;
}

export interface Drawing {
  nodes: CanvasNode[];
  edges: CanvasEdge[];
}

const MODE_WORD: Record<ReferenceMode, string> = { ByIdentity: "identity", Pinned: "pinned" };

export function placeId(p: Place): string {
  return `place:${p.kind}|${p.graph}|${p.label}`;
}

function boundary(t: LandingTarget, drawing: Drawing): void {
  const root = `root:${t.id}`;
  const a = t.aggregate;
  drawing.nodes.push({ id: root, kind: "root", label: localName(a.rootClass), sub: `root of ${t.id}`, rank: 0, target: t });
  const references = (from: string, refs: ReferenceEdge[], rank: number, path: string) => {
    for (const r of refs) {
      const id = `ref:${t.id}:${path}:${r.inverse ? "^" : ""}${r.property}`;
      const label = r.class ? localName(r.class) : localName(r.property);
      const word = r.ownership === "Vocabulary" ? "vocabulary" : MODE_WORD[r.mode];
      drawing.nodes.push({ id, kind: "reference", label, sub: `referenced by ${word}`, rank, edge: { property: r.property, inverse: r.inverse, ownership: r.ownership, mode: r.mode } });
      const name = localName(r.property);
      drawing.edges.push({
        id: `e:${id}`, source: from, target: id, kind: "reference", label: `${name} · ${word}`, dashed: true, mode: r.mode,
        title: `${localName(a.rootClass)} references ${label} through ${name}, ${r.ownership === "Vocabulary" ? "as a vocabulary node" : r.mode === "Pinned" ? "pinned to a version" : "by identity"}`,
      });
    }
  };
  const owned = (from: string, edges: OwnedEdge[], depth: number, path: string) => {
    for (const e of edges) {
      const here = `${path}/${e.inverse ? "^" : ""}${e.property}`;
      const id = `own:${t.id}:${here}`;
      const label = e.class ? localName(e.class) : localName(e.property);
      drawing.nodes.push({ id, kind: "owned", label, sub: "owned by the root", rank: -depth, edge: { property: e.property, inverse: e.inverse, ownership: "Owned" } });
      drawing.edges.push({ id: `e:${id}`, source: from, target: id, kind: "owned", label: localName(e.property), dashed: false, title: `${label} is owned through ${localName(e.property)}, so one write covers it` });
      owned(id, e.owned, depth + 1, here);
      references(id, e.references, -(depth + 1), here);
    }
  };
  owned(root, a.owned, 1, "");
  references(root, a.references, -1, "");
}

/** The picture a lens draws for a choice. A place several targets write is one node, drawn once. */
export function drawing(doc: LandingPlaces, lens: Lens, choice: string): Drawing {
  const out: Drawing = { nodes: [], edges: [] };
  const targets = targetsOf(doc, lens, choice);
  const places = new Map<string, CanvasNode>();
  for (const t of targets) {
    const from = lens === "aggregate" ? `root:${t.id}` : `target:${t.id}`;
    if (lens === "aggregate") boundary(t, out);
    else out.nodes.push({ id: from, kind: "target", label: targetLabel(t), sub: `${t.aggregate.strategy ?? "no boundary"}`, rank: 0, target: t });
    for (const p of t.places) {
      const id = placeId(p);
      const node = places.get(id);
      if (node) {
        node.targets!.push(t.id);
        node.place = { ...node.place!, iris: sortedSet([...node.place!.iris, ...p.iris]) };
      } else places.set(id, { id, kind: "place", label: p.label, sub: p.graph, rank: 1, place: p, targets: [t.id] });
      out.edges.push({ id: `e:${from}->${id}`, source: from, target: id, kind: "lands", title: `${p.label}, written to ${p.graph}`, dashed: false });
    }
  }
  out.nodes.push(...[...places.values()].sort((a, b) => compare(a.id, b.id)));
  return out;
}

// --- whether the picture is out of date -------------------------------------------------------------------------------------------

/** A short digest of a text, for telling two readings of the persistence part apart. It is not a secret and not a hash for anything else. */
export function digest(text: string): string {
  let a = 0xdeadbeef;
  let b = 0x41c6ce57;
  for (let i = 0; i < text.length; i++) {
    const c = text.charCodeAt(i);
    a = Math.imul(a ^ c, 2654435761);
    b = Math.imul(b ^ c, 1597334677);
  }
  a = Math.imul(a ^ (a >>> 16), 2246822507) ^ Math.imul(b ^ (b >>> 13), 3266489909);
  b = Math.imul(b ^ (b >>> 16), 2246822507) ^ Math.imul(a ^ (a >>> 13), 3266489909);
  return (4294967296 * (2097151 & b) + (a >>> 0)).toString(16);
}

/** What a compilation read of the workspace: the persistence part as the editor held it, and the baseline as saved, by its revision. */
export function fingerprint(persistenceTurtle: string, baselineRevision: string | undefined): string {
  return `${digest(persistenceTurtle)}:${baselineRevision ?? ""}`;
}

/** `current` where the compilation read what the workspace holds now, `out-of-date` where it read something else, and `unknown` for one
 * this browser did not start, since only the browser that submits a compilation knows what it sent. */
export type Freshness = "current" | "out-of-date" | "unknown";

export function freshness(compiled: string | undefined, now: string): Freshness {
  if (compiled === undefined) return "unknown";
  return compiled === now ? "current" : "out-of-date";
}

export interface RecordStore {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

function browserStore(): RecordStore | undefined {
  try {
    return typeof localStorage === "undefined" ? undefined : localStorage;
  } catch {
    return undefined;
  }
}

const recordKey = (workspace: string) => `lattice-studio:persistence-compiled:${workspace}`;
const memory = new Map<string, Record<string, string>>();

/** What this browser sent with each compilation of a workspace it started, by job. Kept in this browser alone, and the page works without it. */
export function readCompiled(workspace: string, store: RecordStore | undefined = browserStore()): Record<string, string> {
  const held = memory.get(workspace) ?? {};
  try {
    const parsed = JSON.parse(store?.getItem(recordKey(workspace)) ?? "{}") as Record<string, string>;
    return { ...parsed, ...held };
  } catch {
    return { ...held };
  }
}

export function writeCompiled(workspace: string, job: string, sent: string, store: RecordStore | undefined = browserStore()): void {
  const next = { ...readCompiled(workspace, store), [job]: sent };
  // Only the latest few are kept.
  const kept = Object.fromEntries(Object.entries(next).slice(-8));
  memory.set(workspace, kept);
  try {
    store?.setItem(recordKey(workspace), JSON.stringify(kept));
  } catch {
    // kept in memory for this page alone
  }
}
