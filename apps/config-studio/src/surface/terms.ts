// SPDX-License-Identifier: MPL-2.0
// What the canvas knows of the ontology the workspace holds (SVA-Q62), read through the same `Baseline` the ontology view reads. The ontology
// is the baseline with the imports the workspace holds merged beside it, so a term an import declares is declared. A target a contract writes
// is looked up here, and a term the ontology does not declare is marked and never invented.

import { Graph, RDF, XSD, localName } from "@lattice/authoring-domain";
import { Baseline } from "../rdf/baseline";

/** What the drawing asks of the ontology, so that its functions are tested with a small one. */
export interface Terms {
  label(iri: string): string;
  /** The first declared range of a property, and its first declared domain. */
  range(property: string): string | undefined;
  domain(property: string): string | undefined;
  isClass(iri: string): boolean;
  /** A property or class of this name declared as such. */
  declared(kind: "property" | "class", iri: string): boolean;
  rangesOf(property: string): string[];
}

/** The baseline with the held imports and the pinned dependencies beside it, as one ontology to read. */
export function ontologyOf(baseline: Graph, others: readonly Graph[]): Baseline {
  return new Baseline(others.reduce((all, g) => all.merge(g), baseline));
}

const PLAIN = (iri: string): string | undefined => (iri.startsWith(XSD("")) ? iri.slice(XSD("").length) : iri.startsWith(RDF("")) ? `rdf:${iri.slice(RDF("").length)}` : undefined);

export function termsOf(b: Baseline): Terms {
  // A blank node is a class expression, which a range or a domain may be and this does not read. An IRI always holds a colon.
  const named = (iris: string[]) => iris.filter((i) => i.includes(":"));
  return {
    label: (iri) => PLAIN(iri) ?? b.classes.get(iri)?.label ?? b.properties.get(iri)?.label ?? (b.declares(iri) ? b.label(iri) : localName(iri)),
    range: (p) => named(b.properties.get(p)?.ranges ?? [])[0],
    domain: (p) => named(b.properties.get(p)?.domains ?? [])[0],
    isClass: (iri) => b.classes.has(iri),
    declared: (kind, iri) => (kind === "class" ? b.classes.has(iri) : b.properties.has(iri)),
    rangesOf: (p) => named(b.properties.get(p)?.ranges ?? []),
  };
}

export interface TargetInfo {
  kind: "property" | "class";
  iri: string;
  label: string;
  declared: boolean;
  /** A property's declared ranges, by their labels, and a class's own label is its title. */
  ranges: string[];
  /** The datatypes the contracts shown state for the target, by their local names. */
  stated: string[];
  /** Where a stated datatype is none of the declared ranges. A property with no declared range disagrees with nothing. */
  disagrees: boolean;
}

/** A target as the ontology declares it, with the datatypes the contracts state for it. */
export function readTarget(terms: Terms, kind: "property" | "class", iri: string, stated: readonly string[] = []): TargetInfo {
  const declared = terms.declared(kind, iri);
  const ranges = kind === "property" && declared ? terms.rangesOf(iri) : [];
  const states = [...new Set(stated)].sort();
  const disagrees = kind === "property" && declared && ranges.length > 0 && states.some((s) => !ranges.includes(s));
  return { kind, iri, label: terms.label(iri), declared, ranges: ranges.map((r) => terms.label(r)), stated: states.map((s) => terms.label(s)), disagrees };
}
