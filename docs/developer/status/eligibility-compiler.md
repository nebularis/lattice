<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Eligibility Executable Compiler Implementation Status

**Unit:** `eligibility-compiler`
**State:** Implemented, awaiting validation in network environment
**Sketch:** [mork-eligibility-compiler.md](../sketches/mork-eligibility-compiler.md)
**Plan:** [eligibility-compiler.md](../plans/eligibility-compiler.md) (2026-09-23) — verification steps below are now slices A1–A5 there; step 5's Drools/Pellet dependency is redesigned as a shared, test-scope-only module (Part B), never a dependency of `tools/mork_compilers` itself
**Governing ADRs:** [ADR-A23](../../architecture/decisions/ADR-A23-mork-compiler-family-completion-policy.md), [ADR-A24](../../architecture/decisions/ADR-A24-eligibility-executable-semantics-backend-strategy.md), ADR-A81 (proposed, test-only reasoning/rules engine isolation)

## What was built

A compiler family for deterministic, multi-backend eligibility condition execution. Narrowed scope (Phase 5 subset): `elg:IntervalCondition` with three backends, no native implementation.

### Compiler Architecture
- **Shared IR:** `eligibility_ir.py` compiles `elg:IntervalCondition` into a backend-neutral `IntervalPlan` capturing value space and required intervals with closure
- **SPARQL backend** (`sparql_backend.py`): generates `mork:QueryTemplate` + `exe:SparqlArtefact` returning decision per condition
- **SHACL backend** (`shacl_backend.py`): generates readiness and containment shapes as `sh:NodeShape` + `exe:ShaclArtefact`
- **SWRL backend** (`swrl_backend.py`): generates positive-only Horn clauses (`exe:SwrlArtefact`) inferring decision from required intervals
- **Provenance:** every artefact carries `implementsCondition`, `derivedFromEligibilityNode`, `derivedFromQuantificationNode`, `producesArtefact` links

### Artefacts and Specs
- `tools/mork_compilers/src/mork_compilers/` — shared IR, three backends, CLI, tests
- `ontology/mork/spec/Executable.ttl` — `exe:IntervalContainmentPlan`, `exe:SparqlArtefact`, `exe:ShaclArtefact`, `exe:SwrlArtefact` term definitions
- Example trace: `elg:IntervalCondition` → `IntervalPlan` → `{SPARQL|SHACL|SWRL}` → typed artefact with provenance

### Deliberate Non-Coverage
- No "Executable Projection Contract" layer (`exp:ExecutableProjectionContract`) — identified as separate ADR-grade architectural layer
- No profile-level aggregate artefact — only per-condition artefacts; combining requires future work
- No runtime result tracking (`exe:EvaluationRun`, `exe:ConditionResult`) — compilation only, not execution
- Only `elg:IntervalContainment` compiled; `elg:ExactCondition`, `elg:SetMembershipCondition`, `elg:WildcardCondition` refused with diagnostic
- SPARQL: one SELECT per condition, multiple required ranges become `||` union
- SHACL: readiness and containment shapes, not a direct SPARQL-based pass/fail mapping
- SWRL: positive-only per ADR-A24; multiple rules per required intervals

## Evidence

- **Source:** [tools/mork_compilers/](../../../tools/mork_compilers/)
- **Tests:** [test_mork_compilers.py](../../../tools/mork_compilers/src/mork_compilers/test_mork_compilers.py) present; not yet run in restricted environment
- **Specification:** [Executable.ttl](../../../ontology/mork/spec/Executable.ttl) present; parsing not yet validated
- **Documentation:** Sketch precisely records what was excluded and why (no guesswork, no silent gaps)

## Verification Plan (not yet executed)

The authoring environment lacked Python interpreter, SHACL/SWRL engines, and SPARQL execution. Superseded by [plans/eligibility-compiler.md](../plans/eligibility-compiler.md), which turns the five steps below into slices A1–A5 and — because step 5 would otherwise pull a JVM reasoner and rules engine onto the main dependency path — designs a shared, test-only `platform/reasoning-testkit` module (Part B) so no product package ever depends on Drools/Pellet directly. Original five steps, kept here for history:

1. Run `python -m unittest mork_compilers.test_mork_compilers -v` (→ A1)
2. Parse `ontology/mork/spec/Executable.ttl` under OWL reasoner with Eligibility imported (→ A2)
3. Execute generated SPARQL from `sparql_backend.compile_query_template()` against `ontology/eligibility/examples/interval-containment.ttl` (→ A3)
4. Validate generated SHACL with real engine against example fixtures (missing candidate, out-of-range candidate) (→ A4)
5. Load generated SWRL into Drools/Pellet and confirm inference (→ A5, gated on Part B)

## Repository integration

- Code layout: follows [ADR-A77](../../architecture/decisions/ADR-A77-repository-topology-and-documentation-governance.md); Python under `tools/mork_compilers/` with `pyproject.toml`
- Vocabulary: imports Eligibility and MORK, adds no external dependencies
- No separate lock or CI task yet (validation environment will add this)

## Acceptance

Implementation is complete and internally coherent. Runtime validation in a network-enabled environment with Python, OWL reasoner, SHACL engine, and SPARQL processor is required before production deployment. The sketch's "Verification plan" section names the exact command matrix.

## Deferred (out of scope)

- Projection contract layer (`exp:ExecutableProjectionContract`)
- Profile-level aggregate artefact and `AllRequired`/`AnySufficient` combination rules
- Runtime result tracking and diagnostics
- Other condition types (`ExactCondition`, `SetMembership`, `Wildcard` with semantics)

## Next steps

Run the verification plan in a network-enabled environment. On pass, move to Phase 5 validation gate. On failure, diagnose and record results in this status file.
