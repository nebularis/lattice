<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Vocabulary Temporal Binding - Status

**Unit ID:** `vocabulary-temporal-binding`
**Status:** Complete. Vocabulary package, SHACL, and both real consumers (Surface, Eligibility) verified green.
**Last updated:** 2026-09-25
**Trigger:** `65ac4a85e11cc1f8616e3e0c24efd59bf4ca410d`
**Plan:** [vocabulary-temporal-fixes.md](../plans/vocabulary-temporal-fixes.md)
**Sketch:** [vocabulary-temporal-binding.md](../sketches/vocabulary-temporal-binding.md)

## Current position

Slices 1-4 are now authored and have been executed in the working Python
environment. `mise run check:vocabulary` passes all 14 tests. The existing
Surface compiler suite passes all 61 tests. The focused consumer-boundary suite
passes 3 tests, but it is intentionally diagnostic and does not modify either
consumer.

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
  `test_consumer_boundary.py` (Slice 4). The suite passes 14/14.
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
| 2. Examples and SHACL constraints | Verified, 14/14 package tests pass | 12 fixtures (11 positive/negative + 1 consumer), `structural.ttl`, `constraints.ttl` |
| 3. Resolution reference implementation | Verified, included in 14/14 package tests | `tools/vocabulary` resolver + determinism/precedence/conflict tests |
| 4. Consumer/provenance integration | Complete, verified | Surface resolves scoped bindings via `vocabulary.resolve` (`tools/surface/src/surface/compile.py`); Eligibility's `HierarchyWellFoundednessShape` checks every scheme a contract could resolve to; both proven against dedicated fixtures |

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
- **Consumer integration (this pass):** Surface's `enumerate_population`
  (`tools/surface/src/surface/compile.py`) now resolves a contract-bound
  population's scheme via `vocabulary.resolve`, given a new optional
  `srf:activeBindingScope` on `srf:ContractBoundPopulation` and the
  compiler's existing `produced_at` as resolution time. Surface's static
  shapes (`BoundSchemePresentShape`, `BoundSchemeGovernanceShape`) and its
  parity shapes (`SurfaceCoverageParityShape`, `SurfaceOrphanSymbolShape`)
  are broadened/repointed accordingly (see "Verification findings" below).
  Eligibility's `elg:HierarchyWellFoundednessShape`
  (`ontology/eligibility/shapes/rules.ttl`) now checks every scheme the
  contract could resolve to (`boundScheme` or any `SchemeBinding`), staying
  pure SHACL since well-foundedness is scope-invariant and needs no runtime
  context. `tools/surface/pyproject.toml` depends on
  `lattice-vocabulary-resolver`, and `mise.toml`'s `bootstrap` task now
  installs `bootstrap:vocabulary` before `bootstrap:surface`.
- **ADR-A85 status:** left as Proposed. Ratifying it is a human decision, not
  an automatic consequence of authoring the artefacts it called for.
- **Ontology version IRI:** left at `0.0.2`, unchanged, per the plan.

## Verification findings

### SHACL and resolution rules

The SHACL package now checks structural completeness, temporal interval order,
scopeless binding agreement with `boundScheme`, context-independent equal-scope
overlap conflicts, and historical provenance time. The resolver checks
caller-dependent scope applicability, strict-superset precedence, incomparable
or equal-specificity conflicts, temporal applicability, and fallback selection.

Strict-superset precedence cannot be enforced by the current SHACL shapes
because SHACL receives no caller-supplied active context or resolution time. It
is covered by the resolver and its tests instead. This is a deliberate
boundary, not a complete SHACL enforcement of every README rule.

### Consumer integration

Both real consumers now honour scoped bindings, verified in the working
environment:

- **Surface.** `enumerate_population` (`tools/surface/src/surface/compile.py`)
  resolves a contract-bound population's scheme via `vocabulary.resolve`,
  using the population's declared `srf:activeBindingScope` values and the
  compiler's `produced_at` as resolution time, instead of reading
  `voc:boundScheme` directly. A new fixture,
  `ontology/surface/examples/employment-job-family-scoped.ttl`, and test,
  `test_contract_bound_population_resolves_the_scoped_binding` in
  `tools/surface/src/surface/test_surface.py`, prove the compiler mints
  symbols from the scoped scheme's members, not the fallback's — confirmed
  independently by comparing a raw `boundScheme` read against `resolve()`
  against the same fixture (they diverge, as expected). Surface's own static
  shapes (`BoundSchemePresentShape`, `BoundSchemeGovernanceShape` in
  `ontology/surface/README.md` / `shapes/constraints.ttl`, mechanically kept
  in sync via `tools/literate_extract.py`) now check every scheme the
  contract could resolve to (`boundScheme` or any `SchemeBinding`), the same
  way Eligibility's shape does, since these are declaration-time checks with
  no runtime context. The parity shapes
  (`SurfaceCoverageParityShape`, `SurfaceOrphanSymbolShape` in
  `shapes/surface-parity.ttl`) now pivot on the generated surface's own
  `srf:hasReadSetEntry`/`srf:readsSource` provenance — whichever scheme was
  actually resolved at generation time — rather than recomputing
  `boundScheme`, which is correct regardless of scoped or unscoped
  resolution. `tools/surface/pyproject.toml` depends on
  `lattice-vocabulary-resolver`, and `mise.toml`'s `bootstrap` task installs
  `bootstrap:vocabulary` before `bootstrap:surface` so the dependency resolves
  from the already-installed local package rather than PyPI.
- **Eligibility.** `elg:HierarchyWellFoundednessShape`
  (`ontology/eligibility/shapes/rules.ttl`) now unions `boundScheme` with
  every scheme bound via a `SchemeBinding` naming the same contract, so a
  cycle reachable only through a scoped binding is caught. This stays pure
  SHACL — no runtime context needed — because well-foundedness must hold for
  every scheme the contract could ever resolve to, not only whichever is
  currently in force. Verified with an isolated pyshacl run against a
  synthetic scoped-only cyclic scheme: the broadened shape catches it; the
  old shape (checking `boundScheme` only) would have missed it, since the
  fixture declares no `boundScheme` at all.

All of the above ran in the working Python environment: `mise run
check:vocabulary` (14/14), `python -m unittest surface.test_surface -q`
(62/62, including the new scoped-binding test), and `mise run
check:python-root` (77/77 plus Phase 8 conformance), none of which existed or
passed with the resolver wired in before this pass.

## Human validation gate

Before treating this unit as closed:

1. Review this implementation against the plan, ADR-A85, and the sketch's
   invariants.
2. The automated checks have run: `mise run check:vocabulary` (14/14),
   `python -m unittest surface.test_surface -q` (62/62), and `mise run
   check:python-root` (77/77 plus Phase 8 conformance).
3. Perform the validation pack's human mutation probe (disable strict-superset
   precedence in the resolver and rerun VTB-06; disable the equal-specificity
   SHACL-SPARQL constraint and rerun VTB-07) to confirm the tests are not
   vacuous.
4. Ratify ADR-A85, currently left as Proposed.

## Blockers

Human review and ADR-A85 ratification. All authored artefacts, including the
Surface and Eligibility consumer integration, are executed and green.
