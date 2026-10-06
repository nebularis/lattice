<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Formal Methods, Track C: Status

**Unit ID:** `formal-methods-track-c` (phase, within the `formal-methods` epic)
**Status:** C1 and C2 done, 2026-10-06. Both checked, results recorded. No ADR drafted yet
(not this track's job — see plan §6)
**Last updated:** 2026-10-06
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

**Next action, for the human:** decide the overlap rule (forbid overlapping membership by a new
Vocabulary shape; order composed sources by an explicit precedence rule; or allow free union and
require `broader`'s transitive closure to stay acyclic), and decide who drafts the shared
Vocabulary ADR IMA-D4a names (this track produced the checked evidence for it, not the ADR
itself). C3 (slot exclusivity and exhaustiveness, SMT, CCS C13a) is next in track C's own
numbering, not started.

## Slices

| Slice | State | Blocked on |
|---|---|---|
| C1 (Alloy skeleton) | **done** | nothing |
| C2 (scheme composition) | **done**, results recorded | nothing — the overlap-rule *decision* is the human's, not a blocker on this slice's own completion |
| C3 (slot exclusivity, SMT) | not started, outline only | C2 (done) |

## Open questions

| # | Question | Owner |
|---|---|---|
| the overlap rule | what composition does when two composed schemes share a member with different `skos:broader` parents — **confirmed reachable** by C2's `NoOverlapDisagreement` counterexample, three candidates named (sketch §2, §5; model README) | human decision, for whichever ADR accepts composition |
| home for the model | confirmed: `tools/models/vocabulary-scheme-composition/` (plan §4) | closed |
| who writes the shared Vocabulary ADR | track C produced the checked evidence; a human, or whichever agent is asked to draft it from that evidence, writes the ADR itself | human |

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
