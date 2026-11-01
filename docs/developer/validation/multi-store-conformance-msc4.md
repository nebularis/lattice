<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: MSC-4, cost probes to a benchmark

**Unit:** [`multi-store-conformance`](../status/multi-store-conformance.md)
**Machine:** a macOS arm64 laptop with 8 logical cores (run R-S of the [discovery record](../../architecture/triple-store-discovery.md)). **Branch:** a worktree detached from `multi-store-conformance`, uncommitted
**Plan:** [plan](../plans/multi-store-conformance.md), slice MSC-4 and MSC-Q4
**Findings:** TSD-42 (restated, rdflib column added), TSD-Q22 (next step names the benchmark). **Capability:** CAP-97, not ratified
**Decisions:** none that needs the maintainer. The routine ones are listed at the end

## Invariant

`check` carries no timing assertion. The cost of a graph variable bound outside an `OPTIONAL` is reported as a ratio per form, engine and engine version by `benchmark/persistence-store-probes`, which fails only on a wrong count.

## Scope

In scope. The benchmark, its task `check:persistence-store-probes`, removal of P3 from `check:persistence`, a search of every `check` suite for another timing assertion, the run on rdflib and on Oxigraph 0.5.11, 0.5.12 and 0.5.13, and the discovery record, the capability register and this pack. Out of scope. TSD-40's path forms (they need the ledger store of `benchmark/ledger-posting-cost`, 10,063 postings, and a synthetic tree would be a new measure and not a reproduction), the Jena column (the package `tools/testing/jena` is built in MSC-1), and the CCS status record's mention of P3.

## Tests

| ID | What | Where | Result |
|---|---|---|---|
| MSC4-01 | each of the four forms counts the graph on rdflib, at the smallest size | `test_bs1` | pass |
| MSC4-02 | each of the four forms counts the graph on Oxigraph, at the smallest size | `test_bs1` | pass |
| MSC4-03 | a form that counts another graph fails the check with `WrongResult` | `test_bs2` | pass |
| MSC4-04 | an engine that counts one too many fails the check | `test_bs3` | pass |
| MSC4-05 | a clock that reads a million seconds per tick does not fail the check | `test_bs4` | pass |
| MSC4-06 | the report names its run and is written where asked | `test_bs5` | pass |
| MSC4-07 | an absent Jena is a noted skip, not a failure | `test_bs6` | pass |
| MSC4-08 | `check:persistence` without P3 | 3,975 tests | pass |
| MSC4-09 | `check:persistence-conformance` on rdflib and Oxigraph | 4,370 tests | pass |
| MSC4-10 | the benchmark on rdflib 7.6.0 with Oxigraph 0.5.11, 0.5.12 and 0.5.13 | R-S | below |

## Commands and results

Run from the worktree, each through mise.

| Command | Result |
|---|---|
| `mise run check:persistence` | `3975 passed, 22 warnings in 81.41s` |
| `mise run check:persistence-conformance` | `4370 passed, 2994 warnings in 153.79s` |
| `mise run check:persistence-store-probes` | `7 passed`, then the report, exit 0 |
| `mise run check:catalogue` | `repository catalogue: 20 module(s) and 9 tool package(s) agree with the tree` |
| `mise run check:python-root` | `OK`, 87 tests, and the Phase 8 conformance line |
| `mise run check:deny-terms` | `0 finding(s) against 5 entries` |
| `mise run check:agent-guidance` | `9 passed` |
| `mise run check:identifiers` | **fails, 5 findings, none from this slice** (below) |

`check:identifiers` failed at first on the plan's line naming the unit's reserved ranges by their end points, which are not defined. We reworded that line to give the ranges as numbers. CAP-97 and TSD-42's edits add no undefined identifier

## The ratios

`mise run check:persistence-store-probes` for 0.5.13 and rdflib. For 0.5.11 and 0.5.12, the same `check.py` run under `python -I` with `pip install --target <scratch> pyoxigraph==<version>` first on `sys.path`. 100 graphs of 3,000 triples against 1, best of five, Python 3.14.7. The ratio is the time over 100 graphs divided by the time over one. Milliseconds in brackets are the one-graph and the 100-graph time.

| Form | rdflib 7.6.0 | Oxigraph 0.5.11 | Oxigraph 0.5.12 | Oxigraph 0.5.13 |
|---|---|---|---|---|
| bind-optional | 1.4 to 1.7 (48 to 70 ms) | 1.0 (0.6 ms) | 1.0 (0.6 ms) | **79** (0.7 to 52 ms) |
| values-optional | 1.4 to 1.5 (50 to 76 ms) | 1.0 (0.6 ms) | 1.0 (0.6 ms) | **82** (0.7 to 54 ms) |
| join | 1.8 (23 to 42 ms) | 1.0 (0.6 ms) | 1.0 (0.6 ms) | 1.0 (0.6 ms) |
| constant | 2.4 to 2.5 (12 to 31 ms) | 1.0 (0.3 ms) | 1.0 (0.3 ms) | 1.0 (0.3 ms) |

This agrees with TSD-42 (73 to 78 before, 79 and 82 now, same order). rdflib reads one graph under every form. Its ratios above 1 appear in the constant form, which cannot scan, so they come from a larger dataset and not from reading every graph. The rdflib column is new evidence for TSD-42.

## Adversarial probe

The `bind-optional` form was edited in memory to name a different graph (`OPTIONAL { GRAPH <urn:g:1> ... }`) and `check.main()` run with `STORE_PROBES_QUICK=1`.

```
WRONG RESULT: rdflib: the query returned 1, and the graph holds 500: SELECT (COUNT(*) AS ?n) WHERE { BIND(<urn:g:0> AS ?g) OPTIONAL { GRAPH <urn:g:1> { ?s ?p ?o } } }
exit 1
```

MSC4-03 and MSC4-04 hold the same two breaks as tests, and MSC4-05 shows time does not fail it.

## Other timing assertions

A search of `tools/`, `packages/`, `platform/`, `workers/`, `apps/` and `test/` for `perf_counter`, `time.time`, `monotonic`, `process_time`, `timeit`, `nanoTime`, `currentTimeMillis`, `Instant.now` and `Duration.between` in Python and Java files, and for pytest and JUnit timeout markers. Found in tests.

- `tools/test_ledger.py:144`, `time.monotonic()` around a SHACL validation of 10,000 accounts. It records the seconds with `record_property` and asserts only `conforms`. Not a timing assertion, left.
- `tools/knowledge/test_extract.py:485`, `time.time() + 3600` as a file stamp for a staleness test. Not a measurement, left.
- `tools/persistence/tests/test_architecture.py:51` and `tools/vocabulary/tests/test_architecture.py:31`, docstrings about forbidding `time.time()` in code. Not an assertion on time.
- `subprocess.run(..., timeout=...)` in `tools/test_reasoning_server.py` is a hang guard and not an assertion on how long the work takes. Left.

No other ratio or duration assertion exists. P3 was the only one.

## Changes

- `benchmark/persistence-store-probes/` (`check.py`, `test_check.py`, `README.md`) and the task in `mise.toml`.
- `tools/persistence/tests/test_store_probes.py`. P3, `_p3_ratio`, `_oxigraph_version` and the unused `import time` are removed, with a pointer comment where P3 was.
- `docs/architecture/triple-store-discovery.md`. R-S, TSD-42 (evidence, rdflib and version table, what it means, reproduce), the index row of TSD-42, TSD-Q22's next step.
- `docs/developer/capabilities.md`. CAP-97.
- Not changed, history. `FMH-H2-4b.md` and `FMH-TS-2.md` (P3 as it was then) and the CCS status record's 2026-10-27 line. The CCS status record's "Next action" still asks the maintainer to countersign P3's strict expected failure, which is moot now. That is the CCS unit's file.

## Decisions taken

- The benchmark reads rdflib and pyoxigraph directly and bulk-loads Oxigraph, as `benchmark/sparql-constraint-query-cost` does. It does not use `engines.py`, so it needs no pytest fixture and loads 300,000 quads in about a second.
- The Jena engine is written against the interface the plan gives (`lattice_testing_jena.available()` and a store with `update` and `select`) and is **not exercised**, since the package does not exist at this base. Whoever lands MSC-1 runs the benchmark once and corrects the two calls if the names differ. Until then Jena is a printed skip.
- TSD-40's path forms are left out, for the reason under Scope.
- The scratch pyoxigraph versions were installed outside the repository and nothing of them is kept.

## Index misses

`mise run graph:ask -- misses` reports none recorded. Weak answers I met.

- `find` with `--kind discovery --tech sparql` for the left-join cost ranked TSD-42 first, but a question on where cost probes belong (check or benchmark) returned CAP-55, CAP-57 and STD-044, none of which says that a timing assertion must not sit in `check`. ADR-A124 says it, and no standard states it. A standard for it (STD-290 onward is reserved) would make the index answer it.
- The skill `lattice-triple-stores` (line 52) still says to turn a probe into a test under `test_store_probes.py`. A cost probe goes to a benchmark now, which the skill does not say. The skill is the lead's to edit.
