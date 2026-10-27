// SPDX-License-Identifier: MPL-2.0
// What the author's baseline declares: classes, properties, concept schemes and instances.

import { Graph } from "./graph";
import { COMMENT, LABEL, OWL, PREFIXES, RDF, RDFS, SKOS, TYPE, humanise, localName, namespaceOf } from "./ns";

const VOC = PREFIXES.voc;
const CLASS_TYPES = [OWL("Class"), RDFS("Class")];
const PROPERTY_TYPES = [OWL("ObjectProperty"), OWL("DatatypeProperty"), RDF("Property"), OWL("AnnotationProperty")];
const SCHEME_TYPES = [SKOS("ConceptScheme"), VOC + "ConceptScheme"];

export interface BaselineClass {
  iri: string;
  label: string;
  comment: string;
  parents: string[];
  children: string[];
  instances: number;
}

export interface BaselineProperty {
  iri: string;
  label: string;
  comment: string;
  domains: string[];
  ranges: string[];
  datatype: boolean;
}

export interface Concept {
  iri: string;
  label: string;
  broader: string[];
}

export interface Scheme {
  iri: string;
  label: string;
  concepts: Concept[];
}

export class Baseline {
  readonly classes = new Map<string, BaselineClass>();
  readonly properties = new Map<string, BaselineProperty>();
  readonly schemes: Scheme[] = [];
  readonly namespace: string;

  constructor(readonly graph: Graph) {
    const named = (types: string[]) =>
      [...new Set(types.flatMap((t) => graph.ofType(t).map((n) => n.value)))].sort();

    for (const iri of named(CLASS_TYPES)) {
      this.classes.set(iri, {
        iri,
        label: this.label(iri),
        comment: graph.value(iri, COMMENT) ?? "",
        parents: graph.objects(iri, RDFS("subClassOf")).filter((t) => t.termType === "NamedNode").map((t) => t.value),
        children: [],
        instances: graph.subjects(TYPE, iri).length,
      });
    }
    for (const c of this.classes.values()) {
      for (const parent of c.parents) this.classes.get(parent)?.children.push(c.iri);
    }
    for (const iri of named(PROPERTY_TYPES)) {
      this.properties.set(iri, {
        iri,
        label: this.label(iri),
        comment: graph.value(iri, COMMENT) ?? "",
        domains: graph.objects(iri, RDFS("domain")).map((t) => t.value),
        ranges: graph.objects(iri, RDFS("range")).map((t) => t.value),
        datatype: graph.types(iri).includes(OWL("DatatypeProperty")),
      });
    }
    for (const iri of named(SCHEME_TYPES)) {
      const concepts = graph
        .subjects(SKOS("inScheme"), iri)
        .map((c) => ({
          iri: c.value,
          label: this.label(c.value),
          broader: graph.objects(c, SKOS("broader")).map((b) => b.value),
        }))
        .sort((a, b) => a.label.localeCompare(b.label));
      this.schemes.push({ iri, label: this.label(iri), concepts });
    }
    this.namespace = dominantNamespace([...this.classes.keys(), ...this.properties.keys()]);
  }

  static parse(turtle: string): Baseline {
    return new Baseline(Graph.parse(turtle));
  }

  label(iri: string): string {
    const g = this.graph;
    return g.value(iri, LABEL) ?? g.value(iri, SKOS("prefLabel")) ?? humanise(localName(iri));
  }

  /** A class and every class it is asserted to be a subclass of, nearest first. */
  ancestors(iri: string): string[] {
    const out = [iri];
    for (let i = 0; i < out.length; i++) {
      for (const parent of this.classes.get(out[i])?.parents ?? []) if (!out.includes(parent)) out.push(parent);
    }
    return out;
  }

  /** The properties an instance of the class can have, by declared domain, inherited ones included. */
  propertiesOf(classIri: string): BaselineProperty[] {
    const lineage = new Set(this.ancestors(classIri));
    return [...this.properties.values()].filter((p) => p.domains.some((d) => lineage.has(d)));
  }

  roots(): BaselineClass[] {
    return [...this.classes.values()].filter((c) => !c.parents.some((p) => this.classes.has(p)));
  }

  /** Whether the baseline says anything about the term at all. */
  declares(iri: string): boolean {
    return this.graph.has(iri);
  }
}

function dominantNamespace(iris: string[]): string {
  const counts = new Map<string, number>();
  for (const iri of iris) counts.set(namespaceOf(iri), (counts.get(namespaceOf(iri)) ?? 0) + 1);
  return [...counts.entries()].sort((a, b) => b[1] - a[1])[0]?.[0] ?? "https://example.org/config#";
}
