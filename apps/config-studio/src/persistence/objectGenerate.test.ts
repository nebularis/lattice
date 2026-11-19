// SPDX-License-Identifier: MPL-2.0
// The object generated from a boundary shape (SVA-P5). The browser holds no SHACL engine, since the run worker checks a payload against the shape, so
// the conformance check here is a small one written for the test. It reads minCount, maxCount, datatype, class, nodeKind, in, hasValue, the four numeric
// bounds, the two lengths and pattern, and follows sh:node into an owned member. The run worker's own check of the generated facility is the journey's
// fixture, whose frames SimulatorJourneyTest records from the worker.

import { readFileSync } from "node:fs";
import { Graph, SH, namedNode, type Term } from "@lattice/authoring-domain";
import { describe, expect, it } from "vitest";
import { readLanding } from "./landing";
import { formSpec, formTriples, type FormSpec } from "./objectForm";
import { MOST_PER_PROPERTY, generateObject, instancesIn, type Instances } from "./objectGenerate";
import { addLines, buildStep, initialWorld, ntLine, EMPTY_WORLD } from "./simulator";
import { DEFAULT_TIME } from "./simulatorStore";

const EX = "https://example.org/lending#";
const XSD = "http://www.w3.org/2001/XMLSchema#";
const ROOT = `${EX}facility-1`;
const TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type";
const read = (rel: string) => readFileSync(new URL(rel, import.meta.url), "utf-8");
const sample = Graph.parse(read("../../../../contracts/config-studio/samples/facility-baseline.ttl"));

// A strict boundary shape over the same classes, which asks for what the sample's does not.
const STRICT = `
@prefix ex: <${EX}> . @prefix sh: <http://www.w3.org/ns/shacl#> . @prefix xsd: <${XSD}> .
ex:StrictFacilityShape a sh:NodeShape ; sh:targetClass ex:Facility ;
  sh:property [ sh:path ex:facilityReference ; sh:datatype xsd:string ; sh:minCount 1 ; sh:maxCount 1 ; sh:minLength 12 ] ,
              [ sh:path ex:commitment ; sh:datatype xsd:decimal ; sh:minCount 1 ; sh:minInclusive 1000 ; sh:maxExclusive 2000 ] ,
              [ sh:path ex:margin ; sh:datatype xsd:decimal ; sh:minCount 1 ] ,
              [ sh:path ex:status ; sh:datatype xsd:string ; sh:minCount 1 ; sh:in ( "draft" "signed" ) ] ,
              [ sh:path ex:code ; sh:datatype xsd:string ; sh:minCount 1 ; sh:pattern "^FAC$" ] ,
              [ sh:path ex:legalEntityCode ; sh:datatype xsd:string ; sh:minCount 1 ; sh:pattern "^[A-Z]{4}[0-9]{2}$" ] ,
              [ sh:path ex:rank ; sh:datatype xsd:integer ; sh:minCount 1 ; sh:minExclusive 4 ; sh:maxInclusive 6 ] ,
              [ sh:path ex:signed ; sh:datatype xsd:boolean ; sh:minCount 1 ] ,
              [ sh:path ex:arrangedBy ; sh:class ex:Branch ; sh:minCount 1 ; sh:maxCount 1 ] ,
              [ sh:path ex:borrower ; sh:class ex:Borrower ; sh:minCount 1 ] ,
              [ sh:path ex:lender ; sh:class ex:Lender ; sh:minCount 2 ] ,
              [ sh:path ex:note ; sh:datatype xsd:string ] ,
              [ sh:path ex:hasDrawdown ; sh:node ex:StrictDrawdownShape ; sh:minCount 2 ] .
ex:StrictDrawdownShape a sh:NodeShape ; sh:targetClass ex:Drawdown ;
  sh:property [ sh:path ex:drawnAmount ; sh:datatype xsd:decimal ; sh:minCount 1 ] ,
              [ sh:path ex:drawdownDate ; sh:datatype xsd:date ; sh:minCount 1 ] ,
              [ sh:path ex:hasFee ; sh:node ex:FeeShape ; sh:minCount 1 ; sh:maxCount 1 ] .
ex:FeeShape a sh:NodeShape ; sh:targetClass ex:Fee ;
  sh:property [ sh:path ex:feeRate ; sh:datatype xsd:decimal ; sh:minCount 1 ] .
ex:ImpossibleShape a sh:NodeShape ; sh:targetClass ex:Facility ;
  sh:property [ sh:path ex:rank ; sh:datatype xsd:integer ; sh:minCount 1 ; sh:minInclusive 9 ; sh:maxInclusive 3 ] ,
              [ sh:path ex:fee ; sh:datatype xsd:string ; sh:minCount 3 ; sh:maxCount 2 ] ,
              [ sh:path ex:many ; sh:datatype xsd:string ; sh:minCount ${MOST_PER_PROPERTY + 5} ] ,
              [ sh:path ex:unknown ; sh:datatype xsd:hexBinary ; sh:minCount 1 ] ,
              [ sh:path ex:untyped ; sh:minCount 1 ] .
`;
const strictGraph = sample.merge(Graph.parse(STRICT));
const strict = formSpec(strictGraph, `${EX}StrictFacilityShape`, `${EX}Facility`)!;
const impossible = formSpec(strictGraph, `${EX}ImpossibleShape`, `${EX}Facility`)!;
const plain = formSpec(sample, `${EX}FacilityShape`, `${EX}Facility`)!;

/** A world that holds the nodes a facility refers to, in the graph a step would have put them. */
const world = addLines(EMPTY_WORLD, "urn:g:other", [
  ntLine(`${EX}branch-london`, TYPE, `<${EX}Branch>`),
  ntLine(`${EX}acme-foods`, TYPE, `<${EX}Borrower>`),
  ntLine(`${EX}lender-south`, TYPE, `<${EX}Lender>`),
  ntLine(`${EX}lender-north`, TYPE, `<${EX}Lender>`),
  ntLine(`${EX}lender-east`, TYPE, `<${EX}Lender>`),
]);

// --- a small conformance check ------------------------------------------------------------------------------------------------

function conforms(shapes: Graph, shape: Term, data: Graph, node: Term, instances: Instances, out: string[] = []): string[] {
  const value = (ps: Term, p: string) => shapes.value(ps, SH(p));
  for (const ps of shapes.objects(shape, SH("property"))) {
    const path = shapes.object(ps, SH("path"))!.value;
    const values = data.objects(node, path);
    const where = `${node.value} ${path}`;
    const min = Number(value(ps, "minCount") ?? 0);
    const max = value(ps, "maxCount") === undefined ? Infinity : Number(value(ps, "maxCount"));
    if (values.length < min) out.push(`${where} has ${values.length}, fewer than ${min}`);
    if (values.length > max) out.push(`${where} has ${values.length}, more than ${max}`);
    const datatype = value(ps, "datatype");
    const cls = value(ps, "class");
    const list = shapes.object(ps, SH("in"));
    const allowed = list ? shapes.list(list)!.map((t) => t.value) : undefined;
    const nested = shapes.object(ps, SH("node"));
    for (const v of values) {
      if (datatype && (v.termType !== "Literal" || (v as { datatype: { value: string } }).datatype.value !== datatype)) out.push(`${where} ${v.value} is not a ${datatype}`);
      if (cls && !instances(cls).includes(v.value)) out.push(`${where} ${v.value} is not a ${cls}`);
      if (allowed && !allowed.includes(v.value)) out.push(`${where} ${v.value} is not one of the listed values`);
      if (value(ps, "hasValue") && v.value !== value(ps, "hasValue")) out.push(`${where} ${v.value} is not the value required`);
      const n = Number(v.value);
      for (const [name, test] of [["minInclusive", (b: number) => n >= b], ["maxInclusive", (b: number) => n <= b], ["minExclusive", (b: number) => n > b], ["maxExclusive", (b: number) => n < b]] as const) {
        const bound = value(ps, name);
        if (bound !== undefined && !test(Number(bound))) out.push(`${where} ${v.value} breaks ${name} ${bound}`);
      }
      const minLength = value(ps, "minLength");
      if (minLength !== undefined && v.value.length < Number(minLength)) out.push(`${where} ${v.value} is shorter than ${minLength}`);
      const pattern = value(ps, "pattern");
      if (pattern !== undefined && !new RegExp(pattern).test(v.value)) out.push(`${where} ${v.value} does not match ${pattern}`);
      if (nested) {
        if (!data.types(v).includes(shapes.object(nested, SH("targetClass"))!.value)) out.push(`${v.value} is not typed by the class of ${nested.value}`);
        conforms(shapes, nested, data, v, instances, out);
      }
    }
  }
  return out;
}

function generated(spec: FormSpec, instances: Instances) {
  const made = generateObject(spec, ROOT, instances);
  const triples = formTriples(spec, made.form, ROOT);
  if (!("lines" in triples)) throw new Error(triples.problem);
  return { ...made, lines: triples.lines, data: Graph.parse(triples.lines.join("\n")) };
}

describe("the object a boundary shape gives", () => {
  it("is the root with a reference, a commitment and a margin where the shape requires those three and nothing else, as the facility sample's does, and it conforms", () => {
    const g = generated(plain, instancesIn(world));
    const get = (p: string) => g.data.objects(ROOT, `${EX}${p}`).map((t) => t.value);
    expect(g.lines).toHaveLength(4);
    expect(g.lines).toContain(ntLine(ROOT, TYPE, `<${EX}Facility>`));
    expect(get("facilityReference")).toHaveLength(1);
    expect(get("commitment")).toHaveLength(1);
    expect(get("margin")).toHaveLength(1);
    expect(get("arrangedBy")).toEqual([]);
    expect(get("borrower")).toEqual([]);
    expect(get("lender")).toEqual([]);
    expect(get("hasDrawdown")).toEqual([]);
    expect(g.left).toEqual([]);
    expect(conforms(sample, namedNode(`${EX}FacilityShape`), g.data, namedNode(ROOT), instancesIn(world))).toEqual([]);
  });

  it("conforms to a shape that requires a value of each kind, a list, a bound, a length, a literal pattern, owned members and nested members", () => {
    const instances = instancesIn(world);
    const g = generated(strict, instances);
    // The one pattern that is not a literal text is left, and so is nothing else.
    expect(g.left).toEqual([`The legal entity code of the facility is left for you, its sh:pattern is a regular expression, and a value for it is given by hand.`]);
    const problems = conforms(strictGraph, namedNode(`${EX}StrictFacilityShape`), g.data, namedNode(ROOT), instances).filter((p) => !p.includes("legalEntityCode"));
    expect(problems).toEqual([]);
    const get = (p: string) => g.data.objects(ROOT, `${EX}${p}`).map((t) => t.value).sort();
    expect(get("code")).toEqual(["FAC"]);
    expect(["draft", "signed"]).toContain(get("status")[0]);
    expect(["5", "6"]).toContain(get("rank")[0]);
    expect(get("note")).toEqual([]);
    expect(Number(get("commitment")[0])).toBeGreaterThanOrEqual(1000);
    expect(get("facilityReference")[0].length).toBeGreaterThanOrEqual(12);
  });

  it("gives as many of a property as its minimum asks for and never more, a reference from the world and an owned member under the root", () => {
    const g = generated(strict, instancesIn(world));
    expect(g.data.objects(ROOT, `${EX}lender`).map((t) => t.value).sort()).toEqual([`${EX}lender-east`, `${EX}lender-north`]);
    expect(g.data.objects(ROOT, `${EX}borrower`).map((t) => t.value)).toEqual([`${EX}acme-foods`]);
    const drawdowns = g.data.objects(ROOT, `${EX}hasDrawdown`).map((t) => t.value).sort();
    expect(drawdowns).toEqual([`${ROOT}-drawdown-1`, `${ROOT}-drawdown-2`]);
    for (const d of drawdowns) expect(g.data.objects(d, `${EX}hasFee`).map((t) => t.value)).toEqual([`${d}-fee-1`]);
    expect(g.data.objects(`${ROOT}-drawdown-1`, `${EX}drawnAmount`)[0].value).not.toBe(g.data.objects(`${ROOT}-drawdown-2`, `${EX}drawnAmount`)[0].value);
  });

  it("is the same object each time, and a step built from it is the same TriG", () => {
    const profile = readLanding(read("../../e2e/fixtures/compiled-profile-facility.ttl"));
    if (profile.state !== "ready") throw new Error("predates");
    const facility = profile.doc.targets.find((t) => t.id === "Facility")!;
    const start = initialWorld(facility);
    const once = generated(strict, instancesIn(world));
    const twice = generated(strict, instancesIn(world));
    expect(twice.form).toEqual(once.form);
    expect(twice.lines).toEqual(once.lines);
    const step = (lines: string[]) => buildStep({ target: facility, operation: facility.operations.find((o) => o.operation === "create-if-absent")!, root: ROOT, object: lines, world: start, steps: 0, time: DEFAULT_TIME, asAnotherWriter: false });
    const a = step(once.lines);
    const b = step(twice.lines);
    if (!("trig" in a) || !("trig" in b)) throw new Error("a step is built");
    expect(b.trig).toBe(a.trig);
  });

  it("leaves a reference for the author where the world holds no node of its class, and says which and why, and never invents one", () => {
    const g = generated(strict, instancesIn(EMPTY_WORLD));
    expect(g.data.objects(ROOT, `${EX}borrower`)).toEqual([]);
    expect(g.data.objects(ROOT, `${EX}arrangedBy`)).toEqual([]);
    expect(g.data.objects(ROOT, `${EX}lender`)).toEqual([]);
    expect(g.left).toEqual(expect.arrayContaining([
      "The borrower of the facility is left for you, the sample world holds no borrower.",
      "The arranged by of the facility is left for you, the sample world holds no branch.",
      "The lender of the facility is left for you, the sample world holds no lender.",
    ]));
  });

  it("gives the references the world holds when it holds fewer than the minimum, and leaves the rest", () => {
    const one = addLines(EMPTY_WORLD, "urn:g:other", [ntLine(`${EX}lender-north`, TYPE, `<${EX}Lender>`)]);
    const g = generated(strict, instancesIn(one));
    expect(g.data.objects(ROOT, `${EX}lender`).map((t) => t.value)).toEqual([`${EX}lender-north`]);
    expect(g.left).toContain("The lender of the facility has 1 of the 2 values the shape asks for, and the rest is left for you, the sample world holds only 1 lender.");
  });

  it("never refers the object to itself", () => {
    const self = addLines(EMPTY_WORLD, "urn:g:other", [ntLine(ROOT, TYPE, `<${EX}Lender>`)]);
    expect(generated(strict, instancesIn(self)).data.objects(ROOT, `${EX}lender`)).toEqual([]);
  });

  it("says why it leaves a value that no number, datatype or count gives, and caps a minimum above what a small object holds", () => {
    const g = generated(impossible, instancesIn(world));
    expect(g.left).toEqual(expect.arrayContaining([
      "The rank of the facility is left for you, no number satisfies the bounds the shape states.",
      "The fee of the facility is left for you, it asks for at least 3 and at most 2.",
      `The many of the facility has ${MOST_PER_PROPERTY} of the ${MOST_PER_PROPERTY + 5} values the shape asks for, and the rest is left for you, it asks for ${MOST_PER_PROPERTY + 5}, and a generated object holds at most ${MOST_PER_PROPERTY}.`,
      "The unknown of the facility is left for you, the generator has no value for the datatype hexBinary.",
      "The untyped of the facility is left for you, the shape states no datatype, and the value could be a literal or a reference.",
    ]));
    expect(g.data.objects(ROOT, `${EX}many`)).toHaveLength(MOST_PER_PROPERTY);
  });

  it("derives a value from the property and the node's path, so that two properties and two members differ", () => {
    const g = generated(strict, instancesIn(world));
    const values = [`${EX}facilityReference`, `${EX}margin`, `${EX}commitment`].map((p) => g.data.objects(ROOT, p)[0].value);
    expect(new Set(values).size).toBe(3);
  });
});
