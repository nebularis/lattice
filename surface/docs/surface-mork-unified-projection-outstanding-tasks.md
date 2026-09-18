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
| 2 | Surface compiler refactor and entailment policy | **Done, unverified.** |
| 3 | Surface-to-MORK lowering engine | **Done, unverified.** |
| 4 | MORK governance and versioning enhancements | **Done, unverified.** |
| 5 | Compiler family implementation (+ folded-in Eligibility tranche) | **Done, unverified, narrowed.** No native backend; no domain-binding layer; no profile-level artefacts; no runtime result tracking. |
| 6 | Eligibility tranche | **Substantially absorbed into Phase 5**, on user instruction. One deliverable not carried over (item 6 below). |
| 7 | Provenance and invalidation hardening | **Not started.** |
| 8 | Conformance and parity framework | **Not started.** |
| 9 | Migration and rollout | **Not started.** |
| 10 | Scale and optimisation | **Not started.** |

**The single fact that qualifies every "Done" above: nothing has been executed.** This environment has no Python interpreter and no SHACL/SPARQL/SWRL engine. Every piece of code and every shape in Phases 2–5 has been written and reviewed by careful reading, not run. Treat every first execution as part of code review, not as a regression check — this is stated in each affected module's own docstring, and is restated here because it is the top-priority blocker for everything else in this document.

---

## 2. Immediate priority: verification debt

Nothing below matters until this is done, because every other outstanding item assumes the Phase 2–5 work is correct, and that has not been checked mechanically.

1. **Run the Surface compiler test suite.** `python -m unittest tools.surface.test_surface -v` from the repository root. Covers Phases 1–3: `ProjectionContract` parsing (laws P2–P5), entailment-regime guard, stack composition (ADR-A21), lowering (`lower_projection`, `lower_contract`, `lower_all`, dependency edges).
2. **Run the MORK compiler test suite.** `python -m unittest tools.mork_compilers.test_mork_compilers -v`. Covers Phase 5: the Eligibility IR, and the SPARQL/SHACL/SWRL backends.
3. **Run `tools/literate_extract.py --check`** across every layer README to confirm no extraction drift was introduced while editing `surface/README.md`.
4. **Load `mork/spec/Mork.ttl` + `mork/spec/Executable.ttl` + `foundation/vocab/foundation-vocab.ttl` into a real OWL reasoner** and confirm consistency — the new `fnd:Governable`/`fnd:Version` axioms on `mork:GenerativeMapping` (ADR-A22) and the punned `elg:`/`qnt:` references in `Executable.ttl` have only been checked by hand.
5. **Run `mork/shapes/constraints.ttl`** (governance shapes) and the SHACL shapes `tools/mork_compilers/shacl_backend.py` generates, against a real SHACL engine, using the fixtures already written for exactly this purpose:
   - `mork/examples/Governance/GovernanceAndVersioning.ttl` (expected pass/fail cases documented inline)
   - `eligibility/examples/interval-containment.ttl` compiled through `shacl_backend.compile_shapes`
6. **Execute the generated SPARQL query** (`sparql_backend.compile_query_template`) against `eligibility/examples/interval-containment.ttl` and confirm `ex:question-1` resolves to `"Permitted"`.
7. **Load the generated SWRL rule** (`swrl_backend.compile_rules`) into a SWRL-capable reasoner and confirm it derives `exe:impliesDecision(ex:question-1, elg:Permitted)`.
8. **Regenerate and commit real output** where a "no hand-written golden" note was left deliberately:
   - `surface/execution/` packages (see `surface/execution/README (1).md` for the exact command)
   - a lowered MORK mapping graph for `surface/examples/saas-subscription-arr-projection.ttl` (`python -m tools.surface lower ...`)

---

## 3. Deferred or carved-out items inside "done" phases

These were identified, scoped, and explicitly *not* built during Phases 1–5, rather than silently missed. Each has a pointer to where the reasoning lives.

| Item | Tag | Where it's recorded |
|---|---|---|
| `srf:RangePartitionPopulation` (bucketing law X7) | Deferred, planned | [OUTSTANDING-ITEMS.md](OUTSTANDING-ITEMS.md) §2.1 — needs Quantification partition semantics first |
| Stacking beyond depth 1 (cycle detection, hash-chain freshness) | Deferred, planned | [OUTSTANDING-ITEMS.md](OUTSTANDING-ITEMS.md) §2.2, composition laws already stated in [ADR-A21](../../docs/adr/ADR-A21-signature-scope-composition-for-stacked-surfaces.md) |
| `srf:ExternalIndex` admission criteria | Deferred | [OUTSTANDING-ITEMS.md](OUTSTANDING-ITEMS.md) §2.3 |
| Foundation migration boundary for `srf:DerivedArtefact` (does it move to Foundation?) | Decision needed | [OUTSTANDING-ITEMS.md](OUTSTANDING-ITEMS.md) §3.1; boundary *criteria* (not the decision itself) recorded in `mork/docs/governance-and-versioning-migration.md`'s own "Foundation migration boundary" section |
| `srf:profileIdentityHash` — assert profile identity into the graph, or keep it a pure computation | Blocked | [OUTSTANDING-ITEMS.md](OUTSTANDING-ITEMS.md) §3.3, depends on the item above. `Profile.identity_hash()` exists as a Python-only computation (Phase 2) pending this |
| R2 parity wired to a **shared** conformance corpus (not contract-generated questions) | Deferred | [OUTSTANDING-ITEMS.md](OUTSTANDING-ITEMS.md) §3.4, tracked under [ADR-A28](../../docs/adr/ADR-A28-parity-and-conformance-release-gate.md) — this is Phase 8's job |
| Entailment regimes beyond `NoEntailment` (RDFS/OWL2EL/OWL2DL reasoner integration) | Deferred | [OUTSTANDING-ITEMS.md](OUTSTANDING-ITEMS.md) §3.5; `check_entailment_regime()` (Phase 2) currently refuses all of these outright rather than acting on them incorrectly |
| MORK toolchain join assumptions (namespace/term-name assumptions in `tools/surface/mork.py`) | Decision needed | [OUTSTANDING-ITEMS.md](OUTSTANDING-ITEMS.md) §5 — needs confirming against a live `mork/spec/Mork.ttl` checkout, not re-guessed |
| **"Executable Projection Contract" (`exp:`) domain-binding layer** — lets a domain ontology declare "my `loans:creditScore` supplies candidate evidence" instead of a compiler reading `elg:Question` directly | Decision needed (ADR-scale) | `mork/docs/eligibility-executable-compiler.md` — proposed in `surface/docs/MorkEnhancements.md`'s final section; deliberately not adopted as a side effect of Phase 5 |
| Profile-level aggregate artefacts (`AllRequired`/`AnySufficient` combining several conditions into one SPARQL/SHACL/SWRL decision) | Deferred | `mork/docs/eligibility-executable-compiler.md`; `exe:ProfilePlan` is declared in the ontology and computed in Python (`compile_profile`) but no backend emits RDF for it yet |
| Runtime result tracking (`exe:EvaluationRun`, `exe:ConditionResult`, `exe:Diagnostic`) | Deferred | `mork/docs/eligibility-executable-compiler.md` — this phase compiled artefacts, it did not run them |
| "Native" MORK compiler backend | **Not planned until defined** | No document in this repository defines what a native artefact is; ADR-A23's addendum records this explicitly rather than inventing one |
| Type adapters (e.g. decimal literal → `qnt:Quantity`) for candidate evidence not already shaped as Quantification terms | Not started | Named in `surface/docs/MorkEnhancements.md` §10 ("Type adaptation"); has no home yet since it depends on the `exp:` layer decision above |
| Eligibility strategies beyond `IntervalContainment` (`ExactCondition`, `SetMembershipCondition`, `WildcardCondition`) | Not started | `tools/mork_compilers/eligibility_ir.py`'s own scope note |
| Range-partition two-track remediation wired to an implementation backlog (original Phase 6 deliverable 6) | Not started | Depends on the Quantification partition-semantics item above; never picked up because Phase 6 was folded into Phase 5 around the interval-containment case only |

---

## 4. Remaining phases, as originally planned

### Phase 7 — provenance and invalidation hardening

Not started. Deliverables per the source plan: full provenance chain from a generated result back to source declarations; read-set capture across Surface, MORK, and generated artefacts; an invalidation policy for graph/profile/mapping-version changes; a regeneration planner for minimal-impact rebuilds; a canonicalisation cutover runbook.

Groundwork already in place to build on: Surface's read-set/hash model (ADR-A12, `srf:ReadSetEntry`), the stack-composition laws (ADR-A21), and MORK's new governance/version model (ADR-A22) all bear directly on this phase and did not exist when the source plan was first written.

### Phase 8 — conformance and parity framework

Not started, and the phase this repository most needs next given how much of Phases 2–5 is marked "unverified". Deliverables: extend the shared conformance corpus to cover Projection; a parity harness comparing source versus generated query behaviour; CI regression gates for determinism and parity; a defect-fixture corpus; SHACL execution and extraction-drift as mandatory CI checks.

This phase is also where the R2-parity-to-shared-corpus item (§3 above) belongs, and where the Eligibility interval-containment conformance corpus (originally a Phase 6 exit criterion) should land.

### Phase 9 — migration and rollout

Not started. Deliverables: migration guides for existing Surface and MORK authors; a compatibility mode and deprecation policy; phased rollout profiles (draft/review/production — MORK's `mork:CompilationMode` from Phase 4 is the concrete mechanism this phase would roll out); a release checklist.

### Phase 10 — scale and optimisation

Not started. Deliverables: performance baselines for lowering and compilation; a caching strategy for intermediate graphs; large-vocabulary and large-population stress tests; a high-throughput generation profile.

---

## 5. Suggested next-step order

1. **Get Python (and ideally an rdflib + a SHACL/SPARQL/SWRL engine) into an environment that can run this repository's tooling**, and work through §2 above. Nothing else can be trusted until this happens.
2. Fix whatever §2 turns up. Given the volume of hand-written code across five phases, expect to find something.
3. Make the two ADR-scale decisions §3 is blocked on: the `exp:` Executable Projection Contract layer (yes/no, and if yes, its own ADR), and the `srf:DerivedArtefact` Foundation-migration question.
4. **Start Phase 8 (conformance and parity) before, or at least alongside, Phase 7** — it is what turns "unverified" into "verified" for everything already built. The source plan's own §15.2 groups Phases 7 and 8 together as concurrent, ahead of first production rollout (Phase 9/10); given how much of Phases 2–5 here is still unverified, treat Phase 8's gates as the more urgent half of that pair rather than a strict co-requirement.
5. Phase 7, then Phase 9, then Phase 10, matching the source plan's own §15.2 sequencing.
