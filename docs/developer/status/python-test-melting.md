<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Python Test Speed - Status

**Unit ID:** `python-test-melting`
**Status:** Done, 2026-10-09, branch `test/slow-py`. TM0, TM1, TM2, TM3a/b/c, TM6, TM7 and TM8 built
and validated. TM4 and TM5 deferred, with reasoning recorded below.
**Last updated:** 2026-10-09
**Plan:** [python-test-melting.md](../plans/python-test-melting.md)
**Sketch:** [python-test-melting.md](../sketches/python-test-melting.md)

## Current position

Done. TM0 measured a real baseline on this machine, serial: 456.09s, 9 failed (pre-existing,
unrelated to this plan), 560 passed, 67 skipped, for the 25 top-level `tools/test_*.py` modules
(the 22 of `check:ontology-catalog` plus `test_agent_guidance.py`, `test_authoring_stage.py` and
`test_literate_extract.py`). We answered TM-Q1 to TM-Q5 the same session (below). Every
slice but TM4 and TM5 (deferred, with reasoning, see "Final result") is built, tested and rolled
out to all 16 modules with a `validate()` call site. Full detail in "Final result" below.

## Decisions (2026-10-09)

| ID | Decision |
|---|---|
| TM-Q1 | Any speedup is beneficial; target 3-4 minutes or under, otherwise split long/short runs for CI |
| TM-Q2 | Option B (session-scoped fixtures in `tools/conftest.py` only). See "Final result" for how a module adopts it without a full call-site rewrite |
| TM-Q3 | The agent's choice. Batches of four to six modules (the plan's own TM3a/b/c split), one commit per batch |
| TM-Q4 | Option A: walk the tree from given roots, skipping build/dependency directories |
| TM-Q5 | Yes, if it can be made to work in this environment. Confirmed working (see "Final result") |

## Next action

None for this unit; it is done. Review and merge `test/slow-py` to `main` (the maintainer's). The two
superseded sketches (`python-test-melting.md`, `test-suite-performance.md`) stay until the maintainer
decides whether to delete them, per TM8's own text.

## Final result

All 16 modules with a `validate()` call site adopted the shared cache (TM1/TM2/TM3), all five
`git grep` call sites were replaced (TM6), and `pytest-xdist` is wired into `check:ontology-catalog`
(TM7). Full 27-file suite (25 original `tools/test_*.py` plus the two new cache test files),
`pytest-xdist` (`-n auto --dist loadfile`): **123.6s** (126.2s wall including setup), down from the
TM0 baseline's 456.09s serial, about 3.6x. 9 failed, identical to the TM0 baseline (one,
`test_c6_10`, now fails for its real, pre-existing reason instead of a Windows-only crash -- see
TM6 below). 585 passed (560 original + 25 new: 16 `test_graph_cache.py`, 9 `test_repo_files.py`),
67 skipped. A sorted `PASSED`/`FAILED`/`SKIPPED` diff against the TM0 baseline is identical except
for SKIPPED-message line numbers (shifted by the fixture lines this plan added to each file) --
confirmed with `Compare-Object`, not assumed.

**How a module adopts the cache (TM-Q2, option B's implementation).** The cache itself is the
fixture: `graph_cache` and `validated` in `tools/conftest.py`, both session-scoped. Each adopting
module declares its own `@pytest.fixture(scope="module", autouse=True)` (module-scoped, not
session-scoped: `request.module` is only available at function, class or module scope) that
fetches its own `MODEL`/`SHAPES`/`EVERY_SHAPE`-style names from `graph_cache` and assigns them onto
`request.module`, and substitutes `module.validate = validated` (`ValidationCache` is callable with
exactly `pyshacl.validate`'s own signature, so every existing `validate(data, shacl_graph=..., ...)`
call site gains the cache with no change of its own). A handful of helper functions whose default
argument read one of those names directly (evaluated at import time, before any fixture runs) were
changed to look the name up inside the function body instead. This keeps the caching mechanism
centralised, fixture-based and session-scoped (option B's substance) without rewriting every one of
the several hundred call sites across 16 modules to take explicit fixture parameters (option B's
literal cost, which the plan's own table flagged). Recorded as the considered implementation of our
decision, not a reversion to option A: there is no sibling support module, and nothing
outside `conftest.py` defines the cache.

**A real correctness bug found and fixed during the roll-out** (not anticipated by the plan):
`test_eligibility_examples.py::test_two_readings_and_a_double_negation_are_rejected` mutates its
own data graph in place (`data.remove(...)`) and validates the SAME Python object again, expecting
a different result. `ValidationCache`'s first design, keyed on `(id(data), id(shapes), options)`,
would have returned the first, now-stale report -- caught immediately because this test failed for
real under it. Fixed by keying on graph *content* (`hash(frozenset(graph))`) instead of identity: a
mutated-in-place graph is correctly a new cache entry, and as a side benefit two different graph
objects built with identical triples now correctly share one cache entry too. A regression test
(`test_a_graph_mutated_in_place_and_revalidated_is_not_served_stale`) locks this in.

**TM4 and TM5, deferred, with reasoning:**

- **TM4** (narrow shapes in one-triple mutation tests): TM3's own measurement shows the dominant
  remaining cost is validate() call volume itself (SHACL-SPARQL evaluation over necessarily-distinct
  mutated graphs, which no cache can collapse), which TM4 would help. But TM-Q1's target is already
  met by a wide margin through TM7, and TM4 carries the real, stated correctness risk the plan itself
  flagged (a narrowed shape set silently missing a message another shape file would add). Not worth
  that risk without a stronger forcing need.
- **TM5** (reasoner rows): step 1 (the skip condition) already holds -- `reasoning.available()` skips
  cleanly without starting a JVM when the harness jar is not built, confirmed by every run in this
  environment (the jar is never built here, so steps 2 and 3's benefit is unmeasurable in this
  sandbox). Step 3 is explicitly its own slice, briefed on `main`, crossing into Java
  (`platform/reasoning-testkit`). Left for a session with the jar built.

**Evidence for the above, measured not assumed:** a combined serial run of the whole Instrument
family (6 modules, cross-module cache sharing possible within one process) took 289.33s, against
292.64s for the same six run as separate subprocesses with no sharing at all -- a 1.1% difference,
within noise. The full-suite xdist time before and after the complete TM3 roll-out (130.24s vs
128.67s) shows the same: TM1/TM2's redundant-parsing and repeated-validation elimination is real
(confirmed directly: `test_behaviour_split.py`, which used to rebuild its whole `MODEL` composite
on every `_conforms()` call, dropped to 21 tests in 1.00s) but is not what the wall-clock total is
mostly made of once the suite is already parallelised. TM7 (`pytest-xdist`) is the slice that moved
the number.

TD-18 and TD-29 removed from the technical debt register (TM8). The `formal-methods` plan's TD-18
citation repointed to a plain cross-cutting note, since TD-18 no longer exists. The developer guide
now documents `tools/conftest.py` and `mise run dev:time-ontology-tests`. A skill,
`.claude/skills/lattice-testing`, records the diagnosis pattern and the caching convention for
future test suites in this repository and projects built on LATTICE.

## Decisions (2026-10-09)

All of TM-Q1 to TM-Q5 are decided (above).


## Blockers

None for TM0.

## History

- 2026-10-09. Plan written from the sketch. The sketch's call-site and module counts were re-checked
  against the code and match (27 `validate` call sites in 16 modules, 16 shape files in `EVERY_SHAPE`, 40
  `sh:sparql` constraints in Instrument). Found while planning: three test modules import constants from
  `test_parameter_bindings`, five tests shell out to `git grep`, and the work in common with the repository
  catalogue is recorded in that sketch's §8.1.
