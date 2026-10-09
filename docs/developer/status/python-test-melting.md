<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Python Test Speed - Status

**Unit ID:** `python-test-melting`
**Status:** Planned. Not started.
**Last updated:** 2026-10-09
**Plan:** [python-test-melting.md](../plans/python-test-melting.md)
**Sketch:** [python-test-melting.md](../sketches/python-test-melting.md)

## Current position

Planned at the human's request on 2026-10-09, together with the
[repository-catalogue](../sketches/repository-catalogue.md) sketch. No slice has started. Nothing has been
profiled, so the ranking of causes is the sketch's hypothesis.

## Next action

TM0, measure and baseline. It needs no decision. TM-Q2 must be answered before TM1.

## Open questions

| ID | Question | Blocks |
|---|---|---|
| TM-Q1 | the speed target | set after TM0 |
| TM-Q2 | where the shared graphs and the validation cache live | TM1 |
| TM-Q3 | batch size for the roll-out | TM3a |
| TM-Q4 | what the Python repository scans list | TM6 |
| TM-Q5 | whether `pytest-xdist` may be added | TM7 |

## Blockers

None for TM0.

## History

- 2026-10-09. Plan written from the sketch. The sketch's call-site and module counts were re-checked
  against the code and match (27 `validate` call sites in 16 modules, 16 shape files in `EVERY_SHAPE`, 40
  `sh:sparql` constraints in Instrument). Found while planning: three test modules import constants from
  `test_parameter_bindings`, five tests shell out to `git grep`, and the work in common with the repository
  catalogue is recorded in that sketch's §8.1.
