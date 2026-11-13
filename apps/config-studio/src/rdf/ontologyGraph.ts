// SPDX-License-Identifier: MPL-2.0
// The graphs the ontology views draw (SVA-O2), derived from the baseline graph the browser already holds and never stored. The
// classes are the baseline's own (baseline.ts). In the view of classes and object properties an edge is one object property
// between two classes, read from `rdfs:domain` and `rdfs:range` and, where the author asks, from the node shapes. A shape is read
// as shapes.ts reads it, a node shape with `sh:targetClass`, or a class that is itself one, and a property shape with a plain
// IRI `sh:path`. It is read again here because the drawing needs what shapes.ts merges away, the name of each shape and its
// `sh:node` links. The shapes only ever add to the view. An edge a shape states between classes a domain and a range already
// join is that edge, which then names the shape, so turning shapes on never removes or changes the identity of an edge. Every
// result is sorted, so the same graph gives the same drawing for any order of triples.

import { Graph, OWL, RDFS, SH, type Term } from "@lattice/authoring-domain";
import { Baseline } from "./baseline";
import { readExpression, type ClassExpr } from "./axioms";

export interface OntologyNode {
  iri: string;
  label: string;
}

export interface ClassEdge {
  /** The same for an edge from either origin, so a shape that restates a domain and range keeps the edge it joins. */
  id: string;
  source: string;
  target: string;
  property: string;
  /** Where the edge comes from. An edge both a domain and range and a shape state is `domain-range`, with its shape named. */
  origin: "domain-range" | "shape";
  /** The first of `shapes`, the node shape that states the edge. Absent where no named shape does. */
  shape?: string;
  /** Every named node shape that states the edge, sorted. */
  shapes?: string[];
  /** Whether a node shape states the edge, named or not. Always false where shapes were not asked for. */
  byShape: boolean;
}

export interface HierarchyEdge {
  id: string;
  /** The class. */
  source: string;
  /** Its named superclass. */
  target: string;
}

export interface ClassGraph {
  nodes: OntologyNode[];
  edges: ClassEdge[];
}

export interface HierarchyGraph {
  nodes: OntologyNode[];
  edges: HierarchyEdge[];
}

export interface GraphOptions {
  /** A class IRI. The result is the classes within `hops` edges of it, in either direction. */
  focus?: string;
  /** Defaults to 2. */
  hops?: number;
  /** Classes and properties only. Adds the edges the node shapes state. */
  shapes?: boolean;
}

export const DEFAULT_HOPS = 2;

const text = (a: string, b: string) => (a < b ? -1 : a > b ? 1 : 0);
const sorted = (items: Iterable<string>) => [...new Set(items)].sort(text);

/** The named classes an expression stands for, a union by its named members. Anything else names none. */
function named(e: ClassExpr): string[] {
  if (e.kind === "named") return [e.iri];
  if (e.kind === "union") return e.members.flatMap(named);
  return [];
}

/** The classes a node shape targets, and the shape itself when it is a class, as shapes.ts reads them. */
function targetsOf(graph: Graph, shape: Term): string[] {
  const targets = graph
    .objects(shape, SH("targetClass"))
    .filter((t) => t.termType === "NamedNode")
    .map((t) => t.value);
  if (shape.termType === "NamedNode") {
    const types = graph.types(shape);
    if (types.includes(RDFS("Class")) || types.includes(OWL("Class"))) targets.push(shape.value);
  }
  return sorted(targets);
}

const edgeId = (source: string, target: string, property: string) => `${source}|${target}|${property}`;

interface Index {
  baseline: Baseline;
  /** Each edge with the origins that state it. */
  edges: Map<string, { source: string; target: string; property: string; domainRange: boolean; shapes: Set<string>; byShape: boolean }>;
}

function domainRangeEdges(baseline: Baseline, add: (s: string, t: string, p: string) => void): void {
  const { graph, classes } = baseline;
  for (const property of baseline.properties.keys()) {
    const ends = (predicate: string) => sorted(graph.objects(property, predicate).flatMap((t) => named(readExpression(graph, t)))).filter((c) => classes.has(c));
    const domains = ends(RDFS("domain"));
    const ranges = ends(RDFS("range"));
    for (const d of domains) for (const r of ranges) add(d, r, property);
  }
}

function shapeEdges(baseline: Baseline, add: (s: string, t: string, p: string, shape: string | undefined) => void): void {
  const { graph, classes } = baseline;
  for (const q of graph.quads(null, SH("property"))) {
    const shape = q.subject;
    const path = graph.object(q.object, SH("path"));
    if (path?.termType !== "NamedNode") continue;
    const sources = targetsOf(graph, shape).filter((c) => classes.has(c));
    if (sources.length === 0) continue;
    const ends = new Set<string>();
    for (const c of graph.objects(q.object, SH("class"))) if (c.termType === "NamedNode") ends.add(c.value);
    for (const n of graph.objects(q.object, SH("node"))) for (const c of targetsOf(graph, n)) ends.add(c);
    const name = shape.termType === "NamedNode" ? shape.value : undefined;
    for (const s of sources) for (const t of ends) if (classes.has(t)) add(s, t, path.value, name);
  }
}

function index(graph: Graph, shapes: boolean): Index {
  const baseline = new Baseline(graph);
  const edges: Index["edges"] = new Map();
  const slot = (s: string, t: string, p: string) => {
    const id = edgeId(s, t, p);
    let e = edges.get(id);
    if (!e) edges.set(id, (e = { source: s, target: t, property: p, domainRange: false, shapes: new Set(), byShape: false }));
    return e;
  };
  domainRangeEdges(baseline, (s, t, p) => (slot(s, t, p).domainRange = true));
  if (shapes) {
    shapeEdges(baseline, (s, t, p, shape) => {
      const e = slot(s, t, p);
      e.byShape = true;
      if (shape) e.shapes.add(shape);
    });
  }
  return { baseline, edges };
}

function node(baseline: Baseline, iri: string): OntologyNode {
  return { iri, label: baseline.classes.get(iri)?.label ?? iri };
}

/** The classes within `hops` edges of `focus`, in either direction, over the given pairs. */
function neighbourhood(pairs: [string, string][], focus: string, hops: number, known: Set<string>): Set<string> {
  const near = new Map<string, string[]>();
  for (const [a, b] of pairs) {
    near.set(a, [...(near.get(a) ?? []), b]);
    near.set(b, [...(near.get(b) ?? []), a]);
  }
  const seen = new Set(known.has(focus) ? [focus] : []);
  let frontier = [...seen];
  for (let step = 0; step < hops && frontier.length; step++) {
    const next: string[] = [];
    for (const c of frontier) {
      for (const n of near.get(c) ?? []) {
        if (!seen.has(n) && known.has(n)) {
          seen.add(n);
          next.push(n);
        }
      }
    }
    frontier = next;
  }
  return seen;
}

function superclassPairs(baseline: Baseline): [string, string][] {
  const out: [string, string][] = [];
  for (const c of baseline.classes.values()) for (const p of c.parents) if (baseline.classes.has(p)) out.push([c.iri, p]);
  return out.sort((a, b) => text(a[0], b[0]) || text(a[1], b[1]));
}

/** The view of classes and object properties. */
export function classGraph(graph: Graph, options: GraphOptions = {}): ClassGraph {
  const { baseline, edges: all } = index(graph, options.shapes === true);
  const edges: ClassEdge[] = [...all.entries()].map(([id, e]) => {
    const shapes = sorted(e.shapes);
    const out: ClassEdge = { id, source: e.source, target: e.target, property: e.property, origin: e.domainRange ? "domain-range" : "shape", byShape: e.byShape };
    if (shapes.length) {
      out.shape = shapes[0];
      out.shapes = shapes;
    }
    return out;
  });
  let keep = new Set(baseline.classes.keys());
  if (options.focus !== undefined) {
    const pairs: [string, string][] = [...edges.map((e): [string, string] => [e.source, e.target]), ...superclassPairs(baseline)];
    keep = neighbourhood(pairs, options.focus, options.hops ?? DEFAULT_HOPS, keep);
  }
  return {
    nodes: [...keep].sort(text).map((iri) => node(baseline, iri)),
    edges: edges.filter((e) => keep.has(e.source) && keep.has(e.target)).sort((a, b) => text(a.source, b.source) || text(a.target, b.target) || text(a.property, b.property) || text(a.origin, b.origin)),
  };
}

/** The view of the class hierarchy, each class with an edge to each named superclass. */
export function hierarchyGraph(graph: Graph, options: GraphOptions = {}): HierarchyGraph {
  const baseline = new Baseline(graph);
  const pairs = superclassPairs(baseline);
  let keep = new Set(baseline.classes.keys());
  if (options.focus !== undefined) keep = neighbourhood(pairs, options.focus, options.hops ?? DEFAULT_HOPS, keep);
  return {
    nodes: [...keep].sort(text).map((iri) => node(baseline, iri)),
    edges: pairs.filter(([s, t]) => keep.has(s) && keep.has(t)).map(([source, target]) => ({ id: `subclass|${source}|${target}`, source, target })),
  };
}

export interface Counts {
  classes: number;
  links: number;
  /** The links a node shape states, whether or not a domain and range state them too. */
  byShape: number;
}

/** How many classes and links a view holds, so the UI can say so before it draws one. */
export function counts(view: { nodes: unknown[]; edges: object[] }): Counts {
  return { classes: view.nodes.length, links: view.edges.length, byShape: view.edges.filter((e) => (e as { byShape?: boolean }).byShape).length };
}
