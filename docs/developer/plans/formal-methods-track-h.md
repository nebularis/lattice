<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: Formal Methods, Track H: Persistence

**Unit ID:** `formal-methods-track-h`
**Unit type:** Phase (Epic Decomposition Model, `copilot-instructions.md`)
**Epic:** [formal-methods](formal-methods.md)
**Sketches:** [formal-methods-track-h.md](../sketches/formal-methods-track-h.md) (main),
[formal-methods-track-h-protocols.md](../sketches/formal-methods-track-h-protocols.md) (rung T4,
the centrepiece), [formal-methods-track-h-specification.md](../sketches/formal-methods-track-h-specification.md)
(the specification registry and the typed IR, the enabling move)
**Status record:** [formal-methods-track-h.md](../status/formal-methods-track-h.md)
**Decided by:** [ADR-A-FM4](../../architecture/decisions/ADR-A-FM4-persistence-formal-methods-home-and-scope.md)
(Proposed: home and scope. Tracks A-FM2's and A-FM3's conventions for mechanised theories and
design-time models, excludes all relational/SQL work)
**Source:** [persistence-fml.md](../notes/rdf-engine/persistence-fml.md), an independent,
exhaustive review of the Persistence layer against this epic's own techniques
**Status:** Proposed. Not started. Needs nothing from tracks A-G to begin: it reuses their
methods (Isabelle, Alloy, the claim/gate discipline) but has its own capability-record,
specification-registry and protocol-model work with no cross-track blocker

## 1. Scope

Formal methods applied to the `dal:` configuration vocabulary, `tools/persistence`'s compiler and
its generated SPARQL, and the pluggable RDF-store backends it targets — the **RDF and SPARQL side
of Persistence only** (sketch §2). **Explicitly, permanently out of scope for this entire track:
any relational or SQL-compilation work**, which is a separate review
([sql-feedback.md](../notes/rdf-engine/sql-feedback.md)) naming its own, different formal-methods
programme, not read as this track's scope (ADR-A-FM4 decision 1).

This plan details **H1** (static hygiene: the cheapest, no-new-toolchain fixes, startable
immediately) in full, and **H2, H3** (the typed IR and the specification registry — the enabling
move) in enough detail to begin, since both are natural, low-risk follow-ons to H1 using tools
already in the repository (Python, no new install). **H4 onward stay at outline level** (§4) until
H1-H3 land, per the Epic Decomposition Model's rolling-wave rule, the same discipline every other
track in this epic already follows for its own later slices.

## 2. What this plan depends on, and what blocks it

| Dependency | State | Blocks |
|---|---|---|
| `tools/persistence`'s existing compiler, templates, shapes and examples | exist, stable (ADR-A78, ADR-A79, ADR-A80) | nothing — H1 reads and checks what exists today |
| an ADR for this track's home and scope | [ADR-A-FM4](../../architecture/decisions/ADR-A-FM4-persistence-formal-methods-home-and-scope.md), drafted 2026-10-08, **Proposed, not yet accepted** | nothing blocking for H1 (pure analysis and additive checks, no new top-level directory needed yet); H5's protocol models should wait for ADR-A-FM4's acceptance, since they are the one place the ADR's own "marginally widens an existing convention" point (decision 3) matters |
| track E's Isabelle pattern (`tools/proofs/<layer>/`) | established (ADR-A-FM2) | H6 only — reused, not re-decided |
| track C's Alloy pattern (`tools/models/<topic>/`) | established (its own plan §4) | H5, H7 — reused, not re-decided |
| a TLA+ or Quint toolchain | **not installed, not chosen** | H5's protocol models only. H1-H4 need no new toolchain at all |
| track A (the ledger and the harness) | not started (epic status) | nothing — this track's own claims and Validation Packs are the interim record, same arrangement tracks B and C already use |
| CCS, insurml-alignment | no direct dependency either way | nothing. Persistence's own compiler and layer are not gated by either epic's own slices |

## 3. H1: static hygiene — ready to start

The cheapest items in the review, needing no new toolchain, each tied to a specific, named finding
(review §18, priority items 1-4; §12; §7.4; §8.1).

### H1.1: the prefix antichain and overlap check

- A static check over every declared `dal:graphPrefix` and `dal:iriPrefix` value: do the declared
  prefixes form an antichain (no one a proper prefix of another) or, if a longest-prefix rule is
  intended, is it actually implemented? Reports a counterexample IRI when it is not.
- **Closes:** the main sketch's L3 gap, specifically the finding that `dal:GraphPatternScope`'s
  "unscoped fallback for instances outside any of them" is only well-defined if the declared
  prefixes form an antichain, which nothing checks today (review §6.2, finding #2).
- **Validation:** a fixture with two overlapping prefixes (for example `urn:g:lending/` and
  `urn:g:lending/behaviour/`) must fail the check with the overlapping pair named; a fixture with
  a genuine antichain must pass.

### H1.2: witness coverage for every rule, shape, warning and audit

- A harness that, for every refusal rule, warning, SHACL shape and always-on audit query in
  `tools/persistence`, requires at least one fixture that **triggers** it (a non-vacuity check,
  review §7.4) — not only a fixture that satisfies it. Missing coverage is a build failure, listed
  by rule/shape/audit name, mirroring `tools/check_formal_freshness.py`'s own existing discipline
  for Eligibility's laws.
- **Closes:** the review's own calibration-table defects D.3 A6 (a shape that could never fire)
  and D.1's `sh:prefixes` defect (a constraint that silently targeted nothing), both vacuity
  failures a non-vacuity check would have caught in seconds.
- **Validation:** seed one deliberately-vacuous rule (a refusal condition that can never be true
  given the other rules) and confirm the harness reports it as uncovered; confirm every existing
  rule, shape and audit in `tools/persistence` today either has a witness or is listed as a gap.

### H1.3: static template checks (S-3, S-4)

- Two checks over every generated SPARQL template and its parameter-binding list, run per compile:
  **S-3**, every variable in an INSERT template is bound in every solution, or is on an explicit,
  named allow-list of deliberately-optional positions; **S-4**, no blank nodes appear in any
  INSERT template at all (a SPARQL fact: blank nodes in an INSERT template are fresh per solution
  per execution, so a retry is not a no-op, and blank nodes are illegal in DELETE templates
  outright).
- **Closes:** the review's own judgement that these are "the two I would implement first," given
  their severity (a silently missing triple reintroducing a confirmation-outcome defect; a retry
  that silently inserts a second set of fresh blank nodes) and the fact that both are statically,
  fully checkable from the template text alone, today, without any new toolchain.
- **Validation:** run against every template `tools/persistence` currently generates; a template
  violating S-3 or S-4 (seeded deliberately in a copy, not the real templates, unless a real
  violation is found) must fail with the specific variable or blank node named.

### H1.4: enumerate the declaration/implementation gap, as data

- A report, generated per compile, listing every resolved `dal:` dimension whose value the
  generated SPARQL does **not** actually implement: declared shard counts not honoured,
  infrastructure graph IRIs that are compiler constants regardless of configuration, retention and
  epoch bumps delegated to housekeeping, a composite boundary that binds only the first property
  its shape reaches. Each entry names whether it is a caller obligation, a housekeeping
  obligation, or genuinely unimplemented.
- **Closes:** the main sketch's L6 gap directly — review finding #9, which treats the composite-
  boundary case specifically as a soundness bug (an unswept closure member leaves exactly the
  dangling triple whole-replace exists to prevent), not a mere limitation. **This report should
  flag that specific case as a refusal, not a documented limitation**, pending H2/H3 or a direct
  fix to the composite-boundary templates (this track reports the gap; fixing
  `tools/persistence`'s own templates is that package's own follow-up, same division of labour
  track B already uses for defects it finds in `tools/mork_compilers`).
- **Validation:** run against `tools/persistence`'s current examples; the composite-boundary gap
  must appear in the report, named, with the specific shape and property it was found against.

### H1.5: stable compiled-profile labels

- Fix blank-node labelling in compiled profiles so that re-compiling the same configuration twice
  produces byte-identical output, closing the determinism gap the review names (§16.4) that
  currently prevents compiled profiles from being committed and diffed the way generated SPARQL
  already is.
- **Validation:** compile one example twice, confirm byte-for-byte identity of the compiled
  profile (not only the rendered `.rq` files, which already have this property per `tools/
  persistence`'s own existing determinism test, if one exists — confirm it covers the compiled
  profile too, not only the final SPARQL text).

**H1's overall validation:** one command runs all five checks across every example
`tools/persistence` ships today, and the report is read by a human before any of H2 onward
starts, since H1.4's gap enumeration in particular may change what H2/H3 treat as urgent.

## 4. H2, H3: the typed IR and the specification registry

Detailed in [their own sketch](../sketches/formal-methods-track-h-specification.md). Two slices,
H2 first (the typed IR, since it is the smaller, more self-contained change and several of H1's
own checks — S-3, S-4, the term/value divergence — become structural guarantees once it exists
rather than external checks running against untyped template text) and H3 second (the
specification registry, which generates the rules, the selection table and the README's own
tables from one source, closing the review's finding #3 drift and enabling the exhaustive
cross-axis validation H4 needs as its input).

**H2 (typed IR), outline:**
- Give `tools/persistence`'s compiler an intermediate representation for a generated operation:
  typed parameters, a declared read/write set per operation (direct input to H5's protocol
  models), guards tagged `Term`/`Value`, template variables tagged `Bound`/`OptionalAllowed`.
- Rewrite the emitter to render from this IR, not from ad hoc string templates.
- **Validation:** every hazard in the specification sketch's own table (§3) becomes a type error
  rather than a runtime or static-check finding; re-run H1.3's checks against the new emitter's
  output and confirm they now pass by construction, not by a separate pass.
- This is an **addendum to ADR-A79** (persistence compiler toolchain), dated, when this slice is
  detailed for real — not decided here, and not a new formal-methods ADR (ADR-A-FM4 decision 4).

**H3 (specification registry), outline:**
- One machine-readable registry (syntax not yet chosen, specification sketch §2) generating:
  `shapes/constraints.ttl`'s cross-axis rules, the compiler's own validation predicate and
  selection table, the README's own rule tables, a new obligation-set field per generated
  operation (review's PV-D2), a new laws-held field per compiled target (PV-D5).
- **Validation:** the generated shapes and the generated compiler predicate are checked against
  each other for agreement (closing finding #3's drift, review §7.3's V2/V3), and against the
  pre-existing hand-written versions for a one-time migration diff, reviewed by a human before
  the hand-written versions are retired.
- Also an **ADR-A79 addendum** when detailed, per ADR-A-FM4 decision 4.

## 5. H4 onward, outline only

| Slice | Delivers | Rung | Depends on |
|---|---|---|---|
| H4 | exhaustive cross-axis validation (BDD/SMT) over the registry's own rule data: V1-V10 (review §7.3), most valuably V2 (no shape/compiler disagreement, checked universally) and V10 (every guarantee-forfeiting combination is warned, naming the law) | T3 | H3 |
| H5 | **the capability-record extension** (full `StoreCapabilities`, three-valued, `unknown` pessimistic, bound to a TCK report digest — review's PV-D1), **the TLA+/Quint toolchain spike**, and **protocol models A-D** (guarded CAS, append form, first-write/create race, key claim) — the main sketch's matrix idea, first four cells | T4 (first use anywhere in this epic) | H2 (read/write sets from the IR), nothing else |
| H6 | Isabelle theories: `Resolution.thy` (determinism, locality, winner dominance, the capability-monotonicity-fails negative lemma), `Positions.thy` (order agreement of zero-padded positions, injectivity of revision IRIs), `Encoding.thy` (injectivity of the request-digest encoding, with the canonicalisation gap named as an explicit hypothesis, not assumed away), `Outcomes.thy` (totality, disjointness and soundness of the confirmation procedure, relative to an abstract history predicate H5's models discharge) | T5 | H1 (resolver as currently specified), H5 (for `Outcomes.thy`'s history predicate) |
| H7 | protocol models E-J (outcome classification, epoch bump/restore, retention/pruning, global read, fencing, infrastructure-graph writers — expected to be the single richest source of new findings, nothing there is guarded today) | T4 | H5, H6 |
| H8 | protocol models K-N (erasure, multi-aggregate writes, bulk load/cutover, shard migration), plus grounding every model built so far against at least one real MVCC-style backend (isolation probes, history checking, predicted-anomaly reproduction) | T4/T7 | H7 |
| H9 | detection-coverage closure: generate the nine missing audits the review names (L11's gap) from the same invariants H4's registry states, Alloy detection-completeness/soundness obligations per invariant, applicability labelling so a not-applicable audit cannot be read as "clean" | T2/T0 | H3, H4 |
| H10 | runtime monitors from the same invariants (T7): housekeeping evidence, capability drift, declaration drift, an erasure audit, a position-reuse audit, feeding track A's ledger once it exists | T7 | H9 |

## 6. Milestones

| # | Outcome | Slice |
|---|---|---|
| FMH1 | every rule, shape, warning and audit in `tools/persistence` has a witness fixture or is listed as a gap; S-3/S-4 pass on every shipped template; the declaration/implementation gap is enumerated as data, not prose | H1 |
| FMH2 | the compiler's emitter cannot produce an untyped, unbound-variable, blank-node-bearing or term/value-confused operation, by construction | H2 |
| FMH3 | the cross-axis rules exist in exactly one hand-written place, with the shapes, the compiler and the README all generated from it and checked to agree | H3 |
| FMH4 | the first capability × strategy matrix cell exists, generated by a protocol model, not hand-written, with a named counterexample for at least one known-unsafe baseline | H5 |
| FMH5 | the resolver's capability-monotonicity-fails negative lemma is proved, mirroring Eligibility's own De Morgan negative lemma | H6 |
| FMH6 | at least one real backend has been grounded against a model's prediction, with a reproduced or a model-correcting result | H8 |
| FMH7 | every invariant the review names has a detector, with applicability correctly labelled | H9 |

## 7. Metrics and abandonment conditions

Following the epic's own §6 discipline, declared now rather than discovered mid-track:

| Metric | Measures |
|---|---|
| vacancy rate closed | the fraction of H1.2's witness-coverage gaps closed per slice |
| matrix cells populated | how many (strategy, capability-profile) cells have a generated, grounded guarantee, out of the total the compiler's own strategy/profile space implies |
| grounding agreement rate | the fraction of a model's predicted counterexamples that reproduce on a real backend, versus corrections needed to the model |
| static-check false-positive rate | for H1-H4's checks specifically, since a check too eager to refuse a legitimate configuration is as costly as one that misses a real defect |

| Signal | Action |
|---|---|
| the TLA+/Quint spike (H5) cannot carry model A to a result (pass or counterexample) within a budget comparable to track D's own prover spike | do not proceed past models A-D. H1-H4, H6 and H9-H10 do not depend on protocol models at all and continue regardless |
| grounding (H8) finds a model's prediction does not reproduce on any real backend across two consecutive attempts | the model's own assumptions are wrong; revise or retire that specific model before building on it further, do not accumulate unverified models |
| the witness-coverage check (H1.2) finds more than half of `tools/persistence`'s existing rules lack a witness | this is itself the finding, not a reason to stop — it means H1 is doing its job |

## 8. Decisions for the human

None of these may be taken by an agent.

| # | Decision | Recommendation | State |
|---|---|---|---|
| H-D1 | accept, revise or reject [ADR-A-FM4](../../architecture/decisions/ADR-A-FM4-persistence-formal-methods-home-and-scope.md) | accept, including its point 3 (TLA+/Quint models share `tools/models/` with Alloy) | open |
| H-D2 | TLA+ or Quint, for protocol models | undecided; H5's own toolchain spike decides it on measured evidence, the same discipline track D used for Rocq vs Isabelle | open, deferred to H5 |
| H-D3 | whether the specification registry's and typed IR's design (H2, H3) are recorded as an ADR-A79 addendum or a fresh ADR | recommend an addendum, dated, per ADR-A-FM4 decision 4 and this repository's own practice for a decision found while building | open, deferred to H2/H3 |
| H-D4 | whether the composite-boundary soundness gap (H1.4's flagged finding) is fixed immediately as a `tools/persistence` defect, or left as a documented, refused combination until H2's typed IR makes the fix structural | recommend: refuse the combination now (cheap, one line in the existing validation predicate), fix properly once H2 lands | open |
| H-D5 | whether track H's claims feed track A's ledger once it exists, or keep their own interim Validation-Pack record permanently | recommend: feed track A once it starts, per ADR-A-FM4 decision 7 | open, not urgent |

## 9. Alignment with other work

| Unit | Item | Relationship |
|---|---|---|
| this epic, track A | the ledger and the harness | track H's claims feed it once it exists (H-D5); until then, Validation Packs are the interim record |
| this epic, track B | the reference semantics and the oracle | no direct dependency; track H does not need a Python reference oracle in track B's sense (there is no independent "meaning" of `dal:` configuration beyond the compiler itself, unlike Eligibility's laws). B2.1's hardening work (seed a compiler-side fault) is a methodological sibling to H1.2's witness-coverage work, not a dependency |
| this epic, track C | the design-time models | H5/H7's protocol models reuse track C's `tools/models/` home (ADR-A-FM4 decision 3) and its "bounded scope, never read as a proof" discipline directly |
| this epic, track E | the prover programme | H6 reuses track E's `tools/proofs/` home (ADR-A-FM2) and gate discipline unchanged, including the hardening items E1.4 queues (digest transitive definitions, characterising lemmas) — H6's own Isabelle work should apply E1.4's fixes from the start, not repeat the gaps it found |
| CCS, insurml-alignment | — | no direct dependency either way |
| the platform, `workers/` | housekeeping jobs, the outbox, the store SPI | H9/H10's generated monitors extend `tools/persistence`'s own existing housekeeping boundary (ADR-A80), not a new runtime |

## 10. Risks

- **The cross-axis rule space (1.3×10⁸ combinations) may strain a naive BDD encoding** before
  one-hot consistency constraints and shard-count/identity-role multiplicities are added (review
  §7.2's own caveat). H4's own first action is a size check before committing to exhaustive
  checking as stated.
- **TLA+/Quint authoring cost for a protocol as detailed as the guarded-write path (model A) may
  exceed the toolchain spike's own budget**, the same risk track D's prover spike carried for
  Isabelle/Rocq. The spike's own abandonment condition (§7) is stated for exactly this reason.
- **Grounding (H8) needs a real MVCC-style backend available to this project's own CI/development
  environment.** If none is practically available, grounding stays a human-run, off-CI activity,
  recorded as such rather than silently skipped.
- **The declaration/implementation gap (H1.4) may be larger than this sketch assumes** once
  enumerated — if so, that is itself the most important finding this track could produce, not a
  reason to narrow its scope.

## 11. Out of scope

Everything named in the sketch's §2 and §6: any relational/SQL-compilation work, full SPARQL or
store-engine mechanisation, verifying third-party engines, replacing `tools/persistence`'s Python
compiler wholesale, any ontology change ahead of a specific slice's own ADR, building a second TCK
from scratch (the existing one is extended, not replaced).

## 12. Documentation deltas

At H1's gate: `tools/persistence/README.md` (the new checks and how to run them),
`docs/developer/plans/formal-methods.md` and `docs/developer/status/formal-methods.md` (track H
added to the track board). At H5's gate: root `README.md` (the new TLA+/Quint toolchain, if a
native install or image route is added), `mise.toml` (new `check:persistence-formal-*` tasks),
`docs/architecture/ontology-architecture.md` (the capability-matrix idea, once it has its first
populated row). At H9/H10's gate: `docs/architecture/semantic-platform.md` (new monitor job
families), the ADR catalogue (the ADR-A79 addenda from H2/H3, if taken).
