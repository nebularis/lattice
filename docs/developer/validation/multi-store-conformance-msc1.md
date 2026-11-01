<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: MSC-1, Jena joins the conformance run

**Unit:** [`multi-store-conformance`](../status/multi-store-conformance.md)
**Plan:** [multi-store-conformance](../plans/multi-store-conformance.md), MSC-Q1 (a), Q2, Q3, Q5
**Machine:** a macOS arm64 laptop, Java 25, Jena 5.1.0, rdflib 7.6.0, pyoxigraph 0.5.13. **Placement:** T0, public. Test support and engine probes, nothing domain-specific.
**Status:** authored and run, not accepted. The lead's review and the maintainer's merge are the sign-off.

## Scope

- `platform/sparql-testkit`, a test-only Maven module (Jena ARQ at `${jena.version}`, in-memory transactional dataset, no TDB) with a `serve` command, one JSON request and one JSON answer per line.
- `tools/testing/jena`, package `lattice_testing_jena`, with the methods of `tools/testing/oxigraph`'s store, one JVM per Python process.
- `tools/testing/sparql_probes`, package `sparql_probes`, holding the aggregate-over-an-error matrix moved from `tools/mork_compilers`, with a registry of rdflib, Oxigraph and Jena and Jena now executed.
- `check:conformance`, `check:sparql-probes-conformance`, `bootstrap:` and `check:` tasks for the kit and the Jena package, the packages in `bootstrap:python`, catalogue entries, the register entries CAP-90 to CAP-94.
- Out of scope. Jena in the persistence and MORK registries (MSC-2, MSC-3), any change to a `check` default.

## Tests

| ID | Where | What |
|---|---|---|
| MSC1-01 to MSC1-07 | `SparqlTestkitTest` (JUnit, 7 tests) | load then select with datatype and language tag, ask and construct and errors that do not end the server, a failing load, a failing multi-operation update, reset, serve's line framing and blank lines, separate datasets and a blank node label that stays one node |
| MSC1-08 to MSC1-21 | `tools/testing/jena/tests/test_store.py` JE-T1 to JE-T14 | parameter substitution, update with parameters and quads back, a parameter left out, select with unbound variables and `remove_graph`, default graph is not the union, literal datatypes and language tags and escapes, blank nodes, ask and construct and load (N-Quads, TriG), reset and separate stores, a query error as `JenaError`, an update that fails part way, a bad load, jar override and `available()`, a killed JVM |
| MSC1-22 | `tools/testing/sparql_probes/tests/test_aggregate_errors.py` AE-01 to AE-22 | the matrix, now on all three engines |
| MSC1-23 | AE-23 | with `SPARQL_PROBES_REQUIRED=1` every engine is available, so a missing engine cannot pass as a skip |

## Commands and results

Run from the worktree on 2026-10-27, after the last edit.

| Command | Result |
|---|---|
| `mise run check:sparql-testkit` | passed (quiet), 7 tests, jar built |
| `mise run check:testing-jena` | `14 passed in 0.71s` |
| `mise run check:sparql-probes-conformance` | `37 passed, 1087 subtests passed` (23 probes, 14 Jena package tests) |
| `mise run check:mork-compilers` | `156 passed, 25 subtests passed in 11.97s` (149 before, plus the 7 reasoner tests, which ran because the jar is built) |
| `mise run check:mork-compilers-conformance` | `156 passed, 25 subtests passed in 14.58s` |
| `mise run check:agent-guidance` | `0 problem(s)`, 9 passed |
| `mise run check:catalogue` | `20 module(s) and 11 tool package(s) agree with the tree. Bypass scan: 13 known file(s)` |
| `mise run check:python-root` | `Ran 87 tests ... OK`, Phase 8 conformance passed |
| `mise run check:deny-terms` | `0 finding(s) against 5 entries` |
| `mise run check:identifiers` | failed at first on the plan's line naming the reserved ranges by their end points. The plan now gives them as number ranges, and the check passes on the unit branch |
| `mise run check:full-sweep` | 16 of 17 pass (`check:persistence` 3975 passed 1 xfailed, `check:ontology-catalog` 1209 passed). The one failure is `ontology versions`, UNBUMPED, expected and unrelated |

## How Jena executed compares with the recorded column

All 352 cells of the matrix, remedies and groups came out as recorded. There is no difference, so no expectation changed and none needs a reason. The suite now executes the column that TSD-43 recorded from a one-off runner, and the recorded values stay as the expected result per engine. Adversarial probe, below, shows the test notices a change.

## Adversarial probes

1. Flipped the recorded Jena cell `COUNT(expr) | one unbound` from `2` to `3`. AE-01 failed with the subtest `engine='jena', case='COUNT(expr) | one unbound'` and AE-16 failed (`'3' != '2'`). The file was restored.
2. Pointed `LATTICE_SPARQL_TESTKIT` at a missing jar. Without `SPARQL_PROBES_REQUIRED` the Jena cases skip (23 passed, 13 skipped). With it AE-23 fails with `('rdflib', 'oxigraph') != ('rdflib', 'oxigraph', 'jena')`.
3. Killed the JVM between two calls (JE-T14). The next call raised `JenaError` (its datasets were gone) and the one after started another JVM. My first version silently restarted and answered from an empty dataset, which JE-T14 caught, so the wrapper now raises.
4. A multi-operation update whose second operation fails while running (a `SERVICE` to a closed port) leaves the first operation's insert undone (JE-T11 and the JUnit test).

## What Jena does, recorded for the findings (TSD number left to the lead)

- A failing request leaves the dataset as it was. Each load and each update request runs in `Txn.executeWrite` on `DatasetFactory.createTxnMem()`, and an exception aborts the write transaction. Hypothesis for other Jena datasets (TDB2 is not tested here).
- Blank node labels in a load are fresh per parse by default. The kit uses `LabelToNode.createUseLabelEncoded()`, so one label is one node across loads, which matches `add` of a `BNode` on Oxigraph.
- rdflib's `n3()` writes a multi-line literal in triple quotes, which N-Quads rejects. The wrapper writes N-Quads literals itself.
- Jena's default graph is not the union of the named graphs, as on Oxigraph.

## Cost, measured once (a hypothesis across machines, STD-176)

Median of repeated calls on the machine above, JVM options as the reasoning kit's (class-data archive, serial collector, C1 only).

| Measure | Result |
|---|---|
| JVM start to first answer, first start (archive written at exit) | 0.32 s |
| JVM start to first answer, with the archive | 0.08 s (five runs, all 0.08 s) |
| JVM start to first answer, JVM defaults | 0.19 s |
| `JenaStore()` plus first update and first select, from Python | 0.50 s |
| ask round trip | 0.31 ms |
| `INSERT DATA` of one triple | 0.13 ms |
| `add` of one quad | 0.06 ms |
| select of 10000 rows | 186 ms |
| for comparison, in process: Oxigraph ask / rdflib ask | 0.015 ms / 0.57 ms |

C1-only compilation suits short tests. A cost probe that measures Jena's engine on large data (MSC-4) should set `LATTICE_SPARQL_TESTKIT_JVM_OPTIONS` without `TieredStopAtLevel=1`.

## Decisions taken

- **Datasets per store.** The protocol takes an optional `dataset` name and an op `drop`, so several `JenaStore` objects in one process do not share data, as `OxigraphStore` objects do not. A `weakref.finalize` drops the dataset.
- **Rdflib terms in and out** for `JenaStore`, where `OxigraphStore` speaks pyoxigraph terms, because the engine is across a text protocol and callers compare against rdflib terms. `quads()` returns a `Quad(subject, predicate, object, graph)` named tuple with `graph` None for the default graph.
- **Parameter substitution is textual,** as for Oxigraph, so both engines see the same query text. Jena's initial bindings are not used.
- **Finding the jar** from `LATTICE_SPARQL_TESTKIT`, then `LATTICE_ROOT`, then the nearest directory at or above the working directory holding `repository-catalogue.md`. The package is installed and cannot import `tools/`, so it repeats the reader's rule and is listed in `tools/lattice_repo_catalogue_exceptions.txt` (TD-54 now says 13 files, and `test_rc3_t16` expects 13).
- **The probes package does not depend on `mork_compilers`.** It has its own `engines.run_query` and does not list the Oxigraph and Jena packages as dependencies, since a standalone `pip install` would look for them on PyPI. `bootstrap:testing-sparql-probes` installs the three together, and `available()` says which engines can run.
- **Protocol output is UTF-8 explicitly,** not the platform charset.
- **The jar is not part of `mise run bootstrap`.** The reasoning kit's is not either. `bootstrap:testing-jena` builds it, and the conformance task depends on that.
- **`check:conformance`** runs `check:persistence-conformance`, `check:mork-compilers-conformance` and `check:sparql-probes-conformance` in turn as `{ task = ... }` entries, so it stops at the first failure. No `check` default changed. `check:persistence-conformance` and `check:mork-compilers-conformance` still name rdflib and Oxigraph and rdflib, and Jena joins them in MSC-2 and MSC-3.
- **The old probe files were moved with `git mv`,** their references updated in TSD-43, the C9b3 Validation Pack (with a note at the top) and the triple-stores skill's engine table, and `write_text` now passes `encoding="utf-8", newline="\n"` (STD-275).

## Open matters

- **ADR-A83 and PRI-25** say a reasoner, rules engine or JVM bridge is declared only in `platform/reasoning-testkit`. Jena is a SPARQL engine, `check:reasoning-isolation` passes, and the pattern is the same as the reasoning kit's (a subprocess, no JPype). Whether PRI-25's wording covers a second test kit is for the maintainer. An addendum to ADR-A125 would settle it.
- **`check:identifiers`** failed on the plan's reserved-range line, now reworded as number ranges on the unit branch.
- Nothing prevents a product module from depending on `sparql-testkit`. The reasoning kit has an isolation check and this has none.

## Index misses

- `graph:ask read CAP-90` returned the plan's text, not the register row. `read STD-153`, `STD-173`, `STD-274` and `STD-176` each returned a section of the testing skill, not the register row of the standard. A `read` of a register identifier should give its row.
- `find` for a test-only Java engine driven from Python found ADR-A83 and PRI-25 first, which was right. Nothing in the index says how a test-support Java kit's JVM options were chosen (the class-data archive). That was in `reasoning.py`'s docstring only.
- No register entry says that rdflib's `n3()` is not N-Quads for a multi-line literal, nor that Jena preserves blank node labels only with `createUseLabelEncoded`. Both are candidates for a discovery entry.
