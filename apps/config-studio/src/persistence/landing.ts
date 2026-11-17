// SPDX-License-Identifier: MPL-2.0
// The persistence canvas's pure part (SVA-P1). It turns `landing-places.json`, the artefact a persistence compile job gives, into the
// nodes and edges each lens draws, and says whether the picture is out of date. Nothing here reads the configuration to find where a
// target's data lands. That reading is the worker's (contracts/config-studio/landing-places.schema.json), and the browser draws what the
// latest compilation says.

export type PlaceKind =
  | "data-graph" | "version" | "events" | "version-row" | "receipt" | "transaction-claim" | "patch-log-add" | "patch-log-del"
  | "key-claim" | "merge-record" | "key-quarantine" | "retention-mark" | "dataset-epoch" | "derived-rows";

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
  graph: string;
  from: string[];
  operations: string[];
}

export interface TargetOperation {
  operation: string;
  templateId: string;
  kind: string;
  path: string;
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

export const LANDING_PLACES = "landing-places.json";

/** The document a compile job holds, read. A document that is not the one the worker writes is refused in plain words. */
export function parseLanding(text: string): LandingPlaces {
  let value: unknown;
  try {
    value = JSON.parse(text);
  } catch {
    throw new Error("The landing places are not JSON.");
  }
  const targets = (value as { targets?: unknown } | null)?.targets;
  const ok = (t: unknown): t is LandingTarget => {
    const x = t as Partial<LandingTarget> | null;
    return !!x && typeof x.id === "string" && typeof x.class === "string" && Array.isArray(x.profiles) && Array.isArray(x.matchedScopes) && Array.isArray(x.places) && Array.isArray(x.operations) && !!x.aggregate && typeof x.aggregate.rootClass === "string" && Array.isArray(x.aggregate.owned) && Array.isArray(x.aggregate.references);
  };
  if (!Array.isArray(targets) || !targets.every(ok)) throw new Error("The landing places are not the document the worker writes. Compile again.");
  return value as LandingPlaces;
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

const compare = (a: string, b: string) => (a < b ? -1 : a > b ? 1 : 0);

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
      if (node) node.targets!.push(t.id);
      else places.set(id, { id, kind: "place", label: p.label, sub: p.graph, rank: 1, place: p, targets: [t.id] });
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
