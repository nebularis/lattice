// SPDX-License-Identifier: MPL-2.0
// The surface canvas's pure part, over the facility sample's surface configuration and the compilation the worker's own test keeps in e2e/fixtures.

import { readFileSync } from "node:fs";
import { Graph, SRF } from "@lattice/authoring-domain";
import { describe, expect, it } from "vitest";
import type { Issue } from "../rdf/report";
import { fingerprint } from "../persistence/landing";
import { contractsOf, drawContract, drawContracts, targetId } from "./drawing";
import { infix, readExpression, expressionLine } from "./expression";
import { placeFindings } from "./findings";
import { boxesFor, readProjections, schemeOf, staleMark } from "./scheme";
import { ontologyOf, readTarget, termsOf } from "./terms";
import type { Job } from "../rdf/report";

const sample = (n: string) => Graph.parse(readFileSync(new URL(`../../../../contracts/config-studio/samples/${n}`, import.meta.url), "utf-8"));
const surface = sample("facility-surface.ttl");
const baseline = sample("lending-baseline.ttl").merge(sample("facility-baseline.ttl"));
const terms = termsOf(ontologyOf(baseline, []));
const EX = "https://example.org/lending#";
const at = (n: string) => `${EX}${n}`;
const draw = (n: string) => drawContract(surface, at(n), terms);
const labels = (d: { edges: { label?: string }[] }) => d.edges.map((e) => e.label).filter(Boolean);
const titles = (d: { nodes: { title: string; kind: string }[] }, kind: string) => d.nodes.filter((n) => n.kind === kind).map((n) => n.title);

describe("the drawing of each kind of contract", () => {
  it("lists the contracts, promotions first", () => {
    expect(contractsOf(surface).map((c) => [c.kind, c.name])).toEqual([
      ["promotion", "drawdown-sector"], ["index", "borrower-sector"], ["projection", "borrower-exposure"], ["projection", "drawdown-schedule"],
      ["projection", "facility-branch"], ["projection", "facility-covenant-test"], ["projection", "facility-margin"], ["projection", "facility-refinancing"],
    ]);
  });

  it("draws a promotion as each hop of its read path to the promoted property", () => {
    const d = draw("drawdown-sector-promotion");
    expect(d.kind).toBe("promotion");
    expect(labels(d)).toEqual(["drawn under", "borrower", "borrower sector"]);
    expect(titles(d, "class")).toEqual(["Facility", "Borrower"]);
    expect(d.targets.map((t) => t.iri)).toEqual(["https://example.org/lending/exec#drawdownSector"]);
  });

  it("marks an inverse hop", () => {
    const g = surface.edit((e) => e.setAll(at("drawdown-sector-step-1"), SRF("stepDirection"), [{ termType: "NamedNode", value: SRF("Inverse") } as never]));
    const d = drawContract(g, at("drawdown-sector-promotion"), terms);
    expect(labels(d)[1]).toBe("← borrower");
    expect(d.edges.find((e) => e.inverse)?.title).toContain("inversely");
  });

  it("draws an index with its path and what it makes", () => {
    const d = draw("borrower-sector-index");
    expect(labels(d)).toEqual(["borrower sector"]);
    expect(d.nodes.find((n) => n.kind === "entries")?.lines).toEqual([
      "forms: closure relation, membership assertion, nominal class", "closure over broader", "population: the members of the scheme SectorContract resolves to",
    ]);
  });

  it("draws a derivation with its expression on the result edge, required evidence solid", () => {
    const d = draw("facility-margin-projection");
    expect(d.kind).toBe("derivation");
    expect(titles(d, "evidence")).toEqual(["commitment", "margin"]);
    expect(d.edges.filter((e) => e.kind === "read").map((e) => e.dashed)).toEqual([false, false]);
    expect(d.targets[0]).toMatchObject({ iri: at("marginWeightedCommitment"), stated: "http://www.w3.org/2001/XMLSchema#decimal", edge: { label: "commitment × margin : decimal" } });
  });

  it("draws a construction with its class, identity and each value joined to the binding it is written from", () => {
    const d = draw("drawdown-schedule-projection");
    const box = d.nodes.find((n) => n.kind === "statement")!;
    expect(box.title).toBe("RepaymentSchedule");
    expect(box.lines).toEqual(["identity: for each instance", "scheduledAmount ← drawn amount", "scheduleStart ← drawdown date"]);
    expect(d.edges.filter((e) => e.kind === "write" && e.target === box.id).map((e) => e.label)).toEqual(["hasSchedule", "scheduledAmount", "scheduleStart"]);
    expect(d.targets.map((t) => [t.kind, t.iri.split("#")[1]])).toEqual([["class", "RepaymentSchedule"], ["property", "hasSchedule"], ["property", "scheduledAmount"], ["property", "scheduleStart"]]);
    expect(draw("borrower-exposure-projection").nodes.find((n) => n.kind === "statement")!.lines[0]).toBe("identity: by key (borrower)");
  });

  it("draws a join with a box for the second carrier, the key pair and the two cardinality rules", () => {
    const d = draw("facility-branch-projection");
    expect(d.kind).toBe("join");
    expect(d.nodes.filter((n) => n.kind === "carrier").map((n) => [n.tag, n.title])).toEqual([["Join", "Facility"], ["Second carrier", "Branch"]]);
    expect(d.edges.find((e) => e.kind === "key")?.label).toBe("=");
    expect(d.nodes.find((n) => n.kind === "statement")!.lines).toEqual(["one value finds: at most one", "one instance links: any number (default)"]);
  });

  it("draws an expansion as its members path with the closure on its hop, dashed for candidate evidence", () => {
    const d = draw("facility-refinancing-projection");
    expect(d.kind).toBe("expansion");
    const hop = d.edges.find((e) => e.kind === "hop")!;
    expect(hop).toMatchObject({ label: "refinances +", closure: "+", dashed: true });
    expect(d.targets[0].iri).toBe(at("refinancesInChain"));
  });

  it("draws a node for each member with the list path, the node's identity and what it writes from the member", () => {
    const d = draw("facility-covenant-test-projection");
    expect(d.kind).toBe("member");
    expect(labels(d).slice(0, 3)).toEqual(["covenants", "rdf:rest *", "rdf:first"]);
    expect(d.edges.find((e) => e.label === "rdf:rest *")?.closure).toBe("*");
    const box = d.nodes.find((n) => n.kind === "statement")!;
    expect(box.lines).toEqual(["identity: by key (facility reference, the member)", "testedFacilityReference ← facility reference", "testsCovenant ← the member"]);
    expect(titles(d, "class")).toEqual(["list", "list", "member"]);
  });

  it("draws a contract that states nothing yet, with placeholders and no failure", () => {
    const bare = Graph.parse(`@prefix srf: <${SRF("")}> . @prefix ex: <${EX}> . ex:p a srf:ProjectionContract ; srf:carrier ex:Facility ; srf:projectionKind srf:ExpansionProjection . ex:q a srf:PromotionContract .`);
    for (const c of ["p", "q"]) expect(() => drawContract(bare, at(c), terms)).not.toThrow();
    expect(drawContract(bare, at("q"), terms).edges[0].label).toBe("no read path");
    expect(drawContracts(bare, [at("p"), at("q")], terms).nodes.filter((n) => n.kind === "target").map((n) => n.title)).toEqual(["…", "…"]);
  });

  it("shares a target between contracts that write the same term, on the right", () => {
    const twice = surface.merge(Graph.parse(`@prefix srf: <${SRF("")}> . @prefix ex: <${EX}> . ex:p2 a srf:PromotionContract ; srf:carrier ex:Drawdown ; srf:readProperty ex:drawnUnder ; srf:promotesTo <https://example.org/lending/exec#drawdownSector> .`));
    const all = drawContracts(twice, [at("drawdown-sector-promotion"), at("p2")], terms);
    const id = targetId("property", "https://example.org/lending/exec#drawdownSector");
    expect(all.nodes.filter((n) => n.id === id)).toHaveLength(1);
    expect(all.edges.filter((e) => e.target === id)).toHaveLength(2);
    expect(all.nodes.find((n) => n.id === id)!.rank).toBe(all.targetRank);
  });
});

describe("an expression as one line of infix text", () => {
  const g = (body: string) => Graph.parse(`@prefix srf: <${SRF("")}> . @prefix ex: <${EX}> . @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
    ex:a a srf:ProjectionRoleBinding ; srf:bindsProperty ex:commitment . ex:b a srf:ProjectionRoleBinding ; srf:bindsProperty ex:margin . ${body}`);
  const text = (body: string) => infix(readExpression(g(body), at("e"), (i) => terms.label(i)));

  it("writes each kind, with brackets only where precedence needs them", () => {
    expect(text(`ex:e a srf:SumExpression ; srf:leftOperand ex:a ; srf:rightOperand ex:b .`)).toBe("commitment + margin");
    expect(text(`ex:e a srf:ProductExpression ; srf:leftOperand ex:s ; srf:rightOperand ex:b . ex:s a srf:SumExpression ; srf:leftOperand ex:a ; srf:rightOperand ex:b .`)).toBe("(commitment + margin) × margin");
    expect(text(`ex:e a srf:SumExpression ; srf:leftOperand ex:a ; srf:rightOperand ex:s . ex:s a srf:ProductExpression ; srf:leftOperand ex:a ; srf:rightOperand ex:b .`)).toBe("commitment + commitment × margin");
    expect(text(`ex:e a srf:DifferenceExpression ; srf:leftOperand ex:a ; srf:rightOperand ex:s . ex:s a srf:DifferenceExpression ; srf:leftOperand ex:a ; srf:rightOperand ex:b .`)).toBe("commitment − (commitment − margin)");
    expect(text(`ex:e a srf:QuotientExpression ; srf:leftOperand ex:s ; srf:rightOperand ex:b . ex:s a srf:QuotientExpression ; srf:leftOperand ex:a ; srf:rightOperand ex:b .`)).toBe("commitment ÷ margin ÷ margin");
    expect(text(`ex:e a srf:RoundingExpression ; srf:roundedOperand ex:s ; srf:roundingScale 2 . ex:s a srf:ProductExpression ; srf:leftOperand ex:a ; srf:rightOperand ex:b .`)).toBe("round(commitment × margin, 2)");
    expect(text(`ex:e a srf:SumExpression ; srf:leftOperand ex:a ; srf:rightOperand ex:t . ex:t a srf:TypedLiteralExpression ; srf:typedValue "1.5"^^xsd:decimal .`)).toBe("commitment + 1.5");
    expect(text(`ex:e a srf:ChoiceExpression ; srf:comparisonOperator srf:LessThan ; srf:comparedLeft ex:a ; srf:comparedRight ex:b ; srf:whenTrue ex:a ; srf:whenFalse ex:s . ex:s a srf:SumExpression ; srf:leftOperand ex:a ; srf:rightOperand ex:b .`)).toBe("commitment < margin ? commitment : commitment + margin");
  });

  it("gives the line with its datatype, and a placeholder where a part is missing", () => {
    const body = `ex:e a srf:RoundingExpression ; srf:roundedOperand ex:s ; srf:roundingScale 2 ; srf:resultDatatype xsd:decimal . ex:s a srf:ProductExpression ; srf:leftOperand ex:a ; srf:rightOperand ex:b .`;
    expect(expressionLine(readExpression(g(body), at("e"), (i) => terms.label(i)))).toBe("round(commitment × margin, 2) : decimal");
    expect(text(`ex:e a srf:ProductExpression ; srf:leftOperand ex:a .`)).toBe("commitment × …");
    expect(text(`ex:e a srf:RoundingExpression ; srf:roundedOperand ex:a .`)).toBe("round(commitment, …)");
    expect(text(`ex:e a srf:SumExpression ; srf:leftOperand ex:e ; srf:rightOperand ex:a .`)).toBe("… + commitment");
    expect(expressionLine(readExpression(g(""), undefined, (i) => i))).toBe("… : …");
  });

  it("draws an incomplete derivation of a contract without failing", () => {
    const d = surface.edit((e) => e.remove(at("fm-expression")));
    expect(drawContract(d, at("facility-margin-projection"), terms).targets[0].edge.label).toBe("… : decimal");
  });
});

describe("the findings on the canvas", () => {
  const all = drawContracts(surface, contractsOf(surface).map((c) => c.iri), terms);
  const issue = (focus: string | undefined, path?: string): Issue => ({ severity: "Warning", message: "m", focus, path, source: "studio" });
  const where = (i: Issue) => [...placeFindings(all, [i]).byElement.keys()];

  it("places a finding by its focus node and path", () => {
    expect(where(issue(at("fm-target"), SRF("bindsProperty")))).toEqual([`${at("facility-margin-projection")}|e|target|${at("facility-margin-projection")}|carrier|${targetId("property", at("marginWeightedCommitment"))}`]);
    expect(where(issue(at("fm-commitment"), SRF("bindsProperty")))).toEqual([`${at("facility-margin-projection")}|ev|${at("fm-commitment")}`]);
    expect(where(issue(at("fm-commitment"), SRF("roleKind")))).toEqual([`${at("facility-margin-projection")}|e|read|${at("fm-commitment")}`]);
    expect(where(issue(at("fm-expression")))).toHaveLength(1);
    expect(where(issue(at("drawdown-sector-step-1"), SRF("stepProperty")))).toEqual([`${at("drawdown-sector-promotion")}|e|hop|1`]);
  });

  it("places a finding on the contract on its carrier, and keeps one it cannot place for the form", () => {
    expect(where(issue(at("facility-margin-projection")))).toEqual([`${at("facility-margin-projection")}|carrier`]);
    const found = placeFindings(all, [issue(at("nowhere")), issue(undefined)]);
    expect(found.byElement.size).toBe(0);
    expect(found.unplaced).toHaveLength(2);
  });
});

describe("the targets as types", () => {
  const declared = termsOf(ontologyOf(baseline, []));
  it("reads a declared property's range and marks an undeclared one", () => {
    expect(readTarget(declared, "property", at("commitment"))).toMatchObject({ declared: true, ranges: ["decimal"], disagrees: false });
    expect(readTarget(declared, "property", at("marginWeightedCommitment"))).toMatchObject({ declared: false, ranges: [] });
    expect(readTarget(declared, "class", at("Facility"))).toMatchObject({ declared: true, label: "Facility" });
    expect(drawContracts(surface, [at("facility-margin-projection")], declared).nodes.find((n) => n.kind === "target")!.lines).toEqual(["not declared in the ontology"]);
  });

  it("marks where the declared range disagrees with the datatype the contract states", () => {
    const t = readTarget(declared, "property", at("commitment"), ["http://www.w3.org/2001/XMLSchema#string"]);
    expect(t).toMatchObject({ disagrees: true, stated: ["string"] });
    expect(readTarget(declared, "property", at("commitment"), ["http://www.w3.org/2001/XMLSchema#decimal"]).disagrees).toBe(false);
  });

  it("reads a term an import declares as declared", () => {
    const imported = Graph.parse(`@prefix owl: <http://www.w3.org/2002/07/owl#> . @prefix ex: <${EX}> . ex:marginWeightedCommitment a owl:DatatypeProperty .`);
    expect(termsOf(ontologyOf(baseline, [imported])).declared("property", at("marginWeightedCommitment"))).toBe(true);
  });
});

describe("the lowered scheme", () => {
  const fixture = JSON.parse(readFileSync(new URL("../../e2e/fixtures/compiled-surface-facility.json", import.meta.url), "utf-8")) as { artefacts: Job["artefacts"] };
  const job = { artefacts: fixture.artefacts } as Job;
  const projections = readProjections(job)!;

  it("reads each scheme's name, mappings and review findings from the projections group and its manifest", () => {
    const box = boxesFor(projections, "current");
    expect(box(at("facility-margin-projection"))).toMatchObject({ title: "scheme_facility-margin", state: "ready", lines: ["2 mappings", "DerivationReview × 1"] });
    expect(box(at("facility-covenant-test-projection"))?.lines).toEqual(["4 mappings", "ExpansionReview × 1", "MappingReview × 1"]);
    expect(box(at("drawdown-schedule-projection"))?.lines).toEqual(["4 mappings", "no review findings"]);
    expect(box(at("nowhere"))).toMatchObject({ state: "absent" });
  });

  it("says so where there is no compilation, and reads no group where a compilation holds none", () => {
    expect(boxesFor("none", "unknown")(at("facility-margin-projection"))).toMatchObject({ state: "none", lines: ["no compilation yet"] });
    expect(readProjections({ artefacts: [] } as unknown as Job)).toBeUndefined();
  });

  it("is marked stale when the surface part or the baseline changed since the compilation", () => {
    const sent = fingerprint(surface.toTurtle(), "1");
    expect(staleMark(sent, fingerprint(surface.toTurtle(), "1"))).toBe("current");
    expect(staleMark(sent, fingerprint(surface.toTurtle(), "2"))).toBe("out-of-date");
    expect(staleMark(sent, fingerprint(surface.edit((e) => e.remove(at("fm-margin"))).toTurtle(), "1"))).toBe("out-of-date");
    expect(staleMark(undefined, sent)).toBe("unknown");
    expect(boxesFor(projections, "out-of-date")(at("facility-margin-projection"))!.stale).toBe(true);
  });

  it("gives the mapping canvas the scheme's mappings and how they nest", () => {
    const { scheme, describe } = schemeOf(projections.schemes.find((s) => s.key === "facility-branch")!);
    expect(scheme.mappings.map((m) => [m.label, m.depth])).toEqual([["root", 0], ["node", 1]]);
    expect(describe(scheme.mappings[1].iri)).toContain("MappingReview");
  });
});

