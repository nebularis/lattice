// SPDX-License-Identifier: MPL-2.0
// What the Baseline view's list of ontologies shows, derived from the baseline, the imports the workspace holds
// and the graphs of those the browser has loaded. Nothing is stored and nothing is fetched. An import is missing
// when an owl:imports statement of the baseline, or of a loaded held import, names an IRI that no held import
// declares as its ontology IRI or version IRI (SVA-Q7). The same input in any order gives the same output.

import { OWL, type Graph } from "@lattice/authoring-domain";

export interface HeldImport {
  digest: string;
  label: string;
  /** The ontology IRI its document declares, when it declares one. */
  ontology?: string;
  /** The version IRI its document declares, when it declares one. */
  version?: string;
  /** Its graph, where the browser has loaded it. */
  graph?: Graph;
}

export interface MissingImport {
  iri: string;
  /** The ontology IRIs, or for a document that declares none its label, of what imports it. Sorted. */
  importedBy: string[];
}

export type OntologyEntry =
  | { kind: "own"; ontology?: string; version?: string }
  | { kind: "held"; digest: string; label: string; ontology?: string; version?: string }
  | { kind: "missing"; iri: string; importedBy: string[] };

export interface HeldView {
  heldByIri: Map<string, string>;
  missingImports: MissingImport[];
  ontologyList: OntologyEntry[];
}

const compare = (a: string, b: string): number => (a < b ? -1 : a > b ? 1 : 0);

/** The named nodes a graph declares as owl:Ontology, sorted. */
function ontologiesOf(graph: Graph): string[] {
  return graph
    .ofType(OWL("Ontology"))
    .map((n) => n.value)
    .sort(compare);
}

/** The own header of a graph: its first ontology IRI by order, and that ontology's version IRI. */
function ownHeader(graph: Graph): { ontology?: string; version?: string } {
  const ontology = ontologiesOf(graph)[0];
  if (ontology === undefined) return {};
  const version = graph
    .objects(ontology, OWL("versionIRI"))
    .filter((t) => t.termType === "NamedNode")
    .map((t) => t.value)
    .sort(compare)[0];
  return { ontology, version };
}

/** Every owl:imports object of a graph's named ontologies, with the ontology that states it. */
function importsOf(graph: Graph): { from: string; to: string }[] {
  return ontologiesOf(graph).flatMap((from) =>
    graph
      .objects(from, OWL("imports"))
      .filter((t) => t.termType === "NamedNode")
      .map((t) => ({ from, to: t.value })),
  );
}

const orderedHeld = (held: readonly HeldImport[]): HeldImport[] => [...held].sort((a, b) => compare(a.label, b.label) || compare(a.digest, b.digest));

/**
 * From every ontology IRI and version IRI a held import declares to its digest, the `held` input of `resolveImports`.
 * Where two held imports declare one IRI, the one with the lesser digest answers.
 */
export function heldByIri(held: readonly HeldImport[]): Map<string, string> {
  const out = new Map<string, string>();
  for (const h of [...held].sort((a, b) => compare(a.digest, b.digest))) {
    for (const iri of [h.ontology, h.version]) if (iri !== undefined && !out.has(iri)) out.set(iri, h.digest);
  }
  return out;
}

/** The imports that none of the held imports declares, each with what imports it. */
export function missingImports(baseline: Graph, held: readonly HeldImport[]): MissingImport[] {
  const declared = heldByIri(held);
  const own = ownHeader(baseline);
  const stated: { from: string; to: string }[] = importsOf(baseline);
  for (const h of held) {
    if (!h.graph) continue;
    const name = h.ontology ?? ownHeader(h.graph).ontology ?? h.label;
    for (const edge of importsOf(h.graph)) stated.push({ from: name, to: edge.to });
  }
  const missing = new Map<string, Set<string>>();
  for (const { from, to } of stated) {
    if (declared.has(to) || to === own.ontology || to === own.version) continue;
    if (!missing.has(to)) missing.set(to, new Set());
    missing.get(to)!.add(from);
  }
  return [...missing.entries()].sort(([a], [b]) => compare(a, b)).map(([iri, by]) => ({ iri, importedBy: [...by].sort(compare) }));
}

/** What the left list shows: the workspace's own ontology, each held import, then each missing import. */
export function ontologyList(baseline: Graph, held: readonly HeldImport[]): OntologyEntry[] {
  const own = ownHeader(baseline);
  return [
    { kind: "own", ontology: own.ontology, version: own.version },
    ...orderedHeld(held).map((h): OntologyEntry => ({ kind: "held", digest: h.digest, label: h.label, ontology: h.ontology, version: h.version })),
    ...missingImports(baseline, held).map((m): OntologyEntry => ({ kind: "missing", iri: m.iri, importedBy: m.importedBy })),
  ];
}

/** The three at once, for a view that needs them together. */
export function heldView(baseline: Graph, held: readonly HeldImport[]): HeldView {
  return { heldByIri: heldByIri(held), missingImports: missingImports(baseline, held), ontologyList: ontologyList(baseline, held) };
}

/** An IRI cut in the middle when it is longer than `max`, for a list, with the whole IRI left to a title. */
export function shortIri(iri: string, max = 44): string {
  const bare = iri.replace(/^[a-zA-Z][a-zA-Z0-9+.-]*:\/\//, "");
  if (bare.length <= max) return bare;
  const head = Math.ceil((max - 1) / 2);
  return `${bare.slice(0, head)}…${bare.slice(bare.length - (max - 1 - head))}`;
}

/** A label of at most `max` characters, cut in the middle with an ellipsis when longer. */
export function shortLabel(label: string, max = 200): string {
  if (label.length <= max) return label;
  const head = Math.ceil((max - 1) / 2);
  return `${label.slice(0, head)}…${label.slice(label.length - (max - 1 - head))}`;
}
