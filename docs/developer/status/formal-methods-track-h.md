<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Formal Methods, Track H: Status

**Unit ID:** `formal-methods-track-h` (phase, within the `formal-methods` epic)
**Status:** In progress. H1.1 to H1.2c signed off. H1.2d, H1.3 and H1.4a are authored and verified, awaiting human review
**Last updated:** 2026-10-08
**Plan:** [formal-methods-track-h.md](../plans/formal-methods-track-h.md)
**Sketches:** [formal-methods-track-h.md](../sketches/formal-methods-track-h.md) (main),
[formal-methods-track-h-protocols.md](../sketches/formal-methods-track-h-protocols.md),
[formal-methods-track-h-specification.md](../sketches/formal-methods-track-h-specification.md)
**Epic status:** [formal-methods.md](formal-methods.md)
**Decided by:** [ADR-A-FM4](../../architecture/decisions/ADR-A-FM4-persistence-formal-methods-home-and-scope.md)
(**Proposed**, not yet accepted)

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

**Next action, for the human:** review and accept (or revise) `ADR-A-FM4`
(`docs/architecture/decisions/ADR-A-FM4-persistence-formal-methods-home-and-scope.md`), which
decides this track's home (mechanised theories under `tools/proofs/persistence/`, design-time
models — Alloy **and** the new TLA+/Quint protocol models — under `tools/models/`) and its scope
(RDF/SPARQL only, no relational work). H1 (static hygiene) needs no toolchain and no ADR
acceptance to start, and could begin immediately if the human wants work to proceed before
reviewing the ADR; H2 onward should wait for ADR-A-FM4's acceptance.

## Slices

| Slice | State | Blocked on |
|---|---|---|
| H1.1 (prefix antichain and overlap check) | **signed off.** [Validation Pack](../validation/FMH-H1-1.md) | |
| H1.2a (witness harness, audit witnesses, measured gap list) | **signed off.** [Validation Pack](../validation/FMH-H1-2.md) | |
| H1.2b (witnesses for the refusals and warnings) | **signed off.** [Validation Pack](../validation/FMH-H1-2b.md) | |
| H1.2c (witnesses for the 13 remaining shapes) | **signed off.** [Validation Pack](../validation/FMH-H1-2c.md) | |
| H1.2d (refuse a multi-valued single-valued property, TD-25) | **authored, verified by the agent, awaiting the human's gate.** [Validation Pack](../validation/FMH-H1-2d.md) | the human's review |
| H1.3 (static template checks S-3 and S-4) | **authored, verified by the agent, awaiting the human's gate.** [Validation Pack](../validation/FMH-H1-3.md) | the human's review |
| H1.4a (refuse a composite boundary with several node properties, H-D4) | **authored, verified by the agent, awaiting the human's gate.** [Validation Pack](../validation/FMH-H1-4a.md) | the human's review |
| H1.4b (the declaration/implementation gap report) | not started | none |
| H1.5 (stable labels) | not started, fully detailed in the plan | H1.4's gates, by the working agreement |
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
| H-D1 | accept, revise or reject ADR-A-FM4 | human |
| H-D2 | TLA+ or Quint | deferred to H5's own toolchain spike |
| H-D3 | ADR-A79 addendum vs a fresh ADR for H2/H3's design | recommend an addendum; deferred to H2/H3 |
| H-D4 | fix the composite-boundary soundness gap now (a refusal) or wait for H2's typed IR | decided by the human, 2026-10-09: left as a documented, refused combination until H2's typed IR makes the fix structural. H1.4 carries the refusal. Its exact condition needs care, because the shipped composite example nests one property inside another (`lineItem` then `sku`) and TD-03 concerns sibling properties |
| H-D5 | feed track A's ledger once it exists, or keep an independent record permanently | recommend: feed track A once it starts |
| H-D6 | H1.1 reads "antichain" per scope kind. Nested `dal:graphPrefix` values are a **violation** only when the scopes cover a common class (each graph-pattern scope is its own target, so disjoint classes cannot collide). Nested `dal:iriPrefix` values are a **warning**, because the resolver ranks by `dal:priority`. The plan says only "antichain", so this narrows it | agreed by the human, 2026-10-09 |
| H-D8 | H1.2 is delivered in three parts (a, b, c), because the first run found 55 of 83 rules unwitnessed and closing them together breaks the slice-sizing rule. The plan's H1.2 validation ("every existing rule either has a witness or is listed as a gap") is met by part a. The plan's metric "vacancy rate closed" is then measured as the shrinkage of `known-gaps.txt` | agreed by the human, 2026-10-09 |
| H-D9 | the rule inventory is read from the package's own source (refusals and warnings by syntax, shapes from `constraints.ttl`, audits from the template names), not from a hand-kept list, so a new rule cannot dodge the check. A rule is keyed by its `CrossAxisViolation` kind, or by exception class name for the four refusals that carry no kind | agreed by the human, 2026-10-09 |
| H-D10 | how to close TD-25 (a multi-valued functional property is resolved by triple order, law L1). Refuse it in the resolver, run the structural shapes inside `compile`, or add a hygiene check. See the H1.2c Validation Pack for the consequences of each | decided by the human, 2026-10-09: refuse it in the resolver. Done in H1.2d |
| H-D11 | S-3 treats a `$name` variable as bound by the caller, read from the template text, since the compiled profile lists no request-time parameters | **decided by the human, 2026-10-09**: keep option A, let H2's typed IR settle it. [Walkthrough](../plans/formal-methods-track-h.md#133-h-d11-how-does-the-check-know-which-variables-the-caller-supplies) |
| H-D12 | S-3 treats a `BIND` over bound inputs as binding its variable, though an expression can fail and leave it unbound | **decided by the human, 2026-10-09**: keep option A, record the limitation here and in TD-26, take option D (a required-parameter guard) in H2. [Walkthrough](../plans/formal-methods-track-h.md#134-h-d12-does-a-bind-count-as-giving-its-variable-a-value) |
| H-D13 | H1.4a also changes what is bound for a shape with exactly one node property, from the first path to the node property, and puts the boundary closure in path order. The old binding could pick a plain property and depended on triple order. See the H1.4a Validation Pack | human, confirm at H1.4a's gate |
| H-D7 | H1's checks live in one new module, `persistence.hygiene`, behind one `hygiene` subcommand, and run under `check:persistence`. No new `mise` task until H1's closing slice | agreed by the human, 2026-10-09 |

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
  finding against any shipped example. Working agreement for Track H changed by the human: the agent
  completes each slice, commits and pushes it, and debriefs. The sign-off in `validation/LOG.md`
  stays the human's.
- 2026-10-08: the human reported an intermittent failure in
  `test_identity_minting_m1.py::test_export_recipes_writes_each_recipe_and_refuses_a_tampered_one`.
  It predates H1.1 and is unrelated to it. The test tampered with an arbitrary recipe node by
  replacing `urn:` with `urx:`, and the `AdoptedIdentity` recipe contains no `urn:`, so one run in
  seven the edit changed nothing and no error was raised (11 failures in 60 runs before the fix).
  The test now chooses a node deterministically and asserts the edit took effect (0 in 60 after).
  The assertion it protects is unchanged, so this does not weaken the test.
- 2026-10-09: H1.1 signed off by the human. H1.2a authored: `persistence.witness`, the `witness`
  subcommand, ten audit witness datasets, `known-gaps.txt` and 20 test cases. First measurement: 28
  of 83 rules witnessed (refusals 10/34, warnings 3/11, shapes 10/33, audits 5/5), 55 listed as gaps.
  All five audits fire on a violating dataset and stay silent on a clean one, so no audit defect was
  found. Six refusals are named by no test and are the first targets of H1.2b. `check:persistence`
  is at 842 passed. An architecture test (only `persistence.render` may import `chevron`) caught a
  first draft of the harness, which now fills the request-time slot by plain substitution.
- 2026-10-09: H1.2a signed off, and H-D6 to H-D9 confirmed by the human. H1.2b authored: 33 witness
  fixtures, a patch format for them, a drift check, and `known-gaps.txt` reduced to the 13 shapes.
  Refusals are 36 of 36 witnessed and warnings 11 of 11, shapes 20 of 33, audits 5 of 5 (72 of 85).
  Correction to H1.2a's harness: its source scan missed two refusals whose kind reaches `fail`
  through a helper parameter. It now follows parameters and reports any kind it cannot determine.
  Two defects found and entered in the technical debt register as TD-23 (a class named only by
  `dal:coversClass` is never compiled) and TD-24 (the CLI suggests a `--target-class` option that
  does not exist). `check:persistence` is at 849 passed.
- 2026-10-09: H1.2b signed off. An interim fix, by the human's request: `witness --verbose` prints
  WITNESSED lines green and GAP lines red on a terminal (`6bd91a8`). H1.2c authored: 13 shape
  witnesses, one conforming fixture, and a stricter rule for shapes (a shape is witnessed only if some
  fixture makes it report and some fixture has data it accepts, prompted by a probe in which a
  shape that fires on everything counted as witnessed). `known-gaps.txt` is now empty, 85 of 85 rules
  are witnessed (refusals 36, warnings 11, shapes 33, audits 5). H1.2 is complete. New finding TD-25,
  asserted with TD-23 as strict expected failures in `tests/test_known_defects.py`, and recorded as
  the open decision H-D10. `check:persistence` is at 857 passed and 2 xfailed.
- 2026-10-09: H1.2c signed off. The human decided H-D10: the compiler refuses a multi-valued
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
- 2026-10-09: the human asked for walkthroughs of H-D11 and H-D12 and decided H-D4. The walkthroughs
  are [plan §13](../plans/formal-methods-track-h.md#13-walkthrough-the-two-assumptions-behind-check-s-3-h-d11-and-h-d12),
  written from experiments on the real templates. They found one new hazard, TD-26: an update run
  without a required `$parameter` writes a partial record and advances the counter, with no error.
  `main` was merged into the branch (`f7c72d9`), with no conflicts.
- 2026-10-09: the human decided H-D11 and H-D12 (option A for both, remedies in H2). Recorded in the
  plan (§8 and §13.5), in TD-26, and in the `templatecheck.py` docstring. No code behaviour changed.
- 2026-10-09: H-D11 and H-D12 recorded. The TD-26 demonstration was re-run on a conforming engine
  (Oxigraph) and corrected: rdflib's `update` evaluates lazily, and had wrongly shown no revision
  record after the retry. H1.4 is split into H1.4a and H1.4b. H1.4a authored: a composite boundary
  whose shape reaches other nodes through more than one property is refused
  (`CompositeBoundaryMultipleProperties`), the bound property is the node property and no longer the
  first path found, and the closure no longer depends on triple order. Findings: the shipped
  composite example is sound (one node property, `sku` is a plain property), and the old binding
  was both incomplete and order-dependent. The plan's expectation that the shipped example would
  show the gap was wrong. 87 of 87 rules witnessed. `check:persistence` is at 905 passed, 3 skipped
  (the tests that need `pyoxigraph`) and 1 xfailed.
