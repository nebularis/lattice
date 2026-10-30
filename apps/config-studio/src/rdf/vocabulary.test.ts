// SPDX-License-Identifier: MPL-2.0
// How forms read SHACL shapes first, then rdfs:domain and rdfs:range, on a small vocabulary written
// here. The staged vocabulary is covered at the end, against the repository's own shapes.

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { DAL, QNT } from "@lattice/authoring-domain";
import { Vocabulary } from "./vocabulary";

const EX = "https://example.org/f#";
const PREFIXES = `
@prefix ex: <${EX}> .
@prefix dal: <https://www.nebularis.org/neuro-semantic/lattice/persistence#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
`;

const vocab = Vocabulary.parse(`${PREFIXES}
ex:Base a owl:Class .
ex:Thing a owl:Class ; rdfs:subClassOf ex:Base .
ex:Implicit a owl:Class, sh:NodeShape ; sh:property [ sh:path ex:ownCount ; sh:datatype xsd:integer ] .
ex:Mode a owl:Class .
ex:fast a ex:Mode .
ex:slow a ex:Mode .
ex:Part a owl:Class .

# No rdfs:domain, so only a shape places these.
ex:size a owl:DatatypeProperty .
ex:mode a owl:ObjectProperty .
ex:part a owl:ObjectProperty .
ex:kind a owl:ObjectProperty .
ex:tags a owl:DatatypeProperty .
ex:inherited a owl:DatatypeProperty .
ex:ownCount a owl:DatatypeProperty .
# A domain and a range, and no shape on the class that names it.
ex:legacy a owl:DatatypeProperty ; rdfs:domain ex:Thing ; rdfs:range xsd:boolean .
# A domain and a range that a shape contradicts.
ex:contested a owl:DatatypeProperty ; rdfs:domain ex:Thing ; rdfs:range xsd:string .
ex:named a owl:DatatypeProperty ; rdfs:label "Own label" .
dal:priority a owl:DatatypeProperty .

ex:BaseShape a sh:NodeShape ; sh:targetClass ex:Base ;
  sh:property [ sh:path ex:inherited ; sh:datatype xsd:boolean ] .

ex:ThingShape a sh:NodeShape ; sh:targetClass ex:Thing ;
  sh:property [ sh:path ex:size ; sh:datatype xsd:integer ; sh:minCount 1 ; sh:maxCount 1 ] ,
    [ sh:path ex:mode ; sh:in ( ex:fast ex:slow ) ; sh:maxCount 1 ] ,
    [ sh:path ex:part ; sh:class ex:Part ] ,
    [ sh:path ex:kind ; sh:class ex:Mode ] ,
    [ sh:path ex:tags ; sh:datatype xsd:string ] ,
    [ sh:path ex:contested ; sh:datatype xsd:integer ] ,
    [ sh:path ex:named ; sh:name "Shape name" ; sh:description "Shape description" ] ,
    [ sh:path ex:legacy ; sh:maxCount 1 ] ,
    [ sh:path dal:priority ; sh:datatype xsd:string ; sh:minCount 1 ] ,
    [ sh:path ( ex:part ex:size ) ; sh:minCount 1 ] .

# A second shape for the same class and property: the most restrictive counts hold.
ex:ThingMoreShape a sh:NodeShape ; sh:targetClass ex:Thing ;
  sh:property [ sh:path ex:size ; sh:maxCount 2 ] , [ sh:path ex:tags ; sh:minCount 2 ; sh:maxCount 4 ] , [ sh:path ex:tags ; sh:maxCount 3 ] .
`);

const T = (local: string) => EX + local;

describe("a property placed by a shape", () => {
  it("is offered on the shape's class although it has no rdfs:domain", () => {
    const placed = vocab.propertiesOf(T("Thing"));
    expect(placed).toEqual(expect.arrayContaining([T("size"), T("mode"), T("part"), T("kind"), T("tags")]));
  });

  it("is offered on a class that is itself the shape", () => {
    expect(vocab.propertiesOf(T("Implicit"))).toEqual([T("ownCount")]);
    expect(vocab.field(T("ownCount"), T("Implicit")).kind).toBe("number");
  });

  it("is not offered by a shape's complex path, nor on another class", () => {
    expect(vocab.propertiesOf(T("Base"))).toEqual([T("inherited")]);
    expect(vocab.propertiesOf(T("Mode"))).toEqual([]);
  });

  it("takes its control from sh:datatype", () => {
    expect(vocab.field(T("size"), T("Thing")).kind).toBe("number");
    expect(vocab.field(T("tags"), T("Thing")).kind).toBe("text");
    expect(vocab.field(T("inherited"), T("Base")).kind).toBe("boolean");
  });

  it("offers the values of sh:in as choices", () => {
    const mode = vocab.field(T("mode"), T("Thing"));
    expect(mode.kind).toBe("choice");
    expect(mode.options.map((o) => o.iri)).toEqual([T("fast"), T("slow")]);
    expect(mode.single).toBe(true);
  });

  it("reads sh:class as a choice among individuals, or else a reference", () => {
    expect(vocab.field(T("kind"), T("Thing")).kind).toBe("choice");
    expect(vocab.field(T("kind"), T("Thing")).options.map((o) => o.iri)).toEqual([T("fast"), T("slow")]);
    expect(vocab.field(T("part"), T("Thing")).kind).toBe("reference");
  });

  it("is single only where sh:maxCount says 1, or the ontology's own rule does", () => {
    expect(vocab.field(T("size"), T("Thing")).single).toBe(true);
    // The two shapes give maxCount 1 and 2, and the most restrictive holds.
    expect(vocab.constraint(T("Thing"), T("size"))?.maxCount).toBe(1);
    // Not functional, and no maxCount of 1, so several values.
    expect(vocab.field(T("part"), T("Thing")).single).toBe(false);
    expect(vocab.constraint(T("Thing"), T("tags"))).toMatchObject({ minCount: 2, maxCount: 3 });
  });

  it("is required only where sh:minCount is at least 1", () => {
    expect(vocab.field(T("size"), T("Thing")).required).toBe(true);
    expect(vocab.field(T("tags"), T("Thing")).required).toBe(true);
    expect(vocab.field(T("mode"), T("Thing")).required).toBe(false);
  });

  it("takes sh:name and sh:description only where the property has no label or comment", () => {
    const named = vocab.field(T("named"), T("Thing"));
    expect(named.label).toBe("Own label");
    expect(named.comment).toBe("Shape description");
    expect(vocab.field(T("tags"), T("Thing")).label).toBe("Tags");
  });
});

describe("precedence", () => {
  it("has an OVERRIDES entry beat the shape, which still says whether the field is required", () => {
    const priority = vocab.field(DAL("priority"), T("Thing"));
    expect(priority.kind).toBe("number");
    expect(priority.required).toBe(true);
  });

  it("has a shape beat rdfs:domain and rdfs:range", () => {
    expect(vocab.field(T("contested")).kind).toBe("text");
    expect(vocab.field(T("contested"), T("Thing")).kind).toBe("number");
  });

  it("keeps the domain and range where a shape names the property without a control", () => {
    const legacy = vocab.field(T("legacy"), T("Thing"));
    expect(legacy.kind).toBe("boolean");
    expect(legacy.single).toBe(true);
  });

  it("is as before for a field read without a class", () => {
    // No shape applies, so the integer datatype of Thing's shape is not read. A datatype property with no range is text.
    expect(vocab.field(T("size")).kind).toBe("text");
    expect(vocab.field(T("size")).required).toBe(false);
  });
});

describe("inheritance", () => {
  it("takes the shapes of a class's ancestors", () => {
    expect(vocab.propertiesOf(T("Thing"))).toContain(T("inherited"));
    expect(vocab.field(T("inherited"), T("Thing")).kind).toBe("boolean");
  });
});

describe("the staged vocabulary", () => {
  const assets = process.env.LATTICE_STUDIO_ASSETS ?? join(import.meta.dirname, "../../../../.build/config-studio");
  const staged = Vocabulary.parse(readFileSync(join(assets, "vocabulary.ttl"), "utf-8"));

  it("places qnt:onSpace on a range by its shape, since the property has no rdfs:domain", () => {
    expect(staged.graph.value(QNT("onSpace"), "http://www.w3.org/2000/01/rdf-schema#domain")).toBeUndefined();
    expect(staged.propertiesOf(QNT("Range"))).toContain(QNT("onSpace"));
    const field = staged.field(QNT("onSpace"), QNT("Range"));
    expect(field.kind).toBe("reference");
    expect(field.single).toBe(true);
    expect(field.required).toBe(true);
  });

  it("marks a required dal: property from its shape", () => {
    expect(staged.field(DAL("graphPrefix"), DAL("GraphPatternScope")).required).toBe(true);
    expect(staged.field(DAL("describedBy"), DAL("GraphPatternScope")).required).toBe(false);
  });
});
