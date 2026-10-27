<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS C9b3, aggregates over rows with no value

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** a macOS arm64 laptop (run R-K of the [discovery record](../../architecture/triple-store-discovery.md)). **Branch:** `ccs/c9b3-aggregate-errors`
**Plan:** [CCS plan](../plans/computable-contract-substrate.md), C9b3-Q5 (a), a follow-up to [the profile union pack](computable-contract-substrate-c9b3-profile-union.md)
**Findings:** TSD-43 (new), TSD-41 (extended), TSD-Q21 (answered in part), TSD-Q23 (new). **Standards under review:** STD-279 and rule R9, not edited, a replacement is drafted below
**Decisions:** none taken. The proposed rule changes what a generated query may say, so it is the lead's and the maintainer's to decide

## Invariant

For each of the 13 forms of aggregate in TSD-43 and each of seven row states, the discovery record says what SPARQL 1.1 §18.5.1 prescribes and what rdflib 7.6.0, Oxigraph 0.5.13 and Jena ARQ 5.1.0 return. The suite pins the first two. A form of remedy is recommended in the draft rule below only where its meaning for the aggregate is stated and its result on every engine is known.

## Scope

In scope. The evidence matrix, the specification reading per cell, four remedies probed on the three engines, the audit of every generated aggregate in `tools/mork_compilers` and `tools/persistence`, a draft replacement for STD-279 and R9. Out of scope. Editing STD-279, R9 or any generated query, the default engine of any task, Fuseki (TSD-Q12), and aggregates over a property path or a `VALUES` block that the matrix does not model.

## The matrix

The tables are in TSD-43 and are not repeated. The cases are `aggregate_error_cases.py`, the recorded results `aggregate_error_expected.py`, and the engine probes `test_aggregate_errors.py` (AE-01 to AE-22).

Conformance to §18.5.1 over the 91 cells of the 13 aggregates and 7 states, where a cell that the text leaves open counts as conforming for either answer.

| Engine | Conforming cells | Where it departs |
|---|---|---|
| rdflib 7.6.0 | 54 of 91 | skips a row for `SUM`, `MIN`, `GROUP_CONCAT` and `AVG`. Counts it for `COUNT(expr)`. Raises for `SUM` over an IRI. Returns a row for a grouped query over no rows. `STR` of a blank node is a string |
| Oxigraph 0.5.13 | 84 of 91 | `COUNT(expr)` and `COUNT(DISTINCT expr)` unbound over a row that errors (six cells). `AVG` over an all-unbound group (one cell) |
| Jena ARQ 5.1.0 | 84 of 91 | `STR` of a blank node is a string (five cells, in `COUNT(expr)`, `COUNT(DISTINCT expr)` and the three `GROUP_CONCAT` forms). `AVG` over an all-unbound group. `GROUP_CONCAT(DISTINCT)` over an empty group |

`MIN` over a group with a row with no value is unbound on the specification's ordering and on the poisoning reading, so Oxigraph and Jena conform and rdflib does not (TSD-Q21 narrowed). `MAX` is the open cell. Where §15.1 orders no value lowest and an error element is no value, `Max` is `2`, which is rdflib's answer. Where an error element poisons as it does for `SUM`, `Max` is unbound, which is Oxigraph's and Jena's. The text does not say.

## The remedies

The table gives the result in each state for each form. A slash separates rdflib, Oxigraph and Jena where they differ. `raises` is a failed query on rdflib.

| Remedy | Form | all bound | one unbound | one IRI | one blank node | all unbound | empty |
|---|---|---|---|---|---|---|---|
| a filter | `COUNT(?x)` | `2` | `2` | `3` | `3` | `0` | `0` |
| a filter | `COUNT(expr)` | `2` | `2` | `3` | `3` / `unbound` / `3` | `0` | `0` |
| a filter | `COUNT(*)` | `2` | `2` | `3` | `3` | `0` | `0` |
| a filter | `COUNT(DISTINCT ?x)` | `2` | `2` | `3` | `3` | `0` | `0` |
| a filter | `COUNT(DISTINCT expr)` | `2` | `2` | `3` | `3` / `unbound` / `3` | `0` | `0` |
| a filter | `SUM` | `3` | `3` | `raises` / `unbound` / `unbound` | `raises` / `unbound` / `unbound` | `0` | `0` |
| a filter | `AVG` | `1.5 dec` | `1.5 dec` | `1.5 dec` / `unbound` / `unbound` | `1.5 dec` / `unbound` / `unbound` | `0` | `0` |
| a filter | `MIN` | `1` | `1` | `urn:a` / `<urn:a>` / `<urn:a>` | `_:b` | `unbound` | `unbound` |
| a filter | `MAX` | `2` | `2` | `2` | `2` | `unbound` | `unbound` |
| a filter | `SAMPLE` | `a member` | `a member` | `a member` | `a member` | `unbound` | `unbound` |
| a filter | `GROUP_CONCAT(expr)` | `1 2` | `1 2` | `1 2 urn:a` | `1 2 _:b` / `unbound` / `1 2 _:b` | `""` | `""` |
| a filter | `GROUP_CONCAT(?x)` | `1 2` / `unbound` / `1 2` | `1 2` / `unbound` / `1 2` | `1 2 urn:a` / `unbound` / `1 2 urn:a` | `1 2 _:b` / `unbound` / `1 2 _:b` | `""` | `""` |
| a filter | `GROUP_CONCAT(DISTINCT expr)` | `1 2` | `1 2` | `1 2 urn:a` | `1 2 _:b` / `unbound` / `1 2 _:b` | `""` / `""` / `unbound` | `""` / `""` / `unbound` |
| a2 filter numeric | `SUM` | `3` | `3` | `3` | `3` | `0` | `0` |
| a2 filter numeric | `AVG` | `1.5 dec` | `1.5 dec` | `1.5 dec` | `1.5 dec` | `0` | `0` |
| a2 filter numeric | `MIN` | `1` | `1` | `1` | `1` | `unbound` | `unbound` |
| a2 filter numeric | `MAX` | `2` | `2` | `2` | `2` | `unbound` | `unbound` |
| b coalesce | `SUM(COALESCE(?x, 0))` | `3` | `3` | `raises` / `unbound` / `unbound` | `raises` / `unbound` / `unbound` | `0` | `0` |
| b coalesce | `AVG(COALESCE(?x, 0))` | `1.5 dec` | `1 dec` | `1.5 dec` / `unbound` / `unbound` | `1.5 dec` / `unbound` / `unbound` | `0 dec` | `0` |
| b coalesce | `MAX(COALESCE(?x, 0))` | `2` | `2` | `2` | `2` | `0` | `unbound` |
| b coalesce | `COUNT(COALESCE(STR(?x), ''))` | `2` | `3` | `3` | `3` | `2` | `0` |
| b coalesce | `GROUP_CONCAT(COALESCE(STR(?x), ''))` | `1 2` | ` 1 2` | `1 2 urn:a` | `1 2 _:b` / ` 1 2` / `1 2 _:b` | ` ` | `""` |
| b coalesce | `GROUP_CONCAT(DISTINCT COALESCE(STR(?x), ''))` | `1 2` | ` 1 2` | `1 2 urn:a` | `1 2 _:b` / ` 1 2` / `1 2 _:b` | `""` | `""` / `""` / `unbound` |
| c detect | `IF(COUNT(?x) = COUNT(*), SUM(COALESCE(?x, 0)), 1/0)` | `3` | `unbound` | `raises` / `unbound` / `unbound` | `raises` / `unbound` / `unbound` | `unbound` | `0` |
| c detect | `IF(COUNT(?x) = COUNT(*), SUM(?x), 1/0)` | `3` | `unbound` | `raises` / `unbound` / `unbound` | `raises` / `unbound` / `unbound` | `unbound` | `0` |
| c detect | `IF(COUNT(?x) = COUNT(*), AVG(COALESCE(?x, 0)), 1/0)` | `1.5 dec` | `unbound` | `1.5 dec` / `unbound` / `unbound` | `1.5 dec` / `unbound` / `unbound` | `unbound` | `0` |
| c detect | `IF(COUNT(?x) = COUNT(*), MIN(?x), 1/0)` | `1` | `unbound` | `urn:a` / `<urn:a>` / `<urn:a>` | `_:b` | `unbound` | `unbound` |
| c detect | `IF(COUNT(?x) = COUNT(*), MAX(?x), 1/0)` | `2` | `unbound` | `2` | `2` | `unbound` | `unbound` |
| c detect | `IF(COUNT(?x) = COUNT(*), GROUP_CONCAT(COALESCE(STR(?x), '')), 1/0)` | `1 2` | `unbound` | `1 2 urn:a` | `1 2 _:b` / ` 1 2` / `1 2 _:b` | `unbound` | `""` |
| c detect | `COUNT(*) - COUNT(?x)` | `0` | `1` | `0` | `0` | `2` | `0` |
| c detect | `COUNT(*) - COUNT(STR(?x))` | `0` | `0` / `unbound` / `1` | `0` | `0` / `unbound` / `0` | `0` / `unbound` / `2` | `0` |
| c detect | `COUNT(*) - COUNT(?x) (a boolean)` | `true^boolean` | `false^boolean` | `true^boolean` | `true^boolean` | `false^boolean` | `true^boolean` |
| d sub-select | `SUM(?v) over BIND(?x + 0)` | `3` | `3` / `unbound` / `unbound` | `3` / `unbound` / `unbound` | `3` / `unbound` / `unbound` | `0` / `unbound` / `unbound` | `0` |
| d sub-select | `GROUP_CONCAT(?v) over BIND(STR(?x))` | `1 2` | `1 2` / `unbound` / `unbound` | `1 2 urn:a` | `1 2 _:b` / `unbound` / `1 2 _:b` | `""` / `unbound` / `unbound` | `""` |
| d sub-select | `COUNT(?v) over BIND(STR(?x))` | `2` | `2` | `3` | `3` / `2` / `3` | `0` | `0` |
| d sub-select | `SUM(?v) over BIND(?x + 0), FILTER(BOUND(?v))` | `3` | `3` | `3` | `3` | `0` | `0` |

Reading. A filter turns a group whose rows all go into an empty group, so `SUM` and `AVG` over it become 0 and `MIN` and `MAX` unbound, and `COUNT(*)` no longer counts the removed rows. Under `GROUP BY ?s` it removes the group. The three-group probe (AE-19 to AE-22) shows a subject with no value absent after the filter, `0` after a coalesce, unbound after the detect, and `0` or unbound from the bare `SUM` by engine.

## Audit of the generated aggregates

The states an aggregate can meet are those its argument can have in the group. "Correct" means the result is the one the query's meaning needs on rdflib and on Oxigraph, by the matrix.

| # | Where | Aggregate | Row states it can meet | Correct on both |
|---|---|---|---|---|
| 1 | `sparql_backend.py` `_bound_interval_select`, the inner group | `COUNT(DISTINCT ?value)` | all unbound (a subject with no value), one or several bound | yes. `COUNT(DISTINCT ?x)` is 0 and ignores unbound on all three engines |
| 2 | the same group | `SAMPLE(?value)`, `SAMPLE(?number)`, `SAMPLE(?unitOfValue)` | the optional `?number` and `?unitOfValue` unbound on some rows and bound on others, all unbound | yes for a group of one distinct value, which is the only case the decision reads (`?candidates = 1`). Where several rows of that value carry different units, `SAMPLE` returns a different member on each engine (TSD-43 shows rdflib and Oxigraph choosing differently), so the unit read can differ. Not demonstrated on the generated query |
| 3 | `concept_select`'s inner group | `COUNT(DISTINCT ?offered)`, `SAMPLE(?offered)` | all unbound, one or several bound | yes, as 1 and 2 |
| 4 | `_read_set`, the per-value group | `SUM(IF(?decision = "Permitted", 1, 0))` and the `Denied` and `Undetermined` flags | `?decision` bound on every per-value row by construction | conditionally. The argument is `IF(?decision = ..., 1, 0)`, so a row whose `?decision` is unbound makes the aggregate an error on Oxigraph and Jena and a skipped row on rdflib. `?decision` is unbound when the containment test errors, for example `?candLower >= 5` where `?candLower` is a string literal. The probe `SUM(IF(?d = "Permitted", 1, 0))` over `VALUES ?c { 7 "abc" }` with `BIND(IF(?c >= 5, "Permitted", "Denied") AS ?d)` gave `2` on rdflib (it compares a string with a number without error) and unbound on Oxigraph. The existing suite does not reach it |
| 5 | `_read_set` | `SUM(IF(?decision = "Undetermined" && COALESCE(STR(?diagnostic), "") = ..., 1, 0))` for `?missing` | as 4, and `?diagnostic` unbound on most rows, which it coalesces | as 4. `error && false` is false, so only a row that is unbound and whose second operand is true errors |
| 6 | `_read_set` | `MAX(IF(?decision = "Undetermined", COALESCE(STR(?diagnostic), ""), ""))` for `?reason` | as 4 | as 4. The neutral element `""` is right for `MAX` of strings, and the diagnostic is coalesced |
| 7 | `profile_select`, the record group | `SUM(IF(COALESCE(?outcome, "") = "Permitted", 1, 0))` and the two others | `?outcome` unbound for a record with no answer from any condition (all unbound), bound otherwise | yes. A missing answer counts as none of the outcomes, and the missing conditions are counted separately by item 9 and `?missing`, which is the detect form of remedy (c) |
| 8 | `profile_select` | one `SUM(IF(COALESCE(STR(?relied), "") = "<closure>", 1, 0))` per closure | `?relied` unbound for a condition that relied on no closure | yes (TSD-41's fix). The neutral element is right, since a row with no reliance contributes nothing |
| 9 | `profile_select` | `COUNT(DISTINCT ?condition)` | all unbound for a record with no condition rows | yes, 0 on all three engines |
| 10 | `profile_select` | `MAX(COALESCE(STR(?reason), ''))` for `?conditionDiagnostic` | `?reason` unbound for conditions that are not Undetermined | yes. The empty string is below every IRI string |
| 11 | `tools/persistence` `builders.py`, `_duplicated_claims` and `_key_claim_duplicate_audit` | `COUNT(?owner)`, `GROUP_CONCAT(STR(?owner); " ")`, `MIN(STR(?owner))` | `?owner` bound by the group's triple pattern in every row. A blank-node owner would make `STR` an error, so unbound on Oxigraph and Jena and a label on rdflib | yes for IRI owners, which the builders write. A claim written by hand with a blank-node owner would diverge |
| 12 | `builders.py`, the fork, revision and transaction audits | `COUNT(DISTINCT ?txn)`, `COUNT(DISTINCT ?rev)` | bound by the triple pattern | yes |
| 13 | `builders.py`, `_gap_scan_audit` | `COUNT(DISTINCT ?seq)` | `?seq` unbound for a version row with no receipt in range (all unbound), bound otherwise | yes, 0 on all three engines. Every audit is grouped and projects only unbound-able variables with its counts, so rdflib's extra row for a grouped query over no rows is dropped by TSD-10 and `HAVING` never sees it |
| 14 | `ir_render.py` `_projected_bound` | the rule that only `COUNT` is bound over an empty group and any other aggregate needs a `GROUP BY` and a bound argument | the checker, not a query | consistent with the matrix. It refuses the forms in which an aggregate meets an unbound row, so a generated operation cannot contain one. A grouped `COUNT` over no rows is bound on Oxigraph and Jena (there is no row) and absent or unbound on rdflib, which only matters where a bound variable is also projected |
| 15 | `platform/authoring-service` `wording-poc-shapes.ttl` (outside the two tools, found by the search) | `COUNT(?p)`, `COUNT(DISTINCT ?i)`, `MAX(?i)` and `COUNT(DISTINCT ?part)` | `?p` and `?i` unbound together, since one `OPTIONAL` group binds both | yes. `MAX(?i)` is unbound only when the count is 0, and the filter tests `?n > 0` first |

The profile query is correct on both engines except through item 4 to 6, which share one latent dependency on `?decision` never being unbound. No other aggregate in the two tools meets a row it does not coalesce, count safely or bind in the pattern.

## Draft replacement for STD-279 and R9

This is a proposal. We have not edited STD-279, R9 or its row in the table of §2.1.

> **R9 (draft). Say what a row with no value means before an aggregate meets it.**
>
> **Do.** An aggregate whose argument can be unbound, or can error, on a row of its group (an `OPTIONAL`, a branch of a `UNION`, `STR` of a blank node, arithmetic on a term that is not a number) is written with one of three meanings for that row, chosen from what the query is for.
>
> 1. The row is not a member of the group. Filter it out inside the group with a test of the type the aggregate needs (`FILTER(isNumeric(?x))` for `SUM`, `AVG`, `MIN` and `MAX`), since `BOUND` alone leaves an IRI. State what the filter does to `COUNT(*)`, and to the group under `GROUP BY` where every row of a group goes.
> 2. The row contributes the aggregate's neutral element, where one exists and absence contributes nothing. `SUM(COALESCE(?x, 0))`, `MAX(COALESCE(?x, floor))` where `floor` is below every value, a flag `SUM(IF(COALESCE(?x, "") = "k", 1, 0))`. `AVG`, `MIN` and `GROUP_CONCAT` have none. Build a list from one flag per known member and not from `GROUP_CONCAT(COALESCE(...))`, which leaves an empty element and a stray separator.
> 3. The row makes the answer unknown. Detect it and propagate it, as `IF(COUNT(?x) = COUNT(*), <aggregate over the coalesced argument>, 1/0)`, or project `COUNT(*) - COUNT(?x)` beside the aggregate for the consumer to read. Use `COUNT(?x)` and `COUNT(*)` for the test and never `COUNT(<expression>)`.
>
> **Don't.** Pass a bare optional variable, or an expression that can error, to `SUM`, `AVG`, `MIN`, `MAX` or `GROUP_CONCAT`, or to `COUNT` as an expression, and rely on what the engine does with the row.
>
> **Why.** Under SPARQL 1.1 §18.5.1 `COUNT` removes an error row and `SUM`, `AVG` and `GROUP_CONCAT` are errors over one, and `MIN` is unbound, so the variable is unbound. rdflib skips the row, `COUNT(expr)` differs on every engine, and a coalesce can change what the group means (TSD-43). **Evidence:** Source, Observed and Documented, on rdflib 7.6.0, Oxigraph 0.5.13 and Jena ARQ 5.1.0. **Scope.** a correctness rule for every engine.

The draft is a standard in the shape of the existing ones, and the clauses are each justified by a scenario.

| Clause | Scenario that justifies it | Evidence |
|---|---|---|
| 1, filter, with a type test | `SUM` of a numeric attribute over data where some rows hold an IRI or a string. `FILTER(BOUND(?x))` leaves the IRI, so `SUM` is unbound on Oxigraph and Jena and raises on rdflib. `isNumeric` agrees on every engine in every state | AE-03, AE-04 |
| 1, state what it does to `COUNT(*)` and the group | a per-subject total over subjects some of which have no value. The filter removes the subject, a coalesce keeps it at 0 and a detect keeps it unbound | AE-05, AE-19 |
| 2, neutral element, only where absence contributes nothing | the profile query's per-outcome and per-closure flags. A condition that did not rely on a closure adds nothing to its flag, and the missing conditions are counted elsewhere | audit items 7 and 8, PU-06 to PU-09 |
| 2, no neutral element for `AVG` and `MIN` | an average of the values a record has. `AVG(COALESCE(?x, 0))` over 1, 2 and a missing row is 1 and not 1.5, since the denominator grows | AE-07 |
| 2, no neutral element for `GROUP_CONCAT` | a list of the values a record has. The coalesced form gives an empty element and a stray separator on every engine | AE-08 |
| 2, a coalesce cannot tell missing from zero | a weight that must be reported Undetermined when it is missing. `SUM(COALESCE(?w, 0))` equals the filtered sum, so the missing weight is invisible | AE-06 |
| 3, detect and propagate | the same weight. `IF(COUNT(?w) = COUNT(*), SUM(COALESCE(?w, 0)), 1/0)` is the sum when none is missing and unbound when one is, on all three engines, and `0` for an empty group | AE-12, AE-13, AE-21 |
| 3, test with `COUNT(?x)` and `COUNT(*)` only | `COUNT(*) - COUNT(STR(?x))` is 0 on rdflib, unbound on Oxigraph and 1 on Jena for one missing row. `COUNT(*) - COUNT(?x)` is 1 on all three | AE-10, AE-11 |
| Don't, for `MIN` and `MAX` | a bound over a group with a missing row. `MIN` is unbound on the specification and on two engines and skipped on rdflib. `MAX` is open (TSD-Q21) and differs by engine, so a query must not depend on it, and `MIN` and `MAX` take clause 1 or 3 | matrix, AE-01 |
| Don't, as an expression to `COUNT` | `COUNT(STR(?x))`. rdflib counts the row, Oxigraph is unbound, Jena removes it | AE-16 |

Open questions on the draft, for the lead and the maintainer.

- Whether clause 1's filter is acceptable where it drops a group, or whether a query that needs the group must take clause 2 or 3.
- Whether the profile query's dependency on `?decision` (audit items 4 to 6) is in scope for a change, since a fix alters generated SPARQL. It would be `COALESCE(?decision, "")` in the three `IF` tests, and it would change what a malformed value yields from "depends on the engine" to "counted as none of the outcomes", which may need a design decision.
- Whether `MAX` over a group with a missing row should be specified as an engine-independent behaviour of ours, by always taking clause 1 or 3.

## Draft upstream report, not filed

Oxigraph, `COUNT` over an expression that errors on one row.

```sparql
SELECT (COUNT(STR(?x)) AS ?n) WHERE { VALUES ?x { <urn:a> UNDEF } }
```

SPARQL 1.1 §18.5.1.2 removes error elements before counting, so `n` is 1. Oxigraph 0.5.13 leaves `?n` unbound, and `COUNT(?x)` over a bare variable gives 1. Jena ARQ 5.1.0 gives 1. Cause in `AccumulatorWrapper` in `lib/spareval/src/eval.rs`, where an expression that evaluates to nothing sets the accumulator to `None` for every aggregate, `COUNT` included.

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AE-01 | all 352 cases / each engine / the recorded result | L2 | + |
| AE-02 | the matrix / counted / 13 aggregates in 7 states | L1 | + |
| AE-03 | `FILTER(isNumeric(?x))` and `SUM`, `AVG`, `MIN`, `MAX` / rdflib, Oxigraph, Jena / one answer in every state (rdflib's grouped-empty row aside) | L2 | + |
| AE-04 | `FILTER(BOUND(?x))` and `SUM` over an IRI / each engine / unbound, unbound, a raise | L2 | − |
| AE-05 | the filter and `COUNT(*)` / each engine / 3 becomes 2 | L2 | + |
| AE-06 | `SUM(COALESCE(?x, 0))` over one missing row / each engine / 3, as the filtered sum | L2 | + |
| AE-07 | `AVG(COALESCE(?x, 0))` against the filtered `AVG` / each engine / 1 and 1.5 | L2 | + |
| AE-08 | a coalesced `GROUP_CONCAT` / each engine / an empty element and a stray separator | L2 | + |
| AE-09 | `SUM(COALESCE(?x, 0))` over an IRI / Oxigraph / unbound | L2 | − |
| AE-10 | `COUNT(*) - COUNT(?x)` / all engines / 0, 1, 0, 0, 2, 0 | L2 | + |
| AE-11 | `COUNT(*) - COUNT(STR(?x))` / each engine / 0, unbound, 1 | L2 | − |
| AE-12 | the guarded sum and max / each engine / unbound when a row is missing | L2 | + − |
| AE-13 | the guarded sum over an empty group / each engine / 0 | L2 | + |
| AE-14 | `SUM(?v)` over a sub-select's `BIND` / each engine / unbound on Oxigraph, 3 on rdflib | L2 | − |
| AE-15 | the same with `FILTER(BOUND(?v))` / both engines / one answer | L2 | + |
| AE-16 | `COUNT(STR(?x))` over a missing row / each engine / 3, unbound, 2 | L2 | − |
| AE-17 | a grouped query over no rows / each engine / a row on rdflib, none elsewhere | L2 | − |
| AE-18 | `SUM` over an IRI / rdflib / raises | L2 | − |
| AE-19 | three groups, one with no value / each engine / the filter drops it, the coalesce keeps it at 0 | L2 | + |
| AE-20 | the same, bare `SUM` / each engine / 0 on rdflib, unbound elsewhere | L2 | − |
| AE-21 | the same, the guarded sum / each engine / unbound for the group with no value | L2 | + |
| AE-22 | the same, `AVG(COALESCE(?x, 0))` / each engine / 0 | L2 | + |

AE-01 pins every cell, so a change in either engine fails it and sends us to TSD-43. The Jena column is recorded and is checked by the tests that read it (AE-03, AE-04, AE-11, AE-16, AE-17, AE-20 to AE-22), not run.

## One command

```bash
MORK_SPARQL_ENGINE=rdflib mise exec -- python -m pytest tools/mork_compilers/src/mork_compilers/test_aggregate_errors.py -q
MORK_SPARQL_ENGINE=oxigraph mise exec -- python -m pytest tools/mork_compilers/src/mork_compilers/test_aggregate_errors.py -q
mise run check:mork-compilers
mise run check:mork-compilers-conformance
```

The tests name their engines, so they pass under either task and either `MORK_SPARQL_ENGINE`.

## Artefacts to inspect

- `tools/mork_compilers/src/mork_compilers/aggregate_error_cases.py`: the states, the 13 aggregates, the four remedies and the three-group probe
- `tools/mork_compilers/src/mork_compilers/aggregate_error_expected.py`: the recorded results on three engines
- `tools/mork_compilers/src/mork_compilers/test_aggregate_errors.py`: AE-01 to AE-22
- `docs/architecture/triple-store-discovery.md`: TSD-43, the edits to TSD-41, TSD-Q21, TSD-Q23 and run R-K
- the draft above, which replaces nothing yet

## Deliberate non-coverage

- **Fuseki.** Jena ARQ runs in process from a Java program. Fuseki may differ (TSD-Q12).
- **Oxigraph and Jena source for the new cells.** Oxigraph's accumulators are as TSD-41 read them. Jena's source was not read, so its column is Observed only.
- **Several groups for every aggregate.** The three-group probe uses `SUM`, `AVG`, `COUNT(*)` and `MAX`.
- **Speed.** Nothing is timed.
- **Changing any generated query.** Audit items 2 and 4 to 6 are reported and not changed.

## Handoff

**Built.** The matrix and remedies as a probe module on rdflib and Oxigraph with Jena recorded, TSD-43, the TSD-41 and TSD-Q21 edits, and this pack with the draft rule. **Placement:** T0 and T1, public. Probes of triple-store behaviour and generic SPARQL, nothing insurance-specific.

## Verification results

Run on 2026-10-27 on this branch, after the last edit of the code and the records.

| Command | Result |
|---|---|
| `mise exec -- python -m pytest tools/mork_compilers/src/mork_compilers/test_aggregate_errors.py -q` | `22 passed, 728 subtests passed in 1.48s`. Also run with `MORK_SPARQL_ENGINE=rdflib` and `oxigraph` and `PYTHONHASHSEED=3` or `7`, all passed |
| `mise run check:mork-compilers` (rdflib, the default on this branch) | `171 passed, 7 skipped, 753 subtests passed in 13.13s` |
| `mise run check:mork-compilers-conformance` (Oxigraph) | `171 passed, 7 skipped, 753 subtests passed in 9.26s` |
| `mise run build:knowledge` | `knowledge index built at .build/knowledge/store` |
| `mise run check:identifiers` | `identifier check passed: every mention of 859 resolvable identifiers resolves`, 9 passed |
| `mise run check:deny-terms` | `deny terms: 0 finding(s) against 5 entries` |

The seven skips are the reasoner tests (`mise run bootstrap:reasoning-testkit`). The Jena column was produced by the appendix program on 2026-10-27 and is not part of any task.

## Acceptance

Not yet accepted. The lead's review and the maintainer's merge into `ccs-trunk` are the sign-off. STD-279 and R9 are untouched.

## Appendix: the Jena runner

A single-file Java program, run with the classpath of `benchmark/ledger-store-comparison` (Jena 5.1.0). It reads the cases and states that `python -m mork_compilers.aggregate_error_cases DIR` writes, and prints one line per case with the number of rows, the lexical form and datatype of the last row's `?g`, and every row's `?s` and `?g`.

```bash
mise exec -- python -m mork_compilers.aggregate_error_cases /tmp/aggregate-cases
cd benchmark/ledger-store-comparison
mise exec -- mvn -o -q dependency:build-classpath -Dmdep.outputFile=/tmp/jena.cp
mise exec -- java -cp "$(cat /tmp/jena.cp)" Probe.java /tmp/aggregate-cases > /tmp/jena.out
```

```java
import java.nio.file.*;
import org.apache.jena.query.*;
import org.apache.jena.rdf.model.*;

/** Runs the cases of aggregate_error_cases.py on Jena ARQ. Usage: java -cp CP Probe.java DIR. Prints id, rows, lexical, datatype. */
public class Probe {
  public static void main(String[] a) throws Exception {
    Path dir = Path.of(a[0]);
    for (String line : Files.readAllLines(dir.resolve("cases.tsv"))) {
      String[] f = line.split("\t", 3);
      Model m = ModelFactory.createDefaultModel();
      m.read(dir.resolve(f[1] + ".ttl").toUri().toString(), "TTL");
      String out;
      try (QueryExecution qe = QueryExecutionFactory.create(f[2], m)) {
        ResultSet rs = qe.execSelect();
        int n = 0; String lex = "", dt = ""; StringBuilder all = new StringBuilder();
        while (rs.hasNext()) {
          QuerySolution s = rs.next(); n++;
          RDFNode g = s.get("g");
          RDFNode sub = s.get("s");
          all.append(sub == null ? "" : sub.toString()).append("|");
          if (g == null) { lex = "\u0000UNBOUND"; }
          else if (g.isLiteral()) { lex = g.asLiteral().getLexicalForm(); dt = g.asLiteral().getDatatypeURI(); }
          else if (g.isURIResource()) { lex = "<" + g.asResource().getURI() + ">"; dt = ""; }
          else { lex = "_:b"; dt = ""; }
          all.append(lex.equals("\u0000UNBOUND") ? "\u0000UNBOUND" : lex).append("|").append(dt).append(";");
        }
        out = n + "\t" + lex + "\t" + dt + "\t" + all;
      } catch (Exception e) { out = "ERR\t" + e.getClass().getSimpleName() + "\t"; }
      System.out.println(f[0] + "\t" + out);
    }
  }
}
```
