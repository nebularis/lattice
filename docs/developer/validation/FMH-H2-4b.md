<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-H2.4b, a second engine, the store probes and the benchmark

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice H2.4b, planned in
[plan §4.2](../plans/formal-methods-track-h.md#42-h24-the-composite-family-and-what-each-store-does-planned-2026-10-12) under
[ADR-A124](../../architecture/decisions/ADR-A124-benchmark-root.md) and
[ADR-A125](../../architecture/decisions/ADR-A125-test-support-tooling.md).
**For the maintainer:** one open decision (decision 1) and four findings that change what earlier documents say.
**For countersignature (non-weakening rule):** one, added 2026-10-13, below, **countersigned by the maintainer on 2026-10-13**. No test was removed or loosened, and the spike's own checks, which had been
failing since H2.2, were repaired (below).

## Invariant

What each engine does with the generated SPARQL is stated by a test that fails when the engine changes. The composite replace (R0)
leaves exactly the payload on every engine and at every size where a run finishes, and the benchmark fails on a wrong result and on
nothing else.

## What changed

- **`tools/testing/oxigraph`** (ADR-A125), package `lattice-testing-oxigraph`: `OxigraphStore`, taken from the spike, with `bootstrap:testing-oxigraph`
  and its own tests (OX-T1 to T5). `pyoxigraph>=0.5.11,<0.6`, which has a Python 3.14 wheel, so the checkout's `.venv` is enough. The spike's
  `oxigraph_backend.py` re-exports it, and the spike's README no longer has the Python-version caveat.
- **The engine seam in the persistence tests** (`tests/engines.py`, the `engine` fixture and the `oxigraph` marker). A test that executes an
  update opts in with `@engines.each_engine`, and runs on rdflib and on Oxigraph, which skips where the package is absent. `OxDataset` has the
  part of rdflib's `Dataset` API the tests use and answers in rdflib terms. **Six modules now run on both engines, and the probes are per engine:** H2.2's and H2.3's
  behaviour tests, H2.4a's, and the composite lifecycle, boundary and sweep tests of HO1, HO5 and HO7. 56 cases ran on Oxigraph at first
  (66 now with the probes), `mise run check:persistence-oxigraph`.
- **`benchmark/persistence-composite-cost`** (ADR-A124), `mise run check:persistence-composite-cost`, not part of `check`.
- **The probes** P1 to P5 in `test_store_probes.py`, per engine, below.
- **Small changes elsewhere.** `templatecheck.operations(compiled, guards)` takes the guards flag. `.gitignore` ignores the benchmark reports.
  The root README and the developer guide describe the two directories.
- **The spike was failing, and now passes.** Since H2.2 the spike's scenarios ran the guarded updates with `xsd:integer` epochs, and the IR
  renders `DELETE {` across lines. They now run unguarded (the spike studies what the update does) and the regular expressions allow it.
  `mise run check` does not run the spike, which is why nothing showed it.

### For countersignature (added 2026-10-13, countersigned 2026-10-13)

1. **H2.4b-T1 and T2 changed their rdflib expectation.** They asserted that rdflib keeps the triple in both row orders, which held only for
   some hash seeds, so the default check failed at random. On rdflib T1 now runs the probe in child processes under `PYTHONHASHSEED` 0 to
   11 and requires both outcomes to occur, and T2 asserts that neither engine is snapshot. The Oxigraph expectations are unchanged. The
   tests are no weaker. They now assert what the source shows and pass on every run (three runs, both engines, 2026-10-13).

## Findings, by probe

rdflib 7.6.0 and Oxigraph 0.5.11, on 2026-10-12, Python 3.14.8, Linux x86_64.

| Probe | rdflib | Oxigraph | Feeds |
|---|---|---|---|
| P1 `snapshotUpdateSemantics`: a `DELETE`/`INSERT` of one triple in two solutions, in both row orders | **corrected 2026-10-13: False.** rdflib applies one solution at a time, in an order that follows `PYTHONHASHSEED`, so the triple survives or is lost by process. The first reading, True, held only for some seeds ([TSD-01](../../architecture/triple-store-discovery.md#tsd-01-the-order-in-which-a-deleteinsertwhere-is-applied)) | lost when the inserting row comes first. **False** | TD-42's linear form R2 |
| P2 request failure atomicity: `INSERT DATA` then a failing operation | `CREATE GRAPH` is not implemented and `DROP GRAPH` of an absent graph does not fail. A failing `LOAD` leaves the first insert in place. **Not atomic** | a failing `DROP GRAPH` (an error at run time) rolls the insert back. **Atomic** | R1, two operations in one request |
| P3 correlated `GRAPH ?g`: 100 graphs of 3000 triples against 1 | ratio 1.1 | ratio 1.1 on 0.5.11 for a constant `?g`. **Corrected 2026-10-28: about 85 on 0.5.13, and about 85 on every version for the computed `?g` the compiler emits** (TSD-45) | the cost note of H2.3-Q2. It holds for rdflib and not for Oxigraph. The Oxigraph T4 is a strict expected failure from 0.5.13, and T4b pins the computed form |
| P4 unbound graph variable in a template | writes into a fresh blank-node graph | skips the quad, as the specification says | TD-44 |
| P5 numeric datatypes: `"1"^^xsd:long` stored and `DATATYPE`d | `xsd:long` both | **`xsd:integer` both** | TD-45, and decision 1 |

Two more were found on the way, and are tests: a zero-length path from a term that is in no triple of the graph matches itself on rdflib
and nothing on Oxigraph (H2.4a-T6, now per engine), and `CREATE GRAPH` does not exist on rdflib.

**Corrected 2026-10-13.** This paragraph first said P1 corrects the typed IR sketch §4.3 and that rdflib passes. It does not. rdflib's
`evalModify` deletes and inserts one solution at a time, and `evalJoin` puts the solutions of this `WHERE` in a Python `set`, so their order,
and the probe's answer, follow the process's hash seed. Swept over seeds 0 to 11 the triple was lost in both orders for 6, kept for 4 and
lost in one order for 2, and the test that asserted rdflib keeps it failed in 2 of 3 runs. The sketch's §4.3 was right. Neither engine is
snapshot. [TSD-01](../../architecture/triple-store-discovery.md#tsd-01-the-order-in-which-a-deleteinsertwhere-is-applied) has the detail.

### R0 on Oxigraph

R0 is **right** wherever it finishes: the replace leaves exactly the payload, the bystander aggregate and references untouched, and the row at
the next sequence, at M = N of 10, 100, 1000 and 3000 on both engines, and the six modules above pass on Oxigraph. So the plan's stop
condition, R0 wrong and not slow, did not arise. R0 is superlinear in **memory** on Oxigraph, which the plan did not anticipate.

| M = N | rdflib | Oxigraph |
|---|---|---|
| 10 | 0.03 s | 0.0005 s |
| 100 | 0.17 s | 0.0056 s |
| 1000 | 9.2 s | 0.59 s |
| 3000 | 83 s | 14.4 s |
| 10,000 | 983 s | **did not finish** |
| fitted k, 100 and up | 1.87 | 2.26 |

Run on 2026-10-12, Python 3.14.8, rdflib 7.6.0, pyoxigraph 0.5.11, a Linux x86_64 container with 15 GB, each run capped at 8 GB, guards off.
At 10,000 Oxigraph's `DeleteInsertIter` collects the M x N quads in a `Vec` and an allocation of 7 GB failed under the cap. An earlier uncapped run was
killed by the container at 14 GB. Measured separately, a run at 2000 used 1.5 GB and at 4000 used 5.8 GB, so memory is quadratic and 10,000 would need about
36 GB. Timings vary between runs of one machine (Oxigraph at 1000 took 0.56 to 1.9 s), which is why the check does not fail on time.

## Decisions needing confirmation

1. **Decided 2026-10-13: option D, built in H2.5.** The parameter guard's datatype test cannot pass on Oxigraph (P5, TD-45). Oxigraph stores any integer-derived literal as `xsd:integer`
   and `DATATYPE` reports it, in every expression and at any parse. So `DATATYPE($epoch) = xsd:long`, which ADR-A123's addendum names, is false for
   every request there, and an operation with the guard on writes nothing on Oxigraph. Every position there is an `xsd:integer`, so requests and
   stored rows still match each other, and the integer-versus-long hazard the test guards against cannot arise. I did not change the guard. The Oxigraph
   runs of the behaviour tests use the guards off (`engines.guards()`), and the tests about the guard itself run on rdflib only. Options:

   | Option | Consequence |
   |---|---|
   | A. Leave it. Document that a deployment on Oxigraph runs `--no-parameter-guards` | Nothing to build. That deployment loses the protection against a missing or mistyped parameter, which is the guard's main value and does not depend on the datatype |
   | B. Choose the datatype test by what the store keeps. An option on `instantiate` now (and on `compile`, recorded in the profile, from H2.7): `exact` as today, or `integer`, which tests `DATATYPE($p) = xsd:integer` and so accepts any integer-derived literal | Oxigraph keeps its guard, minus the long-versus-integer distinction it cannot make anyway. A second value of an option to maintain, and H5's capability record gets a field (whether a store keeps numeric datatypes) |
   | C. Weaken the test everywhere to `isNumeric($p)` for `Long` and `Position` | One form that runs on both. On a store that keeps datatypes it no longer catches an `xsd:integer` epoch, which a template that only writes the epoch (bootstrap, create) would store |

   My leaning was B. **The maintainer chose a fourth option, D, on 2026-10-13: a self-calibrating test,
   `DATATYPE($p) = DATATYPE("0"^^xsd:long)`**, which compares the parameter's datatype with what the store makes of an `xsd:long`
   constant. On rdflib only `xsd:long` passes, exactly today's guard. On Oxigraph any integer-derived literal passes, which is
   harmless there since all of them become `xsd:integer`. A missing or non-numeric value is refused on both, and no option or capability
   field is needed. Measured on both engines on 2026-10-13 against `xsd:long`, `xsd:integer`, a plain integer, `xsd:int`, a string and an
   unbound parameter. It assumes a store treats a constant, a parameter and a stored value alike, which P5 is extended to assert. Recorded
   as ADR-A123's fourth addendum, and built in H2.5.
2. **R0 needs memory quadratic in the aggregate on Oxigraph** (TD-42's row has the figures). The record of the plan is that H5 selects R2 (one
   operation, linear) by `snapshotUpdateSemantics`. P1 now says R2 is **unsafe on Oxigraph** (it applies in turn) and safe on rdflib, which is the
   reverse of what the sketch assumed. R1 (two operations in one request) is safe on Oxigraph (P2) and not on rdflib. So no single linear form fits
   both engines, which is what the capability record is for. Nothing is built here, per the plan.
3. **The `oxigraph` cases are in `check:persistence` where the package is installed.** `bootstrap` does not install it (ADR-A125 decision 4), so CI
   skips them, and `check:persistence-oxigraph` installs it and runs only them. A developer who ran `bootstrap:testing-oxigraph` sees them in
   `check:persistence` too.
4. **The benchmark's 10,000 point never finishes on Oxigraph, so it records "did not finish".** Each run is a child process under a memory cap
   (default 8 GB, `COMPOSITE_COST_MEMORY_GB`), a run that dies without a result is recorded with its exit status, and that is not a wrong result.
   The check still fails on a wrong result. If you would rather it fail on an engine that cannot finish, say so.

## Test cases

| ID | Given / When / Then | Level | Invariant | +/- |
|---|---|---|---|---|
| OX-T1 to T5 (`tools/testing/oxigraph/tests`) | the adapter / `bind_parameters`, an update with parameters, a parameter left out, a select, `remove_graph` / as described | L1 | the adapter | + |
| H2.4b-T1, T2 | P1 / both row orders / the answers above | L4 | `snapshotUpdateSemantics` | + |
| H2.4b-T3 | P2 / a failing second operation / the answers above | L4 | request failure atomicity | + |
| H2.4b-T4 | P3 / 100 graphs against 1 / a ratio under 8 | L7 | no scan of every graph | + |
| H2.4b-T5 | P4 / an unbound graph variable / skipped, or a blank-node graph | L4 | TD-44 | + |
| H2.4b-T6, T7 | P5 / a long literal stored and `DATATYPE`d, and a bootstrap with the guard on / `xsd:long` and a row on rdflib, `xsd:integer` and no row on Oxigraph | L4 | TD-45 | + |
| H2.4b-T8 to T10 | the facade / terms round-trip, wildcards, the default graph, parameters as text / unchanged | L1 | the facade is faithful | + |
| H2.4b-T11 | `canon` / a long literal / unchanged on rdflib, `xsd:integer` on Oxigraph | L1 | as T6 | + |
| H2.4b-T12 | the Oxigraph cases in a process that cannot import the package / run / skipped, not failed | L1 | ADR-A125 decision 4 | + |
| H2.2-T7 to T19, H2.3-T3 to T32, H2.4a-T4 to T7, HO1, HO5, HO7 | the behaviour tests, now `[rdflib]` and `[oxigraph]` / run / pass on both | L4 | the engines agree on what the operations do, with the guards off on Oxigraph | + |
| BENCH-T1 to T9 (`benchmark/persistence-composite-cost/test_check.py`) | the benchmark / small sizes, a no-op engine, an engine that keeps an old triple, a clock a million seconds slow, a memory cap, a child that did not finish, a quadratic series / passes, fails on the wrong result, does not fail on time or memory, records a run that did not finish and leaves it out of the fit | L2 | the pass criterion of H2.4-Q3 | ± |

## One command

Run from the repository root. `check:persistence` is the gate: `2111 passed, 1 xfailed` here, the 2035 of H2.4a and 76 new cases. The others are
on demand.

```bash
mise run check:persistence
mise run check:persistence-oxigraph          # 5 adapter tests and the 66 Oxigraph cases, about 15 s
mise run check:persistence-composite-cost    # about 25 minutes, most of it rdflib at 10,000. COMPOSITE_COST_MAX=1000 for a quick run
```

## Artefacts to inspect

- `tests/test_store_probes.py`, beside the table above.
- `benchmark/persistence-composite-cost/check.py` and, after a run, its `report.md`.
- `tools/persistence/tests/engines.py`, the facade.

## Adversarial probe

Run on 2026-10-12, restored afterwards.

| Mutation | Result |
|---|---|
| every engine is rdflib (one engine's answer hard-coded) | 8 probe and lifecycle cases fail |
| `canon` is the identity | 3 fail |
| a literal loses its datatype on the way into Oxigraph | 6 fail |
| the benchmark stops checking the data graph | BENCH-T3 fails |
| the adapter's strict parameter check removed | OX-T2 fails |

## Deliberate non-coverage

- Isolation between concurrent writers, and the identical-insert conflict of the ownership sketch §15 (H5).
- A form of the replace other than R0, and the choice between forms (H5).
- Recording any of the probe answers in the compiled profile (H2.7), or a capability record (H5).
- A third engine, and other versions of these two.

## Identifiers renumbered before the merge into `main`, 2026-10-28

Seven identifiers this slice defined were also taken on branches with earlier rows, so under first in wins (ADR-A133 addendum) this branch renumbered its own before merging `main`. The store finding on the graph variable passed into an `OPTIONAL` became TSD-45 and the RDF4J `COUNT(*)` finding became TSD-48, since ccs-trunk recorded its findings numbered 42 and 43 on 2026-10-27. The two open questions became TSD-Q24 and TSD-Q25, after ccs-trunk's questions 21 to 23. The run records became R-M and R-N, since ccs-trunk uses R-J to R-L. The pending decision on the compiler's default graph naming became PDD-17, since the ledger branch raised its pending decision numbered 13 on 2026-10-27 and `main` had already moved its own to PDD-16. ccs-trunk's finding numbered 42 describes the same phenomenon as TSD-45, and the two are reconciled when ccs-trunk merges `main`.
