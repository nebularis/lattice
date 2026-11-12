// SPDX-License-Identifier: MPL-2.0
// The reader of an element's axioms (SVA-O3): each OWL construct, nested expressions, malformed
// lists and cycles, disjointness, inherited properties, shapes, characteristics, the table of what
// is not recognised, and a read that does not depend on the order of the triples.

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { Graph, OWL, RDFS, XSD } from "@lattice/authoring-domain";
import { MAX_DEPTH, classAxioms, individualAxioms, propertyAxioms, readExpression, type ClassExpr } from "./axioms";

const EX = "https://example.org/f#";
const PREFIXES = `
@prefix ex: <${EX}> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
`;
const graph = (body: string) => Graph.parse(PREFIXES + body);
const ex = (name: string) => EX + name;

/** The one superclass of ex:C, read as an expression. */
function superOf(body: string): ClassExpr {
  const axioms = classAxioms(graph(`ex:C a owl:Class . ${body}`), ex("C"));
  expect(axioms.superClasses).toHaveLength(1);
  return axioms.superClasses[0];
}

const restriction = (e: ClassExpr) => {
  if (e.kind !== "restriction") throw new Error(`not a restriction: ${e.kind}`);
  return e;
};

describe("restrictions", () => {
  it.each([
    ["owl:someValuesFrom ex:D", "some"],
    ["owl:allValuesFrom ex:D", "only"],
  ] as const)("%s", (clause, quantifier) => {
    const r = restriction(superOf(`ex:C rdfs:subClassOf [ a owl:Restriction ; owl:onProperty ex:p ; ${clause} ] .`));
    expect(r).toEqual({ kind: "restriction", property: { iri: ex("p") }, quantifier, filler: { kind: "named", iri: ex("D") } });
  });

  it("hasValue with an individual and with a literal", () => {
    const a = restriction(superOf(`ex:C rdfs:subClassOf [ owl:onProperty ex:p ; owl:hasValue ex:i ] .`));
    expect(a).toMatchObject({ quantifier: "value", value: { kind: "iri", value: ex("i") } });
    const b = restriction(superOf(`ex:C rdfs:subClassOf [ owl:onProperty ex:p ; owl:hasValue "x"@en ] .`));
    expect(b.value).toEqual({ kind: "literal", value: "x", language: "en" });
  });

  it("hasSelf", () => {
    const r = restriction(superOf(`ex:C rdfs:subClassOf [ owl:onProperty ex:p ; owl:hasSelf true ] .`));
    expect(r).toEqual({ kind: "restriction", property: { iri: ex("p") }, quantifier: "self" });
  });

  it.each([
    ["owl:minCardinality", "min"],
    ["owl:maxCardinality", "max"],
    ["owl:cardinality", "exactly"],
  ] as const)("%s is unqualified", (predicate, quantifier) => {
    const r = restriction(superOf(`ex:C rdfs:subClassOf [ owl:onProperty ex:p ; ${predicate} "2"^^xsd:nonNegativeInteger ] .`));
    expect(r).toEqual({ kind: "restriction", property: { iri: ex("p") }, quantifier, cardinality: 2 });
  });

  it.each([
    ["owl:minQualifiedCardinality", "min"],
    ["owl:maxQualifiedCardinality", "max"],
    ["owl:qualifiedCardinality", "exactly"],
  ] as const)("%s with owl:onClass", (predicate, quantifier) => {
    const r = restriction(superOf(`ex:C rdfs:subClassOf [ owl:onProperty ex:p ; ${predicate} 3 ; owl:onClass ex:D ] .`));
    expect(r).toEqual({ kind: "restriction", property: { iri: ex("p") }, quantifier, cardinality: 3, filler: { kind: "named", iri: ex("D") } });
  });

  it("a qualified cardinality with owl:onDataRange", () => {
    const r = restriction(superOf(`ex:C rdfs:subClassOf [ owl:onProperty ex:p ; owl:qualifiedCardinality 1 ; owl:onDataRange xsd:integer ] .`));
    expect(r.filler).toEqual({ kind: "named", iri: XSD("integer") });
  });

  it("a property written as the inverse of another", () => {
    const r = restriction(superOf(`ex:C rdfs:subClassOf [ owl:onProperty [ owl:inverseOf ex:p ] ; owl:someValuesFrom ex:D ] .`));
    expect(r.property).toEqual({ iri: ex("p"), inverse: true });
  });

  it("a restriction with no recognised quantifier is unknown and keeps its triples", () => {
    const e = superOf(`ex:C rdfs:subClassOf [ owl:onProperty ex:p ; ex:odd "?" ] .`);
    expect(e.kind).toBe("unknown");
    if (e.kind !== "unknown") return;
    expect(e.term.rows).toEqual(
      expect.arrayContaining([
        { predicate: OWL("onProperty"), object: { kind: "iri", value: ex("p") } },
        { predicate: ex("odd"), object: { kind: "literal", value: "?" } },
      ]),
    );
  });

  it("a statement on a restriction node that nothing uses is kept as extra", () => {
    const e = superOf(`ex:C rdfs:subClassOf [ a owl:Restriction ; owl:onProperty ex:p ; owl:someValuesFrom ex:D ; rdfs:comment "why" ] .`);
    expect(e.extra).toEqual([{ predicate: RDFS("comment"), object: { kind: "literal", value: "why" } }]);
  });
});

describe("class expressions", () => {
  it("intersectionOf", () => {
    const e = superOf(`ex:C rdfs:subClassOf [ owl:intersectionOf ( ex:A ex:B ) ] .`);
    expect(e).toEqual({ kind: "intersection", members: [{ kind: "named", iri: ex("A") }, { kind: "named", iri: ex("B") }] });
  });

  it("unionOf", () => {
    const e = superOf(`ex:C rdfs:subClassOf [ owl:unionOf ( ex:A ex:B ) ] .`);
    expect(e).toMatchObject({ kind: "union", members: [{ iri: ex("A") }, { iri: ex("B") }] });
  });

  it("complementOf", () => {
    const e = superOf(`ex:C rdfs:subClassOf [ owl:complementOf ex:A ] .`);
    expect(e).toEqual({ kind: "complement", operand: { kind: "named", iri: ex("A") } });
  });

  it("oneOf holds individuals and literals", () => {
    const e = superOf(`ex:C rdfs:subClassOf [ owl:oneOf ( ex:i "s" 4 ) ] .`);
    expect(e).toEqual({
      kind: "oneOf",
      members: [
        { kind: "iri", value: ex("i") },
        { kind: "literal", value: "s" },
        { kind: "literal", value: "4", datatype: XSD("integer") },
      ],
    });
  });

  it("a datatype restriction keeps its facets", () => {
    const e = superOf(`ex:C rdfs:subClassOf [ a rdfs:Datatype ; owl:onDatatype xsd:integer ; owl:withRestrictions ( [ xsd:minInclusive 1 ] [ xsd:maxInclusive 9 ] ) ] .`);
    expect(e).toEqual({
      kind: "datatypeRestriction",
      datatype: XSD("integer"),
      facets: [
        { facet: XSD("maxInclusive"), value: { kind: "literal", value: "9", datatype: XSD("integer") } },
        { facet: XSD("minInclusive"), value: { kind: "literal", value: "1", datatype: XSD("integer") } },
      ],
    });
  });

  it("an intersection of a named class and a restriction whose filler is a union", () => {
    const e = superOf(`ex:C rdfs:subClassOf [ owl:intersectionOf ( ex:A [ owl:onProperty ex:p ; owl:someValuesFrom [ owl:unionOf ( ex:B ex:D ) ] ] ) ] .`);
    expect(e).toEqual({
      kind: "intersection",
      members: [
        { kind: "named", iri: ex("A") },
        {
          kind: "restriction",
          property: { iri: ex("p") },
          quantifier: "some",
          filler: { kind: "union", members: [{ kind: "named", iri: ex("B") }, { kind: "named", iri: ex("D") }] },
        },
      ],
    });
  });

  it("a cyclic rdf list terminates and the expression is unknown", () => {
    const e = superOf(`
      ex:C rdfs:subClassOf [ owl:unionOf _:l1 ] .
      _:l1 rdf:first ex:A ; rdf:rest _:l2 .
      _:l2 rdf:first ex:B ; rdf:rest _:l1 .`);
    expect(e).toMatchObject({ kind: "unknown", reason: "malformed" });
  });

  it("a list cell missing its rest is malformed", () => {
    const e = superOf(`ex:C rdfs:subClassOf [ owl:intersectionOf _:l1 ] . _:l1 rdf:first ex:A .`);
    expect(e).toMatchObject({ kind: "unknown", reason: "malformed" });
  });

  it("a cycle through blank nodes terminates", () => {
    const g = graph(`ex:C rdfs:subClassOf _:a . _:a owl:complementOf _:b . _:b owl:complementOf _:a .`);
    const [e] = classAxioms(g, ex("C")).superClasses;
    let depth = 0;
    let node: ClassExpr = e;
    while (node.kind === "complement") {
      node = node.operand;
      depth++;
    }
    expect(depth).toBe(2);
    expect(node).toMatchObject({ kind: "unknown", reason: "cycle" });
  });

  it("the depth cap stops a chain of blank nodes and says so", () => {
    const chain = Array.from({ length: 40 }, (_, i) => `_:n${i} owl:complementOf ${i === 39 ? "ex:Z" : `_:n${i + 1}`} .`).join("\n");
    const g = graph(`ex:C rdfs:subClassOf _:n0 . ${chain}`);
    const [e] = classAxioms(g, ex("C")).superClasses;
    let depth = 0;
    let node: ClassExpr = e;
    while (node.kind === "complement") {
      node = node.operand;
      depth++;
    }
    expect(depth).toBe(MAX_DEPTH);
    expect(node).toMatchObject({ kind: "unknown", reason: "depth" });
  });

  it("a literal where an expression belongs is unknown", () => {
    const g = graph(`ex:C rdfs:subClassOf "text" .`);
    expect(classAxioms(g, ex("C")).superClasses).toEqual([{ kind: "unknown", reason: "unrecognised", term: { kind: "literal", value: "text" } }]);
    expect(readExpression(g, g.objects(ex("C"), RDFS("subClassOf"))[0]).kind).toBe("unknown");
  });
});

describe("class axioms", () => {
  const g = graph(`
    ex:Base a owl:Class .
    ex:Mid a owl:Class ; rdfs:subClassOf ex:Base .
    ex:C a owl:Class ;
      rdfs:label "Thing"@en, "Ding"@de, "Thing, another"@en ;
      rdfs:comment "A thing." ;
      skos:definition "Defined." ;
      skos:example "e.g." ;
      ex:rank 3 ;
      rdfs:subClassOf ex:Mid ;
      owl:equivalentClass [ owl:intersectionOf ( ex:Mid [ owl:onProperty ex:p ; owl:someValuesFrom ex:D ] ) ] ;
      owl:disjointWith ex:X ;
      owl:hasKey ( ex:id ex:code ) .
    ex:Y owl:disjointWith ex:C .
    [] a owl:AllDisjointClasses ; owl:members ( ex:C ex:P ex:Q ) .
    ex:baseProp a owl:DatatypeProperty ; rdfs:domain ex:Base .
    ex:midProp a owl:ObjectProperty ; rdfs:domain ex:Mid .
    ex:ownProp a owl:ObjectProperty ; rdfs:domain ex:C .
    ex:elsewhere a owl:ObjectProperty ; rdfs:domain ex:X .
    ex:one a ex:C .
    ex:two a ex:C, ex:X .
    ex:Shape a sh:NodeShape ; sh:targetClass ex:C ;
      sh:property [ sh:path ex:ownProp ; sh:class ex:D ; sh:minCount 1 ; sh:maxCount 2 ; sh:name "own" ; sh:description "d" ; sh:nodeKind sh:IRI ; sh:pattern "^a" ; sh:hasValue ex:v ; sh:node ex:Other ] ,
                  [ sh:path ex:mode ; sh:in ( ex:fast ex:slow ) ; sh:datatype xsd:string ] .
  `);
  const a = classAxioms(g, ex("C"));

  it("groups annotations by property and language", () => {
    expect(a.annotations.map((x) => [x.property, x.language, x.values.map((v) => v.value)])).toEqual([
      [RDFS("label"), "de", ["Ding"]],
      [RDFS("label"), "en", ["Thing", "Thing, another"]],
      [RDFS("comment"), "", ["A thing."]],
      ["http://www.w3.org/2004/02/skos/core#definition", "", ["Defined."]],
      ["http://www.w3.org/2004/02/skos/core#example", "", ["e.g."]],
      [ex("rank"), "", ["3"]],
    ]);
    expect(a.annotations.at(-1)!.values[0].datatype).toBe(XSD("integer"));
  });

  it("reads superclasses and equivalent classes as trees", () => {
    expect(a.superClasses).toEqual([{ kind: "named", iri: ex("Mid") }]);
    expect(a.equivalentClasses).toHaveLength(1);
    expect(a.equivalentClasses[0]).toMatchObject({ kind: "intersection" });
  });

  it("reads disjointness in both directions and from an AllDisjointClasses", () => {
    expect(a.disjointClasses.map((e) => (e.kind === "named" ? e.iri : "?"))).toEqual([ex("P"), ex("Q"), ex("X"), ex("Y")]);
    // The same is read from the other side of the AllDisjointClasses.
    expect(classAxioms(g, ex("P")).disjointClasses.map((e) => (e.kind === "named" ? e.iri : "?"))).toEqual([ex("C"), ex("Q")]);
    expect(classAxioms(g, ex("Y")).disjointClasses).toEqual([{ kind: "named", iri: ex("C") }]);
  });

  it("reads keys", () => {
    expect(a.keys).toEqual([[{ iri: ex("id") }, { iri: ex("code") }]]);
  });

  it("lists properties by domain, direct and inherited with the superclass", () => {
    expect(a.properties).toEqual([
      { property: ex("baseProp"), from: ex("Base") },
      { property: ex("midProp"), from: ex("Mid") },
      { property: ex("ownProp") },
    ]);
  });

  it("reads the shapes that target the class, each property shape as a row", () => {
    expect(a.shapes).toHaveLength(1);
    const [s] = a.shapes;
    expect(s.shape).toBe(ex("Shape"));
    expect(s.targets).toEqual([ex("C")]);
    const own = s.properties.find((p) => p.path?.value === ex("ownProp"))!;
    expect(own.constraints.map((c) => [c.constraint, c.values.map((v) => v.value)])).toEqual([
      ["class", [ex("D")]],
      ["node", [ex("Other")]],
      ["nodeKind", ["http://www.w3.org/ns/shacl#IRI"]],
      ["minCount", ["1"]],
      ["maxCount", ["2"]],
      ["pattern", ["^a"]],
      ["hasValue", [ex("v")]],
      ["name", ["own"]],
      ["description", ["d"]],
    ]);
    const mode = s.properties.find((p) => p.path?.value === ex("mode"))!;
    expect(mode.constraints).toEqual([
      { constraint: "datatype", values: [{ kind: "iri", value: XSD("string") }] },
      { constraint: "in", values: [{ kind: "iri", value: ex("fast") }, { kind: "iri", value: ex("slow") }] },
    ]);
    expect(mode.other).toEqual([]);
  });

  it("reads a class that is itself a node shape", () => {
    const own = classAxioms(graph(`ex:S a owl:Class, sh:NodeShape ; sh:property [ sh:path ex:p ; sh:minCount 1 ] .`), ex("S"));
    expect(own.shapes).toHaveLength(1);
    expect(own.shapes[0]).toMatchObject({ shape: ex("S"), targets: [ex("S")] });
    expect(own.shapes[0].properties[0].constraints).toEqual([{ constraint: "minCount", values: [{ kind: "literal", value: "1", datatype: XSD("integer") }] }]);
    expect(own.other).toEqual([]);
  });

  it("lists the individuals typed with the class", () => {
    expect(a.individuals).toEqual([ex("one"), ex("two")]);
  });

  it("puts nothing in other when every statement was understood", () => {
    expect(a.other).toEqual([]);
  });
});

describe("the table of other statements", () => {
  it("catches an unrecognised triple and does not repeat a consumed one", () => {
    const g = graph(`
      ex:C a owl:Class, ex:Meta ;
        rdfs:label "C" ;
        rdfs:subClassOf ex:Base ;
        rdfs:seeAlso ex:Doc ;
        ex:note [ ex:inner "x" ] ;
        owl:disjointUnionOf ( ex:A ex:B ) .`);
    const { other } = classAxioms(g, ex("C"));
    expect(other.map((r) => r.predicate)).toEqual([
      "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
      RDFS("seeAlso"),
      OWL("disjointUnionOf"),
      ex("note"),
    ]);
    expect(other[0].object).toEqual({ kind: "iri", value: ex("Meta") });
    expect(other[3].object).toEqual({ kind: "blank", value: "", rows: [{ predicate: ex("inner"), object: { kind: "literal", value: "x" } }] });
    expect(other.map((r) => r.predicate)).not.toContain(RDFS("label"));
    expect(other.map((r) => r.predicate)).not.toContain(RDFS("subClassOf"));
  });

  it("keeps a malformed key list rather than hiding it", () => {
    const g = graph(`ex:C a owl:Class ; owl:hasKey ( "not a property" ) .`);
    expect(classAxioms(g, ex("C")).other.map((r) => r.predicate)).toEqual([OWL("hasKey")]);
  });
});

describe("property axioms", () => {
  const g = graph(`
    ex:p a owl:ObjectProperty, owl:FunctionalProperty, owl:InverseFunctionalProperty, owl:TransitiveProperty, owl:SymmetricProperty ;
      rdfs:label "p" ;
      rdfs:domain ex:A ;
      rdfs:range [ owl:unionOf ( ex:B ex:D ) ] ;
      rdfs:subPropertyOf ex:q ;
      owl:inverseOf ex:r ;
      owl:propertyChainAxiom ( ex:s [ owl:inverseOf ex:t ] ) .
    ex:u owl:inverseOf ex:p .
    ex:a1 a owl:AsymmetricProperty, owl:ReflexiveProperty, owl:IrreflexiveProperty, owl:DatatypeProperty, owl:AnnotationProperty .
    ex:S a sh:NodeShape ; sh:targetClass ex:A ; sh:property ex:PS .
    ex:PS sh:path ex:p ; sh:class ex:B ; sh:maxCount 1 .
    ex:Lonely sh:path ex:p ; sh:minCount 1 .
    ex:Cls a owl:Class, sh:NodeShape ; sh:property [ sh:path ex:p ; sh:nodeKind sh:IRI ] .
  `);
  const a = propertyAxioms(g, ex("p"));

  it("reads kind and characteristics", () => {
    expect(a.kinds).toEqual(["object"]);
    expect(a.characteristics).toEqual(["functional", "inverse functional", "transitive", "symmetric"]);
    const b = propertyAxioms(g, ex("a1"));
    expect(b.kinds).toEqual(["datatype", "annotation"]);
    expect(b.characteristics).toEqual(["asymmetric", "reflexive", "irreflexive"]);
  });

  it("reads domain and range as expressions, and super-properties", () => {
    expect(a.domains).toEqual([{ kind: "named", iri: ex("A") }]);
    expect(a.ranges).toEqual([{ kind: "union", members: [{ kind: "named", iri: ex("B") }, { kind: "named", iri: ex("D") }] }]);
    expect(a.superProperties).toEqual([ex("q")]);
  });

  it("reads inverseOf in both directions", () => {
    expect(a.inverseOf).toEqual([ex("r"), ex("u")]);
    expect(propertyAxioms(g, ex("r")).inverseOf).toEqual([ex("p")]);
    expect(propertyAxioms(g, ex("u")).inverseOf).toEqual([ex("p")]);
  });

  it("reads a property chain, with an inverse member", () => {
    expect(a.chains).toEqual([[{ iri: ex("s") }, { iri: ex("t"), inverse: true }]]);
  });

  it("reads the property shapes that name it, with the node shape and target class", () => {
    expect(a.shapes.map((s) => [s.nodeShape ?? null, s.targets])).toEqual([
      [ex("Cls"), [ex("Cls")]],
      [ex("S"), [ex("A")]],
      [null, []],
    ]);
    const held = a.shapes.find((s) => s.nodeShape === ex("S"))!;
    expect(held.shape.constraints.map((c) => c.constraint)).toEqual(["class", "maxCount"]);
  });

  it("keeps annotations and puts the rest in other", () => {
    expect(a.annotations).toEqual([{ property: RDFS("label"), language: "", values: [{ value: "p" }] }]);
    expect(a.other).toEqual([]);
    const h = propertyAxioms(graph(`ex:p a owl:ObjectProperty ; owl:equivalentProperty ex:q ; rdfs:subPropertyOf [ owl:inverseOf ex:z, ex:y ] .`), ex("p"));
    expect(h.other.map((r) => r.predicate)).toEqual([RDFS("subPropertyOf"), OWL("equivalentProperty")]);
  });
});

describe("individual axioms", () => {
  const g = graph(`
    ex:i a ex:C, owl:NamedIndividual ;
      rdfs:label "I" ;
      skos:note "n" ;
      ex:name "Acme", "Acme Ltd" ;
      ex:knows ex:j ;
      ex:age 4 .
    ex:note a owl:AnnotationProperty .
    ex:k ex:note "custom" ; ex:name "K" .
  `);

  it("reads types, assertions by property and annotations", () => {
    const a = individualAxioms(g, ex("i"));
    expect(a.types).toEqual([OWL("NamedIndividual"), ex("C")]);
    expect(a.annotations.map((x) => x.property)).toEqual([RDFS("label"), "http://www.w3.org/2004/02/skos/core#note"]);
    expect(a.assertions).toEqual([
      { property: ex("age"), values: [{ kind: "literal", value: "4", datatype: XSD("integer") }] },
      { property: ex("knows"), values: [{ kind: "iri", value: ex("j") }] },
      { property: ex("name"), values: [{ kind: "literal", value: "Acme" }, { kind: "literal", value: "Acme Ltd" }] },
    ]);
  });

  it("treats a declared annotation property as an annotation", () => {
    const a = individualAxioms(g, ex("k"));
    expect(a.annotations).toEqual([{ property: ex("note"), language: "", values: [{ value: "custom" }] }]);
    expect(a.assertions.map((x) => x.property)).toEqual([ex("name")]);
  });
});

describe("determinism", () => {
  const statements = [
    `ex:Base a owl:Class .`,
    `ex:C a owl:Class ;
      rdfs:label "C"@en, "K"@de ;
      rdfs:subClassOf ex:Base, [ owl:onProperty ex:p ; owl:minCardinality 1 ], [ owl:intersectionOf ( ex:A [ owl:complementOf ex:B ] ) ] ;
      owl:disjointWith ex:X, ex:Y ;
      ex:extra [ ex:a 1 ; ex:b 2 ] , ex:other .`,
    `ex:p a owl:ObjectProperty, owl:FunctionalProperty ; rdfs:domain ex:C ; rdfs:range ex:D ;
      owl:propertyChainAxiom ( ex:s ex:t ) ; owl:inverseOf ex:r .`,
    `ex:Shape a sh:NodeShape ; sh:targetClass ex:C ; sh:property [ sh:path ex:p ; sh:class ex:D ; sh:minCount 1 ] , [ sh:path ex:q ; sh:datatype xsd:string ] .`,
    `ex:i1 a ex:C ; ex:v 1, 2, 3 .`,
    `ex:i2 a ex:C .`,
  ];
  const body = statements.join("\n");
  const plain = graph(body);
  const shuffled = (seed: number): Graph => {
    const quads = plain.quads();
    let state = seed;
    for (let i = quads.length - 1; i > 0; i--) {
      state = (state * 1103515245 + 12345) % 2147483648;
      const j = state % (i + 1);
      [quads[i], quads[j]] = [quads[j], quads[i]];
    }
    return Graph.of(quads);
  };
  const read = (x: Graph) => ({ c: classAxioms(x, ex("C")), p: propertyAxioms(x, ex("p")), i: individualAxioms(x, ex("i1")) });

  it("reads the same graph the same whatever the order of its triples", () => {
    const expected = JSON.stringify(read(plain));
    for (const seed of [1, 2, 3, 4, 5]) expect(JSON.stringify(read(shuffled(seed)))).toBe(expected);
  });

  it("reads the same from Turtle whose statements are written in another order, so blank labels differ", () => {
    const reversed = graph([...statements].reverse().join("\n"));
    expect(JSON.stringify(read(reversed))).toBe(JSON.stringify(read(plain)));
  });
});

describe("a real file", () => {
  it("reads ex:Facility of the facility baseline sample, its label and its shape", () => {
    const file = join(__dirname, "../../../../contracts/config-studio/samples/facility-baseline.ttl");
    const g = Graph.parse(readFileSync(file, "utf8"));
    const a = classAxioms(g, "https://example.org/lending#Facility");
    expect(a.annotations[0]).toEqual({ property: RDFS("label"), language: "", values: [{ value: "Facility" }] });
    expect(a.shapes).toHaveLength(1);
    expect(a.shapes[0].shape).toBe("https://example.org/lending#FacilityShape");
    expect(a.shapes[0].targets).toEqual(["https://example.org/lending#Facility"]);
    expect(a.shapes[0].properties).toHaveLength(7);
    const lender = a.shapes[0].properties.find((p) => p.path?.value === "https://example.org/lending#lender")!;
    expect(lender.constraints).toEqual([{ constraint: "class", values: [{ kind: "iri", value: "https://example.org/lending#Lender" }] }]);
    expect(lender.other.map((r) => r.predicate)).toEqual(["https://www.nebularis.org/neuro-semantic/lattice/persistence#ownership"]);
  });
});
