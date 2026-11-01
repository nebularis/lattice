<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS C9b3, the profile union on both engines

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** a macOS arm64 laptop (run R-J of the [discovery record](../../architecture/triple-store-discovery.md)). **Branch:** `ccs/c9b3-profile-union`
**Plan:** [CCS plan](../plans/computable-contract-substrate.md), C9b3-Q5 (a)
**Findings:** TSD-41, TSD-Q20 (answered), TSD-Q21 (new). **Standard:** STD-279 (proposed, not ratified)
**Decisions:** [ADR-A105](../../architecture/decisions/ADR-A105-closure-declarations.md) and its 2026-10-12 addendum, which says a profile row names the union of its conditions' closures

## Invariant

A profile row's `?closures` names the union of the closures its conditions relied on, as one space-separated string, unbound when none was relied on. The same generated query returns the same decision and the same `?closures` for every record on rdflib and on Oxigraph. No aggregate in the profile query takes an expression that can error on a row of its group.

## Scope

In scope. The cause of the one failure of `check:mork-compilers-conformance` (TSD-41), a rewrite of `profile_select`'s `?closures`, a probe test of each engine, and the records. Out of scope. The default engine of `check:mork-compilers`, which stays rdflib and is the maintainer's decision under STD-274, any other backend, the row shape, and `ontology/`.

## The bisection

Query. `render_profile_query` for `ex:engineering-admission` in `set-reading-admissions.ttl`, 92 lines, over four records. Each step changes one thing in the one before it, or starts from the one named. Strings are shown without their IRI prefix. "Same" means every row agrees on both engines.

| Step | What we changed | rdflib 7.6.0 | Oxigraph 0.5.13 | Same |
|---|---|---|---|---|
| S0 | the generated query | `ada` closure, `ben` closure, `cai` closure, `dee` none | `ada` **none**, `ben` closure, `cai` closure, `dee` none | no |
| S1 | only the `no-medicine` branch in the `UNION` | agrees | agrees | yes |
| S2 | only the `stem-qualification` branch | agrees | agrees | yes |
| S3 | both branches' rows, with the outer `GROUP BY` and aggregates removed | agrees | agrees | yes |
| S4 | S0 with `GROUP_CONCAT` without `DISTINCT` | as S0 | as S0 | no |
| S5 | S0 with `GROUP_CONCAT(?relied)`, no `DISTINCT`, no `STR` | `ada` closure, `ben` closure, `cai` closure | `ada` none, `ben` **none**, `cai` **none** | no |
| S6 | S0 with `GROUP_CONCAT(DISTINCT COALESCE(STR(?relied), ""))` | `ada` `closure␣` | `ada` `␣closure` | strings differ by one space at one end, the set of closures is equal |
| S7 | a `UNION` of two sub-selects, one binding `?relied` for `ada`, one leaving it unbound, grouped by `?record` | `ada` `urn:c`, the rest `""` | all four unbound | no |
| S8 | S7 with the sub-selects as plain groups | as S7 | as S7 | no |
| S9 | no `UNION` and no sub-select, `VALUES ?s { 1 2 } OPTIONAL { VALUES (?s ?x) { (1 <urn:a>) } }`, `GROUP_CONCAT(STR(?x))` | `urn:a` | unbound | no |
| S10 | `VALUES ?x { <urn:a> UNDEF }`, `GROUP_CONCAT(DISTINCT STR(?x))`, no `GROUP BY` | `urn:a` | unbound | no |
| S11 | S10 with `GROUP_CONCAT(?x)` | `urn:a` | unbound | no |
| S12 | S10 with `GROUP_CONCAT(COALESCE(STR(?x), ""))` | `urn:a␣` | `urn:a␣` | yes |
| S13 | `VALUES ?x { <urn:a> <urn:b> }`, no unbound row | agrees | agrees | yes |
| S14 | `VALUES ?x { UNDEF }` | `""` | unbound | no |
| S15 | an empty group | `""` | `""` | yes |

S10 is the minimal query. It has no `UNION`, no sub-select, no `GROUP BY`, no `DISTINCT` (S11 drops it too) and no `?none` idiom. S3 shows the rows entering the aggregate are the same on both engines, so the sub-selects, the `UNION` and the `?none` binding are not at fault.

Other aggregates over `<urn:a>` and an unbound `?x` (S10's body), or `1` and an unbound `?x` where numeric.

| Aggregate | rdflib 7.6.0 | Oxigraph 0.5.13 | Same |
|---|---|---|---|
| `COUNT(?x)` | 1 | 1 | yes |
| `COUNT(*)` | 2 | 2 | yes |
| `SAMPLE(?x)` | `urn:a` | `urn:a` | yes |
| `COUNT(STR(?x))` | 2 | unbound | no |
| `COUNT(DISTINCT STR(?x))` | 2 | unbound | no |
| `SUM(?x)`, `AVG(?x)` | 1 | unbound | no |
| `MIN(?x)`, `MAX(?x)` | 1 | unbound | no |
| `MIN(STR(?x))`, `MAX(STR(?x))` | no row (TSD-10) | unbound | no |

The same probes, run on Oxigraph 0.5.11 for `GROUP_CONCAT(STR(?x))`, `SUM(?x)`, `COUNT(STR(?x))`, `COUNT(?x)` and the coalesced form, gave the same values as 0.5.13.

## The mechanism

SPARQL 1.1 Query §18.5.1 defines an aggregate over `Flatten(M)`, where `M` is a multiset of `ListEval` results and `ListEval` keeps an error ("`ListEval((unbound), μ) = (error)`"). `Count(M)` first removes the error elements. `Sum(M)` and `GroupConcat(M)` do not, and both are an error when one element is, so the aggregate's variable stays unbound (§18.5, Extend of the aggregate's value). `Min` and `Max` order the flattened values and the text does not say where an error sorts.

Oxigraph follows that for `GROUP_CONCAT`, `SUM` and `AVG`. In `lib/spareval/src/eval.rs` at v0.5.13, `AccumulatorWrapper::accumulate` for `Expression` and `DistinctExpression` sets `accumulator = None` the first time the argument's evaluator returns `None`, and `finish` then returns no value. `COUNT` over a bare variable takes `CountInternal`, which skips a missing value, so `COUNT(?x)` agrees with the specification. `COUNT` over any other expression is built in the same wrapper with a `CountAccumulator`, so a single error makes the count unbound where the specification says to count the rest. That is a departure on Oxigraph's side.

rdflib is the lenient engine. In `rdflib/plugins/sparql/aggregates.py`, `GroupConcat.update` returns without appending when the value is a `NotBoundError` ("skip UNDEF"), and `Sum`, `Average`, `Minimum` and `Maximum` skip the same way. `Counter` counts an erroring non-variable expression. Another error, for example division by zero, is appended to `GROUP_CONCAT` as its message.

Hypothesis, not proved. `MIN` and `MAX` on Oxigraph poison the same way by the same code path, which is consistent with the algebra's silence on an error, and we did not check what the Recommendation's ORDER BY ordering says of an error (TSD-Q21).

So the divergence in the generated query was not caused by the `UNION`, the nested sub-selects, `DISTINCT` or the `?none` idiom. A record whose condition rows all relied, or none did, agreed. A record that relied through one of two conditions (`ada`) had one row with a closure and one without, and the unbound row made Oxigraph's `GROUP_CONCAT` an error. rdflib skipped it.

Which engine follows the specification. Oxigraph for `GROUP_CONCAT`, `SUM` and `AVG`. Neither for `COUNT(expr)`, where the specification gives 1 and rdflib gives 2 and Oxigraph unbound.

## The fix

`profile_select` no longer aggregates `?relied` with `GROUP_CONCAT`. It computes one flag per distinct closure its conditions name, `SUM(IF(COALESCE(STR(?relied), "") = "<closure>", 1, 0))`, the idiom the query's other aggregates already use, and builds `?closureList` from the flags in IRI order with `SUBSTR(CONCAT(IF(?relied0 > 0, " <closure>", ""), ...), 2)`. `?closures` is that string, or unbound when empty, as before. The row shape and the meaning of `?closures` are unchanged. The order of the closures in the string is now the IRI order and no longer the store's scan order (TSD-19). The cost is stated in `profile_select`'s docstring (STD-020).

A coalesced `GROUP_CONCAT` would also agree on the set of closures, but the empty element lands at either end of the string by the order of the group, which differs between engines, and a trim is needed. The flags need none.

`engines.run_query` gained an optional `engine`, so a test of one engine's behaviour runs under either task. The module docstring and the two task descriptions in `mise.toml` no longer say the divergence is open.

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| PU-01 | `GROUP_CONCAT` over `<urn:a>` and an unbound `?x`, with and without `DISTINCT` and `STR` / each engine named / rdflib `urn:a`, Oxigraph unbound | L2 | + |
| PU-02 | `SUM`, `AVG`, `MIN` and `MAX` over `1` and an unbound `?x` / each engine named / rdflib 1, Oxigraph unbound | L2 | + |
| PU-03 | `COUNT(STR(?x))` and `COUNT(?x)` / each engine named / rdflib 2 and 1, Oxigraph unbound and 1 (the departure from §18.5.1.2) | L2 | + |
| PU-04 | `GROUP_CONCAT(DISTINCT COALESCE(STR(?x), ""))` / both engines / the same one closure | L2 | + |
| PU-05 | an empty group / both engines / `""` | L2 | + |
| PU-06 | the admissions profile / both engines, whichever the task sets / `ada`, `ben` and `cai` name the registry's closure, `dee` none | L2 | + − |
| PU-07 | the admissions profile with the stem binding under a second closure / both engines / `ben` and `cai` name both in IRI order, `ada` the first, `dee` none | L2 | + − |
| PU-08 | the generated text / render / no `GROUP_CONCAT` over `?relied` and exactly one coalesced `?relied` aggregate | L1 | − |
| PU-09 | the admissions profile with its closures removed / both engines / no row names a closure, four rows | L2 | + |

PU-01 to PU-03 pin what each engine does now, so a change in a store fails a test and sends us to TSD-41. The existing `RelianceTests` test (HQ6a2-08) is the third guard and now passes on Oxigraph.

## One command

```bash
mise run check:mork-compilers
mise run check:mork-compilers-conformance
mise exec -- python -m pytest tools/mork_compilers/src/mork_compilers/test_profile_union.py -q
mise run check:full-sweep
```

## Artefacts to inspect

- `tools/mork_compilers/src/mork_compilers/sparql_backend.py`: `profile_select`, its docstring and the `closures`, `flags` and `listed` lines
- `tools/mork_compilers/src/mork_compilers/engines.py`: `run_query`'s `engine` argument and the module docstring
- `tools/mork_compilers/src/mork_compilers/test_profile_union.py`: PU-01 to PU-09
- `docs/architecture/triple-store-discovery.md`: TSD-41, §7.6, TSD-Q20 and TSD-Q21
- `docs/architecture/efficient-queries-and-shapes.md`: R9 and its row in §2.1
- `docs/developer/standards.md`: STD-279
- `requirements-lock.txt`: `pyoxigraph==0.5.13`, see the handoff

## Deliberate non-coverage

- **The default engine of `check:mork-compilers`.** Both tasks now pass, which STD-274 asks for before a default changes. Whether to flip it is the maintainer's decision. Our recommendation is in the handoff.
- **Speed.** The new query is not timed against the old one, so the cost in the docstring is a count of operations and any speed claim is a hypothesis (STD-176).
- **The seven reasoner tests** of `check:mork-compilers` skip, since the reasoning test kit is not built on this machine (`mise run bootstrap:reasoning-testkit`).
- **`MIN` and `MAX`** on a group with an error, and an upstream report for `COUNT(expr)` (TSD-Q21).
- **Other backends and `tools/phase8_conformance.py`.** The SHACL backend wraps `profile_select` and takes the change with it. It projects `$this` only, so `?closures` is not read there.

## Handoff

**Built.**

- The cause of TSD-41, in the discovery record, with the minimal query, both engines' source and the Recommendation's text, and TSD-Q20 answered.
- A rewrite of `?closures` in `profile_select` without `GROUP_CONCAT`, with its cost.
- `test_profile_union.py`, 9 tests in 5 probes and 4 profile tests, and `engines.run_query(engine=...)`.
- R9 in the efficient-queries record and STD-279 (Ratified `no`) in the standard register.
- A correction in skill `lattice-testing` (its STD-274 paragraph said no cause was traced) and in the two `check:mork-compilers` task descriptions.

**Deviation: the lock.** `requirements-lock.txt` pinned `pyoxigraph==0.5.11` while `tools/testing/oxigraph` requires `>=0.5.13,<0.6` since the ledger benchmarks commit, so `mise run bootstrap:python` failed with `ResolutionImpossible` on a fresh checkout. We changed the pin to `0.5.13` to bootstrap, in a commit of its own so it can be dropped or taken to `ccs-trunk` first. The last full sweep ran on 0.5.11, installed over it with `pip install --no-deps`, because 0.5.13 fails the persistence probe described under Results. Which version the lock should name is the maintainer's decision.

**Recommendation on the default engine.** Flip `check:mork-compilers` to Oxigraph in a separate change, now that the suite passes on both. STD-153 and ADR-A125 make it the default for suites that execute generated SPARQL, rdflib stays covered by `check:mork-compilers-conformance`, and the one query that depended on rdflib's leniency is fixed. Two cautions. Any new generated aggregate must follow STD-279 or the divergence returns. And the recommendation rests on 119 passing tests with seven reasoner tests skipped here, which should run once before the flip.

**Draft upstream issue, not filed.** For Oxigraph (`oxigraph/oxigraph`).

> Title: `COUNT(expr)` returns unbound when the expression errors on one solution, SPARQL 1.1 §18.5.1.2 removes the error
>
> Query, with pyoxigraph 0.5.13 (and 0.5.11) on an empty store: `SELECT (COUNT(STR(?x)) AS ?g) WHERE { VALUES ?x { <urn:a> UNDEF } }`
>
> Expected: `?g` is `1`. `Count(M)` is defined as `N = Flatten(M)`, "remove error elements from N", `card[N]`, and `STR(?x)` is an error where `?x` is unbound.
>
> Actual: `?g` is unbound. `COUNT(?x)` returns `1`, since a bare variable takes the internal evaluator. In `lib/spareval/src/eval.rs`, `AccumulatorWrapper::Expression` sets its accumulator to `None` when the evaluator returns `None`, which suits `SUM` and `GROUP_CONCAT` and not `COUNT`.
>
> Related and not a defect. `GROUP_CONCAT`, `SUM` and `AVG` over the same solutions are unbound on Oxigraph, which follows the `Flatten` and `CONCAT` definitions. Other engines skip the solution.

**What to check first.** `profile_select`'s `closures`, `flags` and `listed` lines against the generated text for the admissions profile. Then PU-06 and PU-07 on Oxigraph.

## Results

Run on this branch, `ccs/c9b3-profile-union`, on the machine above.

| Command | Result |
|---|---|
| `mise run check:mork-compilers-conformance`, before the fix | `1 failed, 118 passed, 7 skipped, 2 subtests passed in 8.94s`, the failure `RelianceTests::test_a_profile_row_names_the_union_of_its_conditions_closures` |
| `mise run check:mork-compilers-conformance`, after the fix | `128 passed, 7 skipped, 19 subtests passed in 8.30s` on pyoxigraph 0.5.13, and `128 passed, 7 skipped, 19 subtests passed in 8.03s` on 0.5.11 |
| `mise run check:mork-compilers`, after the fix | `128 passed, 7 skipped, 19 subtests passed in 11.58s` on 0.5.13 |
| `mise exec -- python -m pytest tools/mork_compilers/src/mork_compilers/test_profile_union.py -q` | `9 passed, 17 subtests passed in 0.55s` |
| `mise run build:knowledge` | built, STD-279 and the new TSD-41 text found by `graph:ask -- find` |
| `mise run check:identifiers` | `identifier check passed: every mention of 856 resolvable identifiers resolves`, 9 passed |
| `mise run check:deny-terms` | `deny terms: 0 finding(s) against 5 entries` |
| `mise run hooks:run`, over the staged files | `deny-terms`, `agent-guidance`, `catalogue`, `links`, `site-sections`, `writing`, `wrapping`, `published-decisions` ok |
| `mise run check:full-sweep` with pyoxigraph 0.5.13 | `1 of 17 checks failed (3m 41s)`, the failure `check:persistence`, `1 failed, 3975 passed`, `test_h2_4b_t4_p3_a_graph_variable_bound_outside_does_not_make_the_query_scan_every_graph[oxigraph]`, not related to this unit (below) |
| `mise run check:full-sweep` with pyoxigraph 0.5.11 | `All 17 checks passed (3m 32s)`, including `check:mork-compilers`, `check:persistence` 3976 passed and `check:ontology-catalog` 1122 passed, 79 skipped |

The 119 passed of the first conformance run became 128 with `test_profile_union.py`. The seven skips are the reasoner tests.

**An unrelated failure on pyoxigraph 0.5.13.** `test_h2_4b_t4_p3` in `check:persistence` measures the ratio of a query's time over 100 graphs to its time over 1 and requires under 8. On 0.5.13 it measured 82.0 on three runs and failed each time, and with 0.5.11 first on the import path it passed. So on 0.5.13 `BIND(<g>) OPTIONAL { GRAPH ?g { ?s ?p ?o } }` appears to scan every graph, which is a cost difference of the kind TSD-40 records in the other direction. We did not record it as a finding, since the probe's value on each version was not measured here beyond that. It is for the persistence unit. This unit's tests pass on both versions.

## Adversarial probes

Our pick, as the maintainer authorised autonomous work. We restored the pre-change `profile_select` from `HEAD`, ran the tests under the default engine, and restored the new file from a copy (compared byte for byte).

| Artefact | Defect introduced | Caught by |
|---|---|---|
| `sparql_backend.py` `profile_select` | the old `GROUP_CONCAT(DISTINCT STR(?relied))` template | under `check:mork-compilers`, rdflib's default, which the old template passed before: 3 fail, PU-06 on Oxigraph, PU-07 on Oxigraph and PU-08. Under `check:mork-compilers-conformance` the existing HQ6a2-08 test fails as before |

The old template ran with `MORK_SPARQL_ENGINE=rdflib` over the whole `tools/mork_compilers` directory gave `3 failed, 127 passed, 7 skipped, 17 subtests passed in 17.51s`, and over `test_profile_union.py` alone `3 failed, 8 passed, 15 subtests passed in 0.52s`. With the new template restored, the same file gave `9 passed, 17 subtests passed in 0.55s`.

## Acceptance

Not yet accepted. The maintainer's merge into `ccs-trunk` is the sign-off. STD-279 is proposed and stays Ratified `no` until the maintainer ratifies it.
