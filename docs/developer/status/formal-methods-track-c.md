<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Formal Methods, Track C: Status

**Unit ID:** `formal-methods-track-c` (phase, within the `formal-methods` epic)
**Status:** Sketch and plan written 2026-10-06. C1 (Alloy skeleton) and C2 (scheme composition)
about to start
**Last updated:** 2026-10-06
**Plan:** [formal-methods-track-c.md](../plans/formal-methods-track-c.md)
**Sketch:** [formal-methods-track-c.md](../sketches/formal-methods-track-c.md)
**Epic status:** [formal-methods.md](formal-methods.md)

## Current position

Read directly from `main` (without checking it out, to keep this branch clean for a later
bundle): CCS's C8 shipped without deciding HQ-4, explicitly deferring to track C2 ("the lease's
date words are not written, waiting for HQ-4 and track C2," C8's own validation pack).
insurml-alignment's IMA-D4a is in the same state. Track C2 is genuinely green-field: nothing
built elsewhere resolves it.

Both HQ-4 and IMA-D4a are read in full, not assumed: the same underlying need (a contract
resolving to a *set* of schemes in a context, membership and hierarchy the union of theirs),
stated independently by CCS (building C7b) and insurml-alignment (`insurml-typing.md` §6.1),
which itself names HQ-4 and recommends one shared Vocabulary ADR.

**Next action, for the human:** none blocking. C1 (install Alloy, smoke-test it) is starting.

## Slices

| Slice | State | Blocked on |
|---|---|---|
| C1 (Alloy skeleton) | starting | nothing |
| C2 (scheme composition) | starting alongside C1 | C1's toolchain |
| C3 (slot exclusivity, SMT) | not started, outline only | C2 |

## Open questions

| # | Question | Owner |
|---|---|---|
| the overlap rule | what composition does when two composed schemes share a member with different `skos:broader` parents (sketch §2, §5) | C2's model result decides which candidate is recommended; the human decides which is accepted |
| home for the model | `tools/models/vocabulary-scheme-composition/`, provisionally (plan §4) | confirmed or changed once C1 is under way |
| who writes the shared Vocabulary ADR | track C produces the checked evidence; a human, or whichever agent is asked to draft it from that evidence, writes the ADR itself | human |

## Log

- 2026-10-06: sketch and plan written. HQ-4 and IMA-D4a read directly from `main`'s commit
  history and this repository's own CCS/insurml-alignment plans (not assumed): both explicitly
  defer to track C2, confirming it as genuinely unblocked, green-field work. Alloy chosen over
  SMT for C2 specifically, per the epic plan's own C2/C3 split (relational vs numeric), not
  re-derived. No model written yet.
