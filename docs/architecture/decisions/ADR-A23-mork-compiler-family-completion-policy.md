<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A23: MORK compiler family completion policy

**Status:** Accepted
**Date:** 2026-09-18
**Supersedes:** none
**Related:** ADR-A19 (staged compiler architecture), ADR-A24 (Eligibility executable strategy)
**Unit:** [`surface-mork-unified-projection`](../../developer/plans/surface-mork-unified-projection-plan.md) (epic)
**Source plan:** the Surface-MORK Unified Projection Program plan

## Context

The MORK enhancements analysis documents the gap directly: MORK's vocabulary already models `ShapeMapping`, `RuleMapping`, and `QueryTemplate` as generative mappings with parameter bindings and targeting specs, but only `tools/mork/src/mork2rml.py` exists, and it explicitly skips `ShapeMapping` and `RuleMapping` because it targets RML alone. SPARQL and native-IR compilers do not exist at all. The vocabulary is not the blocker. The compiler family is.

## Decision

**RML, SPARQL, SHACL, SWRL, and native IR are first-class compiler targets**, each built on the staged core from ADR-A19. `tools/mork/src/mork2rml.py`'s skip of `ShapeMapping` and `RuleMapping` is closed by adding the SHACL and SWRL compilers those mapping kinds already describe, not by narrowing what the vocabulary claims to support.

## Consequences

- Four compiler modules are added: MORK-to-SPARQL, MORK-to-SHACL, MORK-to-SWRL, MORK-to-native-IR, alongside the existing MORK-to-RML.
- No vocabulary change is required — `mork:GenerativeMapping`'s subclasses already cover all five targets, per the MORK enhancements analysis's own account.
- Each target needs its own fixture corpus and provenance population, because "vocabulary support" without a compiler reading it, as the MORK enhancements analysis's status table records for SPARQL and SWRL today, does not count as complete.
- Eligibility's executable strategy (ADR-A24) is the first consumer that needs the SPARQL, SHACL, and SWRL targets in combination, and its delivery order constrains which of these four is built first.

## Addendum (2026-09-18): implemented, minus native

**No native-IR compiler.** Neither the delivery plan nor any other document in this repository defines what a native artefact would be, so none was built and none is planned pending an actual definition. This ADR's "five targets" is reduced to four in practice: RML (`tools/mork/src/mork2rml.py`, pre-existing), SPARQL, SHACL, and SWRL (`tools/mork_compilers/`, new).

SPARQL, SHACL, and SWRL are implemented for `elg:IntervalCondition` only, via the shared IR in `tools/mork_compilers/eligibility_ir.py`, per ADR-A24. Full details, including what was deliberately left out (profile-level aggregate artefacts, runtime result tracking, and the "Executable Projection Contract" domain-binding layer the MORK enhancements analysis also proposes), are in `ontology/mork/docs/eligibility-executable-compiler.md`. Not executed: no Python interpreter or SPARQL/SHACL/SWRL engine was available when this was written.
