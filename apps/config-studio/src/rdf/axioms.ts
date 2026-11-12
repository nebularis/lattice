// SPDX-License-Identifier: MPL-2.0
// Reads the OWL, SHACL and annotation statements a graph holds about one class, property or
// individual into structures a read-only form can render (SVA-O3, decision SVA-Q9). A class
// expression is a tree, never text. A statement the reader does not recognise is kept, in `other`
// or in an `unknown` node, so nothing the graph says about an element is hidden. Every list is
// sorted by a key that does not depend on the order of the triples or on blank node labels, so the
// same graph reads the same.

import { COMMENT, Graph, LABEL, OWL, RDF, RDFS, SH, SKOS, TYPE, XSD, type Quad, type Term } from "@lattice/authoring-domain";

/** How many nested blank nodes a read follows before it stops and says so. */
export const MAX_DEPTH = 32;

export interface TermValue {
  kind: "iri" | "literal" | "blank";
  /** The IRI or the lexical form. Empty for a blank node, whose label carries no meaning. */
  value: string;
  datatype?: string;
  language?: string;
  /** What a blank node states, for a node the reader did not turn into anything more specific. */
  rows?: Row[];
  /** Set where the depth cap or a cycle stopped the read of a blank node. */
  truncated?: true;
}

export interface Row {
  predicate: string;
  object: TermValue;
}

export interface PropertyRef {
  iri: string;
  /** The property is written as owl:inverseOf the IRI. */
  inverse?: true;
}

export type Quantifier = "some" | "only" | "value" | "self" | "min" | "max" | "exactly";

export type ClassExpr = (
  | { kind: "named"; iri: string }
  | {
      kind: "restriction";
      property: PropertyRef;
      quantifier: Quantifier;
      /** For min, max and exactly. */
      cardinality?: number;
      /** The class or data range of a some, only or qualified cardinality restriction. */
      filler?: ClassExpr;
      /** For hasValue. */
      value?: TermValue;
    }
  | { kind: "intersection"; members: ClassExpr[] }
  | { kind: "union"; members: ClassExpr[] }
  | { kind: "complement"; operand: ClassExpr }
  | { kind: "oneOf"; members: TermValue[] }
  | { kind: "datatypeRestriction"; datatype: string; facets: { facet: string; value: TermValue }[] }
  | { kind: "unknown"; reason: "unrecognised" | "malformed" | "depth" | "cycle"; term: TermValue }
) & {
  /** Statements on the expression's own node that no part of the tree above uses. */
  extra?: Row[];
};

export interface Annotation {
  property: string;
  /** The language tag, empty for none. */
  language: string;
  values: { value: string; datatype?: string }[];
}

export interface ConstraintRow {
  /** The local name in the SHACL namespace, such as "datatype" or "minCount". */
  constraint: string;
  values: TermValue[];
}

export interface PropertyShapeRow {
  path?: TermValue;
  constraints: ConstraintRow[];
  other: Row[];
}

export interface ShapeRow {
  /** Absent for a shape that is a blank node. */
  shape?: string;
  targets: string[];
  properties: PropertyShapeRow[];
}

export interface PropertyShapeUse {
  /** The node shape that holds the property shape, absent when none does. */
  nodeShape?: string;
  targets: string[];
  shape: PropertyShapeRow;
}

export interface DomainProperty {
  property: string;
  /** The named superclass the domain is declared on, absent for a direct domain. */
  from?: string;
}

export interface ClassAxioms {
  iri: string;
  annotations: Annotation[];
  superClasses: ClassExpr[];
  equivalentClasses: ClassExpr[];
  disjointClasses: ClassExpr[];
  keys: PropertyRef[][];
  properties: DomainProperty[];
  shapes: ShapeRow[];
  individuals: string[];
  other: Row[];
}

export type PropertyKind = "object" | "datatype" | "annotation";
export type Characteristic = "functional" | "inverse functional" | "transitive" | "symmetric" | "asymmetric" | "reflexive" | "irreflexive";

export interface PropertyAxioms {
  iri: string;
  kinds: PropertyKind[];
  characteristics: Characteristic[];
  domains: ClassExpr[];
  ranges: ClassExpr[];
  superProperties: string[];
  inverseOf: string[];
  chains: PropertyRef[][];
  shapes: PropertyShapeUse[];
  annotations: Annotation[];
  other: Row[];
}

export interface Assertion {
  property: string;
  values: TermValue[];
}

export interface IndividualAxioms {
  iri: string;
  types: string[];
  assertions: Assertion[];
  annotations: Annotation[];
}

const KINDS: [string, PropertyKind][] = [
  [OWL("ObjectProperty"), "object"],
  [OWL("DatatypeProperty"), "datatype"],
  [OWL("AnnotationProperty"), "annotation"],
];
const CHARACTERISTICS: [string, Characteristic][] = [
  [OWL("FunctionalProperty"), "functional"],
  [OWL("InverseFunctionalProperty"), "inverse functional"],
  [OWL("TransitiveProperty"), "transitive"],
  [OWL("SymmetricProperty"), "symmetric"],
  [OWL("AsymmetricProperty"), "asymmetric"],
  [OWL("ReflexiveProperty"), "reflexive"],
  [OWL("IrreflexiveProperty"), "irreflexive"],
];
const ANNOTATION_ORDER = [LABEL, COMMENT, SKOS("prefLabel"), SKOS("definition"), SKOS("note"), SKOS("scopeNote"), SKOS("example")];
const CONSTRAINTS = ["datatype", "class", "node", "nodeKind", "minCount", "maxCount", "in", "pattern", "hasValue", "name", "description"];
const QUANTIFIERS: [string, Quantifier, boolean][] = [
  [OWL("someValuesFrom"), "some", false],
  [OWL("allValuesFrom"), "only", false],
  [OWL("hasValue"), "value", false],
  [OWL("hasSelf"), "self", false],
  [OWL("minCardinality"), "min", false],
  [OWL("maxCardinality"), "max", false],
  [OWL("cardinality"), "exactly", false],
  [OWL("minQualifiedCardinality"), "min", true],
  [OWL("maxQualifiedCardinality"), "max", true],
  [OWL("qualifiedCardinality"), "exactly", true],
];
const MARKER_TYPES = new Set([OWL("Restriction"), OWL("Class"), RDFS("Datatype")]);

const text = (a: string, b: string) => (a < b ? -1 : a > b ? 1 : 0);
const json = (value: unknown) => JSON.stringify(value);
const byJson = <T>(items: T[]): T[] => [...items].sort((a, b) => text(json(a), json(b)));
const unique = <T>(items: T[]): T[] => [...new Map(items.map((i) => [json(i), i])).values()];
/** A key that orders terms by their lexical form first, and does not depend on blank node labels. */
const termKey = (t: TermValue) => `${t.kind}\u0000${t.value}\u0000${t.datatype ?? ""}\u0000${t.language ?? ""}\u0000${t.rows ? json(t.rows) : ""}`;
const byTerm = (items: TermValue[]): TermValue[] => [...items].sort((a, b) => text(termKey(a), termKey(b)));
const strings = (items: string[]) => [...new Set(items)].sort(text);

/** The quads of one subject, with a record of the ones a section has used. */
class Taken {
  private readonly used = new Set<Quad>();
  constructor(readonly quads: Quad[]) {}

  /** The unused quads of a predicate that pass `accept`, marked used. */
  take(predicate: string, accept: (q: Quad) => boolean = () => true): Quad[] {
    const out = this.quads.filter((q) => q.predicate.value === predicate && !this.used.has(q) && accept(q));
    for (const q of out) this.used.add(q);
    return out;
  }

  takeWhere(accept: (q: Quad) => boolean): Quad[] {
    const out = this.quads.filter((q) => !this.used.has(q) && accept(q));
    for (const q of out) this.used.add(q);
    return out;
  }

  rest(): Quad[] {
    return this.quads.filter((q) => !this.used.has(q));
  }
}

function termValue(graph: Graph, t: Term, depth: number, path: ReadonlySet<string>): TermValue {
  if (t.termType === "NamedNode") return { kind: "iri", value: t.value };
  if (t.termType === "Literal") {
    const out: TermValue = { kind: "literal", value: t.value };
    if (t.language) out.language = t.language;
    else if (t.datatype.value !== XSD("string")) out.datatype = t.datatype.value;
    return out;
  }
  if (depth >= MAX_DEPTH || path.has(t.id)) return { kind: "blank", value: "", rows: [], truncated: true };
  return { kind: "blank", value: "", rows: rowsOf(graph, graph.quads(t), depth + 1, new Set(path).add(t.id)) };
}

function rowsOf(graph: Graph, quads: Quad[], depth: number, path: ReadonlySet<string>): Row[] {
  const rows = quads.map((q) => ({ predicate: q.predicate.value, object: termValue(graph, q.object, depth, path) }));
  return rows.sort((a, b) => text(a.predicate, b.predicate) || text(termKey(a.object), termKey(b.object)));
}

const rank = (e: ClassExpr) => (e.kind === "named" ? 0 : e.kind === "restriction" ? 1 : 2);
const sortExprs = (items: ClassExpr[]): ClassExpr[] => unique(items).sort((a, b) => rank(a) - rank(b) || text(json(a), json(b)));

function propertyRef(graph: Graph, t: Term): PropertyRef | undefined {
  if (t.termType === "NamedNode") return { iri: t.value };
  if (t.termType !== "BlankNode") return undefined;
  const quads = graph.quads(t);
  const inverse = quads.filter((q) => q.predicate.value === OWL("inverseOf"));
  return quads.length === 1 && inverse.length === 1 && inverse[0].object.termType === "NamedNode" ? { iri: inverse[0].object.value, inverse: true } : undefined;
}

function nonNegative(t: Term | undefined): number | undefined {
  const n = t?.termType === "Literal" ? Number(t.value) : NaN;
  return Number.isInteger(n) && n >= 0 ? n : undefined;
}

/** The expression a node stands for. A node the reader cannot read becomes `unknown` with its triples. */
export function readExpression(graph: Graph, t: Term, depth = 0, path: ReadonlySet<string> = new Set()): ClassExpr {
  if (t.termType === "NamedNode") return { kind: "named", iri: t.value };
  const unknown = (reason: "unrecognised" | "malformed" | "depth" | "cycle"): ClassExpr => ({ kind: "unknown", reason, term: termValue(graph, t, depth, path) });
  if (t.termType !== "BlankNode") return unknown("unrecognised");
  if (depth >= MAX_DEPTH) return { kind: "unknown", reason: "depth", term: { kind: "blank", value: "", rows: [], truncated: true } };
  if (path.has(t.id)) return { kind: "unknown", reason: "cycle", term: { kind: "blank", value: "", rows: [], truncated: true } };

  const inner = new Set(path).add(t.id);
  const sub = (x: Term) => readExpression(graph, x, depth + 1, inner);
  const taken = new Taken(graph.quads(t));
  const single = (predicate: string): Term | undefined => {
    const found = taken.quads.filter((q) => q.predicate.value === predicate);
    return found.length === 1 ? found[0].object : undefined;
  };
  const finish = (expr: ClassExpr, predicates: string[]): ClassExpr => {
    for (const p of predicates) taken.take(p);
    const extra = rowsOf(graph, taken.rest(), depth + 1, inner);
    return extra.length ? { ...expr, extra } : expr;
  };
  // The type markers of a restriction or class node say nothing more than its shape does.
  taken.takeWhere((q) => q.predicate.value === TYPE && MARKER_TYPES.has(q.object.value));

  const onProperty = single(OWL("onProperty"));
  if (onProperty) {
    const property = propertyRef(graph, onProperty);
    const present = QUANTIFIERS.filter(([p]) => taken.quads.some((q) => q.predicate.value === p));
    if (!property || present.length !== 1) return unknown("unrecognised");
    const [predicate, quantifier, qualified] = present[0];
    const object = single(predicate);
    if (!object) return unknown("unrecognised");
    const used = [OWL("onProperty"), predicate];
    const expr: Extract<ClassExpr, { kind: "restriction" }> = { kind: "restriction", property, quantifier };
    if (quantifier === "some" || quantifier === "only") expr.filler = sub(object);
    else if (quantifier === "value") expr.value = termValue(graph, object, depth + 1, inner);
    else if (quantifier === "self") {
      if (object.value !== "true") return unknown("unrecognised");
    } else {
      const n = nonNegative(object);
      if (n === undefined) return unknown("malformed");
      expr.cardinality = n;
      if (qualified) {
        const onClass = single(OWL("onClass"));
        const onRange = single(OWL("onDataRange"));
        const filler = onClass ?? onRange;
        if (!filler || (onClass && onRange)) return unknown("unrecognised");
        expr.filler = sub(filler);
        used.push(onClass ? OWL("onClass") : OWL("onDataRange"));
      }
    }
    return finish(expr, used);
  }

  for (const [predicate, kind] of [[OWL("intersectionOf"), "intersection"] as const, [OWL("unionOf"), "union"] as const]) {
    const head = single(predicate);
    if (!head) continue;
    const members = graph.list(head);
    if (!members) return unknown("malformed");
    return finish({ kind, members: members.map(sub) }, [predicate]);
  }
  const complement = single(OWL("complementOf"));
  if (complement) return finish({ kind: "complement", operand: sub(complement) }, [OWL("complementOf")]);

  const oneOf = single(OWL("oneOf"));
  if (oneOf) {
    const members = graph.list(oneOf);
    if (!members) return unknown("malformed");
    return finish({ kind: "oneOf", members: members.map((m) => termValue(graph, m, depth + 1, inner)) }, [OWL("oneOf")]);
  }

  const datatype = single(OWL("onDatatype"));
  if (datatype?.termType === "NamedNode") {
    const head = single(OWL("withRestrictions"));
    const items = head ? graph.list(head) : [];
    if (!items) return unknown("malformed");
    const facets = items
      .flatMap((item) => (item.termType === "BlankNode" ? graph.quads(item) : []))
      .map((q) => ({ facet: q.predicate.value, value: termValue(graph, q.object, depth + 1, inner) }))
      .sort((a, b) => text(a.facet, b.facet) || text(termKey(a.value), termKey(b.value)));
    return finish({ kind: "datatypeRestriction", datatype: datatype.value, facets }, [OWL("onDatatype"), OWL("withRestrictions")]);
  }
  return unknown("unrecognised");
}

function annotationGroups(quads: Quad[]): Annotation[] {
  const groups = new Map<string, Annotation>();
  for (const q of quads) {
    if (q.object.termType !== "Literal") continue;
    const language = q.object.language;
    const key = `${q.predicate.value}\u0000${language}`;
    const group = groups.get(key) ?? { property: q.predicate.value, language, values: [] };
    const value: { value: string; datatype?: string } = { value: q.object.value };
    if (!language && q.object.datatype.value !== XSD("string")) value.datatype = q.object.datatype.value;
    group.values.push(value);
    groups.set(key, group);
  }
  const order = (p: string) => {
    const i = ANNOTATION_ORDER.indexOf(p);
    return i < 0 ? ANNOTATION_ORDER.length : i;
  };
  return [...groups.values()]
    .map((g) => ({ ...g, values: unique(g.values).sort((a, b) => text(a.value, b.value) || text(a.datatype ?? "", b.datatype ?? "")) }))
    .sort((a, b) => order(a.property) - order(b.property) || text(a.property, b.property) || text(a.language, b.language));
}

const named = (quads: Quad[]) => quads.filter((q) => q.object.termType === "NamedNode").map((q) => q.object.value);

function propertyShapeRow(graph: Graph, node: Term): PropertyShapeRow {
  const taken = new Taken(graph.quads(node));
  taken.take(TYPE, (q) => q.object.value === SH("PropertyShape"));
  const pathQuads = taken.quads.filter((q) => q.predicate.value === SH("path"));
  const path = pathQuads.length === 1 ? termValue(graph, pathQuads[0].object, 0, new Set()) : undefined;
  if (path) taken.take(SH("path"));
  const constraints: ConstraintRow[] = [];
  for (const name of CONSTRAINTS) {
    const quads = taken.quads.filter((q) => q.predicate.value === SH(name));
    if (!quads.length) continue;
    if (name === "in") {
      const lists = quads.map((q) => graph.list(q.object));
      if (quads.length !== 1 || !lists[0]) continue;
      taken.take(SH(name));
      constraints.push({ constraint: name, values: lists[0].map((m) => termValue(graph, m, 1, new Set())) });
      continue;
    }
    const values = taken.take(SH(name)).map((q) => termValue(graph, q.object, 0, new Set()));
    constraints.push({ constraint: name, values: byTerm(values) });
  }
  return { path, constraints, other: rowsOf(graph, taken.rest(), 0, new Set()) };
}

const sortShapeRows = (rows: PropertyShapeRow[]) => byJson(rows);

function targetsOf(graph: Graph, shape: Term): string[] {
  const targets = named(graph.quads(shape, SH("targetClass")));
  if (shape.termType === "NamedNode" && graph.types(shape).some((t) => t === OWL("Class") || t === RDFS("Class"))) targets.push(shape.value);
  return strings(targets);
}

/** The superclasses of a class that are named, transitively. */
function ancestors(graph: Graph, iri: string): string[] {
  const out: string[] = [];
  const seen = new Set([iri]);
  const queue = [iri];
  while (queue.length) {
    for (const parent of named(graph.quads(queue.shift()!, RDFS("subClassOf")))) {
      if (seen.has(parent)) continue;
      seen.add(parent);
      out.push(parent);
      queue.push(parent);
    }
  }
  return out;
}

export function classAxioms(graph: Graph, iri: string): ClassAxioms {
  const taken = new Taken(graph.quads(iri));
  const isShape = graph.types(iri).includes(SH("NodeShape"));
  taken.take(TYPE, (q) => q.object.value === OWL("Class") || q.object.value === RDFS("Class") || q.object.value === SH("NodeShape"));

  const expressions = (predicate: string) => sortExprs(taken.take(predicate).map((q) => readExpression(graph, q.object)));
  const superClasses = expressions(RDFS("subClassOf"));
  const equivalentClasses = expressions(OWL("equivalentClass"));

  const disjoint: ClassExpr[] = taken.take(OWL("disjointWith")).map((q) => readExpression(graph, q.object));
  for (const q of graph.quads(null, OWL("disjointWith"), iri)) disjoint.push(readExpression(graph, q.subject));
  for (const predicate of [OWL("members"), OWL("disjointClasses")]) {
    for (const q of graph.quads(null, predicate)) {
      const members = graph.list(q.object);
      if (!members || !members.some((m) => m.termType === "NamedNode" && m.value === iri)) continue;
      if (predicate === OWL("members") && !graph.types(q.subject).includes(OWL("AllDisjointClasses"))) continue;
      for (const m of members) if (!(m.termType === "NamedNode" && m.value === iri)) disjoint.push(readExpression(graph, m));
    }
  }

  const keys: PropertyRef[][] = [];
  for (const q of taken.take(OWL("hasKey"), (x) => {
    const members = graph.list(x.object);
    return !!members && members.every((m) => propertyRef(graph, m));
  })) {
    keys.push(graph.list(q.object)!.map((m) => propertyRef(graph, m)!));
  }

  const lineage = ancestors(graph, iri);
  const properties: DomainProperty[] = [];
  for (const q of graph.quads(null, RDFS("domain"))) {
    if (q.subject.termType !== "NamedNode" || q.object.termType !== "NamedNode") continue;
    if (q.object.value === iri) properties.push({ property: q.subject.value });
    else if (lineage.includes(q.object.value)) properties.push({ property: q.subject.value, from: q.object.value });
  }

  const shapeNodes = new Map<string, Term>();
  for (const q of graph.quads(null, SH("targetClass"), iri)) shapeNodes.set(q.subject.id, q.subject);
  if (isShape) {
    shapeNodes.set(iri, taken.quads[0].subject);
    taken.take(SH("targetClass"));
    taken.take(SH("property"));
  }
  const shapes: ShapeRow[] = [...shapeNodes.values()].map((node) => ({
    shape: node.termType === "NamedNode" ? node.value : undefined,
    targets: targetsOf(graph, node),
    properties: sortShapeRows(graph.quads(node, SH("property")).map((q) => propertyShapeRow(graph, q.object))),
  }));
  shapes.sort((a, b) => text(a.shape ?? "", b.shape ?? "") || text(json(a), json(b)));

  const individuals = strings(
    graph
      .subjects(TYPE, iri)
      .filter((s) => s.termType === "NamedNode")
      .map((s) => s.value),
  );

  const annotations = annotationGroups(taken.takeWhere((q) => q.object.termType === "Literal"));
  return {
    iri,
    annotations,
    superClasses,
    equivalentClasses,
    disjointClasses: sortExprs(disjoint),
    keys: byJson(keys),
    properties: byJson(properties),
    shapes,
    individuals,
    other: rowsOf(graph, taken.rest(), 0, new Set()),
  };
}

export function propertyAxioms(graph: Graph, iri: string): PropertyAxioms {
  const taken = new Taken(graph.quads(iri));
  const marker = new Set([...KINDS.map(([t]) => t), ...CHARACTERISTICS.map(([t]) => t), RDF("Property")]);
  const types = graph.types(iri);
  taken.take(TYPE, (q) => marker.has(q.object.value));

  const expressions = (predicate: string) => sortExprs(taken.take(predicate).map((q) => readExpression(graph, q.object)));
  const domains = expressions(RDFS("domain"));
  const ranges = expressions(RDFS("range"));
  const superProperties = strings(named(taken.take(RDFS("subPropertyOf"), (q) => q.object.termType === "NamedNode")));

  const inverse = named(taken.take(OWL("inverseOf"), (q) => q.object.termType === "NamedNode"));
  for (const q of graph.quads(null, OWL("inverseOf"), iri)) if (q.subject.termType === "NamedNode") inverse.push(q.subject.value);

  const chains: PropertyRef[][] = [];
  for (const q of taken.take(OWL("propertyChainAxiom"), (x) => {
    const members = graph.list(x.object);
    return !!members && members.length > 0 && members.every((m) => propertyRef(graph, m));
  })) {
    chains.push(graph.list(q.object)!.map((m) => propertyRef(graph, m)!));
  }

  const shapes: PropertyShapeUse[] = [];
  for (const q of graph.quads(null, SH("path"), iri)) {
    const row = propertyShapeRow(graph, q.subject);
    const parents = graph.quads(null, SH("property"), q.subject).map((p) => p.subject);
    if (!parents.length) shapes.push({ targets: [], shape: row });
    for (const parent of parents) {
      shapes.push({ nodeShape: parent.termType === "NamedNode" ? parent.value : undefined, targets: targetsOf(graph, parent), shape: row });
    }
  }

  return {
    iri,
    kinds: KINDS.filter(([t]) => types.includes(t)).map(([, k]) => k),
    characteristics: CHARACTERISTICS.filter(([t]) => types.includes(t)).map(([, c]) => c),
    domains,
    ranges,
    superProperties,
    inverseOf: strings(inverse),
    chains: byJson(chains),
    shapes: byJson(shapes),
    annotations: annotationGroups(taken.takeWhere((q) => q.object.termType === "Literal")),
    other: rowsOf(graph, taken.rest(), 0, new Set()),
  };
}

export function individualAxioms(graph: Graph, iri: string): IndividualAxioms {
  const taken = new Taken(graph.quads(iri));
  const known = new Set([...ANNOTATION_ORDER, ...graph.ofType(OWL("AnnotationProperty")).map((p) => p.value)]);
  const types = strings(named(taken.take(TYPE, (q) => q.object.termType === "NamedNode")));
  const annotations = annotationGroups(taken.takeWhere((q) => q.object.termType === "Literal" && known.has(q.predicate.value)));
  const byProperty = new Map<string, TermValue[]>();
  for (const q of taken.rest()) {
    const values = byProperty.get(q.predicate.value) ?? [];
    values.push(termValue(graph, q.object, 0, new Set()));
    byProperty.set(q.predicate.value, values);
  }
  const assertions = [...byProperty].map(([property, values]) => ({ property, values: byTerm(values) })).sort((a, b) => text(a.property, b.property));
  return { iri, types, assertions, annotations };
}
