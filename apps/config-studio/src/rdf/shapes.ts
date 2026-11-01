// SPDX-License-Identifier: MPL-2.0
// Reads the SHACL node shapes and property shapes in the vocabulary the service serves, so a form
// can place and constrain a class's properties by what the shapes say. A shape targets a class
// with sh:targetClass, or is itself a class. Only a plain IRI sh:path is read, and a complex path
// or a SHACL-SPARQL constraint is not a form's concern.

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

/** The constraints the shapes put on each class's properties, as written, with no inheritance. */
export function readShapes(graph: Graph): Map<string, Map<string, Constraint>> {
  const byClass = new Map<string, Map<string, Constraint>>();
  for (const q of graph.quads(null, SH("property"))) {
    const shape = q.subject;
    const path = graph.object(q.object, SH("path"));
    if (path?.termType !== "NamedNode") continue;
    const targets = graph.objects(shape, SH("targetClass")).filter((t) => t.termType === "NamedNode").map((t) => t.value);
    const types = graph.types(shape);
    if (shape.termType === "NamedNode" && (types.includes(RDFS("Class")) || types.includes(OWL("Class")))) targets.push(shape.value);
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
      properties.set(path.value, merge(properties.get(path.value), constraint));
      byClass.set(target, properties);
    }
  }
  return byClass;
}
