<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Vocabulary Temporal Binding - Status

**Unit ID:** `vocabulary-temporal-binding`
**Status:** Planned, awaiting human review. Implementation has not started.
**Last updated:** 2026-09-24
**Trigger:** `65ac4a85e11cc1f8616e3e0c24efd59bf4ca410d`
**Plan:** [vocabulary-temporal-fixes.md](../plans/vocabulary-temporal-fixes.md)
**Sketch:** [vocabulary-temporal-binding.md](../sketches/vocabulary-temporal-binding.md)

## Current position

The triggering commit is present in the current repository and changes only the
Vocabulary README and extracted Turtle. The surrounding conformance package is
incomplete. `ontology/vocabulary/shapes/constraints.ttl`, `rules.ttl`, and
`structural.ttl` are empty placeholders. There are no vocabulary example
fixtures or executable tests for binding precedence, temporal applicability,
conflict detection, or historical provenance.

The original documentation-only plan is superseded by the revised plan. It
underestimated the work because it treated the source ontology change as the
whole unit and did not account for the repository's fixture, SHACL, executable
validation, traceability, and human-gate requirements.

## Planned slices

| Slice | Status | Scope |
|---|---|---|
| 1. Decision and documentation foundation | Planned | ADR-A85 proposal, architecture mirror, fixture/test/traceability skeleton |
| 2. Examples and SHACL constraints | Planned | Positive and negative fixtures, structural constraints, SHACL-SPARQL checks |
| 3. Resolution reference implementation | Planned | Deterministic precedence resolver and mutation-derived tests |
| 4. Consumer/provenance integration | Planned | Surface or Eligibility boundary checks, historical `resolvedUnder`, final docs and VP |

## Decisions awaiting human confirmation

- Whether ADR-A85 should remain Proposed until the implementation slices are
  reviewed, or be ratified before Slice 2 begins.
- The repository location and language for the small reference resolver. The
  plan assumes the existing Python tooling boundary, but no resolver package is
  created by this status record.
- The exact validation-context representation for SHACL checks that need a
  resolution time and active scopes.
- Which consumer provides the narrowest useful cross-layer proof, Surface or
  Eligibility, without expanding this unit into a consumer implementation.
- Whether the ontology version IRI remains `0.0.2` for this backward-compatible
  addition.

## Human validation gate

Before implementation, review the sketch, plan, proposed ADR-A85, fixture list,
validation cases, and deliberate non-coverage. The first implementation slice
must not begin until the slice boundaries and the validation context are
approved.

## Blockers

Human review is the only blocker currently recorded. No code or test command has
been run for this unit.
