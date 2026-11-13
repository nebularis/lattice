// SPDX-License-Identifier: MPL-2.0
// The import graph, a view of the Baseline's diagram (SVA-B4) derived from the graphs the browser already holds and never stored.
// Its nodes are the workspace's own ontology, each held import, each import no held document declares, and each concept scheme
// the workspace holds. Its edges are of three kinds. An `imports` edge is stated by `owl:imports`, from an ontology to the node
// that declares the IRI it names as its ontology IRI or version IRI, or to the missing node. A `binds` edge is stated by a scheme
// contract and its bindings (`voc:constrainsProperty`, `voc:forContract`, `voc:bindsScheme`, `voc:boundScheme`), and is drawn from
// the ontology node whose document declares the contract's property to the scheme the binding names, labelled with the contract.
// A `uses` edge is derived, from an ontology to another whose declared term (a subject with an `rdf:type`) the first document uses
// as a predicate, as an `rdf:type` object or in `rdfs:subClassOf`, `rdfs:subPropertyOf`, `rdfs:domain` or `rdfs:range`, and to a
// scheme whose concept or whose scheme itself a document names as an object. A derived edge is never drawn between a pair a stated
// edge already joins, so it adds information and repeats none. Nodes and edges are sorted by kind and id, so the same graphs in
// any order give the same drawing.

import { Graph, LABEL, OWL, PREFIXES, RDFS, SKOS, TYPE, VOC, compact, humanise, localName } from "@lattice/authoring-domain";
import { heldByIri, missingImports, shortIri, type HeldImport } from "./held";

export type ImportNodeKind = "own" | "held" | "missing" | "scheme";
export type ImportEdgeKind = "imports" | "binds" | "uses";

/** Where a scheme is declared. */
export type SchemeSource = "baseline" | "vocabulary" | "import" | "dependency";

export interface ImportNode {
  id: string;
  kind: ImportNodeKind;
  label: string;
  /** The ontology IRI of an ontology node, the IRI an import names for a missing one, and a scheme's own IRI. */
  iri?: string;
  /** The digest of a held import, and of the held import that declares a scheme. */
  digest?: string;
  /** A scheme's place of declaration. */
  declaredIn?: SchemeSource;
}

export interface ImportEdge {
  id: string;
  source: string;
  target: string;
  kind: ImportEdgeKind;
  /** The contract's compact name, on a `binds` edge. */
  label?: string;
}

export interface ImportGraph {
  nodes: ImportNode[];
  edges: ImportEdge[];
}

export interface ImportGraphInput {
  baseline: Graph;
  held: readonly HeldImport[];
  /** The vocabulary part's graph, where the browser holds it. */
  vocabulary?: Graph;
  /** The graphs of the workspace's dependencies, where the browser holds them. */
  dependencies?: readonly Graph[];
}

const SCHEME_TYPES = [SKOS("ConceptScheme"), VOC("ConceptScheme")];
/** The positions, besides a predicate, where a named term of a document is a use of it. */
const USE_PREDICATES = [RDFS("subClassOf"), RDFS("subPropertyOf"), RDFS("domain"), RDFS("range")];

const text = (a: string, b: string) => (a < b ? -1 : a > b ? 1 : 0);
const byId = (a: { id: string }, b: { id: string }) => text(a.id, b.id);
const named = (terms: readonly { termType: string; value: string }[]) => terms.filter((t) => t.termType === "NamedNode").map((t) => t.value);

const OWN = "own";
const heldId = (digest: string) => `held:${digest}`;
const missingId = (iri: string) => `missing:${iri}`;
const schemeId = (iri: string) => `scheme:${iri}`;

/** The terms a graph declares, each a named subject with an `rdf:type`. */
function declaredTerms(graph: Graph): Set<string> {
  return new Set(graph.quads(null, TYPE).filter((q) => q.subject.termType === "NamedNode").map((q) => q.subject.value));
}

/** The named terms a document uses as a predicate, as a type, and in the four axioms that name a class or a property. */
function usedTerms(graph: Graph): Set<string> {
  const used = new Set<string>();
  for (const q of graph.quads()) {
    used.add(q.predicate.value);
    if ((q.predicate.value === TYPE || USE_PREDICATES.includes(q.predicate.value)) && q.object.termType === "NamedNode") used.add(q.object.value);
  }
  return used;
}

const schemesOf = (graph: Graph): string[] => [...new Set(SCHEME_TYPES.flatMap((t) => graph.ofType(t).map((n) => n.value)))];

function schemeLabel(graph: Graph, iri: string): string {
  return graph.value(iri, SKOS("prefLabel")) ?? graph.value(iri, LABEL) ?? humanise(localName(iri));
}

/** The nodes and edges of the import graph. */
export function importGraph(input: ImportGraphInput): ImportGraph {
  const { baseline, vocabulary, dependencies = [] } = input;
  const held = [...input.held].sort((a, b) => text(a.digest, b.digest));
  const byIri = heldByIri(held);
  const nodes = new Map<string, ImportNode>();
  const edges = new Map<string, ImportEdge>();
  const graphOf = new Map<string, Graph>();

  const ownOntology = baseline.ofType(OWL("Ontology")).map((n) => n.value).sort(text)[0];
  const ownVersion = ownOntology === undefined ? undefined : named(baseline.objects(ownOntology, OWL("versionIRI"))).sort(text)[0];
  nodes.set(OWN, { id: OWN, kind: "own", label: (ownOntology !== undefined && baseline.value(ownOntology, LABEL)) || "This workspace", iri: ownOntology });
  graphOf.set(OWN, baseline);
  for (const h of held) {
    const id = heldId(h.digest);
    nodes.set(id, { id, kind: "held", label: h.label, iri: h.ontology, digest: h.digest });
    if (h.graph) graphOf.set(id, h.graph);
  }
  const missing = missingImports(baseline, held);
  for (const m of missing) nodes.set(missingId(m.iri), { id: missingId(m.iri), kind: "missing", label: shortIri(m.iri), iri: m.iri });

  // The node an owl:imports IRI resolves to.
  const resolve = (iri: string): string | undefined =>
    byIri.has(iri) ? heldId(byIri.get(iri)!) : iri === ownOntology || iri === ownVersion ? OWN : nodes.has(missingId(iri)) ? missingId(iri) : undefined;

  const addEdge = (kind: ImportEdgeKind, source: string, target: string, label?: string) => {
    const id = `${kind}|${source}|${target}${label === undefined ? "" : `|${label}`}`;
    if (!edges.has(id)) edges.set(id, { id, source, target, kind, ...(label === undefined ? {} : { label }) });
  };

  // Stated: owl:imports, from each ontology a loaded graph names.
  for (const [id, graph] of graphOf) {
    for (const from of graph.ofType(OWL("Ontology")).map((n) => n.value)) {
      for (const to of named(graph.objects(from, OWL("imports")))) {
        const target = resolve(to);
        if (target !== undefined && target !== id) addEdge("imports", id, target);
      }
    }
  }

  // Schemes, from every graph the browser holds. Where one is declared in several, the first of these answers.
  const places: { graph: Graph; source: SchemeSource; digest?: string }[] = [
    { graph: baseline, source: "baseline" },
    ...(vocabulary ? [{ graph: vocabulary, source: "vocabulary" as const }] : []),
    ...held.flatMap((h) => (h.graph ? [{ graph: h.graph, source: "import" as const, digest: h.digest }] : [])),
    ...dependencies.map((graph) => ({ graph, source: "dependency" as const })),
  ];
  const conceptSchemes = new Map<string, Set<string>>();
  for (const { graph, source, digest } of places) {
    for (const iri of schemesOf(graph)) {
      const id = schemeId(iri);
      if (!nodes.has(id)) nodes.set(id, { id, kind: "scheme", label: schemeLabel(graph, iri), iri, declaredIn: source, ...(digest === undefined ? {} : { digest }) });
    }
    for (const q of graph.quads(null, SKOS("inScheme"))) {
      if (q.subject.termType !== "NamedNode" || q.object.termType !== "NamedNode") continue;
      if (!conceptSchemes.has(q.subject.value)) conceptSchemes.set(q.subject.value, new Set());
      conceptSchemes.get(q.subject.value)!.add(q.object.value);
    }
  }

  // Stated: a scheme contract's bindings name schemes, and the contract's property belongs to the ontology that declares it.
  const declared = new Map<string, Set<string>>([...graphOf].map(([id, g]) => [id, declaredTerms(g)]));
  const prefixes: Record<string, string> = { ...PREFIXES };
  for (const { graph } of places) Object.assign(prefixes, graph.prefixes);
  for (const { graph } of places) {
    for (const contract of graph.ofType(VOC("SchemeContract"))) {
      const properties = named(graph.objects(contract, VOC("constrainsProperty")));
      const bound = new Set(named(graph.objects(contract, VOC("boundScheme"))));
      for (const b of graph.subjects(VOC("forContract"), contract)) for (const s of named(graph.objects(b, VOC("bindsScheme")))) bound.add(s);
      for (const property of properties) {
        for (const [id, terms] of declared) {
          if (!terms.has(property)) continue;
          for (const scheme of bound) if (nodes.has(schemeId(scheme))) addEdge("binds", id, schemeId(scheme), compact(contract.value, prefixes));
        }
      }
    }
  }

  // Derived: the terms a document uses that another declares.
  const joined = (a: string, b: string) => [...edges.values()].some((e) => e.kind !== "uses" && ((e.source === a && e.target === b) || (e.source === b && e.target === a)));
  const declaredBy = new Map<string, string[]>();
  for (const [id, terms] of declared) for (const t of terms) declaredBy.set(t, [...(declaredBy.get(t) ?? []), id]);
  for (const [id, graph] of graphOf) {
    const mine = declared.get(id)!;
    const reached = new Set<string>();
    for (const term of usedTerms(graph)) {
      if (mine.has(term)) continue;
      for (const other of declaredBy.get(term) ?? []) if (other !== id) reached.add(other);
    }
    for (const other of [...reached].sort(text)) if (!joined(id, other)) addEdge("uses", id, other);
    // A scheme is used where a document names it or one of its concepts as an object, outside the scheme's own structure.
    const schemes = new Set<string>();
    for (const q of graph.quads()) {
      if (q.object.termType !== "NamedNode" || q.subject.termType !== "NamedNode") continue;
      if (conceptSchemes.has(q.subject.value) || nodes.has(schemeId(q.subject.value))) continue;
      const hit = nodes.has(schemeId(q.object.value)) ? [q.object.value] : [...(conceptSchemes.get(q.object.value) ?? [])];
      for (const s of hit) if (nodes.has(schemeId(s)) && !mine.has(s)) schemes.add(s);
    }
    for (const s of [...schemes].sort(text)) if (!joined(id, schemeId(s))) addEdge("uses", id, schemeId(s));
  }

  return {
    nodes: [...nodes.values()].sort((a, b) => text(a.kind, b.kind) || byId(a, b)),
    edges: [...edges.values()].sort((a, b) => text(a.kind, b.kind) || byId(a, b)),
  };
}

export interface ImportCounts {
  /** The workspace's own ontology, always one. */
  ontologies: number;
  held: number;
  missing: number;
  schemes: number;
}

/** How many of each node a view holds, for the line above the canvas. */
export function importCounts(view: ImportGraph): ImportCounts {
  const n = (kind: ImportNodeKind) => view.nodes.filter((x) => x.kind === kind).length;
  return { ontologies: n("own"), held: n("held"), missing: n("missing"), schemes: n("scheme") };
}

/** The line above the canvas, for example "1 ontology of the workspace, 2 imports held, 1 missing, 3 schemes." */
export function importSummary(view: ImportGraph): string {
  const c = importCounts(view);
  const many = (n: number, one: string, other: string) => `${n} ${n === 1 ? one : other}`;
  return `${many(c.ontologies, "ontology", "ontologies")} of the workspace, ${many(c.held, "import", "imports")} held, ${c.missing} missing, ${many(c.schemes, "scheme", "schemes")}.`;
}
