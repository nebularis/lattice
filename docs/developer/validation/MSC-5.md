<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: MSC-5, open store questions and upstream reports

**Unit:** [`multi-store-conformance`](../status/multi-store-conformance.md)
**Machine:** a macOS arm64 laptop with 8 logical cores (runs R-W, R-X and R-Y of the [discovery record](../../architecture/triple-store-discovery.md)). **Branch:** a worktree detached from `multi-store-conformance` at `445b58b8`, uncommitted
**Plan:** [plan](../plans/multi-store-conformance.md), slice MSC-5
**Findings:** TSD-54 to TSD-57 new. TSD-15, TSD-16, TSD-34, TSD-42 and TSD-43 extended with Jena. **Open questions:** Q12, Q18, Q19, Q21, Q22, Q23, Q31 and Q35 updated and dated, Q32 added
**Decisions:** none that needs the maintainer. The routine ones are at the end

## Invariant

Each open store question that a third engine or a reading of the specification can answer is answered or narrowed in the discovery record, with a run record. Every engine departure found by this unit has an upstream draft or a pointer to an existing report, and nothing is filed.

## Tests

All in `tools/testing/sparql_probes/tests/test_store_questions.py`, run by `check:sparql-probes-conformance` on rdflib, Oxigraph and Jena. Each states what every engine returns.

| ID | What | Result |
|---|---|---|
| MSC5-01 | TSD-15, a sub-select with `?s` bound outside. rdflib 1, Oxigraph 3, Jena 3 | pass |
| MSC5-02 | TSD-15, a sub-select inside `GRAPH`. 2 on all three | pass |
| MSC5-03 | TSD-16, `MIN` and `MAX` over IRIs. Literals on rdflib, IRIs on Oxigraph and Jena | pass |
| MSC5-04 | TSD-16, `IRI(MIN(STR(?o)))` is an IRI on all three | pass |
| MSC5-05 | TSD-17, `10 - 3 + 2`, `10 - 3 - 2` and `8 / 4 / 2` from the left on all three | pass |
| MSC5-06 | TSD-18, `COUNT(DISTINCT)` over a `VALUES` row of `xsd:long` and `xsd:integer`. 2, 1, 2 | pass |
| MSC5-07 | TSD-34's query on Oxigraph and Jena gives `b` and `c` (rdflib is hash-seed dependent and not asserted) | pass |
| MSC5-08 | the same without the sub-select gives `b` and `c` on all three | pass |
| MSC5-09 | TSD-54, a blank node label loaded twice. rdflib 1, Oxigraph 2, Jena 1 | pass |
| MSC5-10 | TSD-55, rdflib `n3()` of a multi-line literal is triple-quoted, and Oxigraph and Jena refuse the line | pass |
| MSC5-11 | `Max` over `{2, no value}`. rdflib `2`, Oxigraph and Jena unbound, with `Min` unbound on the last two | pass |
| MSC5-12 | all three engines are available where `SPARQL_PROBES_REQUIRED=1` | pass |

The benchmarks have their own tests. `benchmark/sparql-constraint-query-cost/test_check.py` now runs its engine-parametrised test on Jena too (18 tests passed, up from 15).

## Commands and results

Run from the worktree, each through mise.

| Command | Result |
|---|---|
| `mise run check:sparql-probes-conformance` | `55 passed, 1160 subtests passed in 2.68s` |
| `mise run check:persistence-store-probes` | `8 passed`, then the report with Jena's column, exit 0 |
| `mise run check:sparql-constraint-query-cost` | `18 passed`, then the report with Jena's rows, exit 0, twice (56 s each) |
| `mise run check:testing-jena` | `14 passed in 0.77s` |
| `mise run check:catalogue` | `repository catalogue: 20 module(s) and 11 tool package(s) agree with the tree. Bypass scan: 13 known file(s)` |
| `mise run check:deny-terms` | `deny terms: 0 finding(s) against 5 entries` |
| `mise run check:agent-guidance` | `9 passed` |
| `mise run build:knowledge` and `mise run check:identifiers` | see the end of this pack |
| `java -cp platform/sparql-testkit/target/sparql-testkit.jar Repro.java` in each Jena draft | exit 1 for `jena-avg-all-unbound`, `jena-str-of-blank-node` and `jena-group-concat-distinct-empty-group`, as drafted |
| `mise exec -- python -m pytest .local/upstream/<name>/test_*.py` for each Python draft | every Python draft fails (`oxigraph-count-error` 4 failed). `rdflib-grouped-query-over-no-rows` passed at first, since rdflib drops a row whose projected variables are all unbound (TSD-10), and fails after the query projects a constant |

## The open questions

### 1. TSD-42 on Jena (run R-W)

`mise run check:persistence-store-probes`, 100 graphs of 3,000 triples against 1, best of five, the JVM with its full compiler.

| Form | Jena ARQ 5.1.0 | Oxigraph 0.5.13 | rdflib 7.6.0 |
|---|---|---|---|
| bind-optional | 1.0 (7.7 to 7.3 ms) | 75.1 | 1.3 |
| values-optional | 1.0 (6.7 to 6.4 ms) | 76.0 | 1.4 |
| join | 1.0 (5.4 to 5.2 ms) | 1.0 | 1.7 |
| constant | 0.8 (4.6 to 3.7 ms) | 1.0 | 2.1 |

Jena reads one graph under every form. Only Oxigraph 0.5.13 loses the outer binding, which makes it a departure of one release and not a property of the query. Added to TSD-42, with a pointer to the draft report.

### 2. TSD-43 on Jena, and TSD-Q21's `MAX`

The matrix is executed on Jena by `check:sparql-probes-conformance` and every cell is as recorded (AE-01 passed on all three engines). TSD-43 now says so with run R-X. `MAX` over a group with an error row: read §18.5.1.5, §18.5.1.6 and §15.1 of SPARQL 1.1 and §18.6.1.6 of the SPARQL 1.2 working draft (run R-Y). Both define `Max` as the first element of `Flatten(M)` under `ORDER BY DESC` and say nothing about an element that is an error. §15.1 puts "no value" lowest, which gives `2` if an error is "no value" and unbound if it is an error as for `Sum`. The text does not decide, so the question stays about `MAX` alone and needs the working group. No upstream report is drafted for it because no engine is clearly wrong.

### 3. TSD-Q18, the cost forms on Jena (run R-W)

Cheap. Jena became a `JenaEngine` class in the benchmark, 40 lines on the pattern of the Oxigraph one. Ratios of the naive form over the improved one, smallest and largest size, second run.

| Experiment | rdflib | Oxigraph | Jena |
|---|---|---|---|
| E1 | 1.6x, 14.9x | 1.0x, 1.0x | 1.8x, 1.1x |
| E2 | 15.7x, 61.1x | 1.0x, 1.0x | 3.4x, 2.7x |
| E3 | 16.2x, 20.8x | 1.1x, 1.3x | 0.9x, 1.1x |
| E4 | 1.2x, 1.0x | 1.0x, 1.0x | 1.6x, 1.2x |

Jena has no growth with size. E2 shows a constant factor of 2 to 3 and the first size of each is inflated by JIT warm-up. The pipe costs 0.15 ms per call. Recorded as TSD-57. Q18 is narrowed to Fuseki and disk-backed Jena, which this benchmark cannot reach without a server.

### 4. TSD-Q19, TSD-34's form on Jena

MSC2's TSD-53 holds Jena's answer through the persistence tests. MSC5-07 and MSC5-08 repeat it with the query written out. Jena gives `b` and `c`. The defect is rdflib's alone. The Fuseki half and the "why the sub-select decides" half stay open.

### 5. TSD-Q12 and TSD-15 to TSD-18

TSD-17 and TSD-18 were on Jena already (TSD-52). TSD-15 and TSD-16 were not. MSC5-01 to MSC5-04 give Jena as Oxigraph, which is as the specification says. Recorded as TSD-56. Q12 is narrowed to Fuseki itself.

### 6. New findings

The index and the record hold neither. `find blank node labels fresh per parse Jena --kind discovery --tech jena` returned TSD-50 to TSD-53 and TSD-21, and a search of the record for `LabelEncoded`, `label` and `triple quote` found only TSD-29, which is about parsers in general. So TSD-54 (blank node labels, with a Java program that loads the same line twice on the testkit's jar, 2 quads by default and 1 with `createUseLabelEncoded()`) and TSD-55 (rdflib `n3()`).

One observation that differs from the plan's text. rdflib's N-Quads parser keeps the label across two parses of one `Dataset` (1 node), where TSD-29 recorded fresh labels for Turtle. TSD-54 says so.

### 7. Upstream drafts, none filed

All under `.local/upstream/` in this worktree, each with `ISSUE.md` and a standalone failing test, and the issue trackers searched with the GitHub search API on 2026-10-27 (the search and its result are in the `## Tracker search` section of each `ISSUE.md`). The unit branch's three drafts (`jena-clear-graph-of-a-store-without-empty-graphs`, `rdflib-string-number-ordering`, `rdflib-aggregate-over-erroring-if`) were read and not edited.

| Draft | Test | Search result |
|---|---|---|
| `oxigraph-count-error` (copied from the CCS checkout, with the search added) | `test_count_error.py` | nothing relevant, new issue |
| `oxigraph-avg-all-unbound` | `test_issue.py` fails | nothing relevant, new issue |
| `oxigraph-left-join-reads-every-graph` | `test_issue.py` fails (ratio 80) | related #1980 and #1883 open, #1733 merged, no report of this change |
| `jena-avg-all-unbound` | `Repro.java` exits 1 | nothing relevant |
| `jena-str-of-blank-node` | `Repro.java` exits 1 | nothing relevant |
| `jena-group-concat-distinct-empty-group` | `Repro.java` exits 1 | **already reported**, apache/jena#4240 and PR #4243. A note, not a draft |
| `rdflib-grouped-query-over-no-rows` | `test_issue.py` fails | **open fix** RDFLib/rdflib#3498 |
| `rdflib-sum-over-iri-raises` | `test_issue.py` fails with `AttributeError` | nothing relevant |
| `rdflib-aggregate-skips-error-rows` | two tests fail | nearest #563 (closed 2015, asked for the skip). The skip may be intended |
| `rdflib-str-of-blank-node` | `test_issue.py` fails | nothing relevant in the 12 results read |

Several searches were refused with HTTP 403 at first (the unauthenticated search rate limit). The ones that succeeded on repeat are recorded. One was refused and not repeated (`repo:apache/jena str bnode label error`), and the draft says so. Where a result list was longer than what was read, the draft says how many were read. Q31 and Q35 were searched too, on the existing drafts (0 relevant results for the rdflib pair, 35 results of which 15 read for Jena's `CLEAR GRAPH`, none about it).

## Adversarial probe

The sub-select of TSD-34's query on Oxigraph and Jena was made to keep `a`, by replacing the test `?z <urn:prev>* ?w` with `?z <urn:prev>* <urn:nope>` in the query of MSC5-07 and calling the test's own `run_quads`.

```
oxigraph [('<urn:a>',), ('<urn:b>',), ('<urn:c>',)]
jena     [('<urn:a>',), ('<urn:b>',), ('<urn:c>',)]
```

MSC5-07 expects `b` and `c` and would fail on both. The benchmark's own break, an improved form that returns other solutions, is `test_bq2`, and an engine that is off by one is `test_bq3`, both passing.

## Changes

- `tools/testing/sparql_probes/tests/test_store_questions.py` and its README row.
- `benchmark/sparql-constraint-query-cost/check.py` (class `JenaEngine` and its entry in `available_engines`), its README, and the task's description in `mise.toml`.
- `docs/architecture/triple-store-discovery.md`. R-W, R-X, R-Y. TSD-54 to TSD-57, new, and their index rows. Extended: TSD-15, TSD-16, TSD-34, TSD-42, TSD-43, the index rows of TSD-15, TSD-16, TSD-25 to TSD-27 and TSD-42. Open questions Q12, Q18, Q19, Q21, Q22, Q23, Q31, Q35 dated, and Q32 added.
- `.local/upstream/` ten directories (git-ignored).
- Not changed: the plan and the status record, which are the lead's.

## Decisions taken

- **The benchmark runs Jena when the jar is built and skips it otherwise,** as `persistence-store-probes` does, and the task has no dependency on `bootstrap:testing-jena`. A machine without the jar still passes.
- **Jena's version in the benchmark is a constant, `5.1.0`,** since the package states none. The same note as in `persistence-store-probes`.
- **The probes are tests in `tools/testing/sparql_probes`,** not a new package, since the package exists to hold such probes and its conformance task already runs them. They stay out of `check` (ADR-A125).
- **The `MAX` question is not settled by choosing a reading.** The text does not decide, and picking one would put an unfounded claim in the record.
- **No draft for the unit branch's three existing reports.** Searches for them were added to the open-question rows and not to their files, which are on the unit branch.
- **Q32 added** to carry the filing decision, because filing is the maintainer's.
- **Run records R-W, R-X, R-Y used.** R-Z and the remaining reserved identifiers (findings 58, 59 and 62 to 69, questions 33, 34 and 36 to 39, debt 100 to 104 and 106 to 109, standards 291 to 299) are unused.

## Index misses

`mise run graph:ask -- misses` is empty. Weak answers.

- `find` for Jena and blank node labels returned TSD-50 to TSD-53, none of which is about parsing. The record held no entry on it, so the fallback was a text search.
- Nothing in the index says that a cost benchmark may take an engine through an adapter class (STD-290 is about timing assertions). The pattern was found by reading `persistence-store-probes/check.py`.
- `graph:ask read TSD-15` gives the entry but the open question rows in section 8 are not entries, so `find TSD-Q18` finds nothing by identifier. A question's row is read only from the document.
- No register entry records that the GitHub search API refuses unauthenticated calls after a few requests (HTTP 403). It affected the order of the searches. This is machine specific and belongs in an agent's notes and not in the repository.

## Open matters for the maintainer

- Filing is yours (TSD-Q32). Check RDFLib/rdflib#3498 first, since it may cover the grouped query.
- `rdflib-aggregate-skips-error-rows` may be a design choice that #563 asked for, so a report there should ask.
