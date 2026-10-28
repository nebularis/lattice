// SPDX-License-Identifier: MPL-2.0
// The namespaces the studio reads and writes, and the prefixes its Turtle is written with.

const ns = (base: string) => (local: string) => base + local;

export const PREFIXES: Record<string, string> = {
  rdf: "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
  rdfs: "http://www.w3.org/2000/01/rdf-schema#",
  owl: "http://www.w3.org/2002/07/owl#",
  xsd: "http://www.w3.org/2001/XMLSchema#",
  sh: "http://www.w3.org/ns/shacl#",
  skos: "http://www.w3.org/2004/02/skos/core#",
  dal: "https://www.nebularis.org/neuro-semantic/lattice/persistence#",
  srf: "https://www.nebularis.org/neuro-semantic/lattice/surface#",
  fnd: "https://www.nebularis.org/neuro-semantic/lattice/foundation#",
  voc: "https://www.nebularis.org/neuro-semantic/lattice/vocabulary#",
  qnt: "https://www.nebularis.org/neuro-semantic/lattice/quantification#",
  elg: "https://www.nebularis.org/neuro-semantic/lattice/eligibility#",
  exe: "https://www.nebularis.org/neuro-semantic/lattice/executable#",
  cst: "https://www.nebularis.org/neuro-semantic/lattice/poc/config-studio#",
};

export const RDF = ns(PREFIXES.rdf);
export const RDFS = ns(PREFIXES.rdfs);
export const OWL = ns(PREFIXES.owl);
export const XSD = ns(PREFIXES.xsd);
export const SH = ns(PREFIXES.sh);
export const SKOS = ns(PREFIXES.skos);
export const DAL = ns(PREFIXES.dal);
export const SRF = ns(PREFIXES.srf);
export const CST = ns(PREFIXES.cst);
export const VOC = ns(PREFIXES.voc);
export const FND = ns(PREFIXES.fnd);
export const QNT = ns(PREFIXES.qnt);
export const ELG = ns(PREFIXES.elg);

export const TYPE = RDF("type");
export const LABEL = RDFS("label");
export const COMMENT = RDFS("comment");

/** The namespace of an IRI: everything up to and including its last # or /. */
export function namespaceOf(iri: string): string {
  const cut = Math.max(iri.lastIndexOf("#"), iri.lastIndexOf("/"));
  return cut < 0 ? iri : iri.slice(0, cut + 1);
}

export function localName(iri: string): string {
  return iri.slice(namespaceOf(iri).length) || iri;
}

/** A compact name for display, `dal:strategy` for a known namespace, the local name otherwise. */
export function compact(iri: string, prefixes: Record<string, string> = PREFIXES): string {
  for (const [prefix, base] of Object.entries(prefixes)) {
    if (iri.startsWith(base) && iri.length > base.length) return `${prefix}:${iri.slice(base.length)}`;
  }
  return localName(iri);
}

/** "graphIriTemplate" and "ClassScope" become "graph IRI template" and "class scope". */
export function humanise(name: string): string {
  return name
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .replace(/([A-Z]+)([A-Z][a-z])/g, "$1 $2")
    .replace(/[_-]+/g, " ")
    .replace(/\b([A-Z])([a-z])/g, (_, a: string, b: string) => a.toLowerCase() + b)
    .trim();
}

export function sentence(text: string): string {
  return text ? text[0].toUpperCase() + text.slice(1) : text;
}
