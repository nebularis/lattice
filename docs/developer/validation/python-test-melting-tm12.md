<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: python-test-melting TM12, the serial suites

**Unit:** `python-test-melting` ([plan](../plans/python-test-melting.md), TM12's row)
**Machine:** S, Windows. **Branch:** `py-test-xtra`, from `docs/placement-vehicles-structure`. Commits are the maintainer's.
**Plan and test cases:** [python-test-melting plan](../plans/python-test-melting.md), TM12's row
**Decisions:** none new
**Depends on:** [TM9](python-test-melting-tm9.md), [TM10](python-test-melting-tm10.md), [TM11](python-test-melting-tm11.md)

## Invariant

Each of TM12's six named serial suites over 10 seconds gets `-n auto` with `mem_check`. Each one under 10 seconds stays serial, with its time recorded. No behaviour change to any suite.

## What TM12 found

`check:mork-compilers` is no longer TM12's to decide: TM11 already put it on `-n auto` with `mem_check`, for its own reason (building the engine abstraction its conformance task needed). Of the remaining five, every one measures under the 10-second bar on this machine, so TM12's rule keeps every one of them serial. This is not a gap: the plan's own rule names 10 seconds as the line, and a suite under it stays as it is, with its time recorded here.

| Task | Serial wall (TM9, 2026-10-27) | Serial wall (TM12, re-measured 2026-10-27) | Over 10s? | Action |
|---|---|---|---|---|
| `check:workers` | 5.1s | 7.0s | no | stays serial |
| `check:vocabulary` | 2.1s | 2.2s | no | stays serial |
| `check:reference-eligibility` | 5.4s | 5.3s | no | stays serial |
| `check:minting-python` | 4.4s | 4.3s | no | stays serial |
| `check:persistence-library` | 1.6s | 1.6s | no | stays serial |

The two measurements agree within normal run-to-run noise, confirming these are stably fast rather than a one-off fast run. `check:workers`' own TM9 row already showed `-n auto` making it slower (9.5s against 5.1s serial, xdist start-up cost dominating a 121-test suite), which is independent confirmation in the other direction: parallelising a suite this size would cost time, not save it, consistent with TM12's own bar existing for exactly this reason.

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| TM12-01 | the five named suites, serial / re-measured / each under 10s, matching TM9's figures within noise | L1 | + |
| TM12-02 | `check:mork-compilers` / TM11's Validation Pack / already on the defaults, nothing left for TM12 | L1 | + |

## One command

```bash
mise exec -- python tools/time_ontology_tests.py --task check:workers
mise exec -- python tools/time_ontology_tests.py --task check:vocabulary
mise exec -- python tools/time_ontology_tests.py --task check:reference-eligibility
mise exec -- python tools/time_ontology_tests.py --task check:minting-python
mise exec -- python tools/time_ontology_tests.py --task check:persistence-library
```

## Artefacts to inspect

None changed. This Validation Pack is the record of the measurement and the decision it implies (stay serial).

## Deliberate non-coverage

Forcing any of the five onto `-n auto` to show the plan's rule is followed in both directions (a suite given workers anyway still passes): not run, since the rule's own basis, that start-up cost dominates a sub-10-second suite, is already shown directly by `check:workers`' own TM9 measurement.

## Handoff

Built on `py-test-xtra`, autonomously, per the maintainer's instruction this session. **python-test-melting's TM9 to TM12 follow-on is complete.** Five commits on this branch, all local, none pushed: `7e8f7049` (tool fix), `8503eed8` (TM9), `295ebd1a` (TM10), `44c82c6d` (TM11 registers), `52ea5756` (TM11 implementation), and this Validation Pack closes TM12 with no further commit needed, since no file changed.

**Open for the maintainer, carried over from earlier packs:**
- TSD-41 / TD-92: `check:mork-compilers`'s Oxigraph divergence, mechanism untraced (TSD-Q20).
- TD-91: `tools/import_guard.py`'s missing encoding, a one-line fix, not made here (out of scope for this unit).
- `check:mork` could not be measured anywhere in TM9 to TM12: `tools/mork` is not installed on this machine, a pip-mirror block handed to the maintainer in TM9's pack, not retried since.
