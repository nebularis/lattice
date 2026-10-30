// SPDX-License-Identifier: MPL-2.0
// Sorts an imported graph into the graphs a workspace keeps, by the terms each named subject uses:
// its rdf:type or its predicates. The first part in PARTS whose namespace a subject uses takes it,
// so an elg:Question that names a qnt:RangeSet stays with eligibility. A concept scheme or concept
// goes to vocabulary. A cst:Assembly or wrd:VariableValue goes to assembly, before any other part, a cst:Proposal to review, a subject using mork: terms to mapping, then any subject using ins: terms to meaning, and any
// other wrd: subject to library, after the rest. Everything else is baseline. A blank node goes wherever the subject that
// refers to it went, so path steps written as blank nodes and RDF lists stay with their owner. So does a named node of a mapping's
// own structure that uses no part's terms, such as a guard's SHACL shape or a scheme's prefix declaration.

import { CST, Graph, MORK, PREFIXES, SH, SKOS, TYPE, WRD, type Quad, type Term } from "@lattice/authoring-domain";

export type Part = "baseline" | "library" | "assembly" | "meaning" | "review" | "mapping" | "vocabulary" | "quantification" | "eligibility" | "surface" | "persistence";

/** An assembly and the value records it sets come first, since a value record uses Wording's terms. */
const assembly = (q: Quad) =>
  q.predicate.value === CST("assembles") ||
  q.predicate.value === WRD("forVariable") ||
  (q.predicate.value === TYPE && (q.object.value === CST("Assembly") || q.object.value === WRD("VariableValue")));

/** A proposal and its decision come before stated meaning, since a proposal's own terms are the studio's. */
const review = (q: Quad) =>
  q.predicate.value === CST("proposes") || (q.predicate.value === TYPE && q.object.value === CST("Proposal"));

const OWNERS: [Part, (q: Quad) => boolean][] = [
  ["assembly", assembly],
  ["review", review],
  ["mapping", uses(PREFIXES.mork)],
  ["meaning", uses(PREFIXES.ins)],
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
  // Any other wrd: subject is a form's, last, since a condition a form names is eligibility's.
  ["library", uses(PREFIXES.wrd)],
];

function uses(base: string): (q: Quad) => boolean {
  return (q) => q.predicate.value.startsWith(base) || (q.predicate.value === TYPE && q.object.value.startsWith(base));
}

/** The links from a mapping to named nodes of its own structure. */
const MAPPING_STRUCTURE = new Set([MORK("appliesWhen"), SH("declare"), SH("property")]);

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
  // Blank nodes inherit their referrer's part, breadth first from the named subjects, and so do a mapping's own named nodes.
  while (pending.length) {
    const s = pending.shift()!;
    for (const q of graph.quads(s)) {
      // A blank node first reached from a named node that later moved to mapping moves with it.
      const blank = q.object.termType === "BlankNode" && (!owner.has(q.object.id) || (owner.get(q.object.id) === "baseline" && owner.get(s.id) !== "baseline"));
      const structure = q.object.termType === "NamedNode" && owner.get(s.id) === "mapping" && owner.get(q.object.id) === "baseline" && MAPPING_STRUCTURE.has(q.predicate.value);
      if (blank || structure) {
        owner.set(q.object.id, owner.get(s.id)!);
        pending.push(q.object);
      }
    }
  }
  const parts: Record<Part, Quad[]> = { baseline: [], library: [], assembly: [], meaning: [], review: [], mapping: [], vocabulary: [], quantification: [], eligibility: [], surface: [], persistence: [] };
  for (const q of graph.quads()) parts[owner.get(q.subject.id) ?? "baseline"].push(q);
  return Object.fromEntries(Object.entries(parts).map(([part, quads]) => [part, Graph.of(quads, graph.prefixes)])) as Record<Part, Graph>;
}

/** The configurations a workspace keeps beside its baseline, in the order the service keeps them. */
export type ConfigPart = Exclude<Part, "baseline">;
export const CONFIG_PARTS: ConfigPart[] = ["library", "assembly", "meaning", "review", "mapping", "vocabulary", "quantification", "eligibility", "surface", "persistence"];
