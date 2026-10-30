// SPDX-License-Identifier: MPL-2.0
// The mapping view's model: each MORK mapping scheme of the mapping part, its mappings as the tree their
// mork:compositeBroaderMapping and mork:compositeNarrowerMapping links make, the source concepts they read, the terms each
// writes and its latest review. It is read only, and lays the tree out the same way every time, one row per mapping in
// depth-first order.

import { Graph, LABEL, MORK, TYPE, compact, iri, literal, typed, localName, type Term } from "@lattice/authoring-domain";

export interface Targets {
  tbox: string[];
  rbox: string[];
  inverse: string[];
  abox: string[];
}

export interface Review {
  /** Accepted, Corrected, Rejected or Deferred. */
  decision: string;
  note?: string;
  correctedBy?: string;
  reviewer?: string;
  at?: string;
}

export interface MappingNode {
  iri: string;
  label: string;
  /** Datum, DataMapping or another MORK class, by its local name. */
  kind: string;
  parent?: string;
  template?: string;
  /** What it maps for: a source concept, an entity or a value. */
  source?: string;
  /** The path it reads, its inline value or the name it mints, as written. */
  reads?: string;
  guard?: string;
  targets: Targets;
  /** Whether another mapping names it as its template. */
  isTemplate: boolean;
  review?: Review;
  /** The proposal run that generated it, where one did. */
  generatedBy?: string;
  depth: number;
  row: number;
}

export interface SourceConcept {
  iri: string;
  label: string;
  path?: string;
  representedAs: string[];
}

/** What a proposal run cost, as far as its provider counted. */
export interface RunCost {
  iri: string;
  model?: string;
  inputTokens?: number;
  outputTokens?: number;
  totalTokens?: number;
  seconds?: number;
}

export interface Scheme {
  iri: string;
  label: string;
  run?: RunCost;
  labelled: boolean;
  mappings: MappingNode[];
  sources: SourceConcept[];
}

const label = (g: Graph, node: string) => g.value(node, LABEL) ?? localName(node);
const PROV = "http://www.w3.org/ns/prov#";

/** Each reviewed mapping's latest review, by its time. */
function reviewsOf(g: Graph): Map<string, Review> {
  const latest = new Map<string, Review>();
  for (const r of g.subjects(TYPE, MORK("MappingReview"))) {
    const of = g.value(r, MORK("reviewOf"));
    const decision = g.value(r, MORK("reviewDecision"));
    if (!of || !decision) continue;
    const review = { decision: localName(decision), note: g.value(r, MORK("reviewNote")), correctedBy: g.value(r, MORK("correctedBy")), reviewer: g.value(r, PROV + "wasAssociatedWith"), at: g.value(r, PROV + "endedAtTime") };
    if ((latest.get(of)?.at ?? "") <= (review.at ?? "")) latest.set(of, review);
  }
  return latest;
}
const iris = (terms: Term[]) => terms.filter((t) => t.termType === "NamedNode").map((t) => t.value).sort();

export function schemesOf(g: Graph): Scheme[] {
  const sources = [...g.ofType(MORK("DataConcept")), ...g.ofType(MORK("Entity"))].map((s) => ({
    iri: s.value,
    label: label(g, s.value),
    path: g.value(s, MORK("path")),
    representedAs: iris(g.objects(s, MORK("representedAs"))),
  }));
  const reviews = reviewsOf(g);
  return g.ofType(MORK("MappingScheme")).map((scheme): Scheme => {
    const members = g.subjects(MORK("mappingScheme"), scheme).filter((m) => m.termType === "NamedNode").map((m) => m.value);
    const templates = new Set(members.flatMap((m) => g.objects(m, MORK("templateMapping")).map((t) => t.value)));
    const read = (m: string): MappingNode => {
      const inline = g.object(m, MORK("dataInline"));
      return {
        iri: m,
        label: label(g, m),
        kind: localName(g.types(m).find((t) => t.startsWith(MORK(""))) ?? MORK("Mapping")),
        parent: g.value(m, MORK("compositeBroaderMapping")) ?? g.subjects(MORK("compositeNarrowerMapping"), m).find((p) => p.termType === "NamedNode")?.value,
        template: g.value(m, MORK("templateMapping")),
        source: g.value(m, MORK("mappingFor")),
        reads: g.value(m, MORK("dataRef")) ?? (inline ? `= ${inline.value}` : undefined) ?? g.value(m, MORK("conceptName")) ?? g.value(m, MORK("conceptNameTemplate")),
        guard: g.value(m, MORK("appliesWhen")),
        targets: {
          tbox: iris(g.objects(m, MORK("exactTBoxMatch"))),
          rbox: iris(g.objects(m, MORK("exactRBoxMatch"))),
          inverse: iris(g.objects(m, MORK("inverseRBoxMatch"))),
          abox: iris(g.objects(m, MORK("exactABoxMatch"))),
        },
        isTemplate: templates.has(m),
        review: reviews.get(m),
        generatedBy: g.value(m, PROV + "wasGeneratedBy"),
        depth: 0,
        row: 0,
      };
    };
    const nodes = new Map(members.map((m) => [m, read(m)]));
    const children = new Map<string, MappingNode[]>();
    for (const n of nodes.values()) if (n.parent && nodes.has(n.parent)) children.set(n.parent, [...(children.get(n.parent) ?? []), n]);
    const byLabel = (a: MappingNode, b: MappingNode) => a.label.localeCompare(b.label) || a.iri.localeCompare(b.iri);
    // Roots are the mappings with no parent in the scheme, templates after the rest.
    const roots = [...nodes.values()].filter((n) => !n.parent || !nodes.has(n.parent)).sort((a, b) => Number(a.isTemplate) - Number(b.isTemplate) || byLabel(a, b));
    const ordered: MappingNode[] = [];
    const seen = new Set<string>();
    const visit = (n: MappingNode, depth: number) => {
      if (seen.has(n.iri)) return;
      seen.add(n.iri);
      ordered.push({ ...n, depth, row: ordered.length });
      for (const c of (children.get(n.iri) ?? []).sort(byLabel)) visit(c, depth + 1);
    };
    roots.forEach((r) => visit(r, 0));
    // A cycle of parents has no root, and its mappings are listed after the rest, at depth 0.
    [...nodes.values()].sort(byLabel).forEach((n) => visit(n, 0));
    // A proposal's scheme is unlabelled, and is named by the run that generated its mappings.
    const run = members.map((m) => g.value(m, PROV + "wasGeneratedBy")).find(Boolean);
    const name = g.value(scheme, LABEL) ?? (run ? `${localName(scheme.value)}, proposed in ${run.split(/[:/#]/).pop()}` : localName(scheme.value));
    const used = new Set(ordered.map((n) => n.source));
    return { iri: scheme.value, label: name, labelled: g.value(scheme, LABEL) !== undefined, run: run ? costOf(g, run) : undefined, mappings: ordered, sources: sources.filter((s) => used.has(s.iri)) };
  })
    // A labelled scheme, such as a hand-made pack, before the proposals.
    .sort((a, b) => Number(b.labelled) - Number(a.labelled) || a.label.localeCompare(b.label));
}

function costOf(g: Graph, run: string): RunCost {
  const n = (p: string) => (g.value(run, p) === undefined ? undefined : Number(g.value(run, p)));
  const start = g.value(run, PROV + "startedAtTime");
  const end = g.value(run, PROV + "endedAtTime");
  return {
    iri: run,
    model: g.value(run, MORK("proposerModel")),
    inputTokens: n(MORK("inputTokens")),
    outputTokens: n(MORK("outputTokens")),
    totalTokens: n(MORK("totalTokens")),
    seconds: start && end ? Math.round((Date.parse(end) - Date.parse(start)) / 1000) : undefined,
  };
}

/** A review of one mapping, made in the studio: its decision, note and the mapping that corrects it, by the author, now. */
export function reviewGraph(mapping: string, decision: "Accepted" | "Corrected" | "Rejected" | "Deferred", note: string, at: string, n: number, correctedBy?: string): Graph {
  const review = `${mapping}/review/${n}`;
  return Graph.empty().edit((e) => {
    e.add(review, TYPE, iri(MORK("MappingReview")));
    e.add(review, TYPE, iri(PROV + "Activity"));
    e.add(review, MORK("reviewOf"), iri(mapping));
    e.add(review, MORK("reviewDecision"), iri(MORK(decision)));
    e.add(review, PROV + "wasAssociatedWith", iri("urn:lattice:studio:author"));
    e.add(review, PROV + "endedAtTime", typed(at, "http://www.w3.org/2001/XMLSchema#dateTime"));
    if (note.trim()) e.add(review, MORK("reviewNote"), literal(note.trim()));
    if (correctedBy) e.add(review, MORK("correctedBy"), iri(correctedBy));
  });
}

/** The terms a mapping writes, compacted, each with the box it writes in. */
export function written(n: MappingNode, prefixes: Record<string, string>): { box: string; term: string }[] {
  const c = (t: string) => compact(t, prefixes);
  return [
    ...n.targets.tbox.map((t) => ({ box: "a", term: c(t) })),
    ...n.targets.rbox.map((t) => ({ box: "→", term: c(t) })),
    ...n.targets.inverse.map((t) => ({ box: "←", term: c(t) })),
    ...n.targets.abox.map((t) => ({ box: "=", term: c(t) })),
  ];
}
