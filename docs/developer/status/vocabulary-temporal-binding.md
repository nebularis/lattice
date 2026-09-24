<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Vocabulary Temporal Binding - Status

**Unit ID:** `vocabulary-temporal-binding`
**Status:** Slices 1-4 authored. Not yet executed or human-reviewed. Treat as a draft implementation pending the human validation gate.
**Last updated:** 2026-09-25
**Trigger:** `65ac4a85e11cc1f8616e3e0c24efd59bf4ca410d`
**Plan:** [vocabulary-temporal-fixes.md](../plans/vocabulary-temporal-fixes.md)
**Sketch:** [vocabulary-temporal-binding.md](../sketches/vocabulary-temporal-binding.md)

## Current position

Slices 1-4 are now authored, at the human's explicit direction to execute the
plan in autonomous mode (2026-09-25). This sandbox has no network access to
install `rdflib`/`pyshacl`/`pytest` (corporate proxy blocks PyPI; see
`/memories/repo/lattice-environment.md`), so nothing below has been executed.
Treat every artefact as a draft implementation, not a passing one, until the
human runs `mise run check:vocabulary` and reports the result.

What exists now:

- `ontology/vocabulary/shapes/structural.ttl` and `constraints.ttl` are
  populated. `rules.ttl` deliberately documents why no SHACL rule is defined
  (ADR-A85: no rule may silently choose a winning binding).
- `ontology/vocabulary/examples/` holds 12 fixtures: the 11 the sketch listed,
  plus `consumer-boundary.ttl` for the Slice 4 cross-layer check.
- `tools/vocabulary/` is a new Python package (`vocabulary.resolver.resolve`)
  implementing the precedence law, with a pytest suite: `test_shacl_fixtures.py`
  (SHACL conformance of every fixture), `test_resolver.py` (conjunctive
  scopes, strict-superset precedence, fallback, conflict, temporal handover),
  `test_determinism.py` (triple-order permutation), and
  `test_consumer_boundary.py` (Slice 4).
- `mise.toml` gained `bootstrap:vocabulary` and `check:vocabulary`, wired into
  the aggregate `bootstrap`/`check` tasks.
- `docs/architecture/ontology-architecture.md` §5.6 and the implementation
  status table are synced to this position.
- Root `README.md` and `tools/README.md` document the new `tools/vocabulary/`
  package.

Two decisions were made without a further human checkpoint, because the sketch
and plan explicitly permitted them (see "Decisions made during implementation"
below), and are flagged here for review rather than silently assumed correct:
the resolver's location/language, and the validation-context representation
for the two SHACL checks that need one.

## Planned slices

| Slice | Status | Scope |
|---|---|---|
| 1. Decision and documentation foundation | Done (prior session) | ADR-A85 proposal, architecture mirror, fixture/test/traceability skeleton |
| 2. Examples and SHACL constraints | Authored, not executed | 12 fixtures (11 positive/negative + 1 consumer), `structural.ttl`, `constraints.ttl` |
| 3. Resolution reference implementation | Authored, not executed | `tools/vocabulary` resolver + determinism/precedence/conflict tests |
| 4. Consumer/provenance integration | Authored, not executed | `consumer-boundary.ttl` + `test_consumer_boundary.py`; Surface/Eligibility left unmodified |

## Decisions made during implementation (flagged for human review)

- **Resolver location and language:** `tools/vocabulary/`, a Python package
  mirroring `tools/persistence/`'s `pyproject.toml` + `src/<pkg>/` + `tests/`
  shape. Matches the plan's assumption of "the existing Python tooling
  boundary."
- **SHACL validation-context representation:** four of the sketch's checks
  (temporal interval order, the context-independent form of an
  equal-specificity conflict, scopeless/`boundScheme` agreement, historical
  provenance time) are checkable from the graph alone or via one small,
  explicitly non-normative validation-profile term, `vvp:resolvedAt`
  (documented in `constraints.ttl`'s header). Strict-superset precedence
  genuinely needs a caller-supplied context and time, so it is not a SHACL
  shape at all — it lives only in the resolver.
- **Consumer for Slice 4:** neither Surface nor Eligibility was modified.
  `consumer-boundary.ttl` plus a Python test proves the boundary against a
  synthetic contract, and documents (without changing) that
  `ontology/eligibility/shapes/rules.ttl`'s `elg:HierarchyWellFoundednessShape`
  is today's one real `voc:boundScheme` consumer, reading it directly and
  never resolving a `voc:SchemeBinding`.
- **ADR-A85 status:** left as Proposed. Ratifying it is a human decision, not
  an automatic consequence of authoring the artefacts it called for.
- **Ontology version IRI:** left at `0.0.2`, unchanged, per the plan.

## Human validation gate

Nothing here has been executed. Before treating this unit as complete:

1. Review this authored implementation against the plan, ADR-A85, and the
   sketch's invariants — the review the plan's Slice 1 gate called for, now
   that there is a full implementation to review, not only a proposal.
2. Run `mise run check:vocabulary` (after `mise run bootstrap:vocabulary`) in
   an environment with dependency access, and report the result.
3. Perform the validation pack's human mutation probe (disable strict-superset
   precedence in the resolver and rerun VTB-06; disable the equal-specificity
   SHACL-SPARQL constraint and rerun VTB-07) to confirm the tests are not
   vacuous.

## Blockers

Execution and human review, in that order: the implementation is authored but
unrun (network-restricted sandbox), and unreviewed. No code or test command has
been run for this unit.
