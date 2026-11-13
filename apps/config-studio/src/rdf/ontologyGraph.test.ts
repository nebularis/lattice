// SPDX-License-Identifier: MPL-2.0
// The graphs the ontology views draw (SVA-O2): edges from domains and ranges, unions, datatypes, shapes by class and by node,
// the toggle that only adds, the neighbourhood of a class, the hierarchy, a result that does not depend on the order of the
// triples, and the facility sample, where the toggle's edges are listed exactly.

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { Graph } from "@lattice/authoring-domain";
import { classGraph, counts, hierarchyGraph } from "./ontologyGraph";

const EX = "https://example.org/o#";
const PREFIXES = `
@prefix ex: <${EX}> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
`;
const graph = (body: string) => Graph.parse(PREFIXES + body);
const ex = (name: string) => EX + name;
const classes = (...names: string[]) => names.map((n) => `ex:${n} a owl:Class .`).join("\n");
const id = (s: string, t: string, p: string) => `${ex(s)}|${ex(t)}|${ex(p)}`;
const ids = (g: Graph, shapes = false) => classGraph(g, { shapes }).edges.map((e) => e.id);

describe("domain and range", () => {
  it("draws an edge from the domain to the range of an object property", () => {
    const g = graph(`${classes("A", "B")} ex:p a owl:ObjectProperty ; rdfs:domain ex:A ; rdfs:range ex:B .`);
    expect(classGraph(g).edges).toEqual([{ id: id("A", "B", "p"), source: ex("A"), target: ex("B"), property: ex("p"), origin: "domain-range", byShape: false }]);
    expect(classGraph(g).nodes.map((n) => [n.iri, n.label])).toEqual([[ex("A"), "A"], [ex("B"), "B"]]);
  });

  it("draws an edge for each named member of a union domain and range", () => {
    const g = graph(`${classes("A", "B", "C", "D")}
      ex:p a owl:ObjectProperty ; rdfs:domain [ owl:unionOf ( ex:A ex:B ) ] ; rdfs:range [ owl:unionOf ( ex:C ex:D ) ] .`);
    expect(ids(g)).toEqual([id("A", "C", "p"), id("A", "D", "p"), id("B", "C", "p"), id("B", "D", "p")]);
  });

  it("draws no edge for a datatype range or a range the baseline does not declare", () => {
    const g = graph(`${classes("A")}
      ex:n a owl:DatatypeProperty ; rdfs:domain ex:A ; rdfs:range xsd:string .
      ex:u a owl:ObjectProperty ; rdfs:domain ex:A ; rdfs:range ex:Undeclared .
      ex:v a owl:ObjectProperty ; rdfs:range ex:A .`);
    expect(ids(g)).toEqual([]);
  });

  it("draws an edge for each pair of several domains and several ranges", () => {
    const g = graph(`${classes("A", "B", "C", "D")}
      ex:p a owl:ObjectProperty ; rdfs:domain ex:A , ex:B ; rdfs:range ex:C , ex:D .`);
    expect(ids(g)).toHaveLength(4);
  });

  it("keeps a self edge and tells properties between the same classes apart", () => {
    const g = graph(`${classes("A", "B")}
      ex:p a owl:ObjectProperty ; rdfs:domain ex:A ; rdfs:range ex:B .
      ex:q a owl:ObjectProperty ; rdfs:domain ex:A ; rdfs:range ex:B .
      ex:r a owl:ObjectProperty ; rdfs:domain ex:A ; rdfs:range ex:A .`);
    expect(ids(g)).toEqual([id("A", "A", "r"), id("A", "B", "p"), id("A", "B", "q")]);
  });
});

describe("shapes", () => {
  const base = `${classes("A", "B", "C")}`;

  it("draws an edge for an sh:class constraint, in the second origin, naming its shape", () => {
    const g = graph(`${base} ex:AShape a sh:NodeShape ; sh:targetClass ex:A ; sh:property [ sh:path ex:p ; sh:class ex:B ] .`);
    expect(ids(g)).toEqual([]);
    expect(classGraph(g, { shapes: true }).edges).toEqual([
      { id: id("A", "B", "p"), source: ex("A"), target: ex("B"), property: ex("p"), origin: "shape", shape: ex("AShape"), shapes: [ex("AShape")], byShape: true },
    ]);
  });

  it("draws an edge for an sh:node constraint to the target class of the node", () => {
    const g = graph(`${base}
      ex:AShape a sh:NodeShape ; sh:targetClass ex:A ; sh:property [ sh:path ex:p ; sh:node ex:BShape ] .
      ex:BShape a sh:NodeShape ; sh:targetClass ex:B .`);
    expect(classGraph(g, { shapes: true }).edges.map((e) => [e.id, e.origin, e.shape])).toEqual([[id("A", "B", "p"), "shape", ex("AShape")]]);
  });

  it("reads a class that is itself a node shape, as the source and as the node", () => {
    const g = graph(`${base}
      ex:A a owl:Class , sh:NodeShape ; sh:property [ sh:path ex:p ; sh:node ex:B ] .
      ex:B a owl:Class , sh:NodeShape .`);
    expect(classGraph(g, { shapes: true }).edges.map((e) => [e.id, e.shape])).toEqual([[id("A", "B", "p"), ex("A")]]);
  });

  it("draws no edge for a complex path, a datatype constraint or a shape with no target", () => {
    const g = graph(`${base}
      ex:AShape a sh:NodeShape ; sh:targetClass ex:A ; sh:property [ sh:path [ sh:inversePath ex:p ] ; sh:class ex:B ] ,
        [ sh:path ex:q ; sh:datatype xsd:string ] , [ sh:path ex:r ] .
      ex:Loose a sh:NodeShape ; sh:property [ sh:path ex:s ; sh:class ex:B ] .
      ex:Blank a sh:NodeShape ; sh:targetClass ex:C ; sh:property [ sh:path ex:t ; sh:class ex:Undeclared ] .`);
    expect(ids(g, true)).toEqual([]);
  });

  it("draws an edge from each target of a shape, and names no shape that is a blank node", () => {
    const g = graph(`${base}
      ex:S a sh:NodeShape ; sh:targetClass ex:A , ex:C ; sh:property [ sh:path ex:p ; sh:class ex:B ] .
      [ a sh:NodeShape ; sh:targetClass ex:B ; sh:property [ sh:path ex:q ; sh:class ex:A ] ] .`);
    const edges = classGraph(g, { shapes: true }).edges;
    expect(edges.map((e) => [e.id, e.shape])).toEqual([[id("A", "B", "p"), ex("S")], [id("B", "A", "q"), undefined], [id("C", "B", "p"), ex("S")]]);
    expect(edges.every((e) => e.byShape)).toBe(true);
  });

  it("only adds edges when shapes are turned on, and merges an edge both origins state", () => {
    const g = graph(`${base}
      ex:p a owl:ObjectProperty ; rdfs:domain ex:A ; rdfs:range ex:B .
      ex:q a owl:ObjectProperty ; rdfs:domain ex:A ; rdfs:range ex:C .
      ex:S1 a sh:NodeShape ; sh:targetClass ex:A ; sh:property [ sh:path ex:p ; sh:class ex:B ] , [ sh:path ex:r ; sh:class ex:C ] .
      ex:S2 a sh:NodeShape ; sh:targetClass ex:A ; sh:property [ sh:path ex:p ; sh:class ex:B ] .`);
    const without = classGraph(g).edges;
    const withShapes = classGraph(g, { shapes: true }).edges;
    expect(new Set(ids(g)).size).toBe(2);
    // Every edge there was is still there, with the same id, source, target, property and origin.
    for (const e of without) {
      const same = withShapes.find((w) => w.id === e.id)!;
      expect(same).toMatchObject({ id: e.id, source: e.source, target: e.target, property: e.property, origin: "domain-range" });
    }
    expect(withShapes.map((e) => [e.id, e.origin])).toEqual([[id("A", "B", "p"), "domain-range"], [id("A", "C", "q"), "domain-range"], [id("A", "C", "r"), "shape"]]);
    const merged = withShapes.find((e) => e.id === id("A", "B", "p"))!;
    expect(merged.shapes).toEqual([ex("S1"), ex("S2")]);
    expect(merged.shape).toBe(ex("S1"));
    expect(merged.byShape).toBe(true);
    expect(without.every((e) => !e.byShape && e.shape === undefined)).toBe(true);
    expect(counts(classGraph(g, { shapes: true }))).toEqual({ classes: 3, links: 3, byShape: 2 });
    expect(counts(classGraph(g))).toEqual({ classes: 3, links: 2, byShape: 0 });
  });
});

describe("the neighbourhood of a class", () => {
  // A chain A to B to C to D by properties, E a subclass of C, F unrelated.
  const chain = `${classes("A", "B", "C", "D", "E", "F")}
    ex:E rdfs:subClassOf ex:C .
    ex:ab a owl:ObjectProperty ; rdfs:domain ex:A ; rdfs:range ex:B .
    ex:bc a owl:ObjectProperty ; rdfs:domain ex:B ; rdfs:range ex:C .
    ex:cd a owl:ObjectProperty ; rdfs:domain ex:C ; rdfs:range ex:D .`;
  const names = (g: { nodes: { iri: string }[] }) => g.nodes.map((n) => n.iri.slice(EX.length));

  it("takes the classes within the hops, in either direction, over properties and subclass links", () => {
    const g = graph(chain);
    expect(names(classGraph(g, { focus: ex("B"), hops: 1 }))).toEqual(["A", "B", "C"]);
    expect(names(classGraph(g, { focus: ex("B"), hops: 2 }))).toEqual(["A", "B", "C", "D", "E"]);
    expect(names(classGraph(g, { focus: ex("D"), hops: 1 }))).toEqual(["C", "D"]);
    expect(names(classGraph(g, { focus: ex("D"), hops: 2 }))).toEqual(["B", "C", "D", "E"]);
    expect(names(classGraph(g, { focus: ex("A") }))).toEqual(["A", "B", "C"]);
  });

  it("keeps the edges among the classes it keeps, and the whole graph without a focus", () => {
    const g = graph(chain);
    expect(classGraph(g, { focus: ex("B"), hops: 1 }).edges.map((e) => e.id)).toEqual([id("A", "B", "ab"), id("B", "C", "bc")]);
    expect(names(classGraph(g))).toEqual(["A", "B", "C", "D", "E", "F"]);
    expect(names(classGraph(g, { focus: ex("A"), hops: Infinity }))).toEqual(["A", "B", "C", "D", "E"]);
  });

  it("follows shape edges only where shapes are on", () => {
    const g = graph(`${chain} ex:FShape a sh:NodeShape ; sh:targetClass ex:F ; sh:property [ sh:path ex:fa ; sh:class ex:A ] .`);
    expect(names(classGraph(g, { focus: ex("A"), hops: 1 }))).toEqual(["A", "B"]);
    expect(names(classGraph(g, { focus: ex("A"), hops: 1, shapes: true }))).toEqual(["A", "B", "F"]);
  });

  it("is empty for a focus that is not a declared class", () => {
    const g = graph(chain);
    expect(classGraph(g, { focus: ex("Nothing") }).nodes).toEqual([]);
    expect(hierarchyGraph(g, { focus: ex("ab") }).nodes).toEqual([]);
  });
});

describe("the class hierarchy", () => {
  const body = `${classes("A", "B", "C", "D")}
    ex:B rdfs:subClassOf ex:A . ex:C rdfs:subClassOf ex:A , ex:B , ex:Undeclared . ex:D rdfs:subClassOf [ a owl:Restriction ; owl:onProperty ex:p ; owl:someValuesFrom ex:A ] .`;

  it("draws an edge from each class to each declared named superclass", () => {
    const h = hierarchyGraph(graph(body));
    expect(h.nodes.map((n) => n.label)).toEqual(["A", "B", "C", "D"]);
    expect(h.edges.map((e) => [e.source, e.target])).toEqual([[ex("B"), ex("A")], [ex("C"), ex("A")], [ex("C"), ex("B")]]);
    expect(counts(h)).toEqual({ classes: 4, links: 3, byShape: 0 });
  });

  it("takes the neighbourhood over subclass links in either direction", () => {
    const g = graph(`${body} ex:E a owl:Class ; rdfs:subClassOf ex:D .`);
    expect(hierarchyGraph(g, { focus: ex("B"), hops: 1 }).nodes.map((n) => n.label)).toEqual(["A", "B", "C"]);
    expect(hierarchyGraph(g, { focus: ex("D") }).nodes.map((n) => n.label)).toEqual(["D", "E"]);
  });
});

describe("determinism", () => {
  it("gives the same result for any order of triples", () => {
    const g = graph(`${classes("A", "B", "C", "D")}
      ex:B rdfs:subClassOf ex:A . ex:D rdfs:subClassOf ex:C .
      ex:p a owl:ObjectProperty ; rdfs:domain ex:A , ex:B ; rdfs:range [ owl:unionOf ( ex:C ex:D ) ] .
      ex:S a sh:NodeShape ; sh:targetClass ex:C ; sh:property [ sh:path ex:q ; sh:class ex:A ] , [ sh:path ex:r ; sh:class ex:B ] .`);
    const nquads = g.quads();
    const want = JSON.stringify([classGraph(g, { shapes: true }), classGraph(g, { focus: ex("C"), hops: 1, shapes: true }), hierarchyGraph(g)]);
    for (let round = 0; round < 5; round++) {
      // Rebuild the graph from the same quads in another order, and the blank nodes keep their identity.
      const shuffled = nquads.map((q) => [hash(q.subject.id + q.predicate.value + q.object.id, round), q] as const).sort((a, b) => a[0] - b[0]).map(([, q]) => q);
      const again = Graph.of(shuffled, { ...g.prefixes });
      const got = JSON.stringify([classGraph(again, { shapes: true }), classGraph(again, { focus: ex("C"), hops: 1, shapes: true }), hierarchyGraph(again)]);
      expect(got).toBe(want);
    }
  });
});

function hash(text: string, seed: number): number {
  let h = seed + 1;
  for (const ch of text) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return h;
}

describe("the facility sample", () => {
  const samples = join(__dirname, "../../../../contracts/config-studio/samples");
  const read = (name: string) => Graph.parse(readFileSync(join(samples, name), "utf-8"));
  const LENDING = "https://example.org/lending#";
  const lend = (s: string, t: string, p: string) => `${LENDING}${s}|${LENDING}${t}|${LENDING}${p}`;

  it("the shapes of the facility file state four links, each already a domain and range, and each now names its shape", () => {
    // The sample's baseline is the lending baseline with the facility baseline over it.
    const g = read("lending-baseline.ttl").merge(read("facility-baseline.ttl"));
    const without = classGraph(g);
    const withShapes = classGraph(g, { shapes: true });
    expect(without.edges.map((e) => e.id)).toEqual([
      lend("Drawdown", "Facility", "drawnUnder"),
      lend("Facility", "Borrower", "borrower"),
      lend("Facility", "Branch", "arrangedBy"),
      lend("Facility", "Drawdown", "hasDrawdown"),
      lend("Facility", "Lender", "lender"),
      lend("LoanApplication", "Borrower", "applicant"),
      lend("LoanApplication", "Branch", "branch"),
      lend("LoanApplication", "Decision", "decision"),
      lend("LoanApplication", "Guarantor", "guarantor"),
    ]);
    // The toggle adds no edge here, and a shape names itself on each edge it states.
    expect(withShapes.edges.map((e) => e.id)).toEqual(without.edges.map((e) => e.id));
    expect(withShapes.edges.filter((e) => e.byShape).map((e) => [e.id, e.origin, e.shape])).toEqual([
      [lend("Facility", "Borrower", "borrower"), "domain-range", `${LENDING}FacilityShape`],
      [lend("Facility", "Branch", "arrangedBy"), "domain-range", `${LENDING}FacilityShape`],
      [lend("Facility", "Drawdown", "hasDrawdown"), "domain-range", `${LENDING}FacilityShape`],
      [lend("Facility", "Lender", "lender"), "domain-range", `${LENDING}FacilityShape`],
    ]);
    expect(withShapes.edges.filter((e) => e.origin === "shape")).toEqual([]);
    expect(counts(without)).toEqual({ classes: 9, links: 9, byShape: 0 });
    expect(counts(withShapes)).toEqual({ classes: 9, links: 9, byShape: 4 });
    expect(classGraph(g).nodes.map((n) => n.label)).toEqual(["Borrower", "Branch", "Decision", "Drawdown", "Facility", "Guarantor", "Lender", "Loan application", "Party"]);
    // The datatype shape of a drawdown, and the ranges that are concepts, draw nothing.
    expect(withShapes.edges.some((e) => e.property === `${LENDING}drawnAmount` || e.property === `${LENDING}borrowerSector`)).toBe(false);
  });

  it("the facility file alone draws only the links among the classes it declares", () => {
    const g = read("facility-baseline.ttl");
    expect(classGraph(g, { shapes: true }).edges.map((e) => [e.id, e.shape])).toEqual([
      [lend("Drawdown", "Facility", "drawnUnder"), undefined],
      [lend("Facility", "Drawdown", "hasDrawdown"), `${LENDING}FacilityShape`],
      [lend("Facility", "Lender", "lender"), `${LENDING}FacilityShape`],
    ]);
  });
});
