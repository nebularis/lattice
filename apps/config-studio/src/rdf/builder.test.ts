// SPDX-License-Identifier: MPL-2.0
// The contract builder's model (rdf/builder.ts) and the split rule for its two parts, against the
// facility form and assemblies the builder sample stages (`mise run build:config-studio-assets`).

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { CST, ELG, Graph, INS, PTY, QNT, SKOS, VOC, WRD, XSD } from "@lattice/authoring-domain";
import { addAssembly, assembliesOf, choicesMade, choicesOf, flatten, formsOf, outline, removeAssembly, setForm, settableOf, settingsMade, toggleChoice, writeSetting } from "./builder";
import { CONFIG_PARTS, split } from "./split";

const assets = process.env.LATTICE_STUDIO_ASSETS ?? join(import.meta.dirname, "../../../../.build/config-studio");
const sample = () => Graph.parse(readFileSync(join(assets, "samples/builder.ttl"), "utf-8"));

const F = "https://example.org/lattice/wording/facility-form/";
const A = "https://example.org/lattice/studio/assembly/";
const NS = "https://example.org/lattice/studio/";

const prefixes = `@prefix wrd: <${WRD("")}> . @prefix cst: <${CST("")}> . @prefix xsd: <${XSD("")}> . @prefix ex: <https://example.org/x/> .\n`;
const parse = (ttl: string) => Graph.parse(prefixes + ttl);

describe("the split rule for library and assembly", () => {
  it("keeps the configuration parts in the service's order", () => {
    expect(CONFIG_PARTS).toEqual(["library", "assembly", "meaning", "review", "vocabulary", "quantification", "eligibility", "surface", "persistence"]);
  });

  it("sorts the builder sample into library, assembly and the layers a form reads", () => {
    const parts = split(sample());
    expect(parts.library.types(F + "form")).toContain(WRD("Wording"));
    expect(parts.library.has(F + "cl-5-2b")).toBe(true);
    expect(parts.library.has(F + "gv-lender-count")).toBe(true);
    // A text part written as a blank node stays with its element.
    expect(parts.library.quads(F + "cl-5-1").some((q) => q.predicate.value === WRD("hasTextPart") && q.object.termType === "BlankNode")).toBe(true);
    expect(parts.library.quads().filter((q) => q.subject.termType === "BlankNode").length).toBeGreaterThan(0);
    expect(parts.assembly.ofType(CST("Assembly")).map((a) => a.value).sort()).toEqual([A + "syndicated", A + "unsettled"]);
    // The sample's own assembled wording uses Wording's terms, but its value records are an assembly's.
    expect(parts.assembly.types(F + "v-lender-count")).toEqual([WRD("VariableValue")]);
    expect(parts.library.has(F + "v-lender-count")).toBe(false);
    expect(parts.eligibility.types(F + "more-than-one-lender")).toContain(ELG("IntervalCondition"));
    expect(parts.quantification.types(F + "count-space")).toContain(QNT("ValueSpace"));
    expect(parts.vocabulary.types(F + "uk")).toContain(SKOS("Concept"));
    expect(parts.vocabulary.types(F + "jurisdiction-contract")).toContain(VOC("SchemeContract"));
    // The roles are the party layer's, so they stay with the baseline, and a proposal and its terms are meaning and review.
    expect(parts.baseline.ofType(PTY("Role")).length).toBe(3);
    expect(parts.baseline.quads().every((q) => q.subject.value.startsWith("https://example.org/lattice/studio/roles/"))).toBe(true);
    expect(parts.meaning.types("https://example.org/lattice/studio/meaning/pay-interest")).toContain(INS("Obligation"));
    expect(parts.review.ofType(CST("Proposal")).length).toBe(3);
    expect(parts.review.has("https://example.org/lattice/studio/meaning/pay-interest")).toBe(false);
  });

  it("sends a proposal to review, and a subject using ins: terms to meaning, before the layers", () => {
    const parts = split(
      parse(`
        @prefix ins: <${INS("")}> .
        ex:p cst:proposes ex:t ; cst:payload "x" .
        ex:typed a cst:Proposal .
        ex:t a ins:Term , ins:Template ; ins:expressedIn ex:clause .
        ex:r ins:arisesUnder ex:t .
        ex:clause a wrd:Text .
      `),
    );
    expect(parts.review.has("https://example.org/x/p")).toBe(true);
    expect(parts.review.has("https://example.org/x/typed")).toBe(true);
    expect(parts.meaning.has("https://example.org/x/t")).toBe(true);
    expect(parts.meaning.has("https://example.org/x/r")).toBe(true);
    expect(parts.library.has("https://example.org/x/clause")).toBe(true);
    expect(parts.baseline.size).toBe(0);
  });

  it("sends a value record that uses Wording's terms to assembly, typed or not", () => {
    const parts = split(
      parse(`
        ex:typed a wrd:VariableValue ; wrd:forVariable ex:v ; wrd:value ex:a , ex:b .
        ex:untyped wrd:forVariable ex:v ; wrd:literalValue "3"^^xsd:decimal .
        ex:form a wrd:Wording ; wrd:directlyComprises ex:v .
        ex:v a wrd:GoverningVariable ; wrd:variableKey "k" .
        ex:ask cst:assembles ex:form .
      `),
    );
    expect(parts.assembly.has("https://example.org/x/typed")).toBe(true);
    expect(parts.assembly.has("https://example.org/x/untyped")).toBe(true);
    expect(parts.assembly.has("https://example.org/x/ask")).toBe(true);
    expect(parts.library.has("https://example.org/x/form")).toBe(true);
    expect(parts.library.has("https://example.org/x/v")).toBe(true);
    expect(parts.library.has("https://example.org/x/typed")).toBe(false);
  });

  it("sends a blank-node value to the part of the subject that refers to it", () => {
    const parts = split(parse(`ex:set cst:assembles ex:form ; cst:setting [ a wrd:VariableValue ; wrd:forVariable ex:v ; wrd:literalValue "x" ] .`));
    expect(parts.assembly.size).toBe(5);
  });
});

describe("the outline of a form", () => {
  const world = sample();
  const form = outline(world, F + "form");
  const byId = (id: string) => flatten(form.elements).find((n) => n.objectId === id)!;

  it("finds the forms of the library, never an assembled wording", () => {
    expect(formsOf(world)).toEqual([F + "form"]);
  });

  it("orders siblings by rank key, then object id, and not by the order they are written", () => {
    expect(form.elements.map((e) => e.objectId)).toEqual(["5", "9", "12"]);
    expect(byId("5").children.map((e) => e.objectId)).toEqual(["5.1", "5.2", "5.3"]);
    const shuffled = outline(
      parse(`
        ex:f a wrd:Wording ; wrd:directlyComprises ex:c , ex:a , ex:b , ex:n .
        ex:a a wrd:Text ; wrd:objectId "2" ; wrd:rankKey "b" .
        ex:b a wrd:Text ; wrd:objectId "10" ; wrd:rankKey "b" .
        ex:c a wrd:Text ; wrd:objectId "1" ; wrd:rankKey "z" .
        ex:n a wrd:Text ; wrd:objectId "0" .
      `),
      "https://example.org/x/f",
    );
    // "b" before "z", ties by object id read as numbers, and an element with no rank key last.
    expect(shuffled.elements.map((e) => e.objectId)).toEqual(["2", "10", "1", "0"]);
  });

  it("shows a variation slot with its variants, ordered by object id and not ranked", () => {
    const slot = byId("5.2");
    expect(slot.slot).toBe(true);
    expect(slot.children.map((v) => [v.objectId, v.variant, v.mode])).toEqual([
      ["5.2A", true, "Variation"],
      ["5.2B", true, "Variation"],
    ]);
    expect(slot.children[1].text).toBe("Each interest period is three months.");
    expect(byId("5.1").variant).toBe(false);
  });

  it("reads the inclusion mode, Mandatory when absent", () => {
    expect(byId("5.1").mode).toBe("Mandatory");
    expect(byId("5").mode).toBe("Mandatory");
    expect(byId("5.3").mode).toBe("Optional");
    expect(byId("9.1").mode).toBe("Conditional");
  });

  it("shows the admission profile of a condition and the variable it reads", () => {
    expect(byId("9.1").condition).toEqual({ iri: F + "when-syndicated", name: "when syndicated", reads: [F + "gv-lender-count"] });
    expect(byId("5.3").condition).toBeUndefined();
  });

  it("shows a variable where the text shows it, and leaves it out of the element tree", () => {
    expect(byId("12.1").text).toBe("The borrower may operate in {permitted-jurisdictions}");
    expect(flatten(form.elements).some((e) => e.iri === F + "var-jurisdictions")).toBe(false);
    expect(form.variables.map((v) => [v.key, v.governing, v.multiValued])).toEqual([
      ["lender-count", true, false],
      ["permitted-jurisdictions", false, true],
    ]);
  });
});

describe("what an assembly chooses and sets", () => {
  const world = sample();
  const form = outline(world, F + "form");

  it("offers each Optional element and each variant without a condition, not a Conditional element", () => {
    expect(choicesOf(form).map((c) => [c.objectId, c.kind, c.slot])).toEqual([
      ["5.2A", "variant", F + "slot-5-2"],
      ["5.2B", "variant", F + "slot-5-2"],
      ["5.3", "optional", undefined],
    ]);
  });

  it("offers a variant that has a condition no choice", () => {
    const f = outline(
      parse(`
        ex:f a wrd:Wording ; wrd:directlyComprises ex:s .
        ex:s a wrd:VariationSlot ; wrd:objectId "1" ; wrd:rankKey "a" ; wrd:hasVariant ex:v1 , ex:v2 .
        ex:v1 a wrd:Text ; wrd:objectId "1A" ; wrd:inclusionMode <${WRD("")}> .
        ex:v2 a wrd:Text ; wrd:objectId "1B" ; wrd:includedWhen ex:p .
      `),
      "https://example.org/x/f",
    );
    expect(choicesOf(f).map((c) => c.objectId)).toEqual(["1A"]);
  });

  it("offers a value for each governing variable a condition reads and each embedded variable the text shows", () => {
    expect(settableOf(world, form).map((v) => v.key)).toEqual(["lender-count", "permitted-jurisdictions"]);
  });

  it("reads an assembly's choices and settings", () => {
    const graph = split(world).assembly;
    // By label, so "No lender count yet" comes before "Syndicated, ...".
    expect(assembliesOf(graph)).toEqual([A + "unsettled", A + "syndicated"]);
    expect([...choicesMade(graph, A + "syndicated")]).toEqual([F + "cl-5-2b"]);
    const settings = settingsMade(graph, A + "syndicated");
    // The staged sample is serialised, which writes the decimal 3 as 3.0.
    expect(settings.get(F + "gv-lender-count")).toMatchObject({ record: A + "syndicated-lenders", values: [], literals: [expect.stringMatching(/^3(\.0)?$/)] });
    expect(settings.get(F + "var-jurisdictions")!.values.sort()).toEqual([F + "ie", F + "uk"]);
  });
});

describe("writing an assembly", () => {
  const world = sample();
  const form = outline(world, F + "form");
  const [lenders, jurisdictions] = settableOf(world, form);

  it("builds the sample's syndicated assembly from nothing", () => {
    const empty = Graph.empty();
    const created = addAssembly(empty, world, NS, "Syndicated", F + "form");
    let g = toggleChoice(created.graph, created.iri, F + "cl-5-2b", true);
    g = writeSetting(g, world, NS, created.iri, lenders, { literals: ["3"] });
    g = writeSetting(g, world, NS, created.iri, jurisdictions, { resources: [F + "uk", F + "ie"] });
    expect(g.types(created.iri)).toEqual([CST("Assembly")]);
    expect(g.value(created.iri, CST("assembles"))).toBe(F + "form");
    const settings = settingsMade(g, created.iri);
    // A quantity-valued variable's value is a decimal, and a concept-valued one's a resource.
    const count = settings.get(F + "gv-lender-count")!;
    expect(g.object(count.record, WRD("literalValue"))).toMatchObject({ value: "3", datatype: { value: XSD("decimal") } });
    expect(g.types(count.record)).toEqual([WRD("VariableValue")]);
    expect(g.value(count.record, WRD("forVariable"))).toBe(F + "gv-lender-count");
    expect(settings.get(F + "var-jurisdictions")!.values).toEqual([F + "uk", F + "ie"]);
    expect([...choicesMade(g, created.iri)]).toEqual([F + "cl-5-2b"]);
    // The assembly graph holds the records, so the split would leave it whole.
    expect(split(g).assembly.size).toBe(g.size);
  });

  it("writes a literal as a string where the variable declares no value space", () => {
    const v = { ...jurisdictions, contract: undefined, space: undefined };
    const g = writeSetting(Graph.empty(), world, NS, A + "x", v, { literals: ["UK"] });
    expect(g.object(g.subjects(WRD("forVariable"))[0], WRD("literalValue"))).toMatchObject({ value: "UK", datatype: { value: XSD("string") } });
  });

  it("updates a setting in place, and removes its record when it is cleared", () => {
    const base = split(world).assembly;
    const a = A + "syndicated";
    const changed = writeSetting(base, world, NS, a, lenders, { literals: ["5"] });
    expect(settingsMade(changed, a).get(lenders.iri)).toEqual({ record: A + "syndicated-lenders", values: [], literals: ["5"] });
    const cleared = writeSetting(changed, world, NS, a, lenders, { literals: [" "] });
    expect(settingsMade(cleared, a).has(lenders.iri)).toBe(false);
    expect(cleared.has(A + "syndicated-lenders")).toBe(false);
    expect(settingsMade(cleared, a).has(jurisdictions.iri)).toBe(true);
  });

  it("toggles a choice on and off", () => {
    const base = split(world).assembly;
    const off = toggleChoice(base, A + "syndicated", F + "cl-5-2b", false);
    expect(choicesMade(off, A + "syndicated").size).toBe(0);
    const on = toggleChoice(toggleChoice(off, A + "syndicated", F + "cl-5-3", true), A + "syndicated", F + "cl-5-3", true);
    expect([...choicesMade(on, A + "syndicated")]).toEqual([F + "cl-5-3"]);
  });

  it("drops choices and settings when the form changes, and every record with the assembly", () => {
    const base = split(world).assembly;
    const a = A + "syndicated";
    const other = setForm(base, a, F + "other");
    expect(other.value(a, CST("assembles"))).toBe(F + "other");
    expect(choicesMade(other, a).size).toBe(0);
    expect(settingsMade(other, a).size).toBe(0);
    expect(other.has(A + "syndicated-lenders")).toBe(false);
    expect(other.has(A + "unsettled")).toBe(true);
    const gone = removeAssembly(base, a);
    expect(gone.has(a)).toBe(false);
    expect(gone.has(A + "syndicated-jurisdictions")).toBe(false);
    expect(gone.types(A + "unsettled")).toEqual([CST("Assembly")]);
  });

  it("mints a new assembly's IRI under the workspace namespace without clashing", () => {
    const one = addAssembly(Graph.empty(), world, NS, "Facility A");
    const two = addAssembly(one.graph, one.graph.merge(world), NS, "Facility A");
    expect(one.iri.startsWith(NS)).toBe(true);
    expect(two.iri).not.toBe(one.iri);
    expect(two.graph.ofType(CST("Assembly"))).toHaveLength(2);
  });
});
