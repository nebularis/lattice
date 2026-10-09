<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Python Test Speed - Status

**Unit ID:** `python-test-melting`
**Status:** In progress, branch `test/slow-py`. TM0, TM1, TM2, TM6 and TM7 done, 2026-10-09.
**Last updated:** 2026-10-09
**Plan:** [python-test-melting.md](../plans/python-test-melting.md)
**Sketch:** [python-test-melting.md](../sketches/python-test-melting.md)

## Current position

TM0 measured a real baseline on this machine, serial: 456.09s, 9 failed (pre-existing, unrelated
to this plan), 560 passed, 67 skipped, for the 25 top-level `tools/test_*.py` modules (the 22 of
`check:ontology-catalog` plus `test_agent_guidance.py`, `test_authoring_stage.py` and
`test_literate_extract.py`). The human answered TM-Q1 to TM-Q5 the same session (below). TM7
(`pytest-xdist`, `-n auto --dist loadfile`) alone cuts that to about 127s-139s, comfortably under
the human's 3-4 minute ceiling, with byte-identical per-test outcomes confirmed by a sorted
`PASSED`/`FAILED`/`SKIPPED` diff. TM1 (`tools/conftest.py`'s `graph_cache`, session-scoped) and TM2
(`validated`, a pySHACL report cache keyed on graph/shape identity plus options) are built and
tested (`test_graph_cache.py`, 11 tests, including the TM1 mutation-guard probe run for real and
confirmed to fail the session). TM6 (`repo_files`, replacing the five `git grep` subprocess calls)
is built and tested (`test_repo_files.py`, 9 tests, including a planted-retired-term probe), and is
rolled out to all five original call sites (`test_constitutive_terms.py`, `test_instrument.py`,
`test_keys.py`, `test_terms_in_time.py`, `test_wording.py`). One of those five,
`test_c6_10_no_retired_term_outside_history`, used to crash with a Windows-only
`UnicodeDecodeError` (`git grep`'s subprocess output decoded with the console codepage, not UTF-8);
it now fails with the real, pre-existing `AssertionError` instead (retired terms genuinely present
in `ontology/examples/insure-o/`, out of this plan's scope), the same outcome category (FAILED) as
the baseline, now diagnosable and reproducible on every platform instead of crashing on one.

TM1/TM2's own roll-out across the Instrument family (TM3a) and the rest (TM3b, TM3c) is next.
TM-Q2 (option B, session fixtures in `conftest.py` only) is implemented with a deliberate,
recorded reading: the cache itself is the fixture (`graph_cache`, `validated`, both
session-scoped), and each adopting test module declares its own small
`@pytest.fixture(scope="session", autouse=True)` that fetches its `MODEL`/`SHAPES`/`EVERY_SHAPE`
from the cache and assigns them onto `request.module`, so every existing test function and helper
keeps its current bare-name call sites unchanged. This keeps the caching mechanism centralised,
fixture-based and session-scoped (option B's substance) without rewriting every one of the
several hundred call sites across 25 modules to take explicit fixture parameters (option B's
literal cost, which the plan's own table flagged). Recorded here as the considered implementation
of the human's decision, not a reversion to option A: there is no sibling support module, and nothing
outside `conftest.py` defines the cache.

## Decisions (the human, 2026-10-09)

| ID | Decision |
|---|---|
| TM-Q1 | Any speedup is beneficial; target 3-4 minutes or under, otherwise split long/short runs for CI |
| TM-Q2 | Option B (session-scoped fixtures in `tools/conftest.py` only). See "Current position" for how a module adopts it without a full call-site rewrite |
| TM-Q3 | The agent's choice. Batches of four to five modules (the plan's own TM3a/b/c split), one commit per batch |
| TM-Q4 | Option A: walk the tree from given roots, skipping build/dependency directories |
| TM-Q5 | Yes, if it can be made to work in this environment. Confirmed working (see above) |

## Next action

Continue TM3: roll out `graph_cache`/`validated` to the Instrument family
(`test_parameter_bindings.py`, `test_amendments.py`, `test_regimes.py`, plus
`test_constitutive_terms.py` and `test_instrument.py`, already migrated for TM6), then Behaviour,
Wording and Keys, then the rest. Re-measure after each batch. TM4 and TM5 are evaluated against the
profile once TM3 is done, and may be dropped per the plan if the gain looks small next to their
cost. TM8 closes out with a status update, the developer guide, and TD-18/TD-29 removed from the
technical debt register.

## Open questions

All of TM-Q1 to TM-Q5 are decided (above).


## Blockers

None for TM0.

## History

- 2026-10-09. Plan written from the sketch. The sketch's call-site and module counts were re-checked
  against the code and match (27 `validate` call sites in 16 modules, 16 shape files in `EVERY_SHAPE`, 40
  `sh:sparql` constraints in Instrument). Found while planning: three test modules import constants from
  `test_parameter_bindings`, five tests shell out to `git grep`, and the work in common with the repository
  catalogue is recorded in that sketch's §8.1.
