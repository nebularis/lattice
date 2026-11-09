<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: Formal Methods Track E FME-0, the prelude session

**Unit:** `formal-methods-track-e` ([plan](../plans/formal-methods-track-e.md) §3, [status](../status/formal-methods-track-e.md))
**Machine:** S. **Branch:** `fm/prelude-and-ledger-proofs`, per the [machine S brief](../notes/machine-s-brief-2026-11-08.md). Commits are local, and pushing is the maintainer's.
**Decisions:** ADR-A-FM2's addendum of 2026-11-08, FM-D18, the ledger plan's LG-Q14 decided (d), STD-324
**Reads:** the [HOL sessions survey](../sketches/hol-sessions-survey.md) §7 and §8

## Invariant

One session that is not a layer's, `LatticeBase`, imports the `HOL-Library` theories the layers' proofs reach for and states no law. Every layer session parents on it, every theorem they held is still proved and every claim still gated, and its heap is built on first use, never by `bootstrap` and never with `-f`.

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| FME0-01 | `tools/proofs/base/` / read / `ROOT` declares `session LatticeBase = HOL +` with `sessions "HOL-Library"`, `document = false`, `quick_and_dirty = false`, and `Prelude.thy` imports the survey's nineteen theories and nothing else, with no law, claim or gate marker | L1 | + |
| FME0-02 | `mise run check:proofs` on a machine with no prelude heap / run / the prelude is built first, then every layer session, each `GATE: pass`, and the prelude's gate reports nothing to gate | L2 | + |
| FME0-03 | the same command again / run / the prelude is found current and not rebuilt | L2 | + |
| FME0-04 | `session Eligibility` and `session Ledger` / read / both `= LatticeBase +`, and their claim counts are unchanged | L1 | + |
| FME0-05 | a layer build without `-d base` / run / fails, the parent session not found | L2 | - |
| FME0-06 | `mise run check:formal-freshness` / run / passes, no `Kernel.thy` changed | L1 | + |

## One command

```bash
mise run check:proofs
```

## Artefacts to inspect

`tools/proofs/base/ROOT`, `Prelude.thy` and `README.md`, `tools/proofs/check.py`, `tools/proofs/gate.py`, the two layer `ROOT` files, `tools/proofs/README.md`.

## Deliberate non-coverage

The formal-methods workflow and the cloud setup are unchanged, since they run `tools/proofs/check.py`, which now builds the prelude itself. The prelude's build time on machine R and in the workflow is not measured here. No layer README changes.

## Handoff

Built on machine S, 2026-11-09, Isabelle2025-2 through its bundled Cygwin, committed locally and not pushed.

**What was built.**

- **`tools/proofs/base/`.** `ROOT` declares `LatticeBase` as the brief states, with `timeout = 1800`. `Prelude.thy` imports the nineteen theories of the survey's §7 table in its order, and nothing else. A `README.md` says what the session is for, points at the survey for why each import is there, and says how it is built.
- **`tools/proofs/check.py`** builds `LatticeBase` first, stops if it fails, then each layer. Every build runs from `tools/proofs/` with `-d base`, and a layer's with `-d base -d <layer>`, the brief's `-d tools/proofs/base` relative to that directory. `base/` is never treated as a layer.
- **`tools/proofs/gate.py`** prints `GATE: nothing to gate` for a directory with no claim and no gated statement, and still runs the assumption audit over it, so a `sorry` in the prelude fails as anywhere.
- **The two layer sessions** are `= LatticeBase +`, each with `timeout = 90` in its `ROOT`.
- **`tools/proofs/README.md`** describes the prelude and the build commands, now from `tools/proofs/` with `-d base`.

**Two findings, each changing the design as briefed.**

1. **A command-line timeout rebuilt the prelude.** `check.py` passed `-o timeout=90` to every build, as before. That option applies to every session in the build, the parent included, so the prelude's options differed from those its heap was built with, and the first layer build rebuilt it under a 90 second bound and timed out (`*** Timeout`, `Unfinished session(s): Eligibility, LatticeBase`). Each session's `ROOT` now states its own `timeout`, and `check.py` passes no `-o`.
2. **Naming the prelude's directory two ways rebuilt it once more.** Built from its own directory as `-d .`, then from a layer's as `-d ../base`, the second build rebuilt the heap (`Building LatticeBase ... Finished LatticeBase (0:01:45 elapsed time)`), though the ledger build after it, also `-d ../base`, found it current. So every build now runs from `tools/proofs/` and names it `-d base`, and the next run found every session current.

**What was run, each output read in full.**

| Run | Prelude | Eligibility | Ledger | Exit |
|---|---|---|---|---|
| 1, first build, with `-o timeout=90` | `Finished LatticeBase (0:01:31 elapsed time)`, 0:01:45 overall | rebuilt the prelude, `*** Timeout` | killed, since it was rebuilding the prelude under the same bound | killed |
| 2, timeouts in the `ROOT` files, builds from each directory | `Finished LatticeBase (0:01:33 elapsed time)`, 0:01:47 overall, rebuilt for its changed options | rebuilt the prelude, `0:01:45`, then `Finished Eligibility (0:00:05 elapsed time)` | `Finished Ledger (0:00:06 elapsed time)` | 0 |
| 3, every build from `tools/proofs/` | current, 0:00:07 overall | current, 0:00:08 | current, 0:00:07 | 0 |

So the prelude's first build on machine S is about 1 min 31 s for `LatticeBase` alone, and a run that finds it current spends about 7 s per session, all of it Isabelle starting. The layer sessions' own builds stay seconds. The gate: base `nothing to gate`, eligibility 33 claims and ledger 16 claims each `passed`, with no digest mismatch, and `Assumption audit: clean` for all three.

- `mise run check:formal-freshness`: `3 formal-methods artefact(s) consistent with their literate READMEs`, exit 0.
- **The probe.** `driver.py --route native --workdir tools/proofs isabelle build -d ledger Ledger`, without `-d base`, exit 2 with `*** Bad parent session "LatticeBase" for "Ledger" (line 4 of ".../tools/proofs/ledger/ROOT")`. Nothing was changed for it, so nothing needed restoring, and run 3 is the passing state.

| Row | Result |
|---|---|
| FME0-01 | pass |
| FME0-02 | pass in run 2, after the first finding. Run 1 failed on it |
| FME0-03 | pass in run 3, after the second finding |
| FME0-04 | pass, 33 and 16 claims as before |
| FME0-05 | pass |
| FME0-06 | pass |
