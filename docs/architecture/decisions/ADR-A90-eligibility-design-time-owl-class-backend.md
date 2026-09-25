<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A90: Design-time OWL class backend for Eligibility

**Status:** Proposed
**Date:** 2026-09-25
**Related:** ADR-A23 (compiler family completion), ADR-A24 (backend
strategy), ADR-A83 (test-only reasoning engine isolation, reserved), ADR-A87,
ADR-A89, ADR-A91
**Unit:** [`applied-ontology-readiness`](../../developer/plans/applied-ontology-readiness.md)

## Context

An applied ontology asks questions about its declared conditions before any
instance data exists. Does a revised benefit profile admit anyone the
previous revision did not? Do two trial arms admit overlapping patients? Does
a profile admit anything at all? These are subsumption and satisfiability
questions over classes. A DL reasoner answers them without an A-Box, so the
open-world assumption does not distort the answers.

LATTICE has no backend that turns conditions into OWL classes. The SPARQL,
SHACL and SWRL backends evaluate candidates. They cannot compare two
conditions with each other.

## Decision

1. **An OWL backend on the shared IR.** It reads the same plans as the other
   backends (ADR-A24, ADR-A89) and emits one generated OWL module per
   compilation as an `exe:OwlArtefact`, with the same provenance links as the
   existing artefacts. Each condition is expressed over the domain property
   that carries its candidate, as bound under ADR-A91.
2. **Hierarchy classes.** For a hierarchical dimension property R and each
   concept c of the resolved scheme edition, a primitive class Within_R(c):

       ∃R.{c} ⊑ Within_R(c)
       Within_R(d) ⊑ Within_R(c)      for each d with d skos:broader c

   Both axiom forms are in OWL 2 EL.
3. **Sibling disjointness is a caller option.** Within_R(c) ⊓ Within_R(c′) ⊑ ⊥
   for siblings c and c′ is emitted only when the caller declares the scheme's
   siblings mutually exclusive and R functional. The option is recorded in the
   artefact's provenance. Without it, the checks in item 6 report an overlap or
   an expansion that disjointness would rule out, and never miss one.
4. **Condition classes.** For subject class S:

       Cond ≡ S ⊓ (⊔ᵢ Within_R(rᵢ)) ⊓ ¬(⊔ⱼ Within_R(eⱼ))

   A condition with exclusions only uses the scheme's top concepts in place of
   the required set (L12). An interval condition becomes a datatype restriction
   on its value property, one property per unit, with no conversion. A
   candidate strictly above an excluded concept is neither entailed in nor out
   of Cond, which is the design-time reading of L11.
5. **Profile classes.** `AllRequired` is intersection and `AnySufficient` is
   union. `DimensionConsistent` is refused, as in ADR-A89.
6. **Checks.** A library function and CLI answer three questions over the
   generated module: subsumption (P′ ⊑ P), satisfiability of P, and
   satisfiability of P ⊓ Q. Each answer is recorded with the module's
   provenance. The checks run through the ADR-A83 reasoning harness and never
   through a reasoner declared as a product dependency.
7. **Expressivity is declared.** Hierarchy axioms stay in EL. Condition and
   profile classes use negation, union and datatype restrictions, within OWL 2
   DL. Each generated module states which of the two it contains.

## Consequences

- Executable gains `exe:OwlArtefact` and a check-result record, a MINOR bump.
- The backend cannot be verified until the ADR-A83 harness exists. The
  repository's `reasoning` extra provides an OWL RL engine only.
- Generated class names derive deterministically from condition and concept
  IRIs, so regeneration after an unchanged edition yields identical modules.
- These classes answer design-time questions. Runtime decisions stay with the
  SPARQL reference backend.

## Open questions

- Should sibling exclusivity become a Vocabulary declaration on a scheme
  edition, rather than a compile option? It is a fact about the scheme, which
  argues for the graph. It would also be a Vocabulary MINOR bump that cascades
  to every layer. This ADR recommends the compile option until a second
  consumer needs the declaration.
