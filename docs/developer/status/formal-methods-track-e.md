<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Formal Methods, Track E: Status

**Unit ID:** `formal-methods-track-e` (phase, within the `formal-methods` epic)
**Status:** E1.0 and E1.1 done, 2026-10-06, native route only (human instruction). E1.2's
blocker is resolved by reading track B's sketch (2026-10-07): the rounding/residual theorem
belongs to B4/E3-E4, not Quantification, so E1.2 itself is retargeted, not merely unblocked. E1.3
remains blocked (see Log). **E1.4 done, 2026-10-09**, on branch `fm/eligibility-pass` (machine S),
alongside FM-D17 (built, not only decided) and track B's B2.1/B2.2 -- together the formal-methods
epic's own Eligibility pass (FM-EP) CCS's C9b3 waits on
**Last updated:** 2026-10-09
**Plan:** [formal-methods-track-e.md](../plans/formal-methods-track-e.md)
**Sketch:** [formal-methods-track-e.md](../sketches/formal-methods-track-e.md)
**Epic status:** [formal-methods.md](formal-methods.md)
**Decided by:** [ADR-A-FM1](../../architecture/decisions/ADR-A-FM1-formal-methods-prover-choice.md),
[ADR-A-FM2](../../architecture/decisions/ADR-A-FM2-formal-methods-theory-home.md)

## Current position

Track D closed with FM-D1 decided (Isabelle/HOL). FM-D2 is decided and acted on: track E's
theories live under `tools/proofs/`, one subdirectory per layer. `tools/proofs/eligibility/` now
exists: `Kernel.thy` generated from `ontology/eligibility/README.md`'s new `isabelle-spec` block
(§10), `KernelLaws.thy`/`Eligibility.thy`/`Adequacy.thy` hand-written (ported from track D's
spike, byte-identical statement digests), `gate.py`/`claim-schema.json` carried over, a
`check.py` driver and a `check:proofs` `mise` task. `isabelle build` and `gate.py` both pass,
native route (`spikes/formal-prover/env/driver.py --route native`); no Isabelle image exists, by
design (deferred).

**2026-10-09, branch `fm/eligibility-pass` (machine S), done.** FM-D17 decided (A+B hybrid: a
plain markdown truth table in the README for a reader, a connecting note, then the `isabelle-spec`
block itself widened to carry `or3`/`and3`/`neg3`'s `fun` clauses, with `tools/literate_extract.py`
rendering that same block a second time into a generated Python module) and built. E1.4 done
alongside it. Both verified by mutation (below), not only by a clean build.

**FM-D17, built.** `ontology/eligibility/README.md` §10 now carries the three truth tables
(prose), a connecting note, and the widened `isabelle-spec` block (datatype plus `or3`/`and3`/
`neg3`; `decision_leq` stays out of scope, a predicate not a finite case table, per FM-D17's own
decided text). `tools/literate_extract.py` gained `parse_fun_clauses`/`resolve_truth_table`/
`render_python` and a `--reference-root` argument; `Kernel.thy` now carries the connectives, and a
new generated `tools/reference/eligibility/src/reference_eligibility/_kernel_defs.py` carries their
Python rendering (a literal, fully-resolved lookup table per connective, not symbolic pattern
matching re-derived at import time). A new hand-written `_decision.py` holds `Decision`/the three
constants, breaking what would otherwise be a cycle between `kernel.py` and the generated module.
`kernel.py` now imports `or3`/`and3`/`neg3` from the generated module and keeps `decision_leq`/
`some_value`/`every_value` hand-written. `KernelLaws.thy` no longer defines the connectives itself,
only `decision_leq` and the lemmas. `check_formal_freshness.py` extended to check the generated
Python module's freshness too, alongside `Kernel.thy`'s.

**E1.4, built.** `gate.py`'s digest now covers every `datatype`/`fun`/`definition`/`abbreviation`
block in the layer (`extract_definitions`), not only the gated statement's own text — confirmed by
mutation (below). Five new gated lemma groups in `KernelLaws.thy`/`Eligibility.thy`: **TA3** (the
full truth table for `or3`/`and3`/`neg3`, ruling out the degenerate stand-ins TA1/TA2 alone
admit), **TA4** (commutativity, associativity, idempotence, identity and absorbing elements for
`or3`/`and3`), **TA5** (both De Morgan forms for the connectives themselves, `neg3 (or3 a b) =
and3 (neg3 a) (neg3 b)` and its dual), **TL4a** (the empty-list base cases, stated and gated —
`Undetermined` for both `some_value`/`every_value`, correcting an error in this track's own prior
plan text, which had wrongly written `Denied`/`Permitted`, checked against the actual README and
code rather than perpetuated), **TL4b** (permutation/duplication invariance for both readings,
derived directly from the already-proved TL1 spec lemmas via `set xs = set ys`, not fresh
induction). `Adequacy.thy`'s 15 lemmas now use `by simp` (kernel-checked), not `by eval` (an oracle
dependency). `gate.py`'s banned-pattern scan, now printed explicitly as "Assumption audit: ...",
also flags `by eval`/`by evaluation`. All 13 claims (8 existing, redigested under the new formula;
5 new: TA3, TA4, TA5, TL4a, TL4b) pass.

**Mutation-tested, three scenarios, each reverted after confirming**: (a) a wrong `or3` cell
(`or3 Denied b = Permitted`) — the real Isabelle build now fails, at `Adequacy.thy` **and** at
several of the new TA3/TA4 characterising lemmas, confirming they really do pin down the
semantics; (b) a cosmetically weakened TA1 statement (an added vacuous hypothesis) — `gate.py`
flags exactly `TA1`'s digest, nothing else; (c) **the scenario E1.4 exists for**: changing `or3`'s
definition in `Kernel.thy` while leaving every gated lemma's statement text byte-for-byte
unchanged — before this fix this would have passed silently; now every one of the 13 claims shows
`STATEMENT DIGEST MISMATCH`.

**Validated**: `python tools/proofs/check.py eligibility` — clean build, `GATE: pass`, exit 0.
`python -m pytest tools/reference/eligibility/tests -q` — 66 passed (was 63 at the start of this
branch: +1 B2.2, +2 B2.1). `python tools/check_formal_freshness.py` — both checks (Kernel.thy
and the new Python module's freshness, plus law coverage) clean.

**Next action, for the human:** review and accept this branch's work (FM-D17, E1.4, plus track
B's B2.1/B2.2 described in track B's own status record) so CCS's C9b3 can start. Separately, E1.2's blocker is resolved, not merely diagnosed: the track B
sketch (`formal-methods-track-b.md` §6) reads the reference-evaluator sketch's own RE6/RE-Q4
directly and finds the rounding/residual rule for `split`/`proRata` belongs to the evaluation
context's combinator algebra (track B's B4, mechanised later by track E's own E3/E4) — not to
Quantification, where E1.2 went looking and found nothing. E1.2 as originally scoped (a
Quantification theorem) is retired; the theorem's real home is E3/E4, after B4 states it
precisely, which itself waits on CCS's C12 (track B's own status). E1.3 (binding resolution)
remains blocked: track C's C2 is done, but the overlap-rule decision its model surfaced has not
been made, and the Vocabulary ADR IMA-D4a calls for has not been drafted (track C's own status).
No action needed on E1 until one of those two clears.

## Slices

| Slice | State | Blocked on |
|---|---|---|
| E1.0 (home, generation tooling) | **done** | nothing |
| E1.1 (the kernel, for real) | **done**, folded into E1.0's pass | nothing |
| E1.2 (rounding and residual theorem) | **retired from this track's E1** — its real home is E3/E4, after track B's B4 (see Log, 2026-10-07) | track B's B4, which waits on CCS's C12 |
| E1.3 (binding resolution) | not started | track C's C2 is **done**, but the overlap-rule decision it surfaced, and the Vocabulary ADR IMA-D4a names, are not yet made/drafted (track C's own status) |
| E1.4 (harden the gate and the kernel theory) | **done**, 2026-10-09 | nothing |
| E2 to E5 | not started, outline only | E1 |

## Open questions

| # | Question | Owner |
|---|---|---|
| where `split`/`proRata`/the combinator algebra are specified normatively | **answered, 2026-10-07**: track B's B4 (the evaluation context's combinator algebra), mechanised later by E3/E4, per the reference-evaluator sketch's own RE6/RE-Q4 — not a new Quantification section, not folded into the kernel | closed |
| the Isabelle image | does not exist; needed before epic E9's "image route only" rule applies to track E's recorded claims, not before E1 itself | human, timing deferred 2026-10-06 to conserve tokens, confirmed again when E1 started (native/local explicitly requested) |

## Log

- 2026-10-06: sketch and plan written, following track D's close and ADR-A-FM1. E1 split into
  E1.0 (home and generation tooling, a prerequisite the epic's numbering does not name), E1.1 (the
  kernel), E1.2 (rounding and residual, Quantification), and E1.3 (binding resolution, blocked on
  track C's C2). No code written yet.
- 2026-10-06: FM-D2 decided (ADR-A-FM2): `tools/proofs/`, one subdirectory per layer, not beside
  each layer under `ontology/` and not named `tools/formal/`. The attached
  `improved-ontology-documentation.md` sketch (README narrative into generated `.ttl` annotations)
  was reviewed for compatibility: confirmed orthogonal to track E's own generation (a separate
  extraction target from the same README, fenced-code-block generated, not HTML-comment
  generated), not adopted, no plan or slice opened for it. E1.0 unblocked; still needs the
  human's go-ahead to actually start, and its own generation-direction question decided when it
  does.
- 2026-10-06: E1.0 and E1.1 done, native route only (human instruction, explicit for this slice).
  `tools/literate_extract.py` gained an `isabelle-spec` fence tag and `--proofs-root`, purely
  additively (Surface/Wording/Behaviour's existing `--check` invocations re-run unchanged and
  pass, confirming no regression). `ontology/eligibility/README.md` §10 (new) states the closed
  `decision` datatype; `tools/proofs/eligibility/Kernel.thy` is generated from it.
  `KernelLaws.thy`/`Eligibility.thy`/`Adequacy.thy` are hand-written, ported from
  `spikes/formal-prover/isabelle/` with identical statement digests (TA1, TA2, TL1-some,
  TL1-every, TL2, TL3a, TL3b, AQ). `tools/proofs/gate.py` (PF1's fix carried over) passes.
  Eligibility's pre-existing `spec`/`vocab`/`shapes` drift (TD-16) was left untouched on purpose:
  only the new generated output was written. `check:proofs` wired into `mise.toml`, outside the
  default aggregate `check` task (same "large, explicit" convention as the formal-prover D0
  tasks), since Isabelle is a heavy native toolchain not every host has installed.
- 2026-10-06: E1.2 attempted. Searched `ontology/quantification/README.md` and ADR-A93 to
  ADR-A95 directly (not guessed at): neither names `split`, `proRata`, or any rounding/residual-
  allocation rule. Quantification's only rounding-related content is `qnt:roundingPolicy`, a
  property whose own README already lists it as having no declared vocabulary yet. Searched all
  of `ontology/` for `proRata`: zero matches, in any layer, under any name. The theorem exists
  only in two epic sketches, which do not agree on which track owns it
  (`sketches/formal-methods.md` §8.1 places it with the kernel, §9.2 places it with the
  combinator algebra the epic plan assigns to E3). Not drafted: formalising an operation with no
  design-time decision behind it risks fixing its design inside a proof, the same risk already
  held E1.3 back for binding resolution. Plan and this record both updated; the human's decision
  is needed on where it is specified and under which ADR before this resumes.
- 2026-10-07: E1.2's blocker resolved by reading track B's sketch directly, not re-derived here.
  The reference-evaluator sketch's own RE6 and RE-Q4 already state that the rounding and
  residual-allocation rule for `split`/`proRata` belongs to the evaluation context's combinator
  algebra, with a leaning already recorded ("largest remainder, with ties broken by a total order
  of accounts"). That is track B's B4 (not yet started, waiting on CCS's C12) and track E's own
  E3/E4 (the combinator algebra and the evaluation context), mechanised once B4 states it
  precisely. E1.2 as originally scoped — a Quantification theorem — is retired, not merely
  renamed: there was never a Quantification-level theorem to prove, since the rule was never
  Quantification's to state. No proof is drafted by this change; it only corrects where the work,
  when it is ready, belongs.
- 2026-10-09, branch `fm/eligibility-pass` (machine S), FM-EP: FM-D17 built (A+B hybrid, decided
  the same session after a design discussion — a parser reading the Isabelle `fun` clauses
  themselves, not a third neutral notation, so the proof side is extraction-only, never synthesis;
  `decision_leq` scoped out, by FM-D17's own original text, since it is a predicate, not a finite
  case table) and E1.4 (gate digest covers definitions; TA3/TA4/TA5 characterising lemmas; TL4a/
  TL4b in `Eligibility.thy`; `by eval` replaced with `by simp`; the assumption audit extended and
  printed explicitly; three mutation scenarios run and reverted). Full detail above, under
  "FM-D17, built" and "E1.4, built". `gate.py`'s own module docstring and `check_formal_freshness.py`
  updated to match. Alongside track B's B2.1/B2.2 on the same branch (its own status record).
