// SPDX-License-Identifier: MPL-2.0
// The mapping part and the mapping view's model, read from the studio's ODRL mapping pack.

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { Graph } from "@lattice/authoring-domain";
import { schemesOf } from "./mapping";
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
    expect(schemes.map((s) => s.label).sort()).toEqual(["LegalRuleML metamodel instances to stated meaning", "MS, proposed in legalruleml-cold"]);
    // The scorer reviews every mapping but a template, which it reads through the mappings that use it.
    for (const s of schemes) expect(s.mappings.filter((m) => !m.review).map((m) => m.isTemplate)).not.toContain(false);
  });

  it("follows a narrower link to a child, and links a correction to the pack's mapping", () => {
    const schemes = schemesOf(sample("odrl-mappings").mapping);
    expect(schemes).toHaveLength(2);
    const run = schemes.find((s) => s.label.endsWith("run-1"))!;
    expect(run.mappings.some((m) => m.depth > 0)).toBe(true);
    const corrected = run.mappings.find((m) => m.review?.decision === "Corrected")!;
    expect(corrected.review!.correctedBy!.startsWith(OM)).toBe(true);
  });
});
