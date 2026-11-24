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

## Addendum (2026-10-30, Proposed with ADR-A148): XSLT and JOLT

ADR-A148 proposes XSLT and JOLT as targets for a mapping over an XML or JSON source, compiled from a logical plan read by `tools/mork_rdf`'s reader. It takes effect when ADR-A148 is accepted.

## Addendum (2026-11-23): mork_rdf compiles derivation projections

**Status of this addendum:** Accepted by the maintainer on 2026-11-24.

ADR-A18's addendum of the same date lowers a derivation projection into a mapping scheme whose root takes the source node as its identity and whose assertion has a value expression. Nothing compiles that scheme yet, and by the policy above a vocabulary no compiler reads does not count as complete.

1. **`mork_rdf` compiles a lowered derivation.** The compiler of mapping schemes over an RDF source reads the root and its assertion and writes one CONSTRUCT query. The assertion writes the result property on the source node. The expression compiles to SPARQL arithmetic in a `BIND`, each reference bound by the path it reads, and a rounding, a choice and a quotient compile to `ROUND`, `IF` and division.
2. **A carrier missing an operand writes nothing, and a check reports it.** A value that is undefined, such as a quotient by zero, writes nothing in the same way. A derived property is never half written.
3. **No new vocabulary.** The terms are those ADR-A18's addendum names. A scheme over an RDF source is compiled to SPARQL by `mork_rdf`, and the other kinds keep the compilers this decision lists.

**Consequences.** The compiled query of a derivation is the same for the same scheme, and a sample of the carrier class run through it gives the derived values. Until the compiler exists, a lowered derivation is checked by MORK's shapes and compiled by nothing.

## Addendum (2026-11-24): mork_rdf compiles graph construction projections

**Status of this addendum:** Accepted by the maintainer on 2026-11-24.

ADR-A18's addendum of the same date lowers a graph construction projection into a mapping scheme with a source-node root, a guarded contextual datum that mints the constructed node, and an assertion for each value. By the policy above a vocabulary no compiler reads does not count as complete.

1. **`mork_rdf` compiles a lowered construction with its existing cases.** The root, the contextual datum with its guard and identity, and the assertions are compiled as they are for any scheme, and no mapping kind is added. A guard sits on the datum's frame, which every query beneath inherits, so an instance contributes whole or not at all.
2. **Two checks report what the cases leave unsaid.** One names each instance the datum's guard excludes for want of a required value, with the value it lacks. One names a node whose identity is read from the source and whose instances give a property different values, with the node and each value. A keyed datum beneath a source-node datum also carries a `MappingReview` warning.
3. **No new vocabulary.** The terms are those ADR-A18's addendum names.

**Consequences.** The compiled queries of a construction are the same for the same scheme, and a sample of the carrier class run through them gives the nodes, the links and the values, with the excluded instances and the disagreements reported. Until a reader of the findings acts on `MappingReview`, the review ADR-A41 asks for is a finding and no more.
