<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A15: Realisation-Strategy Neutrality

**Status:** Accepted
**Date:** 2026-09-17

## Context

Eligibility and Behaviour's mechanisms — dimension registries, match strategies, state spaces, transitions, guards, effects — are semantic definitions. Nothing about their meaning depends on how a particular deployment chooses to evaluate them. Written carelessly, though, a specification can read as though a generated/compiled surface were mandatory for the mechanism to be usable at all. Quantification's own README already states this position explicitly ("Quantification does not require every use to be compiled"); this ADR adopts the same position as a substrate-wide, cross-layer rule rather than leaving it as one layer's local statement.

## Decision

Eligibility and Behaviour semantics are defined independently of realisation strategy. A conforming implementation may use direct SPARQL, SHACL, reasoning, graph materialisation, external projection, an application evaluator, or a compiled evaluator — individually or combined — provided it passes the shared semantic conformance corpus (built in Gate 5). Compilation is never a semantic prerequisite.

Concretely, this means:

- A reified declaration is directly usable RDF: queryable by SPARQL, validatable by SHACL, reasoned over immediately after authoring, with no generation step required for it to be operationally meaningful at low-to-medium volume.
- A generated direct-property surface remains a legitimate, optional, high-value profile, chosen for query-plan efficiency, SHACL property-shape ergonomics, or compatibility with existing hand-authored consumers — never the only path to a usable mechanism.
- "Done" for a semantic definition means the semantics are defined and testable across multiple realisation strategies, of which compilation is one.

## Consequences

- Eligibility's operational profiles (E1 direct SPARQL, E2 SHACL, E3 reasoner-assisted, E4 materialised graph, E5 external projection, E6 compiled evaluator) and Behaviour's equivalent profiles (B-P1–B-P7) are all first-class, not a fallback ladder terminating in compilation.
- Gate 2 and Gate 3 both require the semantic model to be directly evaluable via at least the SPARQL and SHACL profiles *before* any generated or compiled surface is built.
- A new profile (a future compiled evaluator, a new external projection) is added to the programme only once it passes the shared semantic conformance corpus (Gate 5) against the profiles already accepted.
