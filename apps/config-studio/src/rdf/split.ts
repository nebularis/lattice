// SPDX-License-Identifier: MPL-2.0
// Sorts an imported graph into the three a workspace keeps: a subject whose type or predicates
// are dal: goes to persistence, srf: to surface, everything else to the baseline. A blank node
// goes wherever the subject that refers to it went, so path steps written as blank nodes and
// RDF lists stay with their owner.

import { Graph, type Quad, type Term } from "./graph";
import { PREFIXES, TYPE } from "./ns";

export type Part = "baseline" | "surface" | "persistence";

const OWNERS: [Part, string][] = [
  ["persistence", PREFIXES.dal],
  ["surface", PREFIXES.srf],
];

function partOfNamed(graph: Graph, subject: Term): Part {
  for (const [part, base] of OWNERS) {
    const quads = graph.quads(subject);
    if (quads.some((q) => q.predicate.value.startsWith(base) || (q.predicate.value === TYPE && q.object.value.startsWith(base)))) {
      return part;
    }
  }
  return "baseline";
}

export function split(graph: Graph): Record<Part, Graph> {
  const owner = new Map<string, Part>();
  const pending: Term[] = [];
  for (const q of graph.quads()) {
    if (q.subject.termType !== "NamedNode" || owner.has(q.subject.id)) continue;
    owner.set(q.subject.id, partOfNamed(graph, q.subject));
    pending.push(q.subject);
  }
  // Blank nodes inherit their referrer's part, breadth first from the named subjects.
  while (pending.length) {
    const s = pending.shift()!;
    for (const q of graph.quads(s)) {
      if (q.object.termType === "BlankNode" && !owner.has(q.object.id)) {
        owner.set(q.object.id, owner.get(s.id)!);
        pending.push(q.object);
      }
    }
  }
  const parts: Record<Part, Quad[]> = { baseline: [], surface: [], persistence: [] };
  for (const q of graph.quads()) parts[owner.get(q.subject.id) ?? "baseline"].push(q);
  return {
    baseline: Graph.of(parts.baseline, graph.prefixes),
    surface: Graph.of(parts.surface, graph.prefixes),
    persistence: Graph.of(parts.persistence, graph.prefixes),
  };
}
