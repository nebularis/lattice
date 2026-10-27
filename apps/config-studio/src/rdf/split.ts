// SPDX-License-Identifier: MPL-2.0
// Sorts an imported graph into the graphs a workspace keeps, by the terms each named subject uses:
// its rdf:type or its predicates. The first part in PARTS whose namespace a subject uses takes it,
// so an elg:Question that names a qnt:RangeSet stays with eligibility. A concept scheme or concept
// goes to vocabulary. Everything else is baseline. A blank node goes wherever the subject that
// refers to it went, so path steps written as blank nodes and RDF lists stay with their owner.

import { Graph, type Quad, type Term } from "./graph";
import { PREFIXES, SKOS, TYPE } from "./ns";

export type Part = "baseline" | "vocabulary" | "quantification" | "eligibility" | "surface" | "persistence";

const OWNERS: [Part, (q: Quad) => boolean][] = [
  ["persistence", uses(PREFIXES.dal)],
  ["surface", uses(PREFIXES.srf)],
  ["eligibility", uses(PREFIXES.elg)],
  ["quantification", uses(PREFIXES.qnt)],
  [
    "vocabulary",
    (q) =>
      uses(PREFIXES.voc)(q) ||
      q.predicate.value === SKOS("inScheme") ||
      (q.predicate.value === TYPE && (q.object.value === SKOS("Concept") || q.object.value === SKOS("ConceptScheme"))),
  ],
];

function uses(base: string): (q: Quad) => boolean {
  return (q) => q.predicate.value.startsWith(base) || (q.predicate.value === TYPE && q.object.value.startsWith(base));
}

function partOfNamed(graph: Graph, subject: Term): Part {
  const quads = graph.quads(subject);
  return OWNERS.find(([, owns]) => quads.some(owns))?.[0] ?? "baseline";
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
  const parts: Record<Part, Quad[]> = { baseline: [], vocabulary: [], quantification: [], eligibility: [], surface: [], persistence: [] };
  for (const q of graph.quads()) parts[owner.get(q.subject.id) ?? "baseline"].push(q);
  return Object.fromEntries(Object.entries(parts).map(([part, quads]) => [part, Graph.of(quads, graph.prefixes)])) as Record<Part, Graph>;
}

/** The configurations a workspace keeps beside its baseline, in the order the studio shows them. */
export type ConfigPart = Exclude<Part, "baseline">;
export const CONFIG_PARTS: ConfigPart[] = ["vocabulary", "quantification", "eligibility", "persistence", "surface"];
