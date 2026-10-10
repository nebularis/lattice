<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Formal Methods, Track H: Status

**Unit ID:** `formal-methods-track-h` (phase, within the `formal-methods` epic)
**Status:** In progress. H1.1 to H1.2c signed off. H1.2d, H1.3, H1.4a, H1.4b, H1.5 and the aggregate-ownership slices HO0 to HO9 are authored and verified (2026-10-10), awaiting the maintainer's verification, the acceptance of ADR-A122, and the merge
**Last updated:** 2026-10-10
**Plan:** [formal-methods-track-h.md](../plans/formal-methods-track-h.md)
**Sketches:** [formal-methods-track-h.md](../sketches/formal-methods-track-h.md) (main),
[formal-methods-track-h-protocols.md](../sketches/formal-methods-track-h-protocols.md),
[formal-methods-track-h-specification.md](../sketches/formal-methods-track-h-specification.md),
[persistence-aggregate-ownership.md](../sketches/persistence-aggregate-ownership.md) (normative for HO0 to HO9)
**Aggregate ownership:** the exploration note [persistence-aggregate-ownership.md](../notes/persistence-aggregate-ownership.md)
and its spike [`spikes/persistence-aggregate-ownership`](../../../spikes/persistence-aggregate-ownership/README.md),
reviewed in [persistence-aggregate-ownership-review.md](../notes/persistence-aggregate-ownership-review.md),
which records our decisions (H-D14) and the findings the HO slices act on
**Epic status:** [formal-methods.md](formal-methods.md)
**Decided by:** [ADR-A-FM4](../../architecture/decisions/ADR-A-FM4-persistence-formal-methods-home-and-scope.md)
(accepted, 2026-10-10, H-D1)

## Current position

This track is new, drafted 2026-10-08 directly from an independent, exhaustive review
(`docs/developer/notes/rdf-engine/persistence-fml.md`) applying this epic's own techniques to the
Persistence layer. Nothing has been built yet. The review itself was read in full, cross-checked
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

In this order, each per [plan §3.5](../plans/formal-methods-track-h.md#35-ho-aggregate-ownership):

0. Done 2026-10-10: `origin/main` is merged (`af2eb89`). `docs/developer/validation/LOG.md` is
   retired. The maintainer's merge is the sign-off, and the index, plans, status records and Validation
   Packs are the record, as the `lattice-lifecycle` skill now says.
1. HO0 to HO9, H1.4b and H1.5: done 2026-10-10. HO2 is done (ADR-A122 drafted, Proposed). ADR-A122 stays Proposed.
   The maintainer accepts it with the work package at the close.
2. Next, per the plan: H2, the typed IR (§4), which types the classified tree, the payload check and the
   required-parameter guard (TD-34), and H3 after it. Nothing in the aggregate-ownership work blocks them.

For the maintainer, at the close: verify the slices (each Validation Pack has its one command), countersign
the removed and rewritten tests listed in FMH-HO5, accept ADR-A122, and merge. Merging signs off every
slice on the branch, including H1.2d, H1.3 and H1.4a. 🔴 RELEASE TAGS REQUIRED once the merge is on `main`:
`persistence-v0.3.0`, `persistence-shapes-v0.3.0` and `persistent-foundation-v0.2.0`, which
`mise run build:ontology-releases` prints among the tags other merged work also owes.

## Slices

| Slice | State | Blocked on |
|---|---|---|
| H1.1 (prefix antichain and overlap check) | **signed off.** [Validation Pack](../validation/FMH-H1-1.md) | |
| H1.2a (witness harness, audit witnesses, measured gap list) | **signed off.** [Validation Pack](../validation/FMH-H1-2.md) | |
| H1.2b (witnesses for the refusals and warnings) | **signed off.** [Validation Pack](../validation/FMH-H1-2b.md) | |
| H1.2c (witnesses for the 13 remaining shapes) | **signed off.** [Validation Pack](../validation/FMH-H1-2c.md) | |
| H1.2d (refuse a multi-valued single-valued property, TD-25) | **authored and verified, awaiting the maintainer's gate.** [Validation Pack](../validation/FMH-H1-2d.md) | the maintainer's review |
| H1.3 (static template checks S-3 and S-4) | **authored and verified, awaiting the maintainer's gate.** [Validation Pack](../validation/FMH-H1-3.md) | the maintainer's review |
| H1.4a (refuse a composite boundary with several node properties, H-D4) | **authored and verified, awaiting the maintainer's gate.** [Validation Pack](../validation/FMH-H1-4a.md) | the maintainer's review |
| H1.4b (the declaration/implementation gap report) | **authored and verified.** [Validation Pack](../validation/FMH-H1-4b.md) | the maintainer's merge |
| H1.5 (stable labels) | **authored and verified.** [Validation Pack](../validation/FMH-H1-5.md) | the maintainer's merge |
| HO0 (correct the ownership note and its spike) | **authored and verified.** [Validation Pack](../validation/FMH-HO0.md) | the maintainer's merge |
| HO1 (composite replace: payload to the default graph, linear sweep, TD-39, TD-36) | **authored and verified.** [Validation Pack](../validation/FMH-HO1.md) | the maintainer's merge |
| HO2 (draft ADR-A122, Proposed) | **done** 2026-10-10. [ADR-A122](../../architecture/decisions/ADR-A122-aggregate-ownership.md), Proposed until the maintainer accepts the work package | |
| HO3 (`dal:` vocabulary 0.3.0: `dal:ownership`, reference data) | **authored and verified.** [Validation Pack](../validation/FMH-HO3.md). 🔴 release tags owed (`persistence-v0.3.0`, `persistence-shapes-v0.3.0`, `persistent-foundation-v0.2.0`), created on `main` | the maintainer's merge |
| HO4 (ownership tree and path compiler, added beside the old walk) | **authored and verified.** [Validation Pack](../validation/FMH-HO4.md) | the maintainer's merge |
| HO5 (switch the compiler to the tree, TD-03, TD-35, TD-37, TD-40) | **authored and verified.** [Validation Pack](../validation/FMH-HO5.md) | the maintainer's merge, and countersigning the removed tests |
| HO6 (ownership refusals and the roots-only warning) | **authored and verified.** [Validation Pack](../validation/FMH-HO6.md) | the maintainer's merge |
| HO7 (composite create and tombstone delete, TD-04) | **authored and verified.** [Validation Pack](../validation/FMH-HO7.md) | the maintainer's merge |
| HO8 (injective graph naming within and across families, TD-38) | **authored and verified.** [Validation Pack](../validation/FMH-HO8.md) | the maintainer's merge |
| HO9 (ownership documentation and close-out) | **authored and verified.** [Validation Pack](../validation/FMH-HO9.md) | the maintainer's merge |
| H2 (typed IR) | not started, outlined in the plan | H1 (informative, not a hard blocker) |
| H3 (specification registry) | not started, outlined in the plan | H2 preferred first (smaller, more self-contained), not a hard blocker |
| H4 (exhaustive cross-axis validation, BDD/SMT) | not started, outline only | H3 |
| H5 (capability-record extension, TLA+/Quint toolchain spike, protocol models A-D) | not started, outline only | H2 (read/write sets from the IR); ADR-A-FM4's acceptance recommended first |
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
| H-D3 | ADR-A79 addendum vs a fresh ADR for H2/H3's design | recommend an addendum; deferred to H2/H3 |
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
