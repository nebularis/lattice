<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Formal Methods, Track H: Status

**Unit ID:** `formal-methods-track-h` (phase, within the `formal-methods` epic)
**Status:** In progress. H1 (H1.1 to H1.5, with H1.4c), the aggregate-ownership slices HO0 to HO9 and H2.0 to H2.3 are merged to `main` and signed off (H1 and HO 2026-10-10, H2.0 to H2.3 2026-10-12). H2.4a and H2.4b are built and reviewed, and every decision in their Validation Packs is taken (2026-10-13), awaiting the maintainer's merge with the triple-store record. ADR-A123 is accepted with five addenda, ADR-A124 and ADR-A125 are accepted. H2.5 and H2.6 are built (2026-10-13). Every decision of H2.5 is taken, and the maintainer approved H2.6 on 2026-10-13 with three design questions open (RQ4 to RQ6), awaiting the merge. H2.6b's event half is built, approved and merged to `main` (2026-10-14), with its six regenerated expected profiles re-approved and the change to `test_ho6_t14` countersigned. Its ADR-A123 addendum is a draft. Its patch-log half is held (H-D33).
**Last updated:** 2026-10-20
**Plan:** [formal-methods-track-h.md](../plans/formal-methods-track-h.md)
**Sketches:** [formal-methods-track-h.md](../sketches/formal-methods-track-h.md) (main),
[formal-methods-track-h-protocols.md](../sketches/formal-methods-track-h-protocols.md),
[formal-methods-track-h-specification.md](../sketches/formal-methods-track-h-specification.md),
[persistence-aggregate-ownership.md](../sketches/persistence-aggregate-ownership.md) (normative for HO0 to HO9),
[formal-methods-track-h-typed-ir.md](../sketches/formal-methods-track-h-typed-ir.md) (H2's brief)
**Aggregate ownership:** the exploration note [persistence-aggregate-ownership.md](../notes/persistence-aggregate-ownership.md)
and its spike [`spikes/persistence-aggregate-ownership`](../../../spikes/persistence-aggregate-ownership/README.md),
reviewed in [persistence-aggregate-ownership-review.md](../notes/persistence-aggregate-ownership-review.md),
which records our decisions (H-D14) and the findings the HO slices act on
**Epic status:** [formal-methods.md](formal-methods.md)
**Decided by:** [ADR-A-FM4](../../architecture/decisions/ADR-A-FM4-persistence-formal-methods-home-and-scope.md)
(accepted, 2026-10-10, H-D1)

## Current position

As of 2026-10-10, H1 and the aggregate-ownership work (HO0 to HO9) are merged to `main`, which signs
off every slice on the branch. ADR-A122 is accepted, and the release tags `persistence-v0.3.0`,
`persistence-shapes-v0.3.0` and `persistent-foundation-v0.2.0` exist on `main` and on the remote. H2
is briefed in the [typed IR sketch](../sketches/formal-methods-track-h-typed-ir.md).

The background, as written when the track began: this track is new, drafted 2026-10-08 directly from an independent, exhaustive review
(`docs/developer/notes/rdf-engine/persistence-fml.md`) applying this epic's own techniques to the
Persistence layer. The review itself was read in full, cross-checked
section by section against the epic's own existing track structure (B, C, E) before this track's
plan and sketches were written, so that it connects to, rather than duplicates, what those tracks
already established (the claim/gate discipline, the Isabelle and Alloy homes, the epic's own
rolling-wave discipline for scoping a first slice).

**Why Persistence, briefly** (full argument in the main sketch §1): it is a structurally different
pilot from Eligibility (tracks B/C/E's only target so far), specifically because its own recorded
defect history (three remediation passes, documented in the review's own calibration table) is
dominated by concurrency and protocol defects — a class none of this epic's existing techniques
(reference semantics, Alloy, Isabelle) reach at all. This track's H5 slice is the epic's first use
of rung T4 (TLA+/Quint model checking), named in the epic sketch since its first draft but never
yet attempted.

**Explicitly out of scope, for this entire track:** any relational or SQL-compilation work (a
separate, independent review, `sql-feedback.md`, names its own different formal-methods
programme). See the main sketch §2 and ADR-A-FM4 decision 1.

`ADR-A-FM4`, which decides this track's home (mechanised theories under `tools/proofs/persistence/`,
design-time models, Alloy and TLA+/Quint, under `tools/models/`) and its scope (RDF/SPARQL only, no
relational work), was accepted on 2026-10-10 (H-D1). The current next action is the
section below.

## Next action

Decided 2026-10-20: VH-P1 (c), with TD-63 before the merge. The ADR-A123 addendum of 2026-10-14 accepted. VH-Q7 confirmed. EX-Q1 (b),
EX-Q2, EX-Q3 and FS-Q1 to FS-Q7 at their leanings. **This branch ignores versioning** until its changes are complete, then bumps a minor
when it merges into `main` (H2.7-Q5, TD-64). We work autonomously, committing on the branch without pushing.

1. **The examples E1 to E8** (sketch §10), drafted in parallel and merged into the sketch.
2. **H2.6c, the write disciplines** ([plan §4.9](../plans/formal-methods-track-h.md#49-h26c-the-write-disciplines-planned-2026-10-20)), then **H2.6d**, the patch log for in-place families (§4.10).
3. **H2.7 and H2.8**, with VH-Q1 to VH-Q6 decided at our leanings (H-D34 met).
4. Then H2.9. H2.10 follows the sketch's answers. Later, PDD-06.
5. Before the merge into `main`: TD-63, and the minor version bump (TD-64).

## Slices

| Slice | State | Blocked on |
|---|---|---|
| H1.1 (prefix antichain and overlap check) | **signed off.** [Validation Pack](../validation/FMH-H1-1.md) | |
| H1.2a (witness harness, audit witnesses, measured gap list) | **signed off.** [Validation Pack](../validation/FMH-H1-2.md) | |
| H1.2b (witnesses for the refusals and warnings) | **signed off.** [Validation Pack](../validation/FMH-H1-2b.md) | |
| H1.2c (witnesses for the 13 remaining shapes) | **signed off.** [Validation Pack](../validation/FMH-H1-2c.md) | |
| H1.2d (refuse a multi-valued single-valued property, TD-25) | **signed off** 2026-10-10, merged. [Validation Pack](../validation/FMH-H1-2d.md) | |
| H1.3 (static template checks S-3 and S-4) | **signed off** 2026-10-10, merged. [Validation Pack](../validation/FMH-H1-3.md) | |
| H1.4a (refuse a composite boundary with several node properties, H-D4) | **signed off** 2026-10-10, merged. [Validation Pack](../validation/FMH-H1-4a.md) | |
| H1.4b (the declaration/implementation gap report) | **signed off** 2026-10-10, merged. [Validation Pack](../validation/FMH-H1-4b.md) | |
| H1.4c (a declaration the compiler cannot honour is a warning or a refusal) | **signed off** 2026-10-10, merged. [Validation Pack](../validation/FMH-H1-4c.md) | |
| H1.5 (stable labels) | **signed off** 2026-10-10, merged. [Validation Pack](../validation/FMH-H1-5.md) | |
| HO0 (correct the ownership note and its spike) | **signed off** 2026-10-10, merged. [Validation Pack](../validation/FMH-HO0.md) | |
| HO1 (composite replace: payload to the default graph, linear sweep, TD-39, TD-36) | **signed off** 2026-10-10, merged. [Validation Pack](../validation/FMH-HO1.md) | |
| HO2 (draft ADR-A122, Proposed) | **done** 2026-10-10. [ADR-A122](../../architecture/decisions/ADR-A122-aggregate-ownership.md), **accepted** 2026-10-10 | |
| HO3 (`dal:` vocabulary 0.3.0: `dal:ownership`, reference data) | **signed off** 2026-10-10, merged. [Validation Pack](../validation/FMH-HO3.md). Release tags created on `main` | |
| HO4 (ownership tree and path compiler, added beside the old walk) | **signed off** 2026-10-10, merged. [Validation Pack](../validation/FMH-HO4.md) | |
| HO5 (switch the compiler to the tree, TD-03, TD-35, TD-37, TD-40) | **signed off** 2026-10-10, merged. [Validation Pack](../validation/FMH-HO5.md) | |
| HO6 (ownership refusals and the roots-only warning) | **signed off** 2026-10-10, merged. [Validation Pack](../validation/FMH-HO6.md) | |
| HO7 (composite create and tombstone delete, TD-04) | **signed off** 2026-10-10, merged. [Validation Pack](../validation/FMH-HO7.md) | |
| HO8 (injective graph naming within and across families, TD-38) | **signed off** 2026-10-10, merged. [Validation Pack](../validation/FMH-HO8.md) | |
| HO9 (ownership documentation and close-out) | **signed off** 2026-10-10, merged. [Validation Pack](../validation/FMH-HO9.md) | |
| H2.0 (ADR-A123) | **done** 2026-10-10. [Validation Pack](../validation/FMH-H2-0.md). A123 **accepted** 2026-10-10, ADR-A79 addendum applied | merged and signed off 2026-10-12 |
| H2.1 (the typed IR and its renderer) | **built and reviewed** 2026-10-10, five defects fixed. [Validation Pack](../validation/FMH-H2-1.md). Its four decisions confirmed. Its suite ran at `1875 passed, 1 xfailed` (2026-10-12) | merged and signed off 2026-10-12 |
| H2.2 (equivalence harness, `bootstrap-version-row` and `append-event` ported) | **built and reviewed** 2026-10-12, two review findings fixed. [Validation Pack](../validation/FMH-H2-2.md). TD-34 closed for these operations | merged and signed off 2026-10-12 |
| H2 (typed IR) | **briefed** 2026-10-10, split into H2.0 to H2.9 ([typed IR sketch §7](../sketches/formal-methods-track-h-typed-ir.md#7-slices)) | |
| H2.3 (named-graph row writers) | **built and reviewed** 2026-10-12, one review fix. [Validation Pack](../validation/FMH-H2-3.md). [Plan §4.1](../plans/formal-methods-track-h.md#41-h23-the-named-graph-row-writers-planned-2026-10-12). Countersignature items signed 2026-10-12. TD-34 closed for its operations | merged and signed off 2026-10-12 |
| H2.4a (the composite ports) | **built and reviewed** 2026-10-12. [Validation Pack](../validation/FMH-H2-4a.md). [Plan §4.2](../plans/formal-methods-track-h.md#42-h24-the-composite-family-and-what-each-store-does-planned-2026-10-12) | the maintainer's merge |
| H2.4b (Oxigraph, probes, benchmark) | **built** 2026-10-12, reviewed 2026-10-13. [Validation Pack](../validation/FMH-H2-4b.md). Decision 1 decided (option D, built in H2.5), and the corrected P1 test countersigned | the maintainer's merge |
| H2.5 (key claims, audits, guard D, the `SELECT` fragment) | **built** 2026-10-13, autonomously, in six gates. [Validation Pack](../validation/FMH-H2-5.md). [Plan §4.3](../plans/formal-methods-track-h.md#43-h25-key-claims-the-audits-and-the-self-calibrating-guard-planned-2026-10-13). TD-34 closed. every decision taken | the maintainer's merge |
| H2.6 (expected compiled profiles, paper check) | **built 2026-10-13 and approved by the maintainer 2026-10-13.** [Validation Pack](../validation/FMH-H2-6.md). [Plan §4.4](../plans/formal-methods-track-h.md#44-h26-the-expected-compiled-profile-examples-first-and-the-paper-check-planned-2026-10-13). Five of eight review questions answered (H-D24 to H-D28), three open ([write-up](../notes/track-h-h26-review-questions.md)). `mise run build:persistence-expected-profiles` and a check in `check:persistence` | the maintainer's merge. H2.7 waits for RQ4 to RQ6 |
| H2.6b (event slots, patch-log half held, H-D33) | **event half built 2026-10-14, approved by the maintainer and complete 2026-10-14.** Six expected profiles re-approved, `test_ho6_t14` countersigned. [Validation Pack](../validation/FMH-H2-6b.md), [plan §4.6](../plans/formal-methods-track-h.md#46-h26b-the-event-and-patch-content-slots-planned-2026-10-14). The patch-log half is held (H-D33) | the merge |
| H2.7 (vocabulary and emission) | **planned** 2026-10-14, [plan §4.7](../plans/formal-methods-track-h.md#47-h27-the-vocabulary-and-the-compilers-emission-planned-2026-10-14) | H2.7-Q1 to Q4, and H2.6b's merge |
| H2.8 (typed payload, caller checks) | **planned** 2026-10-14, [plan §4.8](../plans/formal-methods-track-h.md#48-h28-the-typed-payload-and-the-caller-side-checks-planned-2026-10-14) | H2.8-Q1 to Q3, and H2.7's merge |
| H3 (specification registry) | not started, outlined in the plan | H2 preferred first (smaller, more self-contained), not a hard blocker |
| H4 (exhaustive cross-axis validation, BDD/SMT) | not started, outline only | H3 |
| H5 (capability-record extension, TLA+/Quint toolchain spike, protocol models A-D) | not started, outline only | H2 (read/write sets from the IR). ADR-A-FM4 is accepted |
| H6 (Isabelle theories: Resolution, Positions, Encoding, Outcomes) | not started, outline only | H1; H5 for `Outcomes.thy` |
| H7 (protocol models E-J) | not started, outline only | H5, H6 |
| H8 (protocol models K-N, grounding) | not started, outline only | H7 |
| H9 (detection-coverage closure, generated audits) | not started, outline only | H3, H4 |
| H10 (runtime monitors) | not started, outline only | H9 |

## Open questions

| # | Question | Owner |
|---|---|---|
| H-D1 | accept, revise or reject ADR-A-FM4 | **decided 2026-10-10**: accepted, including decision 3 |
| H-D2 | TLA+ or Quint | deferred to H5's own toolchain spike |
| H-D3 | ADR-A79 addendum vs a fresh ADR for H2/H3's design | **decided 2026-10-10 for H2**, left to us by the maintainer: a new ADR-A123 and a dated addendum to ADR-A79 ([typed IR sketch §6](../sketches/formal-methods-track-h-typed-ir.md#6-the-adrs)). H3's when it is briefed |
| H-D4 | fix the composite-boundary soundness gap now (a refusal) or wait for H2's typed IR | decided 2026-10-09: left as a documented, refused combination until H2's typed IR makes the fix structural. H1.4 carries the refusal. Its exact condition needs care, because the shipped composite example nests one property inside another (`lineItem` then `sku`) and TD-03 concerns sibling properties |
| H-D5 | feed track A's ledger once it exists, or keep an independent record permanently | recommend: feed track A once it starts |
| H-D6 | H1.1 reads "antichain" per scope kind. Nested `dal:graphPrefix` values are a **violation** only when the scopes cover a common class (each graph-pattern scope is its own target, so disjoint classes cannot collide). Nested `dal:iriPrefix` values are a **warning**, because the resolver ranks by `dal:priority`. The plan says only "antichain", so this narrows it | agreed 2026-10-09 |
| H-D8 | H1.2 is delivered in three parts (a, b, c), because the first run found 55 of 83 rules unwitnessed and closing them together breaks the slice-sizing rule. The plan's H1.2 validation ("every existing rule either has a witness or is listed as a gap") is met by part a. The plan's metric "vacancy rate closed" is then measured as the shrinkage of `known-gaps.txt` | agreed 2026-10-09 |
| H-D9 | the rule inventory is read from the package's own source (refusals and warnings by syntax, shapes from `constraints.ttl`, audits from the template names), not from a hand-kept list, so a new rule cannot dodge the check. A rule is keyed by its `CrossAxisViolation` kind, or by exception class name for the four refusals that carry no kind | agreed 2026-10-09 |
| H-D10 | how to close TD-25 (a multi-valued functional property is resolved by triple order, law L1). Refuse it in the resolver, run the structural shapes inside `compile`, or add a hygiene check. See the H1.2c Validation Pack for the consequences of each | decided 2026-10-09: refuse it in the resolver. Done in H1.2d |
| H-D11 | S-3 treats a `$name` variable as bound by the caller, read from the template text, since the compiled profile lists no request-time parameters | **decided 2026-10-09**: keep option A, let H2's typed IR settle it. [Walkthrough](../plans/formal-methods-track-h.md#133-h-d11-how-does-the-check-know-which-variables-the-caller-supplies) |
| H-D12 | S-3 treats a `BIND` over bound inputs as binding its variable, though an expression can fail and leave it unbound | **decided 2026-10-09**: keep option A, record the limitation here and in TD-34, take option D (a required-parameter guard) in H2. [Walkthrough](../plans/formal-methods-track-h.md#134-h-d12-does-a-bind-count-as-giving-its-variable-a-value) |
| H-D13 | H1.4a also changes what is bound for a shape with exactly one node property, from the first path to the node property, and puts the boundary closure in path order. The old binding could pick a plain property and depended on triple order. See the H1.4a Validation Pack | **decided 2026-10-10**: Option 1, as a stop-gap. Its unchecked precondition (the bound property is owned) is TD-35 and is reported by H1.4b. HO5 supersedes it |
| H-D14 | the aggregate-ownership questions AO-Q1 to AO-Q12 | **decided 2026-10-10**: every leaning in the [review §6](../notes/persistence-aggregate-ownership-review.md#6-the-twelve-questions-answered), and no compatibility kept, since nobody else uses `persistence` |
| H-D15 | AO-Q13, naming a named graph from its root | **decided 2026-10-10**: option a (`ENCODE_FOR_URI` of the whole root IRI), on condition that an over-long IRI is very unlikely, which the review shows ([§7](../notes/persistence-aggregate-ownership-review.md#7-one-new-question-ao-q13)) |
| H-D16 | HO5 touches four Python modules and HO4 three, beyond the slice-sizing rule read per file | **decided 2026-10-10: option A**, HO4 and HO5 stay one slice each. A split of HO5 was possible with a temporary shim, and was not worth its churn (plan §8) |
| H-D17 | AO-Q14, which graph a composite aggregate lives in (review F10: today's composite template relies on the default graph, against static check S-1) | **decided 2026-10-10: option a**, a mandatory named data graph `dal:dataGraph`. No decision is open |
| H-D18 | how many slices H2 needs | **decided 2026-10-10**: as many as it needs. Ten proposed |
| H-D19 | the IR replaces the Mustache templates (A) or adds declarations checked against them (B) | **decided 2026-10-10: option A** |
| H-D20 | how far the payload is typed | **decided 2026-10-10**: designed in full for the maintainer's review, weighed by the configuration it asks of a user ([typed IR sketch §4](../sketches/formal-methods-track-h-typed-ir.md#4-the-typed-payload)) |
| H2-Q1 to H2-Q5 | typed payload option, a named-graph family with no boundary shape, closed-shape payloads, where the parameter guard runs, what the compiled profile carries | **answered 2026-10-10**: PL-B (PL-D later, as an SDK, [sketch](../sketches/persistence-client-sdk.md)), (a) and (b), (a), (c), (a) on condition it keeps the relational realisation open ([typed IR sketch §1](../sketches/formal-methods-track-h-typed-ir.md#1-decisions-already-taken-2026-10-10)) |
| H2-Q2 reading | (a) and (b) read as informational by default, a warning under a compile option, no new `dal:` term | **confirmed 2026-10-10** by the maintainer |
| H2-Q6 | the compiled profile's declarations name logical resources (a) or SPARQL graph roles (b) | **decided 2026-10-10: (a)** ([typed IR sketch §3.1](../sketches/formal-methods-track-h-typed-ir.md#31-the-operation-contract-and-the-sparql-realisation-h2-q6)) |
| H-D21 | H2.3 as one slice, beyond the slice-sizing rule (H2.3-Q4) | **decided 2026-10-12**: one slice, about 25 test cases, approved by the maintainer |
| H2.3-Q1, H2.3-Q3 | the value guard's default graph, the patch-log parameters | **decided 2026-10-12: (a) for both**. TD-43 records the value guard |
| H2.3-Q2 | a `GRAPH ?g` inside an inner group, `?g` bound outside it | **decided 2026-10-12**: (a) by default, the rule follows the join. (c), a caller-named `$g`, as an override the caller chooses, checked against the naming rule while guards are on. ADR-A123 addendum |
| H2-Q7 | reopen H2-Q5: should the IR be stored | **decided 2026-10-12: (A)**. H2-Q5 stands, and a stored IR is decided with PDD-06's ADR, so the stored IR is the semantic one. Rules SI-1 to SI-6 keep it possible ([typed IR sketch §9](../sketches/formal-methods-track-h-typed-ir.md#9-toward-a-stored-ir-h2-q7-decided-2026-10-12)). ADR-A123's third addendum |
| H-D22 | H2.5 and H2.6 in parallel or in turn | **decided 2026-10-13**: in turn, on the cloud agent, H2.5 first ([plan §4.5](../plans/formal-methods-track-h.md#45-order-h25-then-h26-then-h27-one-at-a-time-on-the-cloud-agent)) |
| H-D23 | H2.5 split or one slice | **decided 2026-10-13**: one slice, about 40 cases, six ordered gates |
| H-D24 | the names of the new `dal:` terms of the expected profiles (H2.6 review question 1) | **decided 2026-10-13**: the proposed names are fine. H2.7 settles any change when it writes the vocabulary |
| H-D25 | whether `dal:templateId` keeps the `.mustache` suffix (H2.6 review question 2) | **decided 2026-10-13**: drop it. The builder's identity is the operation id. The expected profiles already show it, and the base-profile test allows that one change to today's `compile` output. H2.7 emits it, and H2.9 retires the files |
| H-D26 | whether `Event`, `MergeRecord` and `KeyQuarantine` are folded into another resource (H2.6 review question 3) | **decided 2026-10-13**: kept apart, since each has its own key in both realisations |
| H-D27 | whether the gaps of the paper check are recorded in the relational note (H2.6 review question 7) | **decided 2026-10-13**: yes, as [lattice-sql.md §9.1](../notes/rdf-engine/lattice-sql.md#91-gaps-found-by-the-paper-check-of-formal-methods-h26-2026-10-13) |
| H-D28 | the type of `$oldValue` and `$newValue` of the value guard (H2.6 review question 8) | **decided 2026-10-13**: `IriOrLiteral` for now. TD-43 settles it |
| H-D29 | H2.6-RQ4, the pinned head | **decided 2026-10-14: A**, part of `Receipt`, as built. Reopened if a retention job becomes a generated operation |
| H-D30 | H2.6-RQ5, the digest of `append-event` | **decided 2026-10-14: B.** An event carries domain triples, so the append gains a payload slot of event triples, and the digest's payload part covers that slot like any other write. A change to the operation, in its own slice with H2.8's payload check (see the [write-up](../notes/track-h-h26-review-questions.md#h26-rq5-the-digest-of-append-event)). Its open points: one event or several per request (the guide's example appends three), what bounds an event's triples (its subject, or a shape), and where `opSeq` comes from when the query assigns it |
| H-D31 | H2.6-RQ6, the patch content of a patch log | **decided 2026-10-14: B**, recorded in the same update, built in H2.6b |
| H-D32 | the order of the remaining H2 slices | **decided 2026-10-14**: H2.6b, H2.7, H2.8, on the cloud agent |
| H-D33 | H2.6b's patch-log half, and H2.10 | **decided 2026-10-14**: held for the [history and versioning sketch](../sketches/persistence-history-and-versioning.md). H2.6b ships its event half |
| H-D34 | whether H2.7 waits for the history and versioning sketch | **decided 2026-10-14**: H2.7 waits for VH-Q1, VH-Q3 and VH-Q5, so the `persistence` vocabulary is published once |
| H2.6b-Q1 to Q5 | which writes log patches, who names the delta graphs, the snapshot model, events per request, the digest parts | **decided** 2026-10-14, (a) for Q1 to Q3 and Q5, (c) for Q4, the guide's batch. Q3's warning covers both receipt models while the patch log is held (H-D33). Q1 and Q2 are held with the patch-log half |
| H2.7-Q1 to Q5, H2.8-Q1 to Q3 | the remaining questions of the plans (plan §4.7, §4.8). Q5, how H2.7 is released under ADR-A129, added 2026-10-20 | **decided 2026-10-20 at our leanings (a)**, for the maintainer's review. Q5: versioning ignored on this branch until its merge (TD-64) |
| VH-P1 | how §4.1, §4.2 and §9 of the history and versioning sketch are re-authored | **decided 2026-10-20: (c)**, left as they are, TD-63 before the merge |
| ADR-A123 addendum, 2026-10-14 | the event slots and the digest parts | **accepted 2026-10-20** |
| EX-Q1 to EX-Q3, FS-Q1 to FS-Q7 (decided 2026-10-20: EX-Q1 (b), the rest at their leanings) | which examples, how deep, how costed, and the strategy menu's shape, granularity, guidance, streams, projections and retention ([sketch §10](../sketches/persistence-history-and-versioning.md#10-questions-for-the-examples-and-the-strategy-menu-2026-10-20)) | **decided 2026-10-20** |
| VH-Q1 to VH-Q7 | history, versions and the receipt models ([sketch §8](../sketches/persistence-history-and-versioning.md#8-questions-for-the-maintainer)) | **decided 2026-10-20 at our leanings**, for the maintainer's review (sketch §11 and its closing table, VH-D1 and VH-D2) |
| H2.5-Q1 to Q3, H2.6-Q1 to Q4, NQ1 to NQ7 | the design review's questions and the plans' own ([track-h-feedback.md](../notes/track-h-feedback.md)) | **decided 2026-10-13**: the closed `SELECT` fragment with four type rules and three fragment limits, a `Literal` kind for `$now`, one H2.5 slice, `test/expected-profiles/`, nine expected profiles, the value guard hand-declared, the model proposed now, the pinned head a realisation of receipts, a digest contract, minted IRIs, a strict caller check (H2.8). NQ5 waits for H2.5's `MIN` finding, NQ7 was answered by the template (merge relations go to the keys graph). Recorded in plan §4.3 and §4.4 and ADR-A123's fourth and fifth addenda |
| H-D7 | H1's checks live in one new module, `persistence.hygiene`, behind one `hygiene` subcommand, and run under `check:persistence`. No new `mise` task until H1's closing slice | agreed 2026-10-09 |

## Log

- 2026-10-08: sketch (main, protocols, specification), plan and status record written, following a
  full read of `persistence-fml.md` and a cross-check against the epic's own existing track
  structure (B, C, E) and conventions (ADR-A-FM2, ADR-A-FM3, track C's `tools/models/` home). ADR
  `ADR-A-FM4` drafted, Proposed, deciding this track's own home and scope, including the explicit
  exclusion of all relational/SQL-compilation work (the separate `sql-feedback.md` review). No
  code written yet; H1 is ready to start as the next action.
- 2026-10-08: H1 split into H1.1 to H1.5 as one slice each, since the plan's five items together
  exceed the slice-sizing rule. H1.1 authored: `persistence.hygiene.check_prefix_antichain`, the
  `hygiene` subcommand and 13 test cases (44 with the per-example parameter). The existing suite is
  at 778 passed before the slice. Adversarial probes run and recorded in the Validation Pack. No
  finding against any shipped example. Working agreement for Track H changed: each slice
  is completed, committed, pushed and debriefed in turn. The sign-off in `validation/LOG.md`
  stays the maintainer's.
- 2026-10-08: an intermittent failure was reported in
  `test_identity_minting_m1.py::test_export_recipes_writes_each_recipe_and_refuses_a_tampered_one`.
  It predates H1.1 and is unrelated to it. The test tampered with an arbitrary recipe node by
  replacing `urn:` with `urx:`, and the `AdoptedIdentity` recipe contains no `urn:`, so one run in
  seven the edit changed nothing and no error was raised (11 failures in 60 runs before the fix).
  The test now chooses a node deterministically and asserts the edit took effect (0 in 60 after).
  The assertion it protects is unchanged, so this does not weaken the test.
- 2026-10-09: H1.1 signed off. H1.2a authored: `persistence.witness`, the `witness`
  subcommand, ten audit witness datasets, `known-gaps.txt` and 20 test cases. First measurement: 28
  of 83 rules witnessed (refusals 10/34, warnings 3/11, shapes 10/33, audits 5/5), 55 listed as gaps.
  All five audits fire on a violating dataset and stay silent on a clean one, so no audit defect was
  found. Six refusals are named by no test and are the first targets of H1.2b. `check:persistence`
  is at 842 passed. An architecture test (only `persistence.render` may import `chevron`) caught a
  first draft of the harness, which now fills the request-time slot by plain substitution.
- 2026-10-09: H1.2a signed off, and H-D6 to H-D9 confirmed. H1.2b authored: 33 witness
  fixtures, a patch format for them, a drift check, and `known-gaps.txt` reduced to the 13 shapes.
  Refusals are 36 of 36 witnessed and warnings 11 of 11, shapes 20 of 33, audits 5 of 5 (72 of 85).
  Correction to H1.2a's harness: its source scan missed two refusals whose kind reaches `fail`
  through a helper parameter. It now follows parameters and reports any kind it cannot determine.
  Two defects found and entered in the technical debt register as TD-23 (a class named only by
  `dal:coversClass` is never compiled) and TD-24 (the CLI suggests a `--target-class` option that
  does not exist). `check:persistence` is at 849 passed.
- 2026-10-09: H1.2b signed off. An interim fix, at our request: `witness --verbose` prints
  WITNESSED lines green and GAP lines red on a terminal (`6bd91a8`). H1.2c authored: 13 shape
  witnesses, one conforming fixture, and a stricter rule for shapes (a shape is witnessed only if some
  fixture makes it report and some fixture has data it accepts, prompted by a probe in which a
  shape that fires on everything counted as witnessed). `known-gaps.txt` is now empty, 85 of 85 rules
  are witnessed (refusals 36, warnings 11, shapes 33, audits 5). H1.2 is complete. New finding TD-25,
  asserted with TD-23 as strict expected failures in `tests/test_known_defects.py`, and recorded as
  the open decision H-D10. `check:persistence` is at 857 passed and 2 xfailed.
- 2026-10-09: H1.2c signed off. We decided H-D10: the compiler refuses a multi-valued
  single-valued property in the resolver. H1.2d authored: `persistence.functional.functional_value`
  and 66 `dal:` reads converted, the refusal `MultiValuedFunctionalProperty`, target discovery wrapped
  so the CLI reports it, an architecture test against bare `Graph.value`, and a witness. TD-25 is
  closed and removed from the register, TD-15 reworded. The first run of the change failed with a raw
  exception because scope priorities are read during target discovery, outside the per-target error
  handling. `check:persistence` is at 869 passed and 1 xfailed (TD-23).
- 2026-10-09: H1.3 authored: `persistence.templatecheck` (S-3 unbound INSERT variables and S-4 blank
  nodes, over rdflib's parsed algebra), the `hygiene` command now compiles and checks the generated
  operations, and 23 test cases. Result on the real templates: no blank node anywhere, and the
  previous-revision variable is the only one left unbound (8 templates), deliberately, for the first
  write to a row or stream. Recorded as reviewed allowances that are checked for staleness. Three of
  the 24 templates were never generated by any fixture, so two fixtures were added and a test now
  requires every template to be reached. No template defect found. `check:persistence` is at 894
  passed and 1 xfailed.
- 2026-10-09: we asked for walkthroughs of H-D11 and H-D12 and decided H-D4. The walkthroughs
  are [plan §13](../plans/formal-methods-track-h.md#13-walkthrough-the-two-assumptions-behind-check-s-3-h-d11-and-h-d12),
  written from experiments on the real templates. They found one new hazard, TD-34: an update run
  without a required `$parameter` writes a partial record and advances the counter, with no error.
  `main` was merged into the branch (`f7c72d9`), with no conflicts.
- 2026-10-09: we decided H-D11 and H-D12 (option A for both, remedies in H2). Recorded in the
  plan (§8 and §13.5), in TD-34, and in the `templatecheck.py` docstring. No code behaviour changed.
- 2026-10-09: H-D11 and H-D12 recorded. The TD-34 demonstration was re-run on Oxigraph and corrected (see
  the 2026-10-10 entry for what the correction itself got wrong). H1.4 is split into H1.4a and H1.4b. H1.4a authored: a composite boundary
  whose shape reaches other nodes through more than one property is refused
  (`CompositeBoundaryMultipleProperties`), the bound property is the node property and no longer the
  first path found, and the closure no longer depends on triple order. Findings: the shipped
  composite example is sound (one node property, `sku` is a plain property), and the old binding
  was both incomplete and order-dependent. The plan's expectation that the shipped example would
  show the gap was wrong. 87 of 87 rules witnessed. `check:persistence` was at 905 passed, 3 skipped and 1 xfailed
  (see the 2026-10-10 entry).
- 2026-10-10: we asked for the Oxigraph work to be kept. It is now
  [`spikes/persistence-oxigraph`](../../../spikes/persistence-oxigraph/README.md), a spike that names
  no interface and is not a store SPI. Doing so exposed that **my 2026-10-09 correction was itself
  wrong**. I had said rdflib's `update` applies deletes lazily and so is not a safe engine. It is
  not lazy (rdflib materialises the solutions first), and the two disagreements I saw came from two
  bugs in my own scratch scripts: one counted revision records in the default graph only, and one
  loaded an IRI as a literal. With those fixed, rdflib and Oxigraph agree on all six scenarios. The
  claim is withdrawn from the plan, the register, the H1.4a Validation Pack and a test's skip reason.
  The two data-level composite tests now run on rdflib, so they no longer skip and need no extra
  dependency. The substantive findings stand and are unchanged: the TD-34 partial write (a missing
  parameter advances the counter and leaves a permanent gap at the earlier sequence) and the
  composite-boundary gap. `check:persistence` is at 908 passed and 1 xfailed.
- 2026-10-10: we asked for a review of the exploration note
  [persistence-aggregate-ownership.md](../notes/persistence-aggregate-ownership.md) and its spike, and
  agreed with all of it. The review is [persistence-aggregate-ownership-review.md](../notes/persistence-aggregate-ownership-review.md).
  Recorded: H-D13 decided (Option 1, stop-gap), H-D14 (AO-Q1 to AO-Q12, decided), H-D15 (AO-Q13,
  open), H-D16 (HO5's size, open). Written: the design sketch
  [persistence-aggregate-ownership.md](../sketches/persistence-aggregate-ownership.md) and plan
  §3.5 (HO0 to HO9, with tests and commands). The technical debt register gains TD-35 to TD-38, its
  duplicated numbers are resolved (see the next-but-two entry for the numbers after merging `main`), and
  TD-03, TD-04 and TD-39 now name their HO slice. References to TD-26 in this record, the plan,
  `templatecheck.py` and `spikes/persistence-oxigraph` now read TD-34. We also agreed that
  nobody uses `persistence` outside this stream, so the HO slices keep no compatibility. No code
  behaviour changed (two docstrings were renumbered). Nothing was run.
- 2026-10-10: we asked whether option a of AO-Q13 could produce a graph IRI over a maximum
  length, preferring option c if so. No standard limits IRI length, encoding minted ASCII roots grows
  them by about a fifth, and an over-long IRI would fail loudly where c fails silently. H-D15 is
  decided as option a, and HO8 now waits only for ADR-A122. Recorded in the review §7, the sketch §9
  and §13, the plan and TD-38.
- 2026-10-10: we decided H-D16 (option A, HO4 and HO5 as planned) and H-D1 (ADR-A-FM4
  accepted, recorded in the ADR and the catalogue). ADR-A122 drafted from the sketch's §13, Proposed,
  and listed in the catalogue, so HO2 is done and HO0 to HO9 can run end to end. The maintainer
  accepts ADR-A122 with the work package at the close. We also confirmed that
  `validation/LOG.md` is retired on `main`, where the merge is the sign-off, so H1.5 no longer waits
  on H1.4a's gate. This branch must merge `main` to pick up that skill text. No decision is open.
- 2026-10-10: merged `origin/main` into this branch (`af2eb89`), at our request. No textual
  conflict in the merge itself. `main` had assigned TD-32 and TD-33 to other rows, so this track's rows
  are renumbered: the missing-parameter row (TD-26 originally) is TD-34, and the composite payload row
  (TD-32 originally) is TD-39. `main`'s TD-33, the flaky recipe-tamper test, is removed from the
  register, since its fix `2e729c3` is on this branch. The `insure-o` row was fixed on `main`. Every
  reference in this record, the plan, the sketches, the review, ADR-A122, `templatecheck.py` and the
  two spikes now uses the new numbers. The merge brings `main`'s `lattice-lifecycle` skill, so step 0
  of the next action is done.
- 2026-10-10: we asked whether the ownership design affects Track H's later phases. Traced
  through the plan, the three Track H sketches, the source review and the epic's documents. Tracks A
  to G do not change. In Track H, H1.4b, H2, H3, H4, H5, H6, H8, H9 and H10 do, recorded in the
  [ownership sketch §15](../sketches/persistence-aggregate-ownership.md#15-effect-on-the-later-track-h-slices)
  and mirrored in the plan's outlines, with a new law L16 (ownership is a partition of members) and a
  milestone FMH-O. Two new findings, in the [review](../notes/persistence-aggregate-ownership-review.md):
  F10, composite operations rely on the default graph against the source review's static check S-1
  (TD-40, new question AO-Q14, H-D17, open), and F11, encoding the root is injective within a
  named-graph family but not across families, closed by two rules HO8 now adds
  (`GraphIriTemplateOverlap` and a suffix rule in `GraphIriTemplateInvalid`). ADR-A122 decisions 3
  and 8 updated to match.
- 2026-10-10: we decided H-D17, AO-Q14 option a. A composite family's aggregates live in one named
  graph, the profile's mandatory `dal:dataGraph`, since LATTICE's patterns guide (§14.3 and its
  checklist) already requires every graph to be named, SPARQL leaves the default graph's contents to
  the store, and holding application data in named graphs is ordinary practice (review §7.1).
  Recorded in ADR-A122 decision 3, the sketch (§3, §7, §10), the plan (HO3, HO5) and TD-40, which now
  closes at HO5. No decision is open. Also adopted the team voice: `AGENTS.md` gains a writing rule,
  the skills say "the maintainer" for the ratifying role, `.github/copilot-instructions.md` was
  rebuilt (`check:agent-guidance` passes), and every passive attribution of a decision
  ("decided by", "agreed by" and the like) is reworded across the repository.
- 2026-10-10: we asked to proceed with the plan. HO0 authored (the note and the spike corrected,
  18 spike checks, one probe). HO1 authored: both composite replace templates sweep with one
  `OPTIONAL { $root <p>* ?s . ?s ?p ?o }` and write the payload to the default graph, closing TD-39 and
  TD-36. H1.4a-T10 and T11 failed as predicted before they were run (their helper ran the update with
  `templatecheck`'s payload stand-in, which now lands in the default graph). We chose to remove the
  stand-in from the helper's input, taken from `templatecheck._SLOT_STAND_INS`, and not to filter
  the result, so their assertions are unchanged. Nine new test items. `check:persistence` at 917 passed
  and 1 xfailed. Probes recorded in the Validation Pack. The Oxigraph comparison was not run (not
  installed here) and we decided it is not mandatory. Working agreement confirmed for this cloud
  session: every slice is committed and pushed to `claude/nice-bohr-pmj43u` only, since the
  maintainer cannot otherwise review a large change set. The maintainer merges.
- 2026-10-10: H1.4b authored. `persistence gaps` lists, per compiled target, eleven kinds of
  declaration/implementation gap with whose obligation each is, the register row and the slice that
  removes it. A separate informational subcommand (we chose this over folding it into `compile` or
  `hygiene`, see the Validation Pack). 13 test items, `check:persistence` at 930 passed and 1 xfailed.
  Three probes recorded in the Validation Pack. HO5, HO7 and HO8 remove their rules and expectations in
  the same commit as their change.
- 2026-10-10: H1.5 authored. Every blank node of a compiled profile has a label derived from its
  target, so the same configuration writes the same bytes, across compiles, load order and processes
  with different hash seeds (all four examples tried differed before). TD-09 removed. A probe showed no
  example compiles with a capability spec, so the check node was untested, and T5b was added. No golden
  file is committed. `check:persistence` at 994 passed and 1 xfailed.
- 2026-10-10: HO3 authored. `ontology/persistence` 0.3.0 with `dal:ownership`, the three ownership kinds,
  `dal:ReferenceData`, `dal:ownsReferenceData` and `dal:dataGraph`, three shapes, and no
  `dal:maxTraversalDepth`. The shapes directory goes to 0.3.0 and `persistent-foundation` to 0.2.0 (a
  re-pinned import). Five small deviations from the sketch are listed in the Validation Pack, the main one
  being that `dal:coversClass` loses its `rdfs:domain`. The compiler does not read the new terms yet.
  `check:persistence` at 1003 passed and 1 xfailed, `check:full-sweep` all 14 passed. Tags can only be made
  on `main`, so they remain the build warning on this branch.
- 2026-10-10: HO4 authored. `walk_ownership` reads a boundary shape as a classified tree and `paths.py`
  compiles its owned edges to one property path by state elimination, rendered through `PropertyPath`. The
  reference fixture of sketch §10 is added. 200 seeded random shapes and datasets agree with a
  breadth-first search of the automaton. Nothing calls it from the compiler yet. `check:persistence` at
  1216 passed and 1 xfailed.
- 2026-10-10: HO5 authored. The compiler uses the classified tree: the composite replace sweeps `$root <path> ?s`
  with one path over every owned edge, inside the profile's data graph, and the default graph is not touched. A
  shape with several owned edges, a recursion and an inverse edge now compiles, and the project fixture's delete
  set is exactly its 28 triples on both rdflib and Oxigraph. TD-03, TD-35, TD-37 and TD-40 closed. The H1.4a
  refusal and its witness, `BoundaryCycleError` and its witness, and four H1.4a tests are removed, each with a
  replacement listed in the Validation Pack for the maintainer to countersign. Four deviations are recorded
  there, chiefly `CompositeBoundaryWithoutOwnedEdges` pulled forward from HO6, and the plan's HO5-T8 example
  being unable to fail. `check:persistence` at 1227 passed and 1 xfailed. Oxigraph, run in a Python 3.13
  environment, passes 7 checks.
- 2026-10-10: HO6 authored. Five refusals (`ComplexBoundaryPath`, `UnclassifiedBoundaryEdge`,
  `OwnershipOnValueProperty`, `OwnedReferenceData`, `OverlappingOwnership`) and the warning
  `ReferenceToOwnedClass`, each witnessed (96 of 96), plus the checks for a named-graph profile that names a
  shape. Messages name a shape and a predicate and never a blank node, so a compiled profile stays
  byte-identical (H1.5). `check:persistence` at 1252 passed and 1 xfailed. Probes in the Validation Pack.
- 2026-10-10: HO7 authored. A composite family gets `create-if-absent-composite` (which also asks that nothing of
  the root is in the data graph) and `tombstone-delete-composite`, each with a dataset-guard variant. The
  tombstone removes the project fixture's 28 delete-set triples and tombstones the row, on both rdflib and
  Oxigraph. TD-04 closed and the last composite gap rule removed. `check:persistence` at 1333 passed and 1 xfailed.
- 2026-10-10: HO8 authored. A named graph is the template's prefix, the whole root IRI percent-encoded with
  `ENCODE_FOR_URI`, and the template's suffix, in all seven templates that name one. `GraphIriTemplateInvalid` and
  `GraphIriTemplateOverlap` refuse a template that is not injective, within a family and across families
  (98 of 98 rules witnessed). TD-38 closed. The `dal:graphIriTemplate` comment is edited within the unreleased
  0.3.0. `check:persistence` at 1356 passed and 1 xfailed.
- 2026-10-10: HO9 authored, closing the aggregate-ownership work package. `aggregate-boundaries.md` is rewritten
  from the sketch and the README's boundary sections follow it, recommending a named graph per aggregate for new
  deployments. The legacy sketch's Part 4 points at ADR-A122. The gap report (`persistence gaps`) now lists no
  composite or graph-naming entry. ADR-A122 is rechecked against `origin/main` and every remote branch, and it is
  the same file on `main`, so the number is ours. Nothing is left open in the plan's HO rows. ADR-A122 awaits
  the maintainer's acceptance.
- 2026-10-10: the maintainer accepted ADR-A122. Its status is Accepted in the ADR and the catalogue, and the
  indexes follow. The maintainer merged `main` into this branch (`b0fce2a`). On the open question of whether
  `compile` should fail on gaps, we chose option C: the gap rules for a declaration the compiler ignores become
  compile diagnostics or refusals (see the entry that follows).
- 2026-10-10: option C carried out ([FMH-H1-4c](../validation/FMH-H1-4c.md)). A declaration the compiler cannot
  honour is a compile warning or a refusal, never a gap. An unconditional write for a boundary with no named graph is
  now refused (`UnconditionalWriteRequiresNamedGraph`, TD-02 reworded), the shard-count gap rule duplicated an
  existing warning and is gone, and the gap report keeps four standing entries and is informational only. Open for
  the maintainer: whether `ShardingNotHonoured` should be a refusal. This checkout's `.venv` was new after the
  merge of `main`, so `mise run bootstrap` ran first (`ensurepip` was needed on this machine). `check:persistence`
  at 1360 passed and 1 xfailed.
- 2026-10-10: bootstrap repaired after a pytest `ImportError` in the maintainer's worktree. Two causes. `mise run
  bootstrap` ran about ten pip installs in parallel into one `.venv`, and `workers` capped `pytest<9` while every
  other package asked for `pytest>=8.0`, so two pytest versions were written into the same `_pytest` directory.
  `bootstrap` now depends on `bootstrap:python`, which installs every Python package in one pip resolve, and every
  Python `bootstrap:*` task depends on `bootstrap:pip` (a `uv`-made `.venv` has no pip). The `<9` cap had no
  recorded rationale (it arrived with the AIR-2.1 commit) and workers, minting, authoring-stage and the sweep pass on
  pytest 9.1.1, so it is lifted. `tools/test_python_requirements.py` fails if the `pytest` or `pytest-xdist`
  specifier differs between packages. Not changed: the CI workflows still call several per-package `bootstrap:*`
  tasks in one command, so they can still run in parallel. The repair for an existing worktree is
  `rm -rf .venv && mise run bootstrap`.
- 2026-10-10: the maintainer merged the branch into `main` (`44a5f48`), created the release tags
  `persistence-v0.3.0`, `persistence-shapes-v0.3.0` and `persistent-foundation-v0.2.0` on it and pushed
  them. Every slice on the branch is signed off. The maintainer decided H-D18 to H-D20 and left H-D3 to
  us. We took a new ADR-A123 with an ADR-A79 addendum. H2 is briefed in the
  [typed IR sketch](../sketches/formal-methods-track-h-typed-ir.md): the IR, the typed payload (options
  PL-A to PL-D, leaning PL-B, which asks no new configuration of a composite user), ten slices, and
  questions H2-Q1 to H2-Q5. One hypothesis is recorded there to measure in H2.4, not yet a finding:
  a composite replace may build its payload once per stored triple of the aggregate.
- 2026-10-10: the maintainer answered H2-Q1 (PL-B, with generated code per language kept for a
  published SDK, sketched in [persistence-client-sdk.md](../sketches/persistence-client-sdk.md) for
  the end of Track H), H2-Q2 ((a) and (b), our reading to confirm), H2-Q3 (a), H2-Q4 (c) and H2-Q5 (a),
  the last on condition that it keeps the relational realisation of `notes/rdf-engine/lattice-sql.md`
  open. Read against that note and `sql-feedback.md`, H2 does not change the resolved profile the
  relational compiler reads. The choice that matters is whether the new declarations name logical
  resources or SPARQL graph roles, raised as H2-Q6. The typed IR sketch now also says plainly that a
  caller outside the Python package runs one extra local query for the payload check.
- 2026-10-10: the maintainer decided H2-Q6 (a), a logical operation contract with the SPARQL graph roles
  kept in the builders, and confirmed our reading of H2-Q2. Every H2 question is answered. H2.0, drafting
  ADR-A123 Proposed with the ADR-A79 addendum, is ready to branch from `main`.
- 2026-10-10: four points settled in the work package, in the [typed IR sketch](../sketches/formal-methods-track-h-typed-ir.md).
  (1) The equivalence harness is defined (§7.1): exact equality of normalised algebra, the parameter guard
  removed from the `Operation` value and checked on its own, mutation probes for non-vacuity, and "a port
  changes nothing, a change ports nothing". (2) The quadratic payload hypothesis is measured on rdflib 7.6.0
  with a scratch script and holds (5.6 s at M = N = 1000), recorded as TD-42. rdflib's code applies an update
  per solution, not in the specification's order, and today's form is correct under both orders because every
  solution re-inserts the whole payload. §4.3 draws the three forms (today's, two operations, one `UNION`
  operation) and the store properties each needs, `snapshotUpdateSemantics` (new, added to the main sketch's
  capability record) and `atomicUpdateRequest`, for the later tranches that model each platform. H2.4 ports
  today's form unchanged, commits the benchmark and probes, and stops only if Oxigraph shows today's form to
  be wrong. (3) `INFO` and its warning option get witnesses in H2.8, and the witness harness learns the new
  family, since it records only `WARNING` diagnostics today (§7.3). (4) The paper check of the logical
  resources against `lattice-sql.md` §9 moves to H2.6 (§7.2).
- 2026-10-10: H2.0 built ([FMH-H2-0](../validation/FMH-H2-0.md)). [ADR-A123](../../architecture/decisions/ADR-A123-typed-operation-ir.md)
  is drafted Proposed and catalogued. A123 was free on every remote branch. The ADR-A79 addendum is drafted at the foot of
  A123 and applied on acceptance, since an accepted ADR should not carry text for a decision not yet taken.
- 2026-10-10: H2.1 built ([FMH-H2-1](../validation/FMH-H2-1.md)). `persistence.ir` (the values) and
  `persistence.ir_render` (26 named refusals, rendering, derived read and write sets). Nothing calls them yet.
  `check:persistence` at 1849 passed and 1 xfailed (489 added). The property test of adversarial literals
  found a defect in the existing `Literal.encode`: a value holding a backslash before `u` was written so that
  SPARQL's whole-text `\u` escape processing broke it (rdflib raises). Fixed in `terms.py` (outside the slice's
  module list, listed for the maintainer's review). Probes: seven mutations caught, and an eighth, a duplicated
  path-in-template check, was an equivalent mutant, so the duplicate was removed. Decisions for the maintainer
  are in the Validation Pack.
- 2026-10-10: the maintainer accepted ADR-A123, and we applied the dated ADR-A79 addendum and catalogued both. The
  maintainer confirmed the four decisions of FMH-H2-1. A review of H2.1 found five defects and fixed each with a test
  ([FMH-H2-1, Review](../validation/FMH-H2-1.md#review-2026-10-10)). The serious one: the required-parameter guard
  rendered as a top-level `FILTER`, which applies after the group's patterns, so a replace with no `$root` bound
  `$root` from the data and wrote every matching aggregate. The guard is now its own group, and ADR-A123 decision 5
  says so, corrected before acceptance. The others: prefix compaction changed a literal that looked like an IRI, an
  optional parameter counted as always bound, a graph block's scope ignored the enclosing group, and `Const` accepted
  an IRI built without its encoder that held a `\u` escape. Two questions are open, R1 (refuse an operation without
  its guard) and R2 (type-test `Iri` parameters with `isIRI`). The probes ran on rdflib in a scratch script. The suite
  was not run after the fixes. Its expected total is in the Validation Pack.
- 2026-10-12: we talked F1 to F5 through with the maintainer. F2, F3 and F5 are agreed. F4 was wrong as first fixed:
  SPARQL evaluates an inner group on its own, so a `BIND` inside a nested group, `GRAPH` block, `OPTIONAL` or `UNION`
  branch does not see outer variables, and only `NOT EXISTS` does (checked on rdflib). The `GRAPH` block code was
  right, the first fix is reverted, and the other three scopes now start empty, with engine tests (T29). On F1 the
  maintainer decided that guards are optional and on by default, since input checking normally belongs in the access
  layer, recorded as an [ADR-A123 addendum](../../architecture/decisions/ADR-A123-typed-operation-ir.md#addendum-2026-10-12-parameter-guards-are-optional-and-are-type-tests).
  Guards are now type tests (`isIRI`, `DATATYPE`, `LANG`) in their own group, which catch a missing parameter, a
  mistyped one (R2) and survive text substitution, where `BOUND` became a syntax error. An operation carries the guard
  or `GUARDS_OFF`, never none (R1). Measured on rdflib, the guard in its own group costs nothing, where the top-level
  form cost about 60% on a 20,000-triple sweep. The maintainer also raised a SPARQL semantic IR for a later phase,
  recorded as PDD-06 and plan §5.1, with an interim rule that every semantic rule the checker encodes gets an engine
  test. The suite was not run (1,876 cases collected).
- 2026-10-12: ran the FMH-H2-1 one command after pulling. `check:persistence` gave 4 failures, all in T29
  (`a_bind_sees_only_its_own_group`). The query selected only `?b`, and rdflib 7.6.0 drops a row whose projected
  variables are all unbound, so the expected `[None]` came back empty. The queries now select `?a ?b` and read `?b`,
  which asserts the same scope rule. The expected values are unchanged. `check:persistence` then gave
  `1875 passed, 1 xfailed`.
- 2026-10-12: H2.2 built ([FMH-H2-2](../validation/FMH-H2-2.md)). The equivalence harness (`tests/equivalence.py`) holds a
  builder to its template as normalised rdflib algebra, with the guard off, and `bootstrap-version-row` and
  `append-event` (each with its dataset-guard variant) are ported in `persistence.builders`. The harness caught my
  first port of `append-event` at once: I had put an `epoch` triple in the non-dataset `INSERT` that the template does
  not have. `instantiate` now renders the four ported operations from their builders with the required-parameter guard,
  and `--no-parameter-guards` leaves it out. TD-34 is closed for these operations, with the unbound-`$stream` case (F1)
  run on rdflib as a test. `Kind.IRI_OR_LITERAL` (first named `TERM`) is new, for `$occurredAt`. `check:persistence` gave `1915 passed, 1 xfailed`.
  Six implementation probes were caught. Three decisions are listed for the maintainer in the Validation Pack.
- 2026-10-12: the maintainer agreed to rename the new parameter kind from `Term` to `IriOrLiteral`, because a term
  includes blank nodes, `Term` means something else in `instrument`, and the kind is not an ontology class. Done in the
  IR, the builder, the tests and the Validation Pack. We keep it untyped as to datatype. Typing `$occurredAt` as
  `xsd:dateTime` would refuse `xsd:date`, `xsd:gYear`, `xsd:dateTimeStamp`, an IRI for an instant and untyped strings,
  and no query uses the type. The maintainer agreed to leave the stricter check until later. A datatype taken from the family's declared valid-time property is possible in H2.7.
- 2026-10-12: a review of H2.2 ran `check:persistence` at `1915 passed, 1 xfailed` and found two gaps, both fixed the same
  day. A builder chose each graph's role itself, and nothing checked it: the transaction graph labelled `META` passed every
  test, though the derived read and write sets would carry the wrong role. `GRAPH_ROLES` now gives every role by binding
  or variable name, and T20 and T21 check it. And `Bindings.const` guessed a binding's type from its text, which would have
  read H2.4's `ownedPath` as an IRI. `operation_context` now wraps each binding by its declared `dal:paramType`, with T22 to
  T24. Both fixes were probed by breaking them. `check:persistence` then gave `1920 passed, 1 xfailed`. The record also had
  a duplicated H2.2 row and a stale status line, both corrected.
- 2026-10-12: H2.3 planned in [plan §4.1](../plans/formal-methods-track-h.md#41-h23-the-named-graph-row-writers-planned-2026-10-12).
  Reading its templates found two things. `cas-replace-value-guard` reads and writes the default graph, which the IR cannot
  express and S-1 forbids (TD-43, H2.3-Q1). And the scope rule corrected in F4 refuses the sweep `OPTIONAL { GRAPH ?g {
  ... } }` after an outer `BIND ?g`, which three templates use. F4 is right for a `BIND` and wrong for a pattern, whose
  result is joined on `?g` afterwards (H2.3-Q2). Four questions are open for the maintainer.
- 2026-10-12: the maintainer decided H2.3-Q1 (a), the value guard stays unported until H2.7 (TD-43), H2.3-Q3 (a),
  `$assertGraph` and `$retractGraph` stay optional until H2.7, and H2.3-Q4 (b): **H2.3 is one slice, and the maintainer
  approved exceeding the slice-sizing rule for it** (H-D21). H2.3-Q2 is open, with its options explained in diagrams.
- 2026-10-12: the maintainer decided H2.3-Q2. By default the query names the graph and the scope rule follows the join
  (option a). A caller can override it and name the graph itself as `$g` (option c), which a text-substituting caller
  turns into a constant graph. We added that, while guards are on, the guard group checks `$g` against ADR-A122's naming
  rule, so a wrong `$g` writes nothing. Recorded as the second ADR-A123 addendum of 2026-10-12 and as step 8 of the H2.3
  plan. H2.3 is ready to branch.
- 2026-10-12: clarified for the H2.3 implementer. The plan's "no guard of any kind" for `unconditional-write` meant no
  version or concurrency guard, which the profile's `dal:ProvidedConcurrency` or `dal:LockingConcurrency` already rules out
  and the port keeps. The parameter guard applies as to every operation, `ISIRI($root)` while guards are on. The plan row
  now says so. Nothing decided in H2 removes a concurrency or version protection.
- 2026-10-12: for the H2.3 implementer, on step 8's name check. Rather than a builder passing extra guard conjuncts, which
  would put unchecked expressions into a guard that `check` only compares with the derived one (R1), the check is declared
  on the parameter (`Param(..., equals=...)`), derived by `ParameterGuard.derive` and validated by `check` as a guard
  expression. The plan's step 8 says so.

- 2026-10-12: H2.3 built ([FMH-H2-3](../validation/FMH-H2-3.md)), autonomously on this branch. The create, replace and
  tombstone builders, each with its dataset-guard variant, and the unconditional write are ported, and the harness compares 90
  operations, all equal to their templates. The scope rule follows the join (H2.3-Q2) with an engine test. `Param.equals`
  carries the naming check of the caller-named graph, as the maintainer directed, so a builder never writes a guard
  conjunct, and `InvalidEquals` is a new rule beside the ones he named. `instantiate --caller-graph-names` selects the
  caller-named form. Two findings. A probe that swapped the metadata and transaction roles in `GRAPH_ROLES` was not caught,
  because the role test asked the same table, so T32 states the roles apart from it. And three HO8 tests bound `$epoch` as
  an `xsd:integer`, which the guard now refuses, so their input is `xsd:long`. rdflib also writes a root-less
  unconditional write into a blank-node graph, where the specification skips the quad (recorded in T8). `check:persistence`
  gave `2003 passed, 1 xfailed`. Eight implementation probes, seven caught first time.
- 2026-10-12: a review of H2.3 ran `check:persistence` at `2003 passed, 1 xfailed`, matching FMH-H2-3. The ports, the
  scope rule, `Param.equals` and the caller-named form match the plan and both ADR-A123 addenda, and probes of the scope
  rule at its edges behaved as the join rule says. Fixed: an unknown `graph_names` is now refused by every builder, not only
  those that name a graph. Recorded: on rdflib a template triple whose graph variable is unbound is written to a new
  blank-node graph (TD-44), which matters only with guards off. The status line, which still described H2.2, is corrected.
- 2026-10-12: the maintainer countersigned both FMH-H2-3 items, the removed H2.1 refusal case and HO8's test input made
  `xsd:long`. H2.0 to H2.3 are marked ready for the maintainer's merge. FMH-H2-2's decisions 2 and 3 remain unconfirmed,
  recommended for acceptance.
- 2026-10-12: the maintainer accepted FMH-H2-2's decisions 2 (`instantiate` renders the ported operations from their
  builders now) and 3 (the harness corpus is every fixture that compiles). No decision is open in H2.0 to H2.3.
- 2026-10-12: H2.0 to H2.3 are merged to `main`, and `main` is merged back into this branch (`361b25e`). H2.4 planned in
  [plan §4.2](../plans/formal-methods-track-h.md#42-h24-the-composite-family-and-what-each-store-does-planned-2026-10-12):
  the six composite templates, and the probes and benchmark that measure what rdflib and Oxigraph do (TD-42, TD-44, the
  cost note of H2.3-Q2). Four questions are open, on the `OwnershipTree` reference of ADR-A123 decision 4, where Oxigraph
  runs, where the benchmark lives, and whether to split the slice.
- 2026-10-12: the maintainer decided H2.4-Q2 (Oxigraph as a test-support package at `tools/testing/oxigraph`, not a backend),
  H2.4-Q3 (the benchmark as a check run on demand, in a new root `benchmark/persistence-composite-cost`) and H2.4-Q4 (split
  into H2.4a and H2.4b). Both new directories need an accepted ADR under AGENTS.md, so H2.4b starts by drafting ADR-A124.
  H2.4-Q1 is open, with the reason it drifted: the typed IR brief wrote that the IR holds the `OwnershipTree` without
  checking that `instantiate`, which builds the IR, sees only the compiled profile and so only the path. An agent confirmed
  `pyoxigraph` 0.5.11 has a native Python 3.14 wheel, so the spike's README caveat is out of date.
- 2026-10-12: the maintainer asked whether H2-Q5 should be reversed so the IR is stored, for richer options. Raised as
  H2-Q7, open, with three options and a leaning to keep H2-Q5 until PDD-06's ADR decides what a stored IR is, since storing
  today's syntax IR would publish a format PDD-06 plans to replace. H2.4-Q1's answer waits on it. H2.4a does not.
- 2026-10-12: the maintainer decided H2.4-Q1 (a) and H2-Q7 (A). The compiled path is the IR's reference to the
  `OwnershipTree`, and the IR is not stored until PDD-06's ADR decides a stored IR, so that the semantic IR is the one
  published. Written up as the [typed IR sketch §9](../sketches/formal-methods-track-h-typed-ir.md#9-toward-a-stored-ir-h2-q7-decided-2026-10-12)
  (gains, costs, options, six rules SI-1 to SI-6 that keep a clean stored IR possible, and what PDD-06's ADR must decide),
  ADR-A123's third addendum and PDD-06. One rule does not hold today: a `Path` holds rendered text, not the path's structure.
  H2.4a gains a test of SI-1 and SI-2. The maintainer agreed a `benchmark/` root and a `tools/testing/` directory, and
  confirmed the benchmark's pass criterion. Drafted ADR-A124 and ADR-A125, Proposed. Both numbers were free on every branch.
- 2026-10-12: `main` merged into this branch (`40ddf2e`), bringing CCS's new eligibility, instrument and wording versions.
  `check:ontology-versioning` lists no pending release tag. The maintainer accepted ADR-A124 (`benchmark/`) and ADR-A125
  (`tools/testing/`). Both numbers were rechecked after the merge and are free. AGENTS.md's table of roots, the root README,
  the Copilot copy (`build:agent-guidance`, then `check:agent-guidance` with 0 problems) and an addendum to ADR-A77 name both.

- 2026-10-12: H2.4a built ([FMH-H2-4a](../validation/FMH-H2-4a.md)), autonomously on this branch. The six composite templates are
  ported, and the harness, binding, guard and role cases cover them. A replace with no `$root` over two aggregates writes nothing
  guarded, and unguarded rdflib sweeps both aggregates, writes the payload once and moves both rows (T3). SI-1 and SI-2 have
  tests: every ported operation encodes structurally and back, builds equal twice, and builds with the file, clock and
  environment closed (T8 to T11). The lifecycle tests of HO1, HO5 and HO7 bound `$epoch` as an `xsd:integer`, which the guard
  refuses, so their request and stored epochs are `xsd:long`, assertions unchanged (listed for countersignature). `check:persistence`
  gave `2035 passed, 1 xfailed`. Six probes, all caught.
- 2026-10-12: H2.4b built ([FMH-H2-4b](../validation/FMH-H2-4b.md)), autonomously on this branch, after H2.4a. The packages `tools/testing/oxigraph` and
  `benchmark/persistence-composite-cost` are created per ADR-A125 and ADR-A124, and six test modules run on rdflib and on Oxigraph. **R0 is right on
  Oxigraph, so the plan's stop did not arise.** Findings, none a wrong result: (1) Oxigraph 0.5.11 stores `"1"^^xsd:long` as `xsd:integer`, so the parameter
  guard's datatype test can never pass there (TD-45, **decision 1 is open**, with options A to C and a leaning); (2) R0 needs memory quadratic in the
  aggregate on Oxigraph and does not finish at M = N = 10,000 under 8 GB, where rdflib takes 983 s (TD-42 has the figures); (3) rdflib applies an update in
  the specification's order and Oxigraph applies each solution in turn, the reverse of what the typed IR sketch §4.3 assumed, so R2 is safe on rdflib and
  unsafe on Oxigraph and R1 the other way round (P1 and P2), corrected in the sketch; (4) the spike's own checks had been failing since H2.2, and are repaired.
  `check:persistence` gave `2111 passed, 1 xfailed`. Five implementation probes, all caught.
- 2026-10-13: began [docs/architecture/triple-store-discovery.md](../../architecture/triple-store-discovery.md), the project's record of
  how each triple store behaves (TSD-01 to TSD-14), with skill `lattice-triple-stores` and pointers from AGENTS.md, the testing,
  toolchain and design skills, the docs site and the plugin marketplace. Writing it found that H2.4b's P1 was wrong about rdflib: rdflib
  applies an update one solution at a time, in an order that follows `PYTHONHASHSEED` (`evalJoin` puts the solutions in a Python `set`),
  so the probe's answer changed by process and its test failed `check:persistence` in 2 of 3 runs. The test now sweeps seeds in child
  processes and passes on every run, listed for countersignature in FMH-H2-4b. The Validation Pack, the sketch's §4.3 note and TD-42 are
  corrected. Oxigraph's findings were re-run directly and hold, and Oxigraph's source (`eval_delete_insert`) confirms it collects every
  mutation in a `Vec` before applying them in order. `check:persistence-oxigraph` gave 66 passed.
- 2026-10-13: the maintainer decided FMH-H2-4b decision 1, option D, a self-calibrating datatype test
  (`DATATYPE($p) = DATATYPE("0"^^xsd:long)`), recorded as ADR-A123's fourth addendum and built in H2.5, and countersigned the corrected P1
  test. Planned H2.5 (the ten remaining ports, a sub-select in the IR, guard D, engine tests for `MIN` over IRIs, counts of numeric terms
  and `GROUP_CONCAT`'s order) and H2.6 (expected compiled profiles for eight examples covering every operation kind, an agreement test with
  the builders, and the paper check). They can run in parallel by plan §4.5. While planning: no template reads `registryGraph`, so H2.5
  needs no new graph role, and an expected profile cannot sit in `examples/`, which three tools compile as configurations.
- 2026-10-13: a design review of the H2.5 and H2.6 plans, kept at [docs/developer/notes/track-h-feedback.md](../notes/track-h-feedback.md),
  found seven blocking issues. Checked against the code, two were partly handled already: the IR has a top-level `Select`, though nothing
  enforces its rules and the property test covers only updates, and the pinned, retention and quarantine roles exist. H1.5 had already made
  compiled profiles byte-stable, and the persistence README's sentence saying otherwise is corrected. The templates answered two of its
  questions: merge relations are written to the keys graph, and quarantine is idempotent. The guide answered a third: `pat:retiredAt` has
  range `xsd:dateTime`. The maintainer agreed every leaning, chose a `Literal` kind for `$now`, and decided the slices run in turn on the
  cloud agent, not in parallel. H2.5 goes first, so H2.6 derives every operation from a builder. Plan §4.3 to §4.5, ADR-A123 (a fifth
  addendum and a point in the fourth), the typed IR sketch's §7 and §9.4, and five open questions in the triple-store record (TSD-Q6 to
  Q10) are updated. H2.5 is ready to branch.
- 2026-10-13: H2.5 built ([FMH-H2-5](../validation/FMH-H2-5.md)), autonomously on the branch, in the six gates of plan §4.3. Guard D and the
  extended probe P5 (no divergence, so no stop), the `SELECT` fragment with four new rules and the boundness table, ten builders (every
  template but `cas-replace-value-guard` is now ported), and behaviour tests on both engines with the guards on and off. Running the audits
  found three differences between the stores that change results, now TSD-16 (rdflib's `MIN` over IRIs returns a literal), TSD-17 (Oxigraph groups
  `a - b + c` from the right, which made the gap scan report every complete stream) and TSD-15 (rdflib lets an outer binding into a sub-select),
  with TSD-18 to TSD-20 beside them. TSD-17 is worked around in the renderer. TSD-16 needs a decision (Validation Pack, decision 1). TD-34 is
  closed and TD-45's guard part is done. Seven adversarial probes were run and each was caught. `check:persistence` and
  `check:persistence-oxigraph` ran and passed here.
- 2026-10-13: the maintainer decided FMH-H2-5 decision 1, option B (the canonical owner of a merge is `IRI(MIN(STR(?owner)))`), and that decision 3
  (the fragment-limit fields) is fine for now. Option B is built in the template and the builder, with the checker allowing an aggregate inside a scalar
  function of a projection. Decision 2, how the builder and the template agree about arithmetic, is open with a leaning to parenthesise the template as well.
- 2026-10-13: the maintainer decided FMH-H2-5 decision 2, option B, and approved the rest. The gap-scan template now says `(?S - ?L) + 1`, the harness
  normalisation for arithmetic chains is removed, and H2.5 has no open decision.
- 2026-10-13: H2.6 built ([FMH-H2-6](../validation/FMH-H2-6.md)), autonomously on the branch, and stopped for the maintainer's review. The contract of an
  operation is derived in production code (`persistence.contract`: kinds, access modes, the role-to-resource mapping, builder versions), with the checker
  giving each access a mode. Ten files in `ontology/persistence/test/expected-profiles/` (the eight examples, the caller-named variant, and the
  enumerations) are held to the builders, to `compile` and to a golden check on builder versions by 114 new cases. Mapping findings: only the keys graph
  holds two resources (by predicate), and the pinned graph is a realisation of `Receipt`. Paper check against `lattice-sql.md`: every resource is logical
  or realisation only, and the gaps are in §9 (the transaction claim, the retention mark, tombstone, `ProvidedConcurrency`) and in the contract (the
  patch content of a patch log, the digest input of an append). One intended difference (the patch-log parameters), which H2.7 closes.
- 2026-10-13: the maintainer approved H2.6 and answered its review questions (H-D24 to H-D28): the proposed names are fine, `dal:templateId` loses its
  `.mustache` suffix (the expected profiles now show it, and the base-profile test allows that one change), `Event`, `MergeRecord` and `KeyQuarantine` stay
  apart, `$oldValue` and `$newValue` stay `IriOrLiteral`, and the gaps of the paper check are added to the relational note as §9.1. Questions 4 to 6 (the pinned head,
  the append's digest, the patch content) need a write-up first, now [track-h-h26-review-questions.md](../notes/track-h-h26-review-questions.md), with options,
  consequences and a leaning each. A mise task regenerates the expected profiles (`build:persistence-expected-profiles`) and a check of them is part of
  `check:persistence`, with `build:persistence-builder-goldens` for the builder versions. The class diagram of the Validation Pack did not render (a colon in
  a relationship label) and is fixed, and every diagram of the new documents was loaded in Mermaid.
- 2026-10-14: the maintainer decided H2.6-RQ4 (A, the pinned head stays part of `Receipt`) and RQ5 (B: an event must carry domain triples, so
  the append gains a payload slot, in a slice of its own with H2.8's payload check). On RQ6 the maintainer asked whether rdflib is the only
  store without request atomicity. From the stores' documentation, it is not: SPARQL 1.1 Update only recommends atomicity, Virtuoso's
  recommended update mode commits each operation as it runs, and Jena TDB2 and Neptune appear atomic. Added to TSD-06 as documented evidence,
  with TSD-Q13 to probe them. That favours RQ6 option B. RQ6 awaits the maintainer.
- 2026-10-14: the maintainer chose H2.6-RQ6 B (H-D31) and the order H2.6b, H2.7, H2.8 (H-D32), with `main` merged into this branch. Planned all
  three. Planning H2.6b found that `dal:PatchLog`, which the validator requires for every composite family, is honoured only by the named-graph
  replace, which names its delta graphs and never fills them, and that `dal:SnapshotPerRevision` is never honoured, with no warning for either
  (TD-46). H2.6b comes before H2.7 so the vocabulary is published once against the final slots. Twelve questions are open, every leaning (a).
- 2026-10-14: the maintainer decided H2.6b-Q1 to Q3, each (a), and asked for the snapshot model on the roadmap, now H2.10 (plan §5). Reading
  guide §10.1 showed it already answers H2.6b-Q4. Several events go in one commit with one receipt, ordered by caller-supplied `opSeq`, so the
  earlier claim that they need ordered rows (TSD-01) was wrong. Q4 is re-presented with options (a) to (c), leaning (c), and plan §4.6 gains the
  patch-log invariants and worked space and time costs. Skill `lattice-design` now asks for diagrams and quantified costs by default.
- 2026-10-14: the maintainer decided H2.6b-Q4 (c), several events in one commit ordered by `opSeq`. Asked about retention, we found that
  nothing declares a retention window and nothing prunes, recorded as TD-47.
- 2026-10-14: the maintainer asked why a patch log keeps its added triples. Going back from the current graph needs them, since a pure addition
  has no old value to log. Working this through showed that the guide's as-of read replays forward and loses triples once old buckets are
  pruned, where a backward read does not. Recorded as TD-48.
- 2026-10-14: the maintainer and we discussed how deep a patch tracks a change, with a broker's tower and a carrier's requote as the case.
  Persistence keeps history without reference to Foundation's versioning, and a composite replace deletes an old version ADR-A67 keeps.
  The maintainer placed quotes in a `NegotiationThread` aggregate, not the tower's. H-D33: H2.6b ships its event half only, with
  `ReceiptModelNotHonoured` for both receipt models, and its patch-log half and H2.10 are held for a new sketch,
  [persistence: history, versions and the receipt models](../sketches/persistence-history-and-versioning.md), VH-Q1 to VH-Q7, including
  whether Behaviour's versioning differs for a reason.
- 2026-10-14: the maintainer decided H2.6b-Q5 (a) and confirmed `ReceiptModelNotHonoured` for both receipt models. Plan §4.6 now briefs the
  event half on its own: events as `VALUES` rows in an `eventRows` slot, event data in an `eventTriples` slot, the digest's payload and
  event parts, and the warning. H2.8's checks no longer name the add and del graphs. H2.6b is ready to branch once the planning documents
  are on `main`.
- 2026-10-14: H2.6b's event half built autonomously on the branch ([FMH-H2-6b](../validation/FMH-H2-6b.md)). An append takes `{{{eventRows}}}` and
  `{{{eventTriples}}}`, the contract declares the event digest part, and `compile` warns `ReceiptModelNotHonoured` for both models, so six expected
  profiles changed. TSD-21 recorded. The patch-log half, H2.7 and H2.8 are not built.
- 2026-10-14: reviewed H2.6b's event half. It is built as briefed, and the pack reports honestly that the plan's `VALUES`-in-a-group probe
  could not fail. Three review points, recorded in the documents: the ADR-A123 draft said the checker refuses a nested `RowValues`, which it
  does not, corrected. A row with `UNDEF` for `?event` writes a receipt and claim with no event, and two rows may name one event, so H2.8's
  caller check now refuses both. The rows slot is the first request-time slot inside an update's `WHERE`, where untyped text can change the
  guards, so H2.8 gains a `Rows` type beside `Payload`.
- 2026-10-14: the maintainer approved H2.6b's event half and marked it complete, re-approved its six regenerated expected profiles and
  countersigned the change to `test_ho6_t14` under the non-weakening rule. The ADR-A123 addendum stays a draft until accepted.
- 2026-10-14: the maintainer decided H2.7 waits for VH-Q1, Q3 and Q5 (H-D34), and asked for the VH-Q7 research on Behaviour's versioning,
  on this branch.
- 2026-10-14: VH-Q7 researched ([sketch §6.1](../sketches/persistence-history-and-versioning.md#61-research-2026-10-14)). Behaviour has three
  disciplines, each with a reason: versions for authored configuration, immutable records for what happened, derived artefacts for what is
  computed. A balance is computed per stimulus-log position (evaluation-context sketch, law B3), and its read set crosses accounts, which
  succession cannot carry. Leaning (a). The account record is under-keyed: not typed a derived artefact, no owner, no position. Persistence
  needs three write disciplines, not two.
- 2026-10-14: at the maintainer's request, widened VH-Q7 to the roadmap ([sketch §6.4](../sketches/persistence-history-and-versioning.md#64-the-roadmap-2026-10-14)).
  The account's identity and keying belong to the evaluation-context sketch's EC-Q2, which comes back at CCS C12 and AIR Phase 5, and
  capacity's Phase 0 needs the same answer. So no change to Behaviour in Track H. Capacity's `capx:ExecutableBalance` is an in-place
  current balance with its own version token, a projection beside Behaviour's records. AIR-6.1 pins an exposure set version as evidence,
  which refines VH-Q2. CCS C16b already decides "point, do not copy" for generated meaning. Nothing decided.
- 2026-10-14: cross-referenced the placement vision papers (outside the repository) with LATTICE's layers and the plans under way
  (CCS, AIR, the evaluation context, capacity, Surface, insurml-alignment), as
  [sketch §9](../sketches/persistence-history-and-versioning.md#9-the-vision-papers-lattice-and-the-data-a-placement-makes-2026-10-14).
  Most of the papers' ideas have a home. Four departures to test: state read from acts rather than authored, binding by assent rather
  than copy, versioning chosen per family, the words' history in Wording's amendments. A quote carrying wording and meaning costs about
  5,000 triples a version copied, about 270 under C7c's rules, and about 5 to 20 a requote with sharing (judgement). Eight strategies
  listed for the examples to exercise.
- 2026-10-20: re-oriented after `main` moved (ADR-A126 to A129, AIR-4.2a to 4.4, the claims plan). Plan §4.7 and §4.8 aligned with
  ADR-A129 (one release, H2.7-Q5 added) and ADR-A128. Next action rewritten. New open decisions: VH-P1, the ADR-A123 addendum, and the
  examples and strategy questions EX-Q1 to EX-Q3 and FS-Q1 to FS-Q7 (sketch §10).
- 2026-10-20: the maintainer decided VH-P1 (c), accepted the ADR-A123 addendum, confirmed VH-Q7, took EX-Q1 (b) and every other
  example and strategy leaning, and set this branch to ignore versioning until its merge (TD-64). TD-63 recorded.
- 2026-10-20: the maintainer asked us to proceed at our own leanings and review at the end. VH-Q1 to VH-Q6, H2.7-Q1 to Q4 and
  H2.8-Q1 to Q3 decided at their leanings, and VH-D1 and VH-D2 from the examples' open points.

