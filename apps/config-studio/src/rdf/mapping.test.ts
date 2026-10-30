// SPDX-License-Identifier: MPL-2.0
// The mapping part and the mapping view's model, read from the studio's ODRL mapping pack.

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { Graph, MORK, localName } from "@lattice/authoring-domain";
import { kindOf, sectionsFor } from "./editors";
import { Vocabulary } from "./vocabulary";
import { reviewGraph, schemesOf, setParent, setSource, unlink } from "./mapping";
import { split } from "./split";

const OM = "https://www.nebularis.org/neuro-semantic/lattice/config-studio/odrl-mapping#";
const pack = readFileSync(join(import.meta.dirname, "../../../../contracts/config-studio/odrl/odrl-instrument.mork.ttl"), "utf-8");
const parts = split(Graph.parse(pack));

describe("the mapping part", () => {
  it("takes the scheme, its mappings, its source concepts and the guards its mappings name", () => {
    for (const local of ["Scheme", "Constraint_Required", "ConstraintConcept", "NotEqual", "Comparison"]) expect(parts.mapping.has(OM + local), local).toBe(true);
    expect(parts.meaning.size + parts.eligibility.size + parts.quantification.size).toBe(0);
  });
});

describe("a scheme as a tree", () => {
  const [scheme] = schemesOf(parts.mapping);
  const at = (local: string) => scheme.mappings.find((m) => m.iri === OM + local)!;

  it("lists every mapping once, in depth-first order, each under its parent", () => {
    expect(schemesOf(parts.mapping)).toHaveLength(1);
    expect(new Set(scheme.mappings.map((m) => m.iri)).size).toBe(scheme.mappings.length);
    expect(scheme.mappings.map((m) => m.row)).toEqual(scheme.mappings.map((_, n) => n));
    for (const m of scheme.mappings.filter((m) => m.parent)) {
      const parent = at(m.parent!.slice(OM.length));
      expect(parent.row).toBeLessThan(m.row);
      expect(m.depth).toBe(parent.depth + 1);
    }
  });

  it("reads what a mapping writes, its guard and its template, and puts templates last among the roots", () => {
    expect(at("Constraint_Required")).toMatchObject({ parent: OM + "Constraint", guard: OM + "ConceptOperator", reads: "odrl:rightOperand" });
    expect(at("Upper").template).toBe(OM + "Bound_T");
    expect(at("Space_T").isTemplate).toBe(true);
    const roots = scheme.mappings.filter((m) => m.depth === 0);
    expect(roots.map((m) => m.isTemplate)).toEqual([...roots.map((m) => m.isTemplate)].sort((a, b) => Number(a) - Number(b)));
  });
});

describe("the mapping samples", () => {
  const assets = process.env.LATTICE_STUDIO_ASSETS ?? join(import.meta.dirname, "../../../../.build/config-studio");
  const sample = (id: string) => split(Graph.parse(readFileSync(join(assets, `samples/${id}.ttl`), "utf-8")));

  it("puts the trials' runs, schemes and reviews in the mapping part, each scheme named by its run where it has no label", () => {
    const lrml = sample("legalruleml-mappings");
    // Only the reviewer's description and an ontology header use no part's terms and are not a mapping's own structure.
    expect(lrml.baseline.quads().map((q) => q.subject.value).filter((v, n, all) => all.indexOf(v) === n).sort()).toEqual(["http://example.org/lrml-mapping", "urn:lattice:reviewer:agent-for-the-maintainer"]);
    expect(lrml.mapping.has("http://example.org/lrml-mapping#Map_InForce_mork:appliesWhen1_sh:property1")).toBe(true);
    const schemes = schemesOf(lrml.mapping);
    expect(schemes.map((s) => s.label).sort()).toEqual([
      "LegalRuleML deontic specifications to stated LATTICE relations",
      "LegalRuleML metamodel instances to stated meaning",
      "MS, proposed in legalruleml-cold",
    ]);
    // The scorer reviews every mapping but a template, which it reads through the mappings that use it.
    for (const s of schemes) expect(s.mappings.filter((m) => !m.review).map((m) => m.isTemplate)).not.toContain(false);
  });

  it("follows a narrower link to a child, and links a correction to the pack's mapping", () => {
    const schemes = schemesOf(sample("odrl-mappings").mapping);
    expect(schemes).toHaveLength(3); // the pack, then the trial's two runs
    const run = schemes.find((s) => s.label.endsWith("run-1"))!;
    expect(run.mappings.some((m) => m.depth > 0)).toBe(true);
    const corrected = run.mappings.find((m) => m.review?.decision === "Corrected")!;
    expect(corrected.review!.correctedBy!.startsWith(OM)).toBe(true);
  });
});

describe("a mapping's editor", () => {
  const assets = process.env.LATTICE_STUDIO_ASSETS ?? join(import.meta.dirname, "../../../../.build/config-studio");
  const vocab = Vocabulary.parse(readFileSync(join(assets, "vocabulary.ttl"), "utf-8"));
  const INS = "https://www.nebularis.org/neuro-semantic/lattice/instrument#";

  it("offers the layers' terms as targets, never MORK's or RDF's own", () => {
    const classes = vocab.targets("class").map((o) => o.iri);
    expect(classes).toContain(INS + "Obligation");
    expect(classes.some((c) => c.startsWith(MORK("")) || c.startsWith("http://www.w3.org/"))).toBe(false);
    expect(vocab.targets("property").map((o) => o.iri)).toContain(INS + "obligee");
    expect(vocab.targets("individual").map((o) => o.iri)).toContain("https://www.nebularis.org/neuro-semantic/lattice/eligibility#AllRequired");
  });

  it("groups a mapping's fields by what it reads, what it writes and where it sits, each typed for its use", () => {
    const g = Graph.parse(`<urn:x:m> a <${MORK("Datum")}> .`);
    const sections = sectionsFor(kindOf(g, "urn:x:m", "mapping")!, vocab);
    expect(sections.map((s) => s.title)).toEqual(["Reads", "Writes", "Structure"]);
    const kinds = Object.fromEntries(sections.flatMap((s) => s.fields).map((f) => [localName(f.property), f.kind]));
    expect(kinds).toMatchObject({ exactTBoxMatch: "targetClass", exactRBoxMatch: "targetProperty", exactABoxMatch: "targetIndividual", compositeBroaderMapping: "reference", appliesWhen: "reference", dataRef: "text" });
  });
});

describe("a proposal in the studio", () => {
  const P = "https://example.org/p#";
  const run = "urn:lattice:studio:job:1:run";
  const g = Graph.parse(`@prefix mork: <http://www.nebularis.org/ontologies/Mork#> . @prefix prov: <http://www.w3.org/ns/prov#> . @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
    <${P}S> a mork:MappingScheme . <${P}M> a mork:Datum ; mork:mappingScheme <${P}S> ; prov:wasGeneratedBy <${run}> .
    <${run}> a mork:ProposalRun ; mork:proposerModel "a model" ; mork:inputTokens 1200 ; mork:outputTokens 300 ;
      prov:startedAtTime "2026-10-30T03:00:00Z"^^xsd:dateTime ; prov:endedAtTime "2026-10-30T03:02:15Z"^^xsd:dateTime .`);

  it("names the scheme by its run and reads what the run cost", () => {
    const [scheme] = schemesOf(g);
    expect(scheme.run).toMatchObject({ model: "a model", inputTokens: 1200, outputTokens: 300, seconds: 135 });
    expect(scheme.mappings[0].generatedBy).toBe(run);
  });

  it("records a review made in the studio, the latest deciding", () => {
    const first = g.merge(reviewGraph(P + "M", "Corrected", "names an occupancy", "2026-10-30T04:00:00Z", 1));
    const second = first.merge(reviewGraph(P + "M", "Accepted", "", "2026-10-30T05:00:00Z", 2));
    expect(schemesOf(first)[0].mappings[0].review).toMatchObject({ decision: "Corrected", note: "names an occupancy" });
    expect(schemesOf(second)[0].mappings[0].review?.decision).toBe("Accepted");
  });
});

describe("editing a scheme on the canvas", () => {
  const P = "https://example.org/e#";
  const g = Graph.parse(`@prefix mork: <http://www.nebularis.org/ontologies/Mork#> .
    <${P}S> a mork:MappingScheme .
    <${P}A> a mork:Datum ; mork:mappingScheme <${P}S> ; mork:compositeNarrowerMapping <${P}B> .
    <${P}B> a mork:Datum ; mork:mappingScheme <${P}S> .
    <${P}C> a mork:DataMapping ; mork:mappingScheme <${P}S> ; mork:compositeBroaderMapping <${P}B> .
    <${P}K> a mork:DataConcept ; mork:path "ex:k" .`);
  const parent = (h: Graph, m: string) => schemesOf(h)[0].mappings.find((x) => x.iri === P + m)?.parent;

  it("makes a mapping another's one parent, whichever way the old link was written, and refuses a cycle", () => {
    const moved = setParent(g, P + "B", P + "C");
    expect(moved).toBeUndefined(); // C is beneath B
    const h = setParent(g, P + "C", P + "A")!;
    expect(parent(h, "C")).toBe(P + "A");
    const k = setParent(h, P + "B", P + "C")!;
    expect(parent(k, "B")).toBe(P + "C");
    expect(k.quads(null, "http://www.nebularis.org/ontologies/Mork#compositeNarrowerMapping")).toHaveLength(0);
  });

  it("links a mapping to the concept it maps for, and removes a link", () => {
    const h = setSource(g, P + "C", P + "K");
    expect(schemesOf(h)[0].mappings.find((x) => x.iri === P + "C")?.source).toBe(P + "K");
    expect(parent(unlink(g, "parent", P + "B"), "B")).toBeUndefined();
    expect(schemesOf(unlink(h, "source", P + "C"))[0].mappings.find((x) => x.iri === P + "C")?.source).toBeUndefined();
  });
});
