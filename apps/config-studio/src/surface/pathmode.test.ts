// SPDX-License-Identifier: MPL-2.0
// Path mode's pure part (SVA-S1 part 2, SVA-Q60): what a click writes for each place a path is built, which is what the writers the form uses
// write for the same path, and which properties a next hop may be.

import { readFileSync } from "node:fs";
import { Graph, SH, SRF, RDF } from "@lattice/authoring-domain";
import { describe, expect, it } from "vitest";
import { writePath, writeBindingProperty, writeMembersPath } from "../rdf/path";
import { drawContract, type PathPlace } from "./drawing";
import { readHops } from "./paths";
import { addHop, optionsAt, reachedAfter, readPlace, setClosure, undoHop } from "./pathmode";
import { ontologyOf } from "./terms";

const sample = (n: string) => Graph.parse(readFileSync(new URL(`../../../../contracts/config-studio/samples/${n}`, import.meta.url), "utf-8"));
const surface = sample("facility-surface.ttl");
const ontology = ontologyOf(sample("lending-baseline.ttl").merge(sample("facility-baseline.ttl")), []);
const EX = "https://example.org/lending#";
const at = (n: string) => `${EX}${n}`;
const forward = (p: string) => ({ property: at(p), inverse: false });
const inverse = (p: string) => ({ property: at(p), inverse: true });

const PREFIXES = `@prefix srf: <${SRF("")}> . @prefix sh: <${SH("")}> . @prefix ex: <${EX}> . @prefix rdf: <${RDF("")}> .`;
const bare = Graph.parse(`${PREFIXES}
  ex:promotion a srf:PromotionContract ; srf:carrier ex:Facility ; srf:promotesTo ex:sector .
  ex:index a srf:IndexContract ; srf:carrier ex:Borrower .
  ex:binding a srf:ProjectionRoleBinding ; srf:roleKind srf:RequiredEvidenceRole .
  ex:stated a srf:ExpansionStatement ; srf:expandsFrom ex:covenantsBinding ; srf:expansionSource srf:ListMembers .
  ex:covenantsBinding a srf:ProjectionRoleBinding ; srf:bindsProperty ex:covenants .
  ex:expansion a srf:ExpansionStatement ; srf:expandsFrom ex:expandsBinding .
  ex:expandsBinding a srf:ProjectionRoleBinding ; srf:bindsProperty ex:refinances .`);

const read = (node: string, carrier = at("Facility")): PathPlace => ({ kind: "read", node: at(node), contract: at(node), carrier, label: "the read path" });
const binding: PathPlace = { kind: "binding", node: at("binding"), contract: at("promotion"), carrier: at("Facility"), label: "the property of required evidence" };
const members = (node: string): PathPlace => ({ kind: "members", node: at(node), contract: at("promotion"), carrier: at("Facility"), label: "the members path" });
const click = (g: Graph, place: PathPlace, hop: { property: string; inverse: boolean }) => addHop(g, place, place.carrier, ontology, hop);

describe("a read path built by clicking writes what the hop-by-hop control writes", () => {
  it("writes srf:readProperty for a promotion of one forward hop", () => {
    const g = click(bare, read("promotion"), forward("borrower"));
    expect(g.value(at("promotion"), SRF("readProperty"))).toBe(at("borrower"));
    expect(g.objects(at("promotion"), SRF("hasPathStep"))).toEqual([]);
    expect(g.toTurtle()).toBe(writePath(bare, at("promotion"), [forward("borrower")]).toTurtle());
  });

  it("writes srf:hasPathStep for a promotion of two hops, one inverse, with the triples writePath gives for the same steps", () => {
    const place = read("promotion");
    const one = click(bare, place, forward("borrower"));
    const two = click(one, place, inverse("borrower"));
    expect(two.value(at("promotion"), SRF("readProperty"))).toBeUndefined();
    const steps = two.objects(at("promotion"), SRF("hasPathStep"));
    expect(steps).toHaveLength(2);
    expect(two.value(steps.find((s) => two.value(s, SRF("stepIndex")) === "1")!, SRF("stepDirection"))).toBe(SRF("Inverse"));
    const expected = writePath(bare, at("promotion"), [forward("borrower"), inverse("borrower")]);
    expect(two.toTurtle()).toBe(expected.toTurtle());
    expect(readPlace(two, place).hops).toEqual([forward("borrower"), inverse("borrower")]);
  });

  it("writes an index path the same way", () => {
    const place = read("index", at("Borrower"));
    const g = click(click(bare, place, forward("borrowerSector")), place, forward("borrowerSector"));
    expect(g.toTurtle()).toBe(writePath(bare, at("index"), [forward("borrowerSector"), forward("borrowerSector")]).toTurtle());
    expect(g.objects(at("index"), SRF("hasPathStep"))).toHaveLength(2);
  });

  it("goes on from the hops a contract already states, as the form's control does", () => {
    const place = read("drawdown-sector-promotion", at("Drawdown"));
    const before = readPlace(surface, place).hops;
    expect(before.map((h) => h.property)).toEqual([at("drawnUnder"), at("borrower"), at("borrowerSector")]);
    const after = click(surface, read("drawdown-sector-promotion", at("Drawdown")), inverse("borrower"));
    expect(after.toTurtle()).toBe(writePath(surface, at("drawdown-sector-promotion"), [...before, inverse("borrower")]).toTurtle());
  });
});

describe("a role binding's property", () => {
  it("is the one property it binds, written as srf:bindsProperty", () => {
    const g = click(bare, binding, forward("margin"));
    expect(g.value(at("binding"), SRF("bindsProperty"))).toBe(at("margin"));
    expect(g.toTurtle()).toBe(writeBindingProperty(bare, at("binding"), at("margin")).toTurtle());
    // Another click replaces it, and an inverse hop is not one a binding takes.
    const other = click(g, binding, forward("commitment"));
    expect(other.objects(at("binding"), SRF("bindsProperty")).map((t) => t.value)).toEqual([at("commitment")]);
    expect(click(other, binding, inverse("commitment")).toTurtle()).toBe(other.toTurtle());
  });

  it("is undone by removing it", () => {
    const g = click(bare, binding, forward("margin"));
    expect(undoHop(g, binding).objects(at("binding"), SRF("bindsProperty"))).toEqual([]);
  });
});

describe("a members path built by clicking", () => {
  it("writes a property for one hop and a list for a sequence", () => {
    const place = members("expansion");
    const one = click(bare, place, forward("refinances"));
    expect(one.value(at("expansion"), SRF("membersPath"))).toBe(at("refinances"));
    const two = click(one, place, forward("hasDrawdown"));
    const root = two.object(at("expansion"), SRF("membersPath"))!;
    expect(two.list(root)?.map((t) => t.value)).toEqual([at("refinances"), at("hasDrawdown")]);
    expect(readHops(two, root)).toEqual([forward("refinances"), forward("hasDrawdown")]);
    expect(two.toTurtle()).toBe(writeMembersPath(bare, at("expansion"), [forward("refinances"), forward("hasDrawdown")]).toTurtle());
  });

  it("writes sh:inversePath for an inverse hop", () => {
    const place = members("expansion");
    const g = click(click(bare, place, forward("refinances")), place, inverse("drawnUnder"));
    const root = g.object(at("expansion"), SRF("membersPath"))!;
    const second = g.list(root)![1];
    expect(g.value(second, SH("inversePath"))).toBe(at("drawnUnder"));
    expect(readHops(g, root)).toEqual([forward("refinances"), inverse("drawnUnder")]);
  });

  it("writes sh:oneOrMorePath and sh:zeroOrMorePath around the hop a closure is set on, and takes it off", () => {
    const place = members("expansion");
    const one = click(bare, place, forward("refinances"));
    const plus = setClosure(one, place, 0, "+");
    expect(plus.value(plus.object(at("expansion"), SRF("membersPath"))!, SH("oneOrMorePath"))).toBe(at("refinances"));
    expect(readPlace(plus, place).hops).toEqual([{ ...forward("refinances"), closure: "+" }]);
    const star = setClosure(plus, place, 0, "*");
    expect(star.value(star.object(at("expansion"), SRF("membersPath"))!, SH("zeroOrMorePath"))).toBe(at("refinances"));
    expect(star.value(star.object(at("expansion"), SRF("membersPath"))!, SH("oneOrMorePath"))).toBeUndefined();
    const none = setClosure(star, place, 0, undefined);
    expect(none.value(at("expansion"), SRF("membersPath"))).toBe(at("refinances"));
    // The closure of one hop of a sequence leaves the others, and wraps an inverse hop around its inverse.
    const seq = setClosure(click(click(bare, place, forward("refinances")), place, inverse("drawnUnder")), place, 1, "+");
    expect(readHops(seq, seq.object(at("expansion"), SRF("membersPath"))!)).toEqual([forward("refinances"), { ...inverse("drawnUnder"), closure: "+" }]);
  });

  it("writes out a named source as the path it stands for, in place of it, on the first edit", () => {
    const place = members("stated");
    expect(readPlace(bare, place).hops).toEqual([forward("covenants"), { property: RDF("rest"), inverse: false, closure: "*" }, { property: RDF("first"), inverse: false }]);
    const g = setClosure(bare, place, 0, "+");
    expect(g.value(at("stated"), SRF("expansionSource"))).toBeUndefined();
    const root = g.object(at("stated"), SRF("membersPath"))!;
    expect(readHops(g, root)).toEqual([{ ...forward("covenants"), closure: "+" }, { property: RDF("rest"), inverse: false, closure: "*" }, { property: RDF("first"), inverse: false }]);
  });

  it("adds a closure to the facility's refinancing expansion, which states the property one or more times", () => {
    const place = members("fr-expansion");
    expect(readPlace(surface, place).hops).toEqual([{ ...forward("refinances"), closure: "+" }]);
    const star = setClosure(surface, place, 0, "*");
    expect(star.value(at("fr-expansion"), SRF("expansionSource"))).toBeUndefined();
    expect(drawContract(star, at("facility-refinancing-projection"), { label: (i) => i.split("#")[1], range: () => undefined, domain: () => undefined, isClass: () => false, declared: () => false, rangesOf: () => [] }).edges.find((e) => e.kind === "hop")).toMatchObject({ label: "refinances *", closure: "*" });
  });

  it("undoes the last hop, and removes the path with the first", () => {
    const place = members("expansion");
    const two = click(click(bare, place, forward("refinances")), place, forward("hasDrawdown"));
    const one = undoHop(two, place);
    expect(one.value(at("expansion"), SRF("membersPath"))).toBe(at("refinances"));
    const none = undoHop(one, place);
    expect(none.objects(at("expansion"), SRF("membersPath"))).toEqual([]);
    expect(none.toTurtle()).toBe(bare.toTurtle());
  });

  it("offers a closure to a members path only", () => {
    const g = click(bare, read("promotion"), forward("borrower"));
    expect(setClosure(g, read("promotion"), 0, "+").toTurtle()).toBe(g.toTurtle());
  });
});

describe("undo", () => {
  it("removes the last hop of a read path, and the whole path with the first", () => {
    const place = read("promotion");
    const two = click(click(bare, place, forward("borrower")), place, inverse("borrower"));
    const one = undoHop(two, place);
    expect(one.toTurtle()).toBe(writePath(bare, at("promotion"), [forward("borrower")]).toTurtle());
    expect(one.value(at("promotion"), SRF("readProperty"))).toBe(at("borrower"));
    expect(undoHop(one, place).toTurtle()).toBe(bare.toTurtle());
  });
});

describe("the properties a next hop may be", () => {
  const labels = (list: { label: string }[]) => list.map((o) => o.label);

  it("offers a class's properties going out and coming in, with where each leads", () => {
    const { forward: out, inverse: into } = optionsAt(ontology, at("Facility"));
    expect(labels(out.filter((o) => o.group === "class"))).toEqual(expect.arrayContaining(["arranged by", "borrower", "commitment", "facility reference", "has drawdown", "lender", "margin"]));
    expect(out.find((o) => o.label === "borrower")).toMatchObject({ inverse: false, leads: { kind: "class", iri: at("Borrower") }, group: "class", unknownClass: false });
    expect(out.find((o) => o.label === "commitment")?.leads).toEqual({ kind: "value", datatype: "http://www.w3.org/2001/XMLSchema#decimal" });
    // Coming in to a facility: a drawdown is drawn under it, and a datatype property is never one.
    expect(into.find((o) => o.label === "drawn under")).toMatchObject({ inverse: true, leads: { kind: "class", iri: at("Drawdown") } });
    expect(into.some((o) => o.label === "commitment")).toBe(false);
  });

  it("offers a property of a class above, as its subclass has it", () => {
    expect(labels(optionsAt(ontology, at("Borrower")).forward)).toEqual(expect.arrayContaining(["legal name", "borrower sector"]));
  });

  it("ends the path at a datatype property", () => {
    const place = read("promotion");
    const g = click(click(bare, place, forward("borrower")), place, forward("legalName"));
    const path = readPlace(g, place).hops;
    expect(reachedAfter(ontology, at("Facility"), path)).toEqual({ at: undefined, value: true });
    // No further hop is taken from a value.
    expect(click(g, place, forward("margin")).toTurtle()).toBe(g.toTurtle());
  });

  it("reaches a declared range going forward and a declared domain going back", () => {
    expect(reachedAfter(ontology, at("Facility"), [forward("borrower")]).at).toBe(at("Borrower"));
    expect(reachedAfter(ontology, at("Facility"), [inverse("drawnUnder")]).at).toBe(at("Drawdown"));
  });

  const loose = ontologyOf(Graph.parse(`
    @prefix owl: <http://www.w3.org/2002/07/owl#> . @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> . @prefix ex: <${EX}> .
    ex:A a owl:Class ; rdfs:label "A" . ex:B a owl:Class ; rdfs:label "B" .
    ex:toB a owl:ObjectProperty ; rdfs:label "to B" ; rdfs:domain ex:A ; rdfs:range ex:B .
    ex:anywhere a owl:ObjectProperty ; rdfs:label "anywhere" ; rdfs:range ex:B .
    ex:open a owl:ObjectProperty ; rdfs:label "open" ; rdfs:domain ex:A .
    ex:ofB a owl:ObjectProperty ; rdfs:label "of B" ; rdfs:domain ex:B ; rdfs:range ex:A .
  `), []);

  it("offers a property with no declared domain under any class, marked so", () => {
    const { forward: out } = optionsAt(loose, at("A"));
    expect(out.map((o) => [o.label, o.group])).toEqual([["open", "class"], ["to B", "class"], ["anywhere", "any"]]);
    expect(optionsAt(loose, at("B")).forward.map((o) => [o.label, o.group])).toEqual([["of B", "class"], ["anywhere", "any"]]);
  });

  it("offers a property with no declared range, which leads to a class that is not known", () => {
    expect(optionsAt(loose, at("A")).forward.find((o) => o.label === "open")).toMatchObject({ leads: { kind: "unknown" }, group: "class" });
    // Going back, a property with no range could point at any class, so it is offered of any.
    expect(optionsAt(loose, at("A")).inverse.map((o) => [o.label, o.group])).toEqual([["of B", "class"], ["open", "any"]]);
  });

  it("offers every property, marked so, where the class reached is not known", () => {
    expect(reachedAfter(loose, at("A"), [forward("open")]).at).toBeUndefined();
    const { forward: out, inverse: into } = optionsAt(loose, undefined);
    expect(out.map((o) => o.label)).toEqual(["anywhere", "of B", "open", "to B"]);
    expect(out.every((o) => o.unknownClass && o.group === "any")).toBe(true);
    expect(into.every((o) => o.unknownClass)).toBe(true);
    // A property the ontology does not declare reaches no known class either.
    expect(reachedAfter(loose, at("A"), [forward("nowhere")]).at).toBeUndefined();
  });
});

