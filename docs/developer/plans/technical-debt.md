<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Technical debt register

**Unit type:** Register, not a unit. It has no status record, no slices and no completion gate.
**Last collated:** 2026-10-03, from the in-flight CCS, AIR, NRS and identity-minting records, the
Surface outstanding-items record, and component READMEs.

## Purpose

Debt we have spotted and that no plan owns yet: a shortcut taken, a gap between what a component
claims and what it does, or a check that does not run. Without a register it is recorded in a
status line or a README footnote and lost.

**What goes in.** A defect or shortfall in something that already exists, with no planned home.

**What does not.** Outstanding work: features, follow-ups and deferred slices. They belong in their
unit's plan (for example the CCS plan's F1 follow-ups, or NRS tranche E). An item that gains a home
in a plan is removed from here, with the plan named in the commit.

Each entry says where it was spotted, what it costs while it stays, and the home it would most
likely take.

## Register

### Documentation

| # | Debt | Spotted | Cost while it stays | Likely home |
|---|---|---|---|---|
| TD-01 | The [Persistence README](../../../ontology/persistence/README.md) is not a literate specification. Its Turtle is excerpts, so `spec/persistence.ttl` and `shapes/constraints.ttl` cannot be regenerated from it, and `tools/literate_extract.py` cannot check it, as it does for Wording, Behaviour and Surface. Keep all of its content when fixing this | 2026-10-03, CCS F1 | the README and the spec can drift unnoticed | a Persistence documentation unit |

### Persistence compiler

From the first cut's [known limitations](../../../tools/persistence/README.md#known-limitations-first-cut-honestly-scoped).
The unit that shipped it, `persistence-compiler-iri-sync`, is closed.

| # | Debt | Spotted | Cost while it stays | Likely home |
|---|---|---|---|---|
| TD-02 | `unconditional-write` targets only a named-graph boundary. Provided or locking concurrency with a composite or no boundary fails to render | 2026-09-25 | those combinations cannot be generated | a Persistence compiler unit |
| TD-03 | `cas-replace-composite-property` follows only the first composite property of a boundary shape. Sibling properties need a path alternation | 2026-09-25 | a multi-property aggregate is written partly | a Persistence compiler unit |
| TD-04 | a composite boundary with `dal:AbsentRow` generates no create operation | 2026-09-25 | such a family has no first write | a Persistence compiler unit |
| TD-05 | infrastructure graph IRIs (`urn:g:dataset`, `urn:g:txn`, `urn:g:keys` and the rest) are constants, in an unregistered `urn:` namespace | 2026-09-25 | two deployments merged into one store collide | a Persistence compiler unit |
| TD-06 | `dal:txnShards`, `dal:logShards` and `dal:keyShards` resolve but no template applies them (`ShardingNotHonoured`) | 2026-09-25 | a declared shard count is silently a promise | a Persistence compiler unit |
| TD-07 | `dal:EquivalentClassScope` matching is syntactic, not entailment | 2026-09-25 | an equivalence a reasoner would find is missed | a Persistence compiler unit |
| TD-08 | the restore-runbook bindings (`dal:epochCoordinatorBinding`, `dal:erasureRegisterBinding`, `dal:erasureReplayOnRestore`) are emitted but no check reads them, and no template writes `pat:hlc` | 2026-09-25 | a configuration can name a runbook nothing verifies | housekeeping (ADR-A80) |
| TD-09 | a compiled profile's Turtle is isomorphic between runs but not byte-identical (blank-node labels) | 2026-10-03, CCS F1 | compiled profiles cannot be compared byte for byte, so `mise run build:persistence-execution` writes SPARQL and recipes only | a Persistence compiler unit |
| TD-10 | `examples/invalid-compositeboundary-missing-shape.ttl` is refused by the compiler with `CompositeBoundaryReceiptConflict` (the receipt-only default), before the missing shape is reached | 2026-10-03, CCS F1 | the compiler's `MissingBoundaryShapeError` has no fixture of its own | the next Persistence change touching fixtures |
| TD-15 | the compiler reads one `dal:appliesTo` per uniqueness constraint (`graph.value` in `resolver.py`), and silently uses one scope when a constraint names several | 2026-10-03, CCS F1 | a constraint meant for several classes protects one, with no warning | a Persistence compiler unit, with CCS FU-F1b |

### Ontology sources

| # | Debt | Spotted | Cost while it stays | Likely home |
|---|---|---|---|---|
| TD-16 | the Eligibility README is no longer the literate source of its documents: `tools/literate_extract.py --check` reports drift in `eligibility-vocab.ttl`, and no test or CI step runs it (Foundation's drift was fixed in CCS F1, Instrument's in C6) | 2026-10-03, CCS F1 | edits to the README or the file can diverge unnoticed | an Eligibility maintenance task |
| TD-17 | Behaviour's selection policies, activation policies and trigger kinds (`behaviour-vocab.ttl`) are not declared distinct. Their properties are functional, so a reasoner given Instrument's `owl:hasValue` axioms and a wrongly stated value infers that two policies are the same individual, and every regime transition then carries both. Fix: `owl:AllDifferent` over each group | 2026-10-04, CCS C7a | the error is reported by SHACL at every regime transition, not by the reasoner at the triple that caused it | CCS FU-C7a-a, a Behaviour vocab change |

### Test tooling

| # | Debt | Spotted | Cost while it stays | Likely home |
|---|---|---|---|---|
| TD-18 | the Python test suites under `tools/` take minutes to run. Ten ontology modules took 129 seconds for 383 tests during CCS C7b. Likely causes, unmeasured: each module parses the ontology stack at import, pySHACL validates against every layer's shapes per example, each reasoner row starts a JVM, and OWL RL closures run in pure Python. How to measure and what to try are in the [test suite performance sketch](../sketches/test-suite-performance.md) | 2026-10-05, CCS C7b | slow feedback on every change, and pressure to skip tests locally | a test tooling task: measure first, then a shared session fixture and batched reasoner calls |
| TD-19 | `mise run check:ontology-catalog` runs a fixed list of test modules that omits `tools/test_regimes.py` (CCS C7a) and `tools/test_terms_in_time.py` (CCS C7b), so no task and no CI run executes them | 2026-10-05, CCS C7b | a regression in regimes or terms in time goes unnoticed until someone runs the modules by hand | `mise.toml`, with TD-18, since adding them lengthens the task |

### Surface

From the [Surface outstanding items](../status/surface-outstanding-items.md) record, whose unit is
closed.

| # | Debt | Spotted | Cost while it stays | Likely home |
|---|---|---|---|---|
| TD-11 | Surface's `shapes/constraints.ttl` has never run under a SHACL engine. pySHACL refuses it outright ("A SPARQL Constraint must not contain a VALUES clause", from `srf:PromotionSignatureDisciplineShape` and any other shape using `VALUES`) | 2026-10-03, CCS F1, and §3.4 of that record | Surface's laws are checked by the compiler only, never by the shapes consumers would run | a Surface maintenance task (raised 2026-10-03) |
| TD-12 | profile identity is computed in the compiler, never asserted in the graph (`srf:profileIdentityHash`, §3.3) | 2026-09-25 | a generated surface does not say which profile produced it | a Surface change |
| TD-13 | entailment regimes other than `srf:NoEntailment` are refused, and parity cannot check `DefinitionOnly` forms (§3.5) | 2026-09-25 | the declared regimes are vocabulary without behaviour | a Surface change, after a reasoner choice |
| TD-14 | the MORK toolchain join assumptions are unconfirmed against a live checkout (§5) | 2026-09-25 | a renamed MORK term fails silently | a Surface and MORK integration task |
