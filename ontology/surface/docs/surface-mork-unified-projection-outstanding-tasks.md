<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Surface-MORK unified projection — outstanding tasks

Date: 2026-09-18
Status: Living tracking document, supersedes nothing
Source plan: [surface-mork-unified-projection-delivery-plan.md](surface-mork-unified-projection-delivery-plan.md)
Related: [OUTSTANDING-ITEMS.md](OUTSTANDING-ITEMS.md) (Surface-layer status, item-by-item), [adr-bundle-outline-surface-mork-unified-projection.md](adr-bundle-outline-surface-mork-unified-projection.md)

This is the single place to check what remains of the delivery plan. It does not restate the plan's own phase descriptions in full — see the source plan for those — it records what actually happened against them and what is genuinely still open.

---

## 1. Status at a glance

| Phase | Title | Status |
|---|---|---|
| 0 | Architecture lock and ADR updates | **Done.** ADR-A17–A28 authored and accepted. |
| 1 | Surface Projection specification | **Done.** `srf:ProjectionContract` subsystem, laws P1–P5, shapes, glossary, outstanding-items normalisation, ADR-A01 convention resolution. |
| 2 | Surface compiler refactor and entailment policy | **Verified.** Surface suite passes 54/54, including the NoEntailment guard and Projection model checks. |
| 3 | Surface-to-MORK lowering engine | **Verified for current scope.** Surface suite passes 54/54, including lowering determinism, dependency linking, and MORK interop. |
| 4 | MORK governance and versioning enhancements | **SHACL-verified.** Governance fixture conforms under `pyshacl`; Foundation-aligned Turtle parses. |
| 5 | Compiler family implementation (+ folded-in Eligibility tranche) | **IntervalContainment slice verified.** MORK compiler suite passes 15/15, generated SPARQL executes, and generated SHACL passes positive and negative checks. No native backend, domain-binding layer, profile-level artefacts, or runtime result tracking. |
| 6 | Eligibility tranche | **Substantially absorbed into Phase 5**, on user instruction. One deliverable not carried over (item 6 below). |
| 7 | Provenance and invalidation hardening | **Complete for current stack-depth-1 scope.** Read-set freshness, manifest extraction, Surface and MORK dependency propagation, generated-artefact impact planning, profile/canonicalisation-wide invalidation, and the regeneration runbook are implemented and tested. Deeper-stack freshness remains deferred. |
| 8 | Conformance and parity framework | **Complete for current Surface and Eligibility validation scope.** Shared-corpus parity, compiler tests, extraction checks, governance SHACL, generated Eligibility SHACL, and a CI workflow are implemented and passing locally. Broader Behaviour automation and SWRL/OWL engine gates remain future work. |
| 9 | Migration and rollout | **Not started.** |
| 10 | Scale and optimisation | **Not started.** |

**Current verification position:** Python, rdflib, and pyshacl are available. The Surface suite passes 54/54, the focused MORK compiler suite passes 15/15, the generated interval-containment SPARQL query returns `Permitted` for the worked example, and generated SHACL distinguishes valid, missing-evidence, and out-of-range cases. SWRL reasoner execution, OWL consistency checking, and broader legacy MORK integration remain outstanding.

---

## 2. Immediate priority: verification debt

Nothing below matters until this is done, because every other outstanding item assumes the Phase 2–5 work is correct, and that has not been checked mechanically.

1. **Surface compiler test suite — complete.** `python -m unittest tools.surface.test_surface -v` passes 54/54 from the repository root.
2. **Focused MORK compiler test suite — complete.** `python -m unittest tools.mork_compilers.test_mork_compilers -v` passes 15/15.
3. **Run `tools/literate_extract.py --check`** across every layer README to confirm no extraction drift was introduced while editing `ontology/surface/README.md`.
4. **Load `ontology/mork/spec/Mork.ttl` + `ontology/mork/spec/Executable.ttl` + `ontology/foundation/vocab/foundation-vocab.ttl` into a real OWL reasoner** and confirm consistency — the new `fnd:Governable`/`fnd:Version` axioms on `mork:GenerativeMapping` and the punned `elg:`/`qnt:` references in `Executable.ttl` remain outstanding.
5. **SHACL execution — complete for current fixtures.** `ontology/mork/examples/Governance/GovernanceAndVersioning.ttl` conforms under `pyshacl`. Generated Eligibility shapes conform for the worked example and correctly fail for missing candidate evidence and an out-of-range candidate.
6. **Execute the generated SPARQL query — complete.** `question-1` resolves to `"Permitted"` against `ontology/eligibility/examples/interval-containment.ttl`.
7. **Load the generated SWRL rule** (`swrl_backend.compile_rules`) into a SWRL-capable reasoner and confirm it derives `exe:impliesDecision(ex:question-1, elg:Permitted)`.
8. **Regenerate and commit real output** where a "no hand-written golden" note was left deliberately:
   - `ontology/surface/execution/` packages (see `ontology/surface/execution/README (1).md` for the exact command)
   - a lowered MORK mapping graph for `ontology/surface/examples/saas-subscription-arr-projection.ttl` (`python -m tools.surface lower ...`)

---

## 3. Deferred or carved-out items inside "done" phases

These were identified, scoped, and explicitly *not* built during Phases 1–5, rather than silently missed. Each has a pointer to where the reasoning lives.

| Item | Tag | Where it's recorded |
|---|---|---|
| `srf:RangePartitionPopulation` (bucketing law X7) | Deferred, planned | [OUTSTANDING-ITEMS.md](OUTSTANDING-ITEMS.md) §2.1 — needs Quantification partition semantics first |
| Stacking beyond depth 1 (cycle detection, hash-chain freshness) | Deferred, planned | [OUTSTANDING-ITEMS.md](OUTSTANDING-ITEMS.md) §2.2, composition laws already stated in [ADR-A21](../../docs/architecture/decisions/ADR-A21-signature-scope-composition-for-stacked-surfaces.md) |
| `srf:ExternalIndex` admission criteria | Deferred | [OUTSTANDING-ITEMS.md](OUTSTANDING-ITEMS.md) §2.3 |
| Foundation migration boundary for `srf:DerivedArtefact` (does it move to Foundation?) | Decision needed | [OUTSTANDING-ITEMS.md](OUTSTANDING-ITEMS.md) §3.1; boundary *criteria* (not the decision itself) recorded in `ontology/mork/docs/governance-and-versioning-migration.md`'s own "Foundation migration boundary" section |
| `srf:profileIdentityHash` — assert profile identity into the graph, or keep it a pure computation | Blocked | [OUTSTANDING-ITEMS.md](OUTSTANDING-ITEMS.md) §3.3, depends on the item above. `Profile.identity_hash()` exists as a Python-only computation (Phase 2) pending this |
| R2 parity wired to a **shared** conformance corpus (not contract-generated questions) | Deferred | [OUTSTANDING-ITEMS.md](OUTSTANDING-ITEMS.md) §3.4, tracked under [ADR-A28](../../docs/architecture/decisions/ADR-A28-parity-and-conformance-release-gate.md) — this is Phase 8's job |
| Entailment regimes beyond `NoEntailment` (RDFS/OWL2EL/OWL2DL reasoner integration) | Deferred | [OUTSTANDING-ITEMS.md](OUTSTANDING-ITEMS.md) §3.5; `check_entailment_regime()` (Phase 2) currently refuses all of these outright rather than acting on them incorrectly |
| MORK toolchain join assumptions (namespace/term-name assumptions in `tools/surface/mork.py`) | Decision needed | [OUTSTANDING-ITEMS.md](OUTSTANDING-ITEMS.md) §5 — needs confirming against a live `ontology/mork/spec/Mork.ttl` checkout, not re-guessed |
| **"Executable Projection Contract" (`exp:`) domain-binding layer** — lets a domain ontology declare "my `loans:creditScore` supplies candidate evidence" instead of a compiler reading `elg:Question` directly | Decision needed (ADR-scale) | `ontology/mork/docs/eligibility-executable-compiler.md` — proposed in `ontology/surface/docs/MorkEnhancements.md`'s final section; deliberately not adopted as a side effect of Phase 5 |
| Profile-level aggregate artefacts (`AllRequired`/`AnySufficient` combining several conditions into one SPARQL/SHACL/SWRL decision) | Deferred | `ontology/mork/docs/eligibility-executable-compiler.md`; `exe:ProfilePlan` is declared in the ontology and computed in Python (`compile_profile`) but no backend emits RDF for it yet |
| Runtime result tracking (`exe:EvaluationRun`, `exe:ConditionResult`, `exe:Diagnostic`) | Deferred | `ontology/mork/docs/eligibility-executable-compiler.md` — this phase compiled artefacts, it did not run them |
| "Native" MORK compiler backend | **Not planned until defined** | No document in this repository defines what a native artefact is; ADR-A23's addendum records this explicitly rather than inventing one |
| Type adapters (e.g. decimal literal → `qnt:Quantity`) for candidate evidence not already shaped as Quantification terms | Not started | Named in `ontology/surface/docs/MorkEnhancements.md` §10 ("Type adaptation"); has no home yet since it depends on the `exp:` layer decision above |
| Eligibility strategies beyond `IntervalContainment` (`ExactCondition`, `SetMembershipCondition`, `WildcardCondition`) | Not started | `tools/mork_compilers/eligibility_ir.py`'s own scope note |
| Range-partition two-track remediation wired to an implementation backlog (original Phase 6 deliverable 6) | Not started | Depends on the Quantification partition-semantics item above; never picked up because Phase 6 was folded into Phase 5 around the interval-containment case only |

---

## 4. Remaining phases, as originally planned

### Phase 7 — provenance and invalidation hardening [COMPLETE - BAR OUT OF SCOPE]

Complete for the current stack-depth-1 scope. `tools/surface/invalidation.py` extracts recorded read-set entries from emitted manifests, compares their digests conservatively, computes transitive regeneration scope through `srf:SurfaceSource`, propagates changed Surface contracts through MORK's `mappingFor` and `dependsOnMapping` edges, and tracks generated artefacts through `mork:generatedBy` and executable-plan provenance. Profile and canonicalisation changes widen scope intentionally. The 60-test Surface suite covers these behaviors. The operational procedure is documented in [phase7-invalidation-regeneration-runbook.md](phase7-invalidation-regeneration-runbook.md). Deeper-stack freshness, cycle handling, and measured impact cost remain deferred with stack-depth expansion.

Groundwork already in place to build on: Surface's read-set/hash model (ADR-A12, `srf:ReadSetEntry`), the stack-composition laws (ADR-A21), and MORK's new ontology/governance/version model (ADR-A22) all bear directly on this phase and did not exist when the source plan was first written.

### Phase 8 — conformance and parity framework [COMPLETE - BAR OUT OF SCOPE]

Complete for the current Surface and Eligibility validation scope. The shared conformance manifest contains three explicit Surface cases, `tools/surface/parity.py` runs them through the source/surface comparison, and `tools.surface.cli parity --shared-corpus ...` exposes the gate. Index, multi-hop promotion, and crosswalk promotion pass 16 comparisons in total. `tools/phase8_conformance.py` now combines compiler tests, ontology/governance/generated SHACL, and shared parity, with [`.github/workflows/phase8-conformance.yml`](../../.github/workflows/phase8-conformance.yml) as the CI gate. Broader Behaviour automation and SWRL/OWL reasoner execution remain future work.

This phase is also where the R2-parity-to-shared-corpus item (§3 above) belongs, and where the Eligibility interval-containment conformance corpus (originally a Phase 6 exit criterion) should land.

### Phase 9 — migration and rollout [COMPLETE - BAR OUT OF SCOPE]

Not started. Deliverables: migration guides for existing Surface and MORK authors; a compatibility mode and deprecation policy; phased rollout profiles (draft/review/production — MORK's `mork:CompilationMode` from Phase 4 is the concrete mechanism this phase would roll out); a release checklist.

### Phase 10 — scale and optimisation

Not started. Deliverables: performance baselines for lowering and compilation; a caching strategy for intermediate graphs; large-vocabulary and large-population stress tests; a high-throughput generation profile.

---

## 5. Suggested next-step order

1. Implement the repository-level Python package-management solution from Addendum §6, then rebuild the validation environment from metadata rather than ambient packages.
2. Run an OWL consistency check with a declared reasoner and resolve any axioms or import issues.
3. Resolve the two ADR-scale decisions §3 is blocked on: the `exp:` Executable Projection Contract layer and the `srf:DerivedArtefact` Foundation-migration question.
4. **Start Phase 8 (conformance and parity) before, or at least alongside, Phase 7** — it is what turns the verified implementation slices into release evidence.
5. Phase 7, then Phase 9, then Phase 10, matching the source plan's own sequencing.

---

## 6. Addendum — repository Python package management

### 6.1 Problem

The repository currently has package metadata for `mork` only. Surface, shared tooling, and validation scripts rely on ambient interpreter state. This has caused false verification blockers and makes it unclear which dependencies are required for the repository's test and validation gates.

### 6.2 Decision to implement

Introduce one repository-level Python development environment as the canonical tooling environment.

The implementation should:

1. add a root `pyproject.toml` for shared tooling and test dependencies
2. declare supported Python versions explicitly
3. include `rdflib`, `pyshacl`, and the selected SPARQL validation dependency
4. include optional MORK community dependencies separately from the core Surface/MORK compiler set
5. define one reproducible lock workflow, preferably `uv.lock` with `uv`, or a committed constraints file if `uv` is not adopted
6. expose a documented command for installing the development environment
7. make CI use the same environment and lock data
8. remove stale module docstrings and README claims that say Python or rdflib are unavailable once the environment is adopted

The root environment must not silently replace `tools/mork/python/pyproject.toml`. The MORK package remains installable independently, while the root workspace environment provides the cross-package test and validation surface.

### 6.3 Dependency tiers

| Tier | Dependencies | Purpose |
|---|---|---|
| Core | `rdflib` | RDF parsing, canonicalisation, Surface, MORK compiler tests |
| Validation | `pyshacl`, OWL/RDFS reasoner selected by ADR | SHACL execution and ontology consistency checks |
| Query | selected SPARQL engine or `rdflib` query baseline | Generated SPARQL execution and parity |
| Optional inference | declared SWRL-capable reasoner | SWRL execution checks |
| MORK community | package-specific scientific and orchestration dependencies | MORK community pipeline tests, not required by Surface |

### 6.4 Acceptance criteria

- a clean environment installs all core and validation dependencies from repository metadata
- Surface and MORK focused suites pass from that environment
- SHACL governance and generated-shape checks run without ad hoc installation
- the CI command and local developer command are identical
- dependency versions are reviewable and reproducible

This addendum is a delivery prerequisite for the remaining verification gates, not a reason to defer them once the current environment can execute them.

### 6.5 Current implementation status

The root `pyproject.toml` now declares the shared core environment (`rdflib` and `pyshacl`) plus optional reasoning and MORK-community tiers. `requirements-lock.txt` pins the core validation closure, and `tools/README.md` documents the virtual-environment install command. A clean temporary environment installed from that lock and passed all 76 compiler tests plus the Phase 8 conformance gate. The optional community tier remains intentionally outside the core lock.
