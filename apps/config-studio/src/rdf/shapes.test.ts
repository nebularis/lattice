// SPDX-License-Identifier: MPL-2.0
// The one reader of node shapes (SVA-O6), shared by the forms and the ontology drawing: named and blank shapes, the classes a
// shape targets, a class that is itself a shape, a property shape's classes and sh:node links, a complex path left out, several
// targets, and a result that does not depend on the order of the triples.

import { describe, expect, it } from "vitest";
import { Graph } from "@lattice/authoring-domain";
import { readNodeShapes, readShapes } from "./shapes";

const EX = "https://example.org/o#";
const PREFIXES = `
@prefix ex: <${EX}> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
`;
const ex = (name: string) => EX + name;
const read = (body: string) => readNodeShapes(Graph.parse(PREFIXES + body));

describe("readNodeShapes", () => {
  it("reads a named shape with sh:targetClass and a property shape with sh:class", () => {
    const [shape, ...rest] = read(`ex:S a sh:NodeShape ; sh:targetClass ex:A ; sh:property [ sh:path ex:p ; sh:class ex:B ] .`);
    expect(rest).toEqual([]);
    expect(shape.name).toBe(ex("S"));
    expect(shape.targets).toEqual([ex("A")]);
    expect(shape.properties).toEqual([{ path: ex("p"), classes: [ex("B")], nodes: [], nodeTargets: [] }]);
  });

  it("reads a class that is itself a node shape, as the shape's own target", () => {
    const [shape] = read(`ex:A a owl:Class ; sh:property [ sh:path ex:p ; sh:class ex:B ] .`);
    expect(shape.name).toBe(ex("A"));
    expect(shape.targets).toEqual([ex("A")]);
  });

  it("gives a blank node shape no name", () => {
    const [shape] = read(`[ sh:targetClass ex:A ; sh:property [ sh:path ex:p ; sh:class ex:B ] ] .`);
    expect(shape.shape.termType).toBe("BlankNode");
    expect(shape.name).toBeUndefined();
    expect(shape.targets).toEqual([ex("A")]);
  });

  it("leaves out a shape that targets no class", () => {
    expect(read(`ex:S a sh:NodeShape ; sh:property [ sh:path ex:p ; sh:class ex:B ] .`)).toEqual([]);
  });

  it("resolves sh:node to the classes the referenced shape targets", () => {
    const [shape] = read(`ex:S sh:targetClass ex:A ; sh:property [ sh:path ex:p ; sh:node ex:T ] .
      ex:T sh:targetClass ex:C, ex:B .`);
    expect(shape.properties).toHaveLength(1);
    expect(shape.properties[0].nodes.map((n) => n.value)).toEqual([ex("T")]);
    expect(shape.properties[0].nodeTargets).toEqual([ex("B"), ex("C")]);
  });

  it("resolves sh:node to a class that is itself the referenced shape and to a blank shape", () => {
    const [shape] = read(`ex:S sh:targetClass ex:A ; sh:property [ sh:path ex:p ; sh:node ex:K ] , [ sh:path ex:q ; sh:node [ sh:targetClass ex:D ] ] .
      ex:K a owl:Class .`);
    expect(shape.properties.map((p) => [p.path, p.nodeTargets])).toEqual([[ex("p"), [ex("K")]], [ex("q"), [ex("D")]]]);
  });

  it("leaves out a property shape whose path is not a plain IRI", () => {
    const [shape] = read(`ex:S sh:targetClass ex:A ; sh:property [ sh:path [ sh:inversePath ex:p ] ; sh:class ex:B ] , [ sh:path ex:q ; sh:class ex:B ] .`);
    expect(shape.properties.map((p) => p.path)).toEqual([ex("q")]);
  });

  it("gives each target of a shape with several, with no repeats, even where the shape is also a class that names itself", () => {
    const [shape] = read(`ex:A a owl:Class ; sh:targetClass ex:B, ex:A, ex:C ; sh:property [ sh:path ex:p ; sh:class ex:X, ex:Y ] .`);
    expect(shape.targets).toEqual([ex("A"), ex("B"), ex("C")]);
    expect(shape.properties[0].classes).toEqual([ex("X"), ex("Y")]);
  });

  it("lists named shapes before blank ones, each in order", () => {
    const shapes = read(`[ sh:targetClass ex:A ; sh:property [ sh:path ex:p ] ] .
      ex:Z sh:targetClass ex:A ; sh:property [ sh:path ex:p ] .
      ex:M sh:targetClass ex:A ; sh:property [ sh:path ex:p ] .`);
    expect(shapes.map((s) => s.name)).toEqual([ex("M"), ex("Z"), undefined]);
  });

  it("gives the same result for the triples in any order", () => {
    const lines = [
      `ex:S1 sh:targetClass ex:A , ex:B .`,
      `ex:S1 sh:property ex:P1 , ex:P2 .`,
      `ex:P1 sh:path ex:p ; sh:class ex:X , ex:Y ; sh:node ex:T .`,
      `ex:P2 sh:path ex:q ; sh:class ex:Z .`,
      `ex:T sh:targetClass ex:C .`,
      `ex:K a owl:Class ; sh:property ex:P3 .`,
      `ex:P3 sh:path ex:r ; sh:node ex:K .`,
      `ex:S2 sh:targetClass ex:A ; sh:property [ sh:path ex:s ; sh:class ex:X ] .`,
    ];
    const strip = (shapes: ReturnType<typeof readNodeShapes>) => shapes.map((s) => ({ name: s.name, targets: s.targets, properties: s.properties.map((p) => ({ ...p, nodes: p.nodes.map((n) => n.value) })) }));
    const expected = strip(read(lines.join("\n")));
    expect(expected.map((s) => s.name)).toEqual([ex("K"), ex("S1"), ex("S2")]);
    let seed = 7;
    for (let i = 0; i < 6; i++) {
      const shuffled = [...lines];
      for (let j = shuffled.length - 1; j > 0; j--) {
        seed = (seed * 1103515245 + 12345) % 2147483648;
        const k = seed % (j + 1);
        [shuffled[j], shuffled[k]] = [shuffled[k], shuffled[j]];
      }
      expect(strip(read(shuffled.join("\n")))).toEqual(expected);
    }
  });
});

describe("readShapes", () => {
  it("still merges the constraints of each class's properties, with the same targeting rule", () => {
    const g = Graph.parse(PREFIXES + `ex:S sh:targetClass ex:A ; sh:property [ sh:path ex:p ; sh:minCount 1 ] .
      ex:A a owl:Class ; sh:property [ sh:path ex:p ; sh:maxCount 2 ] .`);
    expect(readShapes(g).get(ex("A"))?.get(ex("p"))).toMatchObject({ minCount: 1, maxCount: 2 });
  });
});
