// SPDX-License-Identifier: MPL-2.0
// The simulator's object (SVA-P4): the form a boundary shape gives, the lines it writes, and an object given as Turtle. Over the facility sample's baseline.

import { readFileSync } from "node:fs";
import { Graph } from "@lattice/authoring-domain";
import { describe, expect, it } from "vitest";
import { EMPTY_FORM, formSpec, formTriples, formValues, newMemberId, turtleTriples, type FormValues } from "./objectForm";
import { ntLine } from "./simulator";

const baseline = Graph.parse(readFileSync(new URL("../../../../contracts/config-studio/samples/facility-baseline.ttl", import.meta.url), "utf-8"));
const EX = "https://example.org/lending#";
const XSD = "http://www.w3.org/2001/XMLSchema#";
const ROOT = `${EX}facility-1`;
const spec = formSpec(baseline, `${EX}FacilityShape`, `${EX}Facility`)!;

const filled: FormValues = {
  fields: { [`${EX}facilityReference`]: "FAC-2026-001", [`${EX}margin`]: "3.25", [`${EX}lender`]: `${EX}lender-north\n${EX}lender-south`, [`${EX}borrower`]: `${EX}acme-foods` },
  owned: { [`${EX}hasDrawdown`]: [{ id: `${EX}drawdown-1`, fields: { [`${EX}drawnAmount`]: "40000000.0" }, owned: {} }] },
};

describe("the form a boundary shape gives", () => {
  it("has a field for each property of the shape, a reference for a class and a typed literal for a datatype, and an owned member for a node shape", () => {
    expect(spec.rootClass).toBe(`${EX}Facility`);
    expect(spec.fields.map((f) => [f.path.slice(EX.length), f.kind, f.datatype?.slice(XSD.length) ?? f.cls?.slice(EX.length)])).toEqual([
      ["arrangedBy", "iri", "Branch"],
      ["borrower", "iri", "Borrower"],
      ["commitment", "literal", "decimal"],
      ["facilityReference", "literal", "string"],
      ["lender", "iri", "Lender"],
      ["margin", "literal", "decimal"],
    ]);
    expect(spec.owned.map((o) => [o.property.slice(EX.length), o.cls.slice(EX.length), o.fields.map((f) => f.path.slice(EX.length))])).toEqual([["hasDrawdown", "Drawdown", ["drawdownDate", "drawnAmount"]]]);
  });

  it("is none where the baseline holds no such shape or the profile names none", () => {
    expect(formSpec(baseline, `${EX}NoShape`, `${EX}Facility`)).toBeUndefined();
    expect(formSpec(baseline, null, `${EX}Facility`)).toBeUndefined();
  });

  it("writes the root and each owned member typed by their class, each value typed by the shape's datatype, and each reference as an IRI", () => {
    const result = formTriples(spec, filled, ROOT);
    if (!("lines" in result)) throw new Error(result.problem);
    expect(result.lines).toEqual(
      [
        ntLine(ROOT, "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", `<${EX}Facility>`),
        ntLine(ROOT, `${EX}facilityReference`, `"FAC-2026-001"`),
        ntLine(ROOT, `${EX}margin`, `"3.25"^^<${XSD}decimal>`),
        ntLine(ROOT, `${EX}borrower`, `<${EX}acme-foods>`),
        ntLine(ROOT, `${EX}lender`, `<${EX}lender-north>`),
        ntLine(ROOT, `${EX}lender`, `<${EX}lender-south>`),
        ntLine(ROOT, `${EX}hasDrawdown`, `<${EX}drawdown-1>`),
        ntLine(`${EX}drawdown-1`, "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", `<${EX}Drawdown>`),
        ntLine(`${EX}drawdown-1`, `${EX}drawnAmount`, `"40000000.0"^^<${XSD}decimal>`),
      ].sort(),
    );
    expect(formTriples(spec, filled, ROOT)).toEqual(result);
  });

  it("refuses a reference that is not an IRI and a member whose identifier is not one, and says which", () => {
    expect(formTriples(spec, { ...EMPTY_FORM, fields: { [`${EX}borrower`]: "acme foods" } }, ROOT)).toEqual({ problem: expect.stringContaining("borrower holds \"acme foods\", which is not an IRI") });
    expect(formTriples(spec, { ...EMPTY_FORM, owned: { [`${EX}hasDrawdown`]: [{ id: "d 1", fields: {}, owned: {} }] } }, ROOT)).toEqual({ problem: expect.stringContaining("drawdown has the identifier") });
  });

  it("gives back the values of the aggregate the world stores, so that a replace starts from it", () => {
    const result = formTriples(spec, filled, ROOT);
    if (!("lines" in result)) throw new Error(result.problem);
    const back: FormValues = formValues(spec, result.lines, ROOT);
    expect(back.fields[`${EX}lender`]).toBe(`${EX}lender-north\n${EX}lender-south`);
    expect(back.owned[`${EX}hasDrawdown`][0].id).toBe(`${EX}drawdown-1`);
    expect(formTriples(spec, back, ROOT)).toEqual(result);
  });

  it("names a new member after its parent and the number no sibling has", () => {
    const owned = spec.owned[0];
    expect(newMemberId(ROOT, owned, [])).toBe(`${ROOT}-drawdown-1`);
    expect(newMemberId(ROOT, owned, [{ id: `${ROOT}-drawdown-2`, fields: {}, owned: {} }])).toBe(`${ROOT}-drawdown-1`);
    expect(newMemberId(ROOT, owned, [{ id: `${ROOT}-drawdown-1`, fields: {}, owned: {} }])).toBe(`${ROOT}-drawdown-2`);
  });
});

describe("an object given as Turtle", () => {
  const turtle = `@prefix ex: <${EX}> . ex:facility-1 a ex:Facility ; ex:margin 3.25 .`;
  it("is the same lines the form writes for the same triples", () => {
    expect(turtleTriples(turtle, ROOT)).toEqual({ lines: [ntLine(ROOT, "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", `<${EX}Facility>`), ntLine(ROOT, `${EX}margin`, `"3.25"^^<${XSD}decimal>`)].sort() });
  });
  it("is refused when it does not parse, is empty, holds a blank node or says nothing of the root", () => {
    expect(turtleTriples("", ROOT)).toEqual({ problem: "The Turtle is empty." });
    expect(turtleTriples("ex:a ex:b", ROOT)).toEqual({ problem: expect.stringContaining("does not parse") });
    expect(turtleTriples(`@prefix ex: <${EX}> . ex:facility-1 ex:lender [ ex:legalName "x" ] .`, ROOT)).toEqual({ problem: expect.stringContaining("blank node") });
    expect(turtleTriples(`@prefix ex: <${EX}> . ex:other ex:margin 1 .`, ROOT)).toEqual({ problem: "The Turtle says nothing of the root." });
  });
});

