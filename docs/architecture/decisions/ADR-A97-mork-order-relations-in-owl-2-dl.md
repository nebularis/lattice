<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A97: MORK order relations in OWL 2 DL

**Status:** Accepted
**Date:** 2026-09-25
**Related:** ADR-A83 (test-only reasoning engine isolation), ADR-A86 (ontology versioning)
**Unit:** [`eligibility-compiler`](../../developer/plans/eligibility-compiler.md) (A2, the Executable consistency check)

## Context

`mork:precedes`, `mork:softPrecedes` and `mork:refinesIntent` were each
declared transitive, asymmetric and irreflexive. OWL 2 DL allows asymmetry
and irreflexivity only on simple properties, and a transitive property is
never simple. So Mork was not OWL 2 DL: HermiT refused it, which blocked the
reasoner check of Executable, which imports Mork.

Asymmetry and irreflexivity also fall short of what the relations mean. They
catch a self-loop and a two-cycle, but not a longer cycle unless transitivity
is applied too. The `precedes` scope note said SHACL enforced acyclicity, but
no such shape existed. Only `tools/mork`'s Python checks tested it, and they
cited a "Shape M7" that was never written.

`refinesIntent` was described as generating a preorder, which is reflexive,
while being declared irreflexive.

## Decision

1. **The three relations stay transitive and lose asymmetry and
   irreflexivity.** Mork is then OWL 2 DL, and consistent under HermiT.
2. **Acyclicity is a SHACL-SPARQL constraint** in
   `ontology/mork/shapes/constraints.ttl`, one shape per relation:
   `mork:PrecedenceAcyclicityShape` (M7), `mork:SoftPrecedenceAcyclicityShape`
   and `mork:IntentRefinementAcyclicityShape`. A transitive relation is
   irreflexive exactly when it is acyclic, so the same graphs are rejected as
   before.
3. **Each shape follows the relation and the named properties it is derived
   from:** `precedes` with `resolvesIdentityFor` and the inverses of
   `compositeBroaderMapping`, `broaderApplicative`, `dependentMapping` and
   `templateMapping` (Axioms P1, P2, P3, P10), and `softPrecedes` with the
   inverse of `hypothesisMapping` (P5). A cycle is found whether or not the
   relation has been materialised.
4. **`precedes` and `softPrecedes` are checked separately**, as declared. A
   cycle mixing hard and soft edges is not a violation.
5. **`refinesIntent` is the strict refinement order.** Its
   reflexive-transitive closure generates the preorder Int(I). Declaring it
   reflexive is not an option: `owl:ReflexiveProperty` is global, and local
   reflexivity (`∃refinesIntent.Self`) needs a simple property.

## Consequences

- Mork 0.3.0 → 0.4.0, MINOR, together with the repair of five GCI axiom
  annotations the OWL API could not parse. Every graph that conformed before still
  conforms. The human accepted MINOR on 2026-09-25 since MORK has no
  consumers yet. The policy's letter would call a new Violation shape MAJOR.
- A reasoner no longer reports a precedence cycle as an inconsistency.
  Running the shapes is the check.
- `tools/test_mork_order_relations.py` runs the shapes and checks Mork and
  Executable for consistency under HermiT.
