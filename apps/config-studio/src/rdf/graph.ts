// SPDX-License-Identifier: MPL-2.0
// An immutable RDF graph over an n3 Store. Every edit copies the store, so a React state holds a
// Graph by value and the undo history is a list of Graphs. Configurations are a few thousand
// triples at most, so a copy costs well under a millisecond.

import { DataFactory, Parser, Store, Writer } from "n3";
import type { BlankNode, Literal, NamedNode, Quad, Quad_Object, Quad_Subject, Term } from "n3";
import { PREFIXES, RDF, TYPE, compact, namespaceOf } from "./ns";

const { namedNode, literal, blankNode, quad } = DataFactory;

export type Subject = NamedNode | BlankNode;
export type { Term, Literal, NamedNode, BlankNode, Quad };
export { namedNode, literal, blankNode };

const FIRST = RDF("first");
const REST = RDF("rest");
const NIL = RDF("nil");

export function term(value: Term | string): Term {
  return typeof value === "string" ? namedNode(value) : value;
}

export class TurtleError extends Error {}

export class Graph {
  private constructor(
    readonly store: Store,
    readonly prefixes: Record<string, string>,
  ) {}

  static empty(prefixes: Record<string, string> = {}): Graph {
    return new Graph(new Store(), prefixes);
  }

  static parse(text: string, baseIRI?: string): Graph {
    const prefixes: Record<string, string> = {};
    try {
      const quads = new Parser({ format: "text/turtle", baseIRI }).parse(text, null, (prefix, iri) => {
        prefixes[prefix] = iri.value;
      });
      return new Graph(new Store(quads.map((q) => quad(q.subject, q.predicate, q.object))), prefixes);
    } catch (error) {
      throw new TurtleError(error instanceof Error ? error.message : String(error));
    }
  }

  static of(quads: Quad[], prefixes: Record<string, string> = {}): Graph {
    return new Graph(new Store(quads), prefixes);
  }

  get size(): number {
    return this.store.size;
  }

  quads(s?: Term | string | null, p?: string | null, o?: Term | string | null): Quad[] {
    return this.store.getQuads(s ? term(s) : null, p ? namedNode(p) : null, o ? term(o) : null, null);
  }

  objects(s: Term | string, p: string): Term[] {
    return this.store.getObjects(term(s), namedNode(p), null);
  }

  object(s: Term | string, p: string): Term | undefined {
    return this.objects(s, p)[0];
  }

  /** The lexical value of the first object, for a literal or an IRI. */
  value(s: Term | string, p: string): string | undefined {
    return this.object(s, p)?.value;
  }

  subjects(p: string | null, o?: Term | string): Term[] {
    return this.store.getSubjects(p ? namedNode(p) : null, o ? term(o) : null, null);
  }

  ofType(type: string): NamedNode[] {
    return this.subjects(TYPE, type)
      .filter((s): s is NamedNode => s.termType === "NamedNode")
      .sort((a, b) => a.value.localeCompare(b.value));
  }

  types(s: Term | string): string[] {
    return this.objects(s, TYPE).map((t) => t.value);
  }

  has(s: Term | string): boolean {
    return this.store.countQuads(term(s), null, null, null) > 0;
  }

  /** The members of the RDF list headed by `head`, or undefined when it is not a well-formed list. */
  list(head: Term): Term[] | undefined {
    const items: Term[] = [];
    const seen = new Set<string>();
    let node = head;
    while (node.value !== NIL) {
      if (node.termType !== "BlankNode" || seen.has(node.id)) return undefined;
      seen.add(node.id);
      const first = this.object(node, FIRST);
      const rest = this.object(node, REST);
      if (!first || !rest) return undefined;
      items.push(first);
      node = rest;
    }
    return items;
  }

  edit(change: (editor: GraphEditor) => void): Graph {
    const store = new Store(this.store.getQuads(null, null, null, null));
    change(new GraphEditor(store));
    return new Graph(store, this.prefixes);
  }

  merge(other: Graph): Graph {
    return this.edit((e) => e.store.addQuads(other.quads())).withPrefixes(other.prefixes);
  }

  withPrefixes(prefixes: Record<string, string>): Graph {
    return new Graph(this.store, { ...this.prefixes, ...prefixes });
  }

  /** Turtle, written in a fixed order: subjects by IRI, rdf:type first, then predicates by IRI.
   * A blank node used once as an object is written inline, a list as ( ... ). */
  toTurtle(only?: Term[]): string {
    const prefixes = this.usedPrefixes();
    const writer = new Writer({ prefixes });
    const references = new Map<string, number>();
    for (const q of this.quads()) {
      if (q.object.termType === "BlankNode") references.set(q.object.id, (references.get(q.object.id) ?? 0) + 1);
    }
    const inline = (node: Term) => node.termType === "BlankNode" && references.get(node.id) === 1;

    const render = (o: Term, depth: number): Quad_Object => {
      if (!inline(o) || depth > 32) return o as Quad_Object;
      const items = this.list(o);
      if (items) return writer.list(items.map((i) => render(i, depth + 1)));
      return writer.blank(this.predicates(o).map((q) => ({ predicate: q.predicate, object: render(q.object, depth + 1) })));
    };

    const subjects = only ?? this.topSubjects(inline);
    for (const s of subjects) {
      for (const q of this.predicates(s)) writer.addQuad(q.subject as Quad_Subject, q.predicate, render(q.object, 0));
    }
    let out = "";
    writer.end((error, result) => {
      if (error) throw error;
      out = result ?? "";
    });
    return out;
  }

  /** The known prefixes the graph uses, and one made up for any other namespace it uses twice or
   * more, named for the namespace's last word, so a configuration reads as ex:Thing, not <...>. */
  private usedPrefixes(): Record<string, string> {
    const all = { ...PREFIXES, ...this.prefixes };
    const used: Record<string, string> = {};
    const unknown = new Map<string, number>();
    const implicit = new Set([FIRST, REST, NIL, TYPE, "http://www.w3.org/2001/XMLSchema#string"]);
    for (const q of this.quads()) {
      for (const t of [q.subject, q.predicate, q.object, (q.object as Literal).datatype]) {
        if (t?.termType !== "NamedNode" || implicit.has(t.value)) continue;
        const known = Object.entries(all).find(([prefix, base]) => prefix && t.value.startsWith(base));
        if (known) used[known[0]] = known[1];
        else if (/[#/][A-Za-z_][\w-]*$/.test(t.value)) unknown.set(namespaceOf(t.value), (unknown.get(namespaceOf(t.value)) ?? 0) + 1);
      }
    }
    for (const [base, count] of unknown) {
      if (count < 2 || Object.values(used).includes(base)) continue;
      const word = (base.match(/([A-Za-z][A-Za-z0-9]*)[^A-Za-z0-9]*$/)?.[1] ?? "ns").toLowerCase();
      let prefix = word;
      for (let i = 2; prefix in used || prefix in all; i++) prefix = `${word}${i}`;
      used[prefix] = base;
    }
    return Object.fromEntries(Object.entries(used).sort(([a], [b]) => a.localeCompare(b)));
  }

  private topSubjects(inline: (t: Term) => boolean): Term[] {
    const seen = new Map<string, Term>();
    for (const q of this.quads()) if (!inline(q.subject)) seen.set(q.subject.id, q.subject);
    return [...seen.values()].sort((a, b) => sortKey(this, a).localeCompare(sortKey(this, b)));
  }

  private predicates(s: Term): Quad[] {
    return this.quads(s).sort((a, b) => {
      if (a.predicate.value !== b.predicate.value) {
        if (a.predicate.value === TYPE) return -1;
        if (b.predicate.value === TYPE) return 1;
        return a.predicate.value.localeCompare(b.predicate.value);
      }
      return a.object.id.localeCompare(b.object.id);
    });
  }
}

function sortKey(graph: Graph, s: Term): string {
  const type = graph.types(s).map((t) => compact(t)).sort()[0] ?? "~";
  return `${s.termType === "BlankNode" ? "~" : ""}${type} ${s.value}`;
}

/** The mutations an edit may make. Each keeps the graph free of orphaned blank nodes. */
export class GraphEditor {
  constructor(readonly store: Store) {}

  add(s: Term | string, p: string, o: Term | string): void {
    this.store.addQuad(quad(term(s) as Quad_Subject, namedNode(p), term(o) as Quad_Object));
  }

  /** Replace every value of `p` on `s` with `objects`. */
  setAll(s: Term | string, p: string, objects: Term[]): void {
    const subject = term(s);
    for (const old of this.store.getObjects(subject, namedNode(p), null)) {
      this.store.removeQuad(quad(subject as Quad_Subject, namedNode(p), old as Quad_Object));
      this.dropIfOrphan(old);
    }
    for (const o of objects) this.add(subject, p, o);
  }

  set(s: Term | string, p: string, o: Term | undefined): void {
    this.setAll(s, p, o ? [o] : []);
  }

  setList(s: Term | string, p: string, items: Term[]): void {
    if (items.length === 0) return this.setAll(s, p, []);
    let rest: Term = namedNode(NIL);
    for (const item of [...items].reverse()) {
      const cell = blankNode();
      this.add(cell, FIRST, item);
      this.add(cell, REST, rest);
      rest = cell;
    }
    this.setAll(s, p, [rest]);
  }

  /** Remove a node, the blank nodes only it owns, and every reference to it. */
  remove(s: Term | string): void {
    const subject = term(s);
    for (const q of this.store.getQuads(null, null, subject, null)) this.store.removeQuad(q);
    for (const q of this.store.getQuads(subject, null, null, null)) {
      this.store.removeQuad(q);
      this.dropIfOrphan(q.object);
    }
  }

  rename(from: string, to: string): void {
    const a = namedNode(from);
    const b = namedNode(to);
    for (const q of this.store.getQuads(a, null, null, null)) {
      this.store.removeQuad(q);
      this.store.addQuad(quad(b, q.predicate, q.object));
    }
    for (const q of this.store.getQuads(null, null, a, null)) {
      this.store.removeQuad(q);
      this.store.addQuad(quad(q.subject, q.predicate, b));
    }
  }

  private dropIfOrphan(node: Term): void {
    if (node.termType !== "BlankNode") return;
    if (this.store.countQuads(null, null, node, null) > 0) return;
    for (const q of this.store.getQuads(node, null, null, null)) {
      this.store.removeQuad(q);
      this.dropIfOrphan(q.object);
    }
  }
}

export function iri(value: string): NamedNode {
  return namedNode(value);
}

export function typed(value: string, datatype: string): Literal {
  return literal(value, namedNode(datatype));
}
