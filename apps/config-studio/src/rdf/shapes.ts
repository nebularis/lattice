// SPDX-License-Identifier: MPL-2.0
// Reads the SHACL node shapes and property shapes in the vocabulary the service serves, so a form
// can place and constrain a class's properties by what the shapes say. A shape targets a class
// with sh:targetClass, or is itself a class. Only a plain IRI sh:path is read, and a complex path
// or a SHACL-SPARQL constraint is not a form's concern. Which shape targets which class, and which
// property shapes count, is decided here once, by `shapeTargets` and `plainPath`. `readShapes` merges
// the constraints for the forms, and `readNodeShapes` gives the shapes as they are written, for the
// ontology drawing.

import { Graph, OWL, RDFS, SH, type Term } from "@lattice/authoring-domain";

export interface Constraint {
  minCount?: number;
  maxCount?: number;
  datatype?: string;
  /** sh:class */
  cls?: string;
  nodeKind?: string;
  /** sh:in, when every listed value is an IRI */
  in?: Term[];
  name?: string;
  description?: string;
}

const count = (graph: Graph, node: Term, predicate: string): number | undefined => {
  const text = graph.value(node, predicate);
  const n = Number(text);
  return text !== undefined && Number.isInteger(n) ? n : undefined;
};

/** Several shapes for one property merge conservatively: the most restrictive counts, and the first value of anything else. */
export function merge(a: Constraint | undefined, b: Constraint): Constraint {
  if (!a) return b;
  const pick = (f: (x: number, y: number) => number, x?: number, y?: number) => (x === undefined ? y : y === undefined ? x : f(x, y));
  return {
    minCount: pick(Math.max, a.minCount, b.minCount),
    maxCount: pick(Math.min, a.maxCount, b.maxCount),
    datatype: a.datatype ?? b.datatype,
    cls: a.cls ?? b.cls,
    nodeKind: a.nodeKind ?? b.nodeKind,
    in: a.in ?? b.in,
    name: a.name ?? b.name,
    description: a.description ?? b.description,
  };
}

/** The classes a node shape targets, by `sh:targetClass`, and the shape itself when it is a named class. In the order written, with repeats. */
export function shapeTargets(graph: Graph, shape: Term): string[] {
  const targets = graph.objects(shape, SH("targetClass")).filter((t) => t.termType === "NamedNode").map((t) => t.value);
  if (shape.termType === "NamedNode") {
    const types = graph.types(shape);
    if (types.includes(RDFS("Class")) || types.includes(OWL("Class"))) targets.push(shape.value);
  }
  return targets;
}

/** The IRI a property shape's `sh:path` is, or undefined for a complex path or none. */
export function plainPath(graph: Graph, propertyShape: Term): string | undefined {
  const path = graph.object(propertyShape, SH("path"));
  return path?.termType === "NamedNode" ? path.value : undefined;
}

export interface PropertyShape {
  /** The plain IRI `sh:path`. */
  path: string;
  /** The named `sh:class` values, sorted. */
  classes: string[];
  /** The `sh:node` values, sorted. */
  nodes: Term[];
  /** The classes the shapes in `nodes` target, sorted. */
  nodeTargets: string[];
}

export interface NodeShape {
  /** The shape's own term, an IRI or a blank node. */
  shape: Term;
  /** The shape's IRI. Absent for a blank node. */
  name?: string;
  /** The classes it targets, sorted, with no repeats. Never empty, since a shape that targets no class is left out. */
  targets: string[];
  /** Its property shapes with a plain IRI path, sorted by path. */
  properties: PropertyShape[];
}

const text = (a: string, b: string) => (a < b ? -1 : a > b ? 1 : 0);
const sorted = (items: Iterable<string>) => [...new Set(items)].sort(text);
const termKey = (t: Term) => `${t.termType}|${t.value}`;

/** The node shapes that target a class and have a property shape with a plain path, as written and in a fixed order, named shapes first. */
export function readNodeShapes(graph: Graph): NodeShape[] {
  const subjects = new Map<string, Term>();
  for (const q of graph.quads(null, SH("property"))) subjects.set(termKey(q.subject), q.subject);
  const out: NodeShape[] = [];
  for (const shape of subjects.values()) {
    const targets = sorted(shapeTargets(graph, shape));
    if (targets.length === 0) continue;
    const properties: PropertyShape[] = [];
    for (const ps of graph.objects(shape, SH("property"))) {
      const path = plainPath(graph, ps);
      if (path === undefined) continue;
      const classes = sorted(graph.objects(ps, SH("class")).filter((c) => c.termType === "NamedNode").map((c) => c.value));
      const nodes = new Map<string, Term>();
      for (const n of graph.objects(ps, SH("node"))) nodes.set(termKey(n), n);
      const ordered = [...nodes.entries()].sort((a, b) => text(a[0], b[0])).map((e) => e[1]);
      const nodeTargets = sorted(ordered.flatMap((n) => shapeTargets(graph, n)));
      properties.push({ path, classes, nodes: ordered, nodeTargets });
    }
    properties.sort((a, b) => text(a.path, b.path) || text(a.classes.join(" "), b.classes.join(" ")) || text(a.nodeTargets.join(" "), b.nodeTargets.join(" ")));
    out.push({ shape, name: shape.termType === "NamedNode" ? shape.value : undefined, targets, properties });
  }
  const key = (s: NodeShape) => `${s.name === undefined ? "1" : "0"}|${s.name ?? ""}|${s.targets.join(" ")}|${s.properties.map((p) => `${p.path} ${p.classes.join(",")} ${p.nodeTargets.join(",")}`).join(";")}`;
  return out.sort((a, b) => text(key(a), key(b)));
}

/** The constraints the shapes put on each class's properties, as written, with no inheritance. */
export function readShapes(graph: Graph): Map<string, Map<string, Constraint>> {
  const byClass = new Map<string, Map<string, Constraint>>();
  for (const q of graph.quads(null, SH("property"))) {
    const shape = q.subject;
    const path = plainPath(graph, q.object);
    if (path === undefined) continue;
    const targets = shapeTargets(graph, shape);
    if (targets.length === 0) continue;
    const list = graph.object(q.object, SH("in"));
    const values = list ? graph.list(list) : undefined;
    const constraint: Constraint = {
      minCount: count(graph, q.object, SH("minCount")),
      maxCount: count(graph, q.object, SH("maxCount")),
      datatype: graph.value(q.object, SH("datatype")),
      cls: graph.value(q.object, SH("class")),
      nodeKind: graph.value(q.object, SH("nodeKind")),
      in: values && values.length > 0 && values.every((t) => t.termType === "NamedNode") ? values : undefined,
      name: graph.value(q.object, SH("name")),
      description: graph.value(q.object, SH("description")),
    };
    for (const target of targets) {
      const properties = byClass.get(target) ?? new Map<string, Constraint>();
      properties.set(path, merge(properties.get(path), constraint));
      byClass.set(target, properties);
    }
  }
  return byClass;
}
