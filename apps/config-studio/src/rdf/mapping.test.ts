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
