<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: MSC-3, the compilers and Eligibility on Jena

**Unit:** [`multi-store-conformance`](../status/multi-store-conformance.md)
**Plan:** [multi-store-conformance](../plans/multi-store-conformance.md), MSC-3
**Machine:** run R-V, a macOS arm64 laptop, Java 25, Jena 5.1.0, rdflib 7.6.0, pyoxigraph 0.5.13. **Placement:** T0, public. Test support and engine findings, nothing domain-specific.
**Status:** authored and run, not accepted. The lead's review and the maintainer's merge are the sign-off.

## Scope

- `jena` in `mork_compilers.engines.REGISTRY`. `run_query` loads the graph as N-Triples into a `lattice_testing_jena.JenaStore`, runs the query through the test kit and returns `_Row`s of rdflib terms, as the Oxigraph branch does. The import is inside the branch, so rdflib and Oxigraph need neither the package nor a JVM. `DEFAULT` stays Oxigraph and `check:mork-compilers` is unchanged.
- The conformance run. A task per engine, not a list read by the module. `MORK_SPARQL_ENGINE` is read once at import, and a list would need the suite to re-import or to parametrise 164 `unittest` methods. `check:mork-compilers-conformance:rdflib` and `:jena` each set the variable, and `check:mork-compilers-conformance` runs both, so its name and `check:conformance` are unchanged.
- Eligibility. Its differential tests (`tools/reference/eligibility/tests/test_differential.py`) run the compilers' generated SPARQL through `mork_compilers.test_concept_backends.sparql`, which calls `run_query`, so they follow `MORK_SPARQL_ENGINE`. `check:reference-eligibility` stays on Oxigraph. `check:reference-eligibility-conformance` is new, with `:rdflib` and `:jena`, and `check:conformance` runs it.
- Probes of the profile read set's `?decision` dependence on the three engines (audit items 4 to 6). The generated query is not changed. That belongs to CCS slice C9b3b.
- Out of scope. A change to any default engine, to a generated query, or to MSC-2's persistence files.

## Tests

| ID | File | What it shows |
|---|---|---|
| MSC3-01 | `tools/mork_compilers/src/mork_compilers/test_engines.py` | `jena` is in the registry |
| MSC3-02 | same | an unknown engine is refused |
| MSC3-03 | same | Jena returns the rows rdflib does, with the same terms, for plain, tagged, integer, decimal, IRI and multi-line literals and an unbound optional |
| MSC3-04 | same | a Jena row reads by attribute, name and position, and `asdict()` leaves out an unbound variable |
| MSC3-05 | same | a query error on Jena is a `JenaError` |
| MSC3-11 | `tools/testing/sparql_probes/tests/test_decision_read_set.py` | each engine returns what is recorded for the three read-set aggregates and the coalesced control, in two ways of leaving `?decision` unbound (TSD-60). Strict, so an engine fixed upstream fails it |
| MSC3-12 | same | Oxigraph and Jena give one answer in every form |
| MSC3-13 | same | `COALESCE(?decision, "")` gives `1` on all three engines for the arithmetic error |
| MSC3-14 | same | rdflib orders a string against a number where Oxigraph and Jena give an error (TSD-61) |
| MSC3-15 | same | `"abc" = 5` is `false` on all three, the control |
| MSC3-16 | same | with `SPARQL_PROBES_REQUIRED=1`, all three engines ran |

The slice adds 11 tests in two modules. The two conformance suites themselves (164 and 67 tests) were not modified.

## Commands and results

All from `/Users/t4/work/lattice-wt/msc-3`, through `mise`.

| Command | Result |
|---|---|
| `mise run check:mork-compilers` | `169 passed, 30 subtests passed` (Oxigraph, 164 plus the 5 new) |
| `mise run check:mork-compilers-conformance` | rdflib `169 passed, 30 subtests passed`, Jena `169 passed, 30 subtests passed` |
| `mise run check:reference-eligibility` | `67 passed` |
| `mise run check:reference-eligibility-conformance` | rdflib `67 passed`, Jena `67 passed` |
| `mise run check:sparql-probes-conformance` | `43 passed, 1131 subtests passed` |
| `mise run check:testing-jena` | `14 passed` |
| `mise run check:conformance` | persistence conformance `4370 passed` (rdflib and Oxigraph, Jena is MSC-2's), then the above. All green, 2 min 5 s |
| `mise run check:catalogue`, `check:python-root`, `check:deny-terms`, `check:agent-guidance`, `check:identifiers` | each exit 0 |

Wall time of the Jena run of the compilers' suite, 4 workers, one JVM per worker: 12.9 s, against 10.8 s for rdflib and 9.5 s for Oxigraph.

## Triage

Every one of the 164 compiler tests and 67 Eligibility tests passed on Jena first time, so the triage table has no failing test.

| Failure | Triage | Action |
|---|---|---|
| none on Jena, in either suite | not applicable | none. No expectation was marked for Jena, no assertion was changed |

Two divergences came out of the `?decision` probe, neither in the suite. Both are rdflib departures from the specification, so each has a finding, an expectation per engine and a drafted upstream report.

| Divergence | Triage | Finding | Upstream draft (not filed) |
|---|---|---|---|
| `SUM(IF(?d = ..., 1, 0))` with `?d` unbound for a row raises `AttributeError` on rdflib, `MAX` returns no row. Oxigraph and Jena return unbound | the engine departs from the specification | TSD-60 | `.local/upstream/rdflib-aggregate-over-erroring-if/` with `test_issue.py`, which fails on rdflib 7.6.0 |
| `"abc" >= 5` is a boolean on rdflib, an error on Oxigraph and Jena | the engine departs from the specification | TSD-61 | `.local/upstream/rdflib-string-number-ordering/` with `test_issue.py`, which fails on rdflib 7.6.0 |

## The `?decision` probe, result per engine

For the lead to pass to the CCS unit (slice C9b3b). The audit predicted a skipped row on rdflib. The probe finds rdflib is worse for an arithmetic error and different again for the audit's own comparison.

| `?decision` unbound for 1 of 2 rows | rdflib 7.6.0 | Oxigraph 0.5.13 | Jena ARQ 5.1.0 |
|---|---|---|---|
| the flag `SUM(IF(?decision = "Permitted", 1, 0))`, error `?c + 1 > 5` | `AttributeError` on reading the result | unbound | unbound |
| the same, the audit's error `?c >= 5` with `?c` = `"abc"` | `2` (rdflib orders the string, so `?decision` is bound) | unbound | unbound |
| the missing-candidate flag (audit item 5), either error | `AttributeError`, or `2` | unbound | unbound |
| the reason `MAX(IF(...))` (audit item 6) | no row, or `"z"` | unbound | unbound |
| `COALESCE(?decision, "")` in the flag | `1`, or `2` | `1` | `1` |

Reading. Oxigraph and Jena agree in every cell, so the dependence is a property of the query and not of an engine. The audit's example hides on rdflib because rdflib does not treat `"abc" >= 5` as an error (TSD-61), so the dependence there is on the comparison and not on the aggregate. Recorded as TD-105 with owner C9b3b. The fix, `COALESCE(?decision, "")` in the three `IF` tests, makes the malformed row count as none of the outcomes on all engines for an arithmetic error, but whether that is the meaning wanted, or the containment test should be guarded with `isNumeric`, is a design decision for the CCS unit. The probe used the three aggregate expressions of `_read_set` on a `VALUES` block. It did not run the generated profile query with a malformed value, which would need a fixture the suite lacks.

## Adversarial probes

- Removed the `store.load(...)` line of `_run_jena` and ran the compilers' suite with `MORK_SPARQL_ENGINE=jena`. Result: `80 failed, 92 passed`. The Jena path is executed, and the 164 passes are not the Oxigraph path in disguise. Restored.
- The probe expectations in MSC3-11 are equality on the exact result, so a fixed rdflib (or a changed Oxigraph or Jena) fails the test and the record is revised, and the standalone upstream tests fail on 7.6.0 and would pass once rdflib is fixed.
- No `FILTER(false)` and no weakened assertion. `check:mork-compilers-conformance:jena` depends on `bootstrap:testing-jena`, so a missing jar is a build step and not a silent skip. If the jar still cannot be built, `JenaStore()` raises `JenaError` and the run fails.

## Decisions taken

- A task per engine, not a list in `MORK_SPARQL_ENGINE`. It keeps the module's read-once rule, adds no import-time state and keeps xdist workers simple. Two more task names, one command each.
- Eligibility gets its own conformance task rather than a line in the compilers' task, since `tools/reference/eligibility/tests` is a separate pytest root and `check:reference-eligibility` is in `check`.
- `check:reference-eligibility-conformance` runs rdflib as well as Jena, so the differential tests are checked against both of the non-default engines, as the compilers' suite is.
- The profile read set is not changed. TD-105 records the owner.
- Debt rows used: TD-105 only. Standards 295 to 299 and open questions 36 to 39 are not used. TSD-Q35 asks whether the two drafts are filed.

## Open matters

- The two upstream drafts are not filed. Filing is the maintainer's.
- `check:persistence-conformance` does not yet name Jena (MSC-2).
- The ADR-A125 addendum's text "each engine added later joins this run and adds nothing to `check`" holds for this slice. `check` gains nothing.

## Index misses

- `find` for "comparing a string with a number is an error" and for "aggregate over an IF of an unbound variable" returned TSD-25, TSD-07, TSD-41 and similar, none of which answers either question. TSD-60 and TSD-61 now do.
- `misses` reports none recorded, since no query is logged as a miss unless the tool is told. The two queries above are the weak answers.
- `read CAP-90` and `read CAP-92` returned `mise.toml` and `pyproject.toml` excerpts rather than the register rows, which makes the capability's meaning hard to confirm from the index. The rows are in `docs/developer/capabilities.md`.
