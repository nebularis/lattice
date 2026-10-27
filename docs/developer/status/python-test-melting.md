<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Python Test Speed - Status

**Unit ID:** `python-test-melting`
**Status:** Done, 2026-10-09, branch `test/slow-py`. TM0, TM1, TM2, TM3a/b/c, TM6, TM7 and TM8 built and validated. TM4 and TM5 deferred, with reasoning recorded below. Reopened 2026-10-21 for TM9 to TM12, **all four built and verified 2026-10-27 on `py-test-xtra`**, not yet reviewed by the maintainer.
**Last updated:** 2026-10-27 (TM12 built, the follow-on complete)
**Plan:** [python-test-melting.md](../plans/python-test-melting.md)
**Sketch:** [python-test-melting.md](../sketches/python-test-melting.md)
**Validation Packs:** [TM9](../validation/python-test-melting-tm9.md), [TM10](../validation/python-test-melting-tm10.md), [TM11](../validation/python-test-melting-tm11.md), [TM12](../validation/python-test-melting-tm12.md)

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

**Reopened 2026-10-21** for TM9 to TM12 (plan, "Follow-on, 2026-10-21"), at the maintainer's request: every suite of `check` on the defaults of skill `lattice-testing`, in the order of expected memory use.

**TM9 done, 2026-10-27, on `py-test-xtra` (branched from `docs/placement-vehicles-structure`), machine S, Windows.** Full detail, including the suite-by-peak-memory table TM9 asks for, in its [Validation Pack](../validation/python-test-melting-tm9.md). In short:
- `tools/time_ontology_tests.py` generalised to profile any pytest-shaped task (not only `check:ontology-catalog`) and gained a Windows memory sampler, since this machine had neither. Committed (`7e8f7049`).
- Every pytest task `check` depends on was measured, serially and (where worth it) under `-n auto`.
- A TM11 candidate the brief did not name: `check:mork-compilers` runs generated SPARQL through plain `rdflib`, with no `@engines.each_engine` opt-in and no Oxigraph default. Needs the maintainer's confirmation before TM11 starts.
- `check:mork` could not be measured: `tools/mork` is not installed on this machine (a pip-mirror block several packages deep in its dependency chain, recorded in repo memory). Handed to the maintainer, not retried.
- TM12's own 10-second bar leaves only `check:mork-compilers` (23.9s serially) as a real parallelisation candidate among its six named suites. The other five stay serial. Since `check:mork-compilers` is also the new TM11 candidate, **TM11 and TM12 need to agree which of them changes it, and in what order, before either starts.**

**2026-10-27, the maintainer confirmed `check:mork-compilers` is in TM11's scope**, and asked for the agent's own leaning on ordering: TM11 goes first for that one suite (it decides what the default task contains before a worker count means anything), and builds both resulting tasks on the skill's defaults from the start. TM12's own list then needs no separate entry for it.

**TM10 done, 2026-10-27, same branch.** Full detail in its [Validation Pack](../validation/python-test-melting-tm10.md). In short:
- `tools/conftest.py` gains `pytest_xdist_auto_num_workers`, the same shape as `tools/persistence/tests/conftest.py`'s, with `PER_WORKER` at 900 MiB (measured with `-n 0`: 0.80 GB tree, 305 MB largest Python process, up to 3 JVMs holding 584 MB at once). One hook and one constant serve both `check:ontology-catalog` and `check:peril-vocabulary`, since the second's file is already part of the first's run.
- On this machine (over 30 GB free) the hook changes nothing observable, by design: its value is on a shorter machine.
- TM9's "flaky" guess for `check:ontology-catalog`'s 2 failures was wrong, corrected here and in TM9's own Validation Pack: a real, deterministic bug in `tools/import_guard.py` (`Path.read_text()` with no explicit encoding, decoding a UTF-8 ontology file as `cp1252` on Windows). Out of scope for this unit, flagged for the maintainer.
- Not run: TM10-03, showing the hook actually lowers the worker count under `MEM_CHECK_AVAILABLE_MIB` set low, since this machine has nothing short to observe directly.

**TM11 done, 2026-10-27, same branch.** Full detail in its [Validation Pack](../validation/python-test-melting-tm11.md). In short:
- `tools/mork_compilers` gained an engine abstraction (`mork_compilers/engines.py`) it never had, and eight test files route their query calls through it.
- **Departed from TM11's literal brief, recorded per `lattice-design`:** running the suite on Oxigraph found a real divergence on one of its 126 tests (TSD-41, a `GROUP_CONCAT` over a `UNION` of nested aggregate sub-selects that drops one record's contribution on Oxigraph only). `check:mork-compilers` therefore keeps rdflib as its default, exactly as it has always run, rather than flipping to Oxigraph as the skill's usual practice (STD-153) would ask. `check:mork-compilers-conformance` is the new task that runs Oxigraph, on demand and before a merge, so the divergence stays visible.
- Both tasks run `-n auto`, sized by TM10's shared `mem_check` hook (no new wiring needed, since pytest discovers `tools/conftest.py` for any test under `tools/`).
- New registers from this finding: TSD-41, STD-274 (prove conformance before trusting a new default), STD-275 (read text with an explicit encoding, generalising TM10's import_guard.py finding), TD-91 (the import_guard.py bug itself) and TD-92 (the mork_compilers divergence). TD-87 corrected (nine files to eight). Committed separately (`44c82c6d`) before TM11's own implementation commit.

**TM12 done, 2026-10-27, same branch, the follow-on complete.** Full detail in its [Validation Pack](../validation/python-test-melting-tm12.md). In short:
- `check:mork-compilers` was already handled by TM11, so TM12's own list was the remaining five: `check:workers`, `check:vocabulary`, `check:reference-eligibility`, `check:minting-python`, `check:persistence-library`.
- Every one re-measured under the plan's 10-second bar (1.6s to 7.0s), so every one stays serial, per the rule, with its time recorded. No code changed.
- `check:workers`' own TM9 figure (9.5s auto against 5.1s serial) independently confirms the bar's own reasoning: parallelising a suite this small costs time rather than saving it.
- Carried forward, unresolved: TSD-41 / TD-92 (the mork_compilers divergence, mechanism untraced), TD-91 (the import_guard.py encoding bug, a one-line fix not made here), and `check:mork` (still not measurable, `tools/mork` not installed on this machine).

For TM0 to TM8: none, it is done. Review and merge `test/slow-py` to `main` (the maintainer's). The two superseded sketches (`python-test-melting.md`, `test-suite-performance.md`) stay until the maintainer decides whether to delete them, per TM8's own text.

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
- 2026-10-17. Follow-up measured on a four-core x86 machine and a laptop with four performance and four
  efficiency cores. Suite time on the first: 427s to about 100s with all 784 tests passing. pySHACL runs
  one query per focus node and rdflib parsed the text again each time, about 90% of a validation, so
  `ValidationCache` now translates each distinct query text once (`tools/conftest.py`, keyed on the text,
  the base and the prefixes the text uses without declaring). The reasoner JVM starts with a class-data
  archive that the JVM builds beside the jar (`mork_compilers/reasoning.py`, 51.8s to 29.9s over 41
  closures). Two `prl:ReferenceCodeShape` queries read the same rows without scanning every concept
  per focus node (peril shapes 0.3.1). `check:ontology-catalog` moved from `--dist loadfile` to
  `--dist worksteal`, 9 to 11 percent faster on both machines. `dev:time-ontology-tests` reports worker
  finish times and memory. `tools/test_peril_vocabulary.py` alone now takes about 27s on four cores, so
  TD-45 can be reviewed.
- 2026-10-17 (later). The reasoner now runs in one long-running JVM per Python process (`reasoning-testkit serve`, ADR-A83
  addendum). 41 closures took 37.7s with a JVM per call and 6.3s through the server, and the suite on four
  workers went from about 82s to about 55s. `dev:record-validations` and `dev:replay-validations` record every
  validation the suite makes and replay them against changed shapes (`tools/validation_replay.py`).
- 2026-10-17 (later still). `tools/test_peril_vocabulary.py` is back in `check:ontology-catalog` (39 tests). Under `--dist worksteal` it adds
  about 22s on four cores (about 80s with it and about 58s without) and no longer queues on one worker. The register's second TD-45 row,
  which recorded its exclusion, is removed. The cost it named, per-concept shape evaluation, was cut by peril shapes 0.3.1.
