<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Amendment: Eligibility law L9

**Affects:** `ontology/eligibility/README.md` (law register), `ontology/eligibility/vocab/eligibility-vocab.ttl` (`elg:L9` individual), `ontology/eligibility/shapes/` (the `elg:HierarchicalClosureRule` discharge)
**Reason:** `elg:HierarchicalClosureRule` is currently both the statement of what hierarchical closure *means* and the only mechanism that *materialises* it. As the sole discharge of L9 it runs unscoped over the whole union graph, with no provenance, no authority declaration, and no record that it ran. Materialisation now belongs to the Surface layer (ADR-A16), which scopes it to a declared population, records a read set, and caps its authority. L9 keeps the semantics; it stops owning the realisation.
**Nature:** narrowing of discharge, not of meaning. Nothing that satisfied the previous L9 fails the replacement.

> **Before applying:** this replacement was written to L9's known content — well-foundedness of the hierarchy underlying `elg:HierarchicalMatch`, and the closure semantics that match depends on. Diff it against the current text before committing; if the existing statement carries anything beyond that, fold it into clause (a) rather than dropping it.

---

## Replacement text — README law register entry

**L9 — Hierarchical match closure.**

Let `H` be the ordering relation underlying a hierarchical match: the relation a condition's bound scheme is ordered by. For a condition asserting value `c`, a candidate value `v` satisfies the condition under `elg:HierarchicalMatch` exactly when `v ≤_H c`, where `≤_H` is the reflexive-transitive closure of `H` restricted to the members of the bound scheme.

Three clauses, all required:

- **(a) Well-foundedness.** `H` is acyclic over the bound scheme. A cycle makes `≤_H` non-antisymmetric, so "more specific than" stops being an ordering and hierarchical match stops having a truth condition. A condition whose bound scheme carries a cycle in `H` is not evaluable.
- **(b) Reflexivity.** `c ≤_H c`. A condition asserting a value is satisfied by that value itself, not only by its descendants.
- **(c) Scope.** The closure is taken within the bound scheme. `H` edges reaching values outside it do not extend the match. Two schemes that happen to share an ordering relation do not thereby order each other's members.

**Register.** L9 is a semantic law. It states what hierarchical match means; it does not require that the closure be materialised, and an implementation that evaluates `≤_H` at query time satisfies it in full.

**Discharge.** Clause (a) is discharged by static analysis of the bound scheme — the traversal is graph-structural and therefore outside OWL, following the same reasoning that puts acyclicity of `mrk:precedes` in SPARQL rather than in the T-box. Clauses (b) and (c) are discharged by the evaluating implementation, whichever realisation it uses.

**Realisation note.** Where an implementation materialises `≤_H` rather than traversing it, the materialisation is a generated surface under ADR-A16, not a rule shipped by this layer. Such a surface declares its basis (`srf:closureBasis`), its scope (`srf:closureScope`), and its population, records the read set it was generated from, and is capped at cached-reproducible authority. It is subject to `srf:X3`, which restates clauses (b) and (c) as soundness and completeness conditions on the emitted relation, and to `srf:R5`, which requires clause (a) to have been established by an executed traversal rather than assumed. A materialised closure never becomes the evidence for an eligibility decision: the decision cites the condition and its bound scheme, and the fact that a surface was used is recorded on the decision as a realisation-profile fact.

---

## Replacement text — vocabulary individual

```turtle
elg:L9 a elg:Law ;
	elg:lawRegister elg:SemanticLaw ;
	rdfs:comment "Hierarchical match closure. A candidate value satisfies a condition under hierarchical match exactly when it stands in the reflexive-transitive closure of the bound scheme's ordering relation, restricted to that scheme's members, below the asserted value. The ordering relation is acyclic over the bound scheme; a scheme carrying a cycle is not evaluable under hierarchical match." .
```

The comment states the law and nothing else. The realisation note above is design rationale and belongs in the README's design-decisions section and in ADR-A16, not in the shipped annotation.

---

## Consequential edits

1. **Remove `elg:HierarchicalClosureRule`** from the Eligibility shapes. It constructs `skos:broaderTransitive` for every `skos:Concept` reachable by `skos:broader+` anywhere in the union graph — unscoped, so it fires across unrelated schemes, and it writes into the SKOS namespace, so its output is indistinguishable from authored vocabulary content. Nothing that depends on hierarchical match depends on this rule having run: clause (c) is now explicit, so an implementation traverses within the scheme instead.

2. **Add a static check for clause (a)** in its place, targeting conditions rather than concepts:

```turtle
elg:HierarchyWellFoundednessShape a sh:NodeShape ;
	sh:targetClass elg:Condition ;
	sh:sparql [
		sh:message "The scheme bound to a hierarchically-matched condition contains a cycle in its ordering relation, so hierarchical match has no truth condition. Discharges elg:L9 clause (a)." ;
		sh:select """
			PREFIX elg: <https://www.nebularis.org/neuro-semantic/lattice/eligibility#>
			PREFIX voc: <https://www.nebularis.org/neuro-semantic/lattice/vocabulary#>
			PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
			SELECT $this WHERE {
				$this elg:matchSemantics elg:HierarchicalMatch ;
					  elg:constrainedByContract ?schemeContract .
				?schemeContract voc:boundScheme ?scheme .
				?concept skos:inScheme ?scheme ;
						 skos:broader+ ?concept .
			}
		"""
	] .
```

This is checkable in fixed SHACL because `skos:broader` is a fixed predicate here. Where a deployment orders a scheme by some other relation, the check is basis-specific and belongs with that deployment, or with the surface generator, which establishes the same property by traversal and discharges `srf:R5`.

3. **Note the dependency** on finding 15.1's resolution: the shape above reads `elg:constrainedByContract`, the property added under option (c). Until that lands, the shape has no path from a condition to its bound scheme and cannot be installed.
