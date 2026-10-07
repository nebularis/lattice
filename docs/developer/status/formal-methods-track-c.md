<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Formal Methods, Track C: Status

**Unit ID:** `formal-methods-track-c` (phase, within the `formal-methods` epic)
**Status:** C1 and C2 done, 2026-10-06. `ADR-A116` (Vocabulary scheme composition) drafted
2026-10-07, Proposed, citing this track's checked evidence
**Last updated:** 2026-10-07
**Plan:** [formal-methods-track-c.md](../plans/formal-methods-track-c.md)
**Sketch:** [formal-methods-track-c.md](../sketches/formal-methods-track-c.md)
**Epic status:** [formal-methods.md](formal-methods.md)

## Current position

Read directly from `main` (without checking it out): CCS's C8 shipped without deciding HQ-4,
explicitly deferring to track C2 ("the lease's date words are not written, waiting for HQ-4 and
track C2," C8's own validation pack). insurml-alignment's IMA-D4a is in the same state. Track C2
was genuinely green-field: nothing built elsewhere resolved it.

C1 installed Alloy Analyzer 6.2.0 (one MIT-licensed JAR, `C:\fmx\alloy\alloy.jar`, not tracked in
the repository) and smoke-tested it headlessly via `exec`: a satisfiable and an unsatisfiable
model were told apart correctly via `receipt.json`.

C2 built `tools/models/vocabulary-scheme-composition/SchemeComposition.als` and ran two checks at
scope 4: `EverySourceResolves` found no counterexample (composition does not drop a source that
resolves alone, HQ-4's own property, made checkable); `NoOverlapDisagreement` **found a
counterexample** — the sketch's proposed "union of members, union of hierarchies" does not by
itself prevent two composed schemes disagreeing about a shared concept's `broader` parent. Full
results, the counterexample instance read and explained, and the three candidate fixes are in
[the model's own README](../../../tools/models/vocabulary-scheme-composition/README.md).

**Next action, for the human:** review and accept (or revise) `ADR-A116`
(`docs/architecture/decisions/ADR-A116-vocabulary-scheme-composition.md`), which decides the
overlap rule (forbid, by a new static Vocabulary shape — the simplest of the three candidates,
not the precedence or free-union alternatives) and the composition construct itself
(`voc:BindingAspect`/`voc:forAspect`). Implementing it (the ontology change, the shape, the
resolver's `CompositionOverlapError`) is a separate follow-up slice, not done by the ADR itself.
C3 (slot exclusivity and exhaustiveness, SMT, CCS C13a) is next in track C's own numbering, not
started.

## Slices

| Slice | State | Blocked on |
|---|---|---|
| C1 (Alloy skeleton) | **done** | nothing |
| C2 (scheme composition) | **done**, results recorded | nothing — the overlap-rule *decision* is the human's, not a blocker on this slice's own completion |
| C3 (slot exclusivity, SMT) | not started, outline only | C2 (done) |

## Open questions

| # | Question | Owner |
|---|---|---|
| the overlap rule | **decided in `ADR-A116` (Proposed)**: forbidden, checked by a new static Vocabulary shape — the simplest of the three candidates named in the sketch/model README | human, to accept or revise the ADR |
| home for the model | confirmed: `tools/models/vocabulary-scheme-composition/` (plan §4) | closed |
| who writes the shared Vocabulary ADR | **done**: `ADR-A116`, drafted 2026-10-07, citing this track's checked evidence directly | human, to accept or revise |

## Log

- 2026-10-06: sketch and plan written. HQ-4 and IMA-D4a read directly from `main`'s commit
  history and this repository's own CCS/insurml-alignment plans (not assumed): both explicitly
  defer to track C2, confirming it as genuinely unblocked, green-field work. Alloy chosen over
  SMT for C2 specifically, per the epic plan's own C2/C3 split (relational vs numeric), not
  re-derived.
- 2026-10-06: C1 done. Alloy Analyzer 6.2.0 installed at `C:\fmx\alloy\alloy.jar` (not tracked),
  run under the mise-managed Java 25 JDK already on this host (the bare `java` on a fresh
  terminal's `PATH` is a stale 1.8.0_491 — invoke the JDK's own `bin\java.exe` explicitly).
  Smoke-tested via `exec` on a two-command model (`smoke.als`, not kept — a one-off toolchain
  check): a satisfiable `run` reported `SAT` with an instance in `receipt.json`, a deliberately
  unsatisfiable `run` reported `UNSAT` with no `solution` key.
- 2026-10-06: C2 done. `SchemeComposition.als` built: `Scheme` given explicit `Concept` members
  and a `broader` hierarchy (needed to state the overlap question concretely, a refinement on the
  sketch's more abstract proposal found necessary once Alloy's type-checking was run against it),
  `single: Source -> Context -> lone Scheme` standing in for ADR-A85's whole resolver collapsed to
  "at most one scheme per source per context." Two checks run at scope 4, both results recorded
  with the actual instances read (not only pass/fail counts): `EverySourceResolves` — no
  counterexample; `NoOverlapDisagreement` — a counterexample found (two schemes sharing two
  member concepts, disagreeing about one concept's `broader` parent). Home confirmed as
  `tools/models/vocabulary-scheme-composition/`, with a parent `tools/models/README.md`. No
  ontology or ADR change made — this track's job is the checked evidence, not the decision or its
  ratification.
- 2026-10-07: `ADR-A116` (Vocabulary scheme composition) drafted, Proposed, at the human's
  explicit request. Cites this track's evidence directly: `EverySourceResolves`'s no-counterexample
  result as the property composition must keep, `NoOverlapDisagreement`'s counterexample as the
  reason the overlap rule cannot be left unstated. Decides the forbid-overlap candidate (a new
  static Vocabulary SHACL-SPARQL shape), a new `voc:BindingAspect`/`voc:forAspect` construct
  (named to avoid colliding with `pty:Role` and `ins:forPurposeOf`, both already taken), and
  reuses ADR-A85's resolution algorithm unchanged, per aspect — fully additive, no existing
  consumer's behaviour changes. Eligibility's own hierarchical-match addendum
  (`insurml-typing.md` §6.1) stays a follow-on against ADR-A100, not decided here. Filed as plain
  `ADR-A116`, not the epic's own `A-FM` block, since this is a shared Vocabulary-layer decision,
  not an epic-scoped artefact — checked against both this branch's and `main`'s catalogues first
  (both agreed up to A115). Implementation (the ontology change itself, the shape, the resolver's
  `CompositionOverlapError`) is explicitly deferred to a follow-up slice, not done by this commit.
  CCS's and insurml-alignment's own plan documents are left untouched (Machine R's own editorial
  territory); the human's own bundle/push to `origin` is expected to surface this ADR to them.
