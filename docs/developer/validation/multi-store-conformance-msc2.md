<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: MSC-2, the persistence tests on three engines

**Unit:** [`multi-store-conformance`](../status/multi-store-conformance.md)
**Plan:** [multi-store-conformance](../plans/multi-store-conformance.md), MSC-2 and the triage rule
**Machine:** a macOS arm64 laptop, Java 25, Jena ARQ 5.1.0 (in memory, never TDB2), rdflib 7.6.0, pyoxigraph 0.5.13. **Placement:** T0, public. Test support and engine findings, nothing domain-specific.
**Status:** authored and run, not accepted. The lead's review and the maintainer's merge are the sign-off.

## Scope

- `jena` in `tools/persistence/tests/engines.py`: a `REGISTRY` entry with the `jena` mark, an `if` in `dataset()`, and `JenaDataset` and `JenaGraph`, which give the dataset interface the other two engines give on `lattice_testing_jena.JenaStore`. The store speaks rdflib terms, so there is no term conversion.
- `tools/persistence/tests/conftest.py`: the `jena` marker, the package and jar named in the required-engines check, and a skip in the `engine` fixture when the package or jar is missing.
- `mise.toml`: `check:persistence-conformance` names `rdflib,oxigraph,jena` and depends on `bootstrap:testing-jena`. `check:persistence` is unchanged.
- Expectations per engine in six tests, the probes among them, and the findings TSD-50 to TSD-53 with runs R-T and R-U, open questions TSD-Q30 and TSD-Q31, and CAP-95.
- Out of scope. Any change to a generated operation, any `check` default, TDB2.

## Result in one paragraph

Jena ran 357 tests of the persistence suite. Nine failed at first. None showed a generated query relying on one engine's reading, so no fix to generated SPARQL and no debt row. Seven were an expectation that named only rdflib and Oxigraph and now names Jena too, one was the harness (`int()` of a decimal), and one is a Jena departure from the specification that is drafted for upstream. The expectation is per engine and no assertion was loosened for every engine.

## Triage

| ID | Test | Engine | Category | Finding or fix |
|---|---|---|---|---|
| MSC2-01 | `test_h2_4a_t6` (two cases, guards on and off) | jena | expectation per engine. Jena matches a zero-length path from a term in no triple, as rdflib does and Oxigraph does not | TSD-51, fixed in the test |
| MSC2-02 | `test_h2_5_t42` | jena | expectation per engine. Jena keeps `xsd:long` and counts distinct terms, which is the specification | TSD-52 |
| MSC2-03 | `test_h2_5_t43` | jena | as MSC2-02, the gap scan reports a duplicate `seq` written as `xsd:integer` | TSD-52 |
| MSC2-04 | `test_h2_5_t44` | jena | the harness. `8 / 4 / 2` is an `xsd:decimal` with the lexical form `1.0` on Jena, which the specification says of a division of integers, and `int(term)` refused it. Now `int(float(term))` for every engine, with the same three expected values. Jena groups from the left | TSD-52, fixed in the test |
| MSC2-05 | `test_h2_4b_t3_p2` | jena | Jena departs from the specification: `CLEAR GRAPH` of a graph that is not there fails and `DROP GRAPH` succeeds, on a dataset that does not record empty graphs. The request rolls back | TSD-50, draft `.local/upstream/jena-clear-graph-of-a-store-without-empty-graphs/`, not filed. The test expects `DROP` to succeed and `CLEAR GRAPH` and `LOAD` of an absent source to fail and roll back |
| MSC2-06 | `test_h2_4b_t6_p5` | jena | expectation per engine, `xsd:long` kept | TSD-52 |
| MSC2-07 | `test_h2_5_t1_p5` | jena | as MSC2-06, in four forms and the equality test | TSD-52 |
| MSC2-08 | `test_h2_5_t4` | jena | guard D refuses an `xsd:integer` epoch where datatypes are kept, as on rdflib | TSD-52 |

Passing on Jena without a change to the assertion, with the expectation now written for Jena where it is a probe of the engine.

| ID | Test | Engine | Note | Finding |
|---|---|---|---|---|
| MSC2-09 | `test_h2_4b_t1`, `t2` (P1) | jena | every deletion then every insertion, in either row order | TSD-53 |
| MSC2-10 | `test_h2_4b_t5` (P4) | jena | an unbound template graph is skipped | TSD-53 |
| MSC2-11 | `test_tsd_34_...` (both cases) | jena | right in both forms | TSD-53 |
| MSC2-12 | the rest of the 357 jena cases | jena | the generated SPARQL of every builder, with the guards on and off | none |
| MSC2-13 | required mode | none | with `PERSISTENCE_ENGINES_REQUIRED=1`, `jena` in the list and the jar missing stops the run ("not installed: the Jena testkit jar"). Without it the Jena cases skip | none |

## Commands and results

Run from the worktree on 2026-10-27, after the last edit.

| Command | Result |
|---|---|
| `mise run check:persistence-conformance` before the expectations changed | `9 failed, 4718 passed in 120.38s`, the nine in MSC2-01 to MSC2-08 |
| `mise run check:persistence-conformance` | `4727 passed, 2994 warnings in 114.62s` |
| `PERSISTENCE_ENGINES=jena mise exec -- python -m pytest tools/persistence/tests -q -n 4 --dist loadgroup -m jena` | `357 passed in 10.44s` |
| `mise run check:persistence` | `3975 passed, 22 warnings in 63.26s`, Oxigraph alone, unchanged |
| `mise run check:testing-jena` | `14 passed in 0.71s` |
| `mise run check:catalogue` | `20 module(s) and 11 tool package(s) agree with the tree. Bypass scan: 13 known file(s)` |
| `mise run check:python-root` | `Ran 87 tests ... OK`, Phase 8 conformance passed |
| `mise run check:deny-terms` | `0 finding(s) against 5 entries` |
| `mise run check:identifiers` | `every mention of 873 resolvable identifiers resolves`, 9 passed |
| `mise run check:agent-guidance` | `0 problem(s)`, 9 passed |
| `mise exec -- python tools/writing_rules.py` on the lines this slice adds to the discovery record | no warning (the file has older ones) |
| `mise exec -- java -cp platform/sparql-testkit/target/sparql-testkit.jar Repro.java`, from the draft's directory | prints `DROP` success, `CLEAR` failure and exits 1 (run R-U) |

## Adversarial probes

1. Changed Jena's expected datatype in P5 from `xsd:long` to `xsd:integer`. `test_h2_4b_t6_p5` and `test_h2_5_t1_p5` failed on `[jena]` and the other 12 probe cases passed. Restored.
2. Made `JenaDataset.update` ignore `initBindings`, so a guarded write loses its parameters. The first failures were the append and replace tests on `[jena-guards]` and `[jena-no-guards]`, which shows the Jena branch is executing the generated writes and the suite checks what they write. Restored.
3. Pointed `LATTICE_SPARQL_TESTKIT` at a missing jar. With `PERSISTENCE_ENGINES_REQUIRED=1` the run stops with a usage error, and without it the 14 probe cases skip.

## Decisions taken

- **Expectation per engine, not an xfail.** The plan asks for a test that cannot pass on one engine to be marked for it with the finding id, strictly. Every Jena difference here is an engine's recorded behaviour that the test already branches on (the file branches on rdflib and Oxigraph), so Jena gets a branch with its finding id in a comment. TSD-50's departure is held strictly in the same way. A fix upstream makes `test_h2_4b_t3` fail, which is the signal. No test is `xfail`.
- **`CLEAR GRAPH` and `LOAD` as Jena's failing operations in P2.** `DROP GRAPH <urn:absent>`, which fails on Oxigraph, succeeds on Jena, so P2 needs another failing second operation. It asserts both.
- **No SPARQL fix and no debt row.** No generated operation emits `CLEAR` or `DROP`, and the three departures rdflib shows do not occur on Jena. So no query relies on a reading Jena disagrees with.
- **`JenaGraph.remove` of a triple with a blank node raises `NotImplementedError`.** `DELETE DATA` refuses blank nodes, and no test removes one. A test that does needs a pattern delete.
- **The dataset reads through `JenaStore.quads`.** One query returns every quad and the pattern is filtered in Python. Adequate for fixtures of the size these tests use. A test that holds thousands of triples on Jena should call `select` instead.
- **Test names kept.** Several names say "on rdflib and Oxigraph". Renaming would break the Validation Packs that cite them, so the docstrings and the discovery record carry the Jena column.
- **Run records R-T and R-U, and "Fifteen run records".** MSC-3 takes R-V, so the sentence in the discovery record that counts the records will conflict on merge and needs the count to follow both slices.

## Open matters

- **TSD-Q13 stays open for TDB2.** TSD-50 says in its first paragraph that it is in-memory ARQ. TSD-Q30 asks the TDB2 and Fuseki questions.
- **`mise run bootstrap` does not build the jar,** so its message in a required run points at `bootstrap:testing-jena`, which the conformance task now depends on.
- **The draft report is not filed** and `.local/` is git-ignored, so the draft lives on this machine only. It is described in TSD-50.
- The status record and the plan's slice table were not edited here. The lead updates them.

## Index misses

- `graph:ask read CAP-90`, `STD-153` and `STD-279` returned the section of a file that mentions them (`mise.toml`, the testing skill, the R9 section) and not the register row. The register rows are in `docs/developer/capabilities.md` and `standards.md`.
- `find` for a zero-length path, the failing-second-operation probe and `xsd:long` found TSD-08, TSD-06 and TSD-07 and TSD-18 first, which was right. `find` for the decimal result of an integer division found TSD-17 and TSD-41 at 0.65 and nothing that says an integer division is an `xsd:decimal`. That fact is in the specification only, and the test's docstring did not say it.
- Nothing in the index says what a failing `DROP`, `CLEAR`, `ADD`, `MOVE` or `COPY` of an absent graph does on any engine except TSD-06's one row. TSD-50 now holds the Jena column.
- `find "mark a test for one engine strictly"` did not return a standard. The testing skill's conformance default says it in passing. A standard for "an expectation per engine carries the finding's id" would answer it, and was not added.
