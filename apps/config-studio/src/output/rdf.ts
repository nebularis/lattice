// SPDX-License-Identifier: MPL-2.0
// RDF output for the explorer (SVA-M4), parsed once with n3 and turned into the three renderings, a Turtle or N-Triples text, a table
// of rows and the nodes and edges of a graph. Each of them is a function of the set of quads, never of the order they arrived in,
// so the same output reads the same however the service wrote it. Nothing here throws, a text that does not parse is an error value.

import { DataFactory, Parser, Writer } from "n3";
import type { Quad, Term } from "n3";
import { Graph, PREFIXES } from "@lattice/authoring-domain";
import { baseType } from "./media";

const { quad } = DataFactory;

const RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type";
const XSD_STRING = "http://www.w3.org/2001/XMLSchema#string";
const LANG_STRING = "http://www.w3.org/1999/02/22-rdf-syntax-ns#langString";

const FORMATS: Record<string, string> = {
  "text/turtle": "text/turtle",
  "application/n-triples": "N-Triples",
  "application/n-quads": "N-Quads",
  "application/trig": "application/trig",
};

export type Parsed = { ok: true; quads: Quad[]; prefixes: Record<string, string> } | { ok: false; message: string };

/** Parses RDF text in its media type. A media type that is not RDF, or a text that does not parse, gives the reason and never throws. */
export function parseRdf(text: string, mediaType: string): Parsed {
  const format = FORMATS[baseType(mediaType)];
  if (!format) return { ok: false, message: `${mediaType} is not an RDF media type.` };
  const prefixes: Record<string, string> = {};
  try {
    const quads = new Parser({ format, blankNodePrefix: "" }).parse(text, null, (prefix, iri) => {
      prefixes[prefix] = iri.value;
    });
    return { ok: true, quads, prefixes };
  } catch (error) {
    return { ok: false, message: error instanceof Error ? error.message : String(error) };
  }
}

const LOCAL = /^[A-Za-z_][\w-]*(?:\.[\w-]+)*$/;

/** The compact form of an IRI under the prefixes, the longest namespace first, else the IRI in angle brackets. */
export function shorten(iri: string, prefixes: Record<string, string>): string {
  let best: [string, string] | undefined;
  for (const [prefix, base] of Object.entries(prefixes)) {
    if (!iri.startsWith(base) || iri.length === base.length || !LOCAL.test(iri.slice(base.length))) continue;
    if (!best || base.length > best[1].length || (base.length === best[1].length && prefix < best[0])) best = [prefix, base];
  }
  return best ? `${best[0]}:${iri.slice(best[1].length)}` : `<${iri}>`;
}

/** What a term reads as in a table or a node, an IRI compacted, a blank node as `_:label`, a literal quoted with its language or datatype. */
export function termText(t: Term, prefixes: Record<string, string>): string {
  switch (t.termType) {
    case "NamedNode":
      return shorten(t.value, prefixes);
    case "BlankNode":
      return `_:${t.value}`;
    case "Literal": {
      const quoted = JSON.stringify(t.value);
      if (t.language) return `${quoted}@${t.language}`;
      return t.datatype && t.datatype.value !== XSD_STRING && t.datatype.value !== LANG_STRING ? `${quoted}^^${shorten(t.datatype.value, prefixes)}` : quoted;
    }
    case "DefaultGraph":
      return "";
    default:
      return t.value;
  }
}

/** The prefixes a part is read with, the studio's known ones, then the ones its own text declares, then those the caller adds. */
export function prefixesOf(declared: Record<string, string>, extra: Record<string, string> = {}): Record<string, string> {
  return { ...PREFIXES, ...declared, ...extra };
}

/** The prefixes the head of a Turtle text declares, as the graph's writer wrote them, so a table and a graph compact as the text does. */
export function declaredPrefixes(turtle: string): Record<string, string> {
  const found: Record<string, string> = {};
  for (const line of turtle.split("\n", 200)) {
    const match = /^@prefix ([^:\s]*): <([^>]*)> ?\.$/.exec(line);
    if (match) found[match[1]] = match[2];
    else if (line.trim() !== "") break;
  }
  return found;
}

const byKey = (a: string, b: string) => (a < b ? -1 : a > b ? 1 : 0);

/** The distinct triples of a dataset, the graph a quad is in dropped, as a store would hold them. */
function triples(quads: readonly Quad[]): Quad[] {
  const seen = new Map<string, Quad>();
  for (const q of quads) seen.set(`${q.subject.termType}${q.subject.value} ${q.predicate.value} ${q.object.termType}${q.object.value}${q.object.termType === "Literal" ? ` ${q.object.datatype?.value} ${q.object.language}` : ""}`, q);
  return [...seen.values()].map((q) => quad(q.subject, q.predicate, q.object));
}

/** Turtle written by the graph's own writer, so it reads as every other Turtle in the studio. */
export function toTurtleText(quads: readonly Quad[], prefixes: Record<string, string>): string {
  return Graph.of(triples(quads), prefixes).toTurtle();
}

/** N-Triples, one line for each distinct triple, in the order of their text. */
export function toNTriplesText(quads: readonly Quad[]): string {
  const key = (q: Quad) => `${termText(q.subject, {})}\u0000${termText(q.predicate, {})}\u0000${termText(q.object, {})}`;
  const sorted = triples(quads)
    .map((q) => ({ q, k: key(q) }))
    .sort((a, b) => byKey(a.k, b.k))
    .map(({ q }) => q);
  const writer = new Writer({ format: "N-Triples" });
  writer.addQuads(sorted);
  let out = "";
  writer.end((_, result) => (out = result ?? ""));
  return out;
}

export interface Row {
  subject: string;
  predicate: string;
  object: string;
  graph: string;
  /** The row in lower case, for a filter. */
  haystack: string;
}

/** One row for each quad, sorted by subject, then predicate, then object, then graph, whatever order the quads came in. */
export function tableRows(quads: readonly Quad[], prefixes: Record<string, string>): Row[] {
  const keyed = quads.map((q) => {
    const row = { subject: termText(q.subject, prefixes), predicate: termText(q.predicate, prefixes), object: termText(q.object, prefixes), graph: termText(q.graph, prefixes) };
    return { row, key: [row.subject, row.predicate, row.object, row.graph, q.object.termType] };
  });
  keyed.sort((a, b) => {
    for (let i = 0; i < a.key.length; i++) {
      const c = byKey(a.key[i], b.key[i]);
      if (c) return c;
    }
    return 0;
  });
  const rows: Row[] = [];
  let before = "";
  for (const { row, key } of keyed) {
    const same = key.join("\u0000");
    if (same === before) continue;
    before = same;
    rows.push({ ...row, haystack: `${row.subject}\u0000${row.predicate}\u0000${row.object}\u0000${row.graph}`.toLowerCase() });
  }
  return rows;
}

/** The rows whose text holds the filter in any column. A blank filter keeps every row. */
export function filterRows(rows: readonly Row[], filter: string): readonly Row[] {
  const needle = filter.trim().toLowerCase();
  return needle ? rows.filter((r) => r.haystack.includes(needle)) : rows;
}

export interface GraphNode {
  id: string;
  label: string;
  blank: boolean;
  types: string[];
  /** The literals the node's subject has, shown inside the node and never as nodes of their own, and links to itself. */
  rows: { predicate: string; value: string }[];
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
}

export interface GraphModel {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

const nodeId = (t: Term) => (t.termType === "BlankNode" ? `_:${t.value}` : t.value);

/**
 * The nodes and edges of a dataset, merged over its graphs. Each subject and each object that is an IRI or a blank node is a node,
 * a literal is a row inside its subject's node, an `rdf:type` to an IRI is a type the node shows, and every other triple between two
 * nodes is an edge labelled with its predicate. A triple from a node to itself is a row of the node, since an edge back to its own
 * box says nothing a row does not.
 */
export function graphModel(quads: readonly Quad[], prefixes: Record<string, string>): GraphModel {
  const nodes = new Map<string, GraphNode>();
  const edges = new Map<string, GraphEdge>();
  const node = (t: Term): GraphNode => {
    const id = nodeId(t);
    let n = nodes.get(id);
    if (!n) nodes.set(id, (n = { id, label: termText(t, prefixes), blank: t.termType === "BlankNode", types: [], rows: [] }));
    return n;
  };
  for (const q of triples(quads)) {
    const s = node(q.subject);
    const predicate = termText(q.predicate, prefixes);
    if (q.object.termType === "Literal") {
      s.rows.push({ predicate, value: termText(q.object, prefixes) });
    } else if (q.predicate.value === RDF_TYPE && q.object.termType === "NamedNode") {
      s.types.push(termText(q.object, prefixes));
    } else if (nodeId(q.object) === s.id) {
      s.rows.push({ predicate, value: "this node" });
    } else {
      const o = node(q.object);
      const id = `${s.id} ${q.predicate.value} ${o.id}`;
      edges.set(id, { id, source: s.id, target: o.id, label: predicate });
    }
  }
  const sortedNodes = [...nodes.values()].sort((a, b) => byKey(a.id, b.id));
  for (const n of sortedNodes) {
    n.types.sort(byKey);
    n.rows.sort((a, b) => byKey(a.predicate, b.predicate) || byKey(a.value, b.value));
  }
  return { nodes: sortedNodes, edges: [...edges.values()].sort((a, b) => byKey(a.id, b.id)) };
}
