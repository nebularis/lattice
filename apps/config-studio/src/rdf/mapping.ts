// SPDX-License-Identifier: MPL-2.0
// The mapping view's model: each MORK mapping scheme of the mapping part, its mappings as the tree their
// mork:compositeBroaderMapping links make, the source concepts they read, and the terms each writes. It is read only, and
// lays the tree out the same way every time, one row per mapping in depth-first order.

import { Graph, LABEL, MORK, compact, localName, type Term } from "@lattice/authoring-domain";

export interface Targets {
  tbox: string[];
  rbox: string[];
  inverse: string[];
  abox: string[];
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
  depth: number;
  row: number;
}

export interface SourceConcept {
  iri: string;
  label: string;
  path?: string;
  representedAs: string[];
}

export interface Scheme {
  iri: string;
  label: string;
  mappings: MappingNode[];
  sources: SourceConcept[];
}

const label = (g: Graph, node: string) => g.value(node, LABEL) ?? localName(node);
const iris = (terms: Term[]) => terms.filter((t) => t.termType === "NamedNode").map((t) => t.value).sort();

export function schemesOf(g: Graph): Scheme[] {
  const sources = [...g.ofType(MORK("DataConcept")), ...g.ofType(MORK("Entity"))].map((s) => ({
    iri: s.value,
    label: label(g, s.value),
    path: g.value(s, MORK("path")),
    representedAs: iris(g.objects(s, MORK("representedAs"))),
  }));
  return g.ofType(MORK("MappingScheme")).map((scheme) => {
    const members = g.subjects(MORK("mappingScheme"), scheme).filter((m) => m.termType === "NamedNode").map((m) => m.value);
    const templates = new Set(members.flatMap((m) => g.objects(m, MORK("templateMapping")).map((t) => t.value)));
    const read = (m: string): MappingNode => {
      const inline = g.object(m, MORK("dataInline"));
      return {
        iri: m,
        label: label(g, m),
        kind: localName(g.types(m).find((t) => t.startsWith(MORK(""))) ?? MORK("Mapping")),
        parent: g.value(m, MORK("compositeBroaderMapping")),
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
    return { iri: scheme.value, label: label(g, scheme.value), mappings: ordered, sources };
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
