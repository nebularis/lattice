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
| TD-16 | **Four READMEs are not, or no longer, the literate source of their documents** (widened 2026-10-06 from Eligibility alone). `tools/literate_extract.py --check`, run 2026-10-06, finds:<br>**Foundation**: the spec and `shapes/constraints.ttl` are in sync (CCS F1, checked by `tools/test_keys.py`), but the README has no extraction contract, and `shapes/structural.ttl` and `shapes/rules.ttl` have no source in it.<br>**Vocabulary**: `spec/vocabulary.ttl` differs in content from the README's blocks (8 triples only in the README, 13 only in the file). No shape file and no extraction contract are in the README.<br>**Party**: `spec/party.ttl` differs in content (9 triples only in the README, 13 only in the file), and is in Protégé's layout rather than the extractor's. `vocab/party-vocab.ttl` is sourced from no README block (`vocab/README.md` holds its blocks as `turtle-spec`). No shapes or extraction contract in the README. Party was edited by hand in CCS C7c, beside its README.<br>**Eligibility**: the spec differs in layout only. `vocab/eligibility-vocab.ttl` has 3 triples the README lacks, and `shapes/constraints.ttl` differs substantially (78 triples only in the README, 19 only in the file). Its one shapes block has no declared target.<br>No test runs the check for Vocabulary, Party or Eligibility. To resolve, per layer: an extraction contract section naming every file, every Turtle construct in a fenced block of the right tag, the files regenerated and diffed for isomorphism against `HEAD` (only formatting may differ, as Quantification's restoration in CCS C7b showed), a version bump where the text changes, and a test running `--check`, as Wording, Behaviour, Surface, Quantification and Instrument have. Keep every piece of the READMEs' content | 2026-10-03, CCS F1. Widened 2026-10-06, before CCS C8b | edits to a README or a file diverge unnoticed, and a reviewer reading a README may read a different ontology from the one the tools load. Which side is right in each difference is not yet examined | an ontology sources maintenance unit, one slice per layer, Party first |
| TD-17 | Behaviour's selection policies, activation policies and trigger kinds (`behaviour-vocab.ttl`) are not declared distinct. Their properties are functional, so a reasoner given Instrument's `owl:hasValue` axioms and a wrongly stated value infers that two policies are the same individual, and every regime transition then carries both. Fix: `owl:AllDifferent` over each group | 2026-10-04, CCS C7a | the error is reported by SHACL at every regime transition, not by the reasoner at the triple that caused it | CCS FU-C7a-a, a Behaviour vocab change |
| TD-20 | **`fnd:Version` reads wrongly as a class name.** Foundation's mixin marks a class whose members are versions of a persistent identity, carrying `fnd:hasIdentity` and linked by `fnd:supersededBy`. Its name makes prose say "an instrument *is* a Version", which reads as nonsense, and "an instrument *has* a version" describes something else. Rename it `fnd:Versioned`, so an instrument "is versioned", as Foundation's other mixins already read (`fnd:Evidenced`, `fnd:TemporallyScoped`). Measured 2026-10-07: 199 uses of `fnd:Version` in 66 tracked files, across every substrate layer's spec, shapes and README (Foundation, Vocabulary, Quantification, Party, Eligibility, Behaviour, Wording, Instrument, Surface), applied layers, tools' tests and about 30 documents. The rename is breaking for Foundation at 0.x (ADR-A113) and cascades to every importer and to Open CBAA. Options for the plan to weigh: a straight rename in one cascade, or `fnd:Versioned` added with `fnd:Version` kept as a deprecated equivalent class for one release, so consumers migrate before it is removed. Prose follows the interim rule in `.github/copilot-instructions.md` ("versioned" for the class, "a version" only for one version node) | 2026-10-07, CCS C9 brief | every README and ADR explains versioning in words that misread, and each new layer adds more uses to migrate | a Foundation maintenance unit, planned with its full cascade |

### Test tooling

| # | Debt | Spotted | Cost while it stays | Likely home |
|---|---|---|---|---|
| TD-18 | the Python test suites under `tools/` take minutes to run. Ten ontology modules took 129 seconds for 383 tests during CCS C7b. Likely causes, unmeasured: each module parses the ontology stack at import, pySHACL validates against every layer's shapes per example, each reasoner row starts a JVM, and OWL RL closures run in pure Python. How to measure and what to try are in the [test suite performance sketch](../sketches/test-suite-performance.md). `check:ontology-catalog` now also runs the C7a and C7b modules, which lengthens it | 2026-10-05, CCS C7b | slow feedback on every change, and pressure to skip tests locally | a test tooling task: measure first, then a shared session fixture and batched reasoner calls |
| TD-22 | **`check:spc` passes without running a test.** `tools/spc/erlang/mix.exs` declares `apps_path: "apps"`, but `spc_boundary/` and `spc_engine/` sit directly under `tools/spc/erlang/`. Every source file's header comment and `tools/spc/python/pipeline.sh` assume the `apps/` path, so the fix is moving the two directories, not editing `apps_path`. Moved here from a developer note retired by ADR-A117 | 2026-09-29, recorded 2026-10-07 | `mise run check` reports SPC as checked when nothing ran | an SPC maintenance task, with the path move confirmed by the human (ADR-A77) |

### Surface

From the [Surface outstanding items](../status/surface-outstanding-items.md) record, whose unit is
closed.

| # | Debt | Spotted | Cost while it stays | Likely home |
|---|---|---|---|---|
| TD-11 | Surface's `shapes/constraints.ttl` has never run under a SHACL engine. pySHACL refuses it outright ("A SPARQL Constraint must not contain a VALUES clause", from `srf:PromotionSignatureDisciplineShape` and any other shape using `VALUES`) | 2026-10-03, CCS F1, and §3.4 of that record | Surface's laws are checked by the compiler only, never by the shapes consumers would run | a Surface maintenance task (raised 2026-10-03) |
| TD-12 | profile identity is computed in the compiler, never asserted in the graph (`srf:profileIdentityHash`, §3.3) | 2026-09-25 | a generated surface does not say which profile produced it | a Surface change |
| TD-13 | entailment regimes other than `srf:NoEntailment` are refused, and parity cannot check `DefinitionOnly` forms (§3.5) | 2026-09-25 | the declared regimes are vocabulary without behaviour | a Surface change, after a reasoner choice |
| TD-14 | the MORK toolchain join assumptions are unconfirmed against a live checkout (§5) | 2026-09-25 | a renamed MORK term fails silently | a Surface and MORK integration task |

### InsurML and ownership

Gaps in who owns what once InsurML components are used. None has a decision, and none is decided
here. Each names the questions an owner must answer.

| # | Debt | Spotted | Cost while it stays | Likely home |
|---|---|---|---|---|
| TD-23 | **Ownership, versioning and verification of InsurML components are not settled.** Open questions. (a) Who owns a component, and a composite built under assembly from components with several authors, including the rights each author keeps over their part and over the whole. (b) How a component, an assembly and each author's contribution are versioned, and whether an assembly pins component versions or ranges, and what a new component version does to an assembly that used the old one. (c) Who owns the verification and validation tooling for components and assemblies, meaning the checks, the fixtures and the verdicts, and whose verdict binds when LATTICE's checks and InsurML's own disagree | 2026-10-08, human request | an assembled wording has no accountable owner or version story, so a change to one author's component cannot be traced, attributed or re-verified, and a failing check has no one to take it | the IMA plan's assembly interface phase (4) and its decisions, with an ADR once the principle is chosen |
| TD-24 | **Where the vocabulary and definition layers, with their SHACL rules, belong is not decided.** The vocabulary and definition layers of InsurML-facing content, including the shapes that constrain them, can sit in LATTICE's substrate, in an applied ontology, or with InsurML's own owner. Open questions. Who owns and releases each, who may change a SHACL rule and how a change is versioned, and whether a shape is part of the layer's contract or an adopter's check. Today the layers' READMEs, specs and shapes are in this repository under `ontology/`, with no statement of ownership for InsurML-derived terms | 2026-10-08, human request | a term or rule can be changed by whoever edits the file, ownership of InsurML-derived vocabulary is implied by location, and a release of one party's layer can break another's shapes | an ADR on ownership of the vocabulary and definition layers, taken with the IMA plan's profile phase (1). Related to TD-16, which concerns the same layers' READMEs |
| TD-25 | **How InsurML maps to InsurLE, and which tool checks that wording and code agree, is not decided.** Two candidates. MORK, which already compiles reviewed meaning to executable form, and the formal methods tooling of the [formal-methods epic](formal-methods.md), which could check an InsurLE rendering against the logic it denotes. They overlap and neither is chosen. Open questions. Which of them is authoritative for agreement between a clause's wording and its executable form. What the mapping from an InsurML component to its InsurLE rendering preserves. Where disagreement is recorded and who adjudicates it. Whether the formal prover choice (FM-D1) changes the answer | 2026-10-08, human request | the three views of a clause (the InsurML words, the controlled rendering and the reviewed meaning) can disagree with no check owning the disagreement, and two tools may be built to do one job | the [logical English alignment sketch](../sketches/logical-english-alignment.md), then an ADR. Decided after FM-D1 and the IMA assembly phase, since both bear on it |

### Graph size

| # | Debt | Spotted | Cost while it stays | Likely home |
|---|---|---|---|---|
| TD-19 | Bound meaning copies stated meaning in full, once per instrument (C6), and C7c's binding per section adds a copy wherever a word's meaning varies by section. Stated meaning is reused by content hash (ADR-A51, C7c R3), so a wording seen before costs nothing, but nothing shares a bound node whose content is the same across instruments or versions. A bound policy from a form the size of theAcme Insurancesample policy is about a thousand nodes, almost all of them the form's content with roles swapped for parties | 2026-10-06, CCS C7c | storage and evaluation cost grow with the number of instances, not with the number of distinct meanings. At insurance volumes the full bound graph becomes too costly to keep, and is treated as ephemeral | CCS slice C16b, required before the CCS epic closes. C7c decides the principle (an instance stores only what differs, bound meaning generated on demand, D1 to D5). Remove this row when C16b lands |

