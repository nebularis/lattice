<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-H2.5, key claims, the audits, guard D and the SELECT fragment

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice H2.5, planned in
[plan §4.3](../plans/formal-methods-track-h.md#43-h25-key-claims-the-audits-and-the-self-calibrating-guard-planned-2026-10-13-built-2026-10-13) (H-D23, one slice in
six gates) under [ADR-A123](../../architecture/decisions/ADR-A123-typed-operation-ir.md) and its addenda of 2026-10-13.
**For the maintainer:** all three decisions were taken on 2026-10-13, and 1 and 2 are built in this slice. Nothing is open. The stop condition on P5 did not arise.
**For countersignature (non-weakening rule):** none. No test was removed or loosened. Two existing tests changed their expected text to follow
the guard (below).

## Invariant

Each of the ten remaining templates (five key-claim operations, five audits) has a builder that does what its template does, held to it by the
equivalence harness. An operation built with its parameter guard writes nothing when a required parameter is missing or mistyped, on rdflib and on
Oxigraph alike. The `SELECT` fragment of the IR refuses the forms that are illegal SPARQL or fail without an error (ADR-A123, addendum of
2026-10-13). A difference between the two stores that changes a result is found by a test and recorded in the
[triple-store record](../../architecture/triple-store-discovery.md), and not left to a review.

## What changed

- **Guard D** (gate 1). `_guard_expr` writes `DATATYPE($p) = DATATYPE("0"^^xsd:long)` for `Long` and `Position`. A new parameter kind,
  `Literal`, is guarded by `isLiteral($p) && LANG($p) = ""`, for the retire time. An operation with no required parameter gets no guard group.
- **The `SELECT` fragment** (gate 2). `SubSelect(select, where)` is a pattern element. `Select` serves a query and a sub-select, and has
  four more fields (`distinct`, `order_by`, `limit`, `offset`) that exist so the checker can refuse them with a named rule. The checker has
  four new rules, `UngroupedProjection`, `HavingNotGrouped`, `SubSelectLeak` and `FragmentLimit`, and the boundness table of the plan
  for a sub-select's projected items. Every walk enters a sub-select (reads and writes, roles, clock variables, boundness, the guard's place).
  A sub-select starts with nothing in scope, and inside a `GRAPH` block it reads that graph.
- **Merge-rewrite takes `IRI(MIN(STR(?owner)))`** (decision 1), in the template and the builder.
- **Ten builders** (gates 4 and 5) in `builders.py`, registered in `BUILDERS`. Every template apart from `cas-replace-value-guard` (TD-43) is now
  ported. `?other` and `?canonical` are declared `Kind.IRI`, with the data invariant from the patterns guide recorded in the builder. The
  gap scan declares `?seq`, `?S` and `?L` as `Compare.VALUE`.
- **The renderer** writes the parentheses of every nested arithmetic operand (TSD-17), and `SELECT DISTINCT` for a top-level query. The gap-scan template says
  `(?S - ?L) + 1` for the same reason (decision 2), so the harness needs no normalisation for it.
- **The tests' engine axis.** `engines.guards()` is now on for both engines. `@engines.each_engine_and_guards` runs a behaviour test with the
  guards on and off (the `guard_axis` fixture), on both engines. **61 behaviour tests across seven modules have the axis**, which doubles each of them.
  The guards-off cases are kept, since `--no-parameter-guards` stays supported.
- **Documents.** [Triple-store record](../../architecture/triple-store-discovery.md) TSD-15 to TSD-20, the consequences of TSD-07 updated,
  TSD-Q6 to Q10 answered and TSD-Q11 and Q12 added. TD-34 removed from the debt register and TD-43 and TD-45 updated. The README of
  `tools/persistence` describes guard D, the fragment and the ten ports.

### The golden text that changed (gate 1, step 2)

Every operation with a `Long` or `Position` parameter has a changed guard line, `DATATYPE($p) = xsd:long` becoming
`DATATYPE($p) = DATATYPE("0"^^xsd:long)`. That is `bootstrap-version-row`, `append-event`, the named-graph and composite create, replace and
tombstone, and each dataset-guard variant. Three files pin the text, and each changes in that one line only:
`tests/fixtures/ir/base-operation.rq`, `replace-named-graph.rq` and `replace-named-graph-caller.rq`. The guard-position test (H2.2-T6) expects the new
form, and expects no guard group at all for an operation with no required parameter.

## Findings, by gate

| Gate | Finding | Where |
|---|---|---|
| 1 | P5 extended: a constant, a substituted parameter, a `VALUES` row and a stored value report one datatype on each store (`xsd:long` on rdflib, `xsd:integer` on Oxigraph), and a simple literal stays `xsd:string`. **No divergence, so guard D stands on both** and the stop condition did not arise. A guarded write now applies on Oxigraph (TD-45's guard part). An `xsd:integer` epoch is refused on rdflib and accepted on Oxigraph, as the addendum says | H2.5-T1 to T4, [TSD-07](../../architecture/triple-store-discovery.md#tsd-07-numeric-datatypes-are-not-kept-by-oxigraph) |
| 2 | rdflib lets an outer binding into a sub-select (a count of 1 where SPARQL and Oxigraph give 3). A sub-select inside a `GRAPH` block reads that graph on both. A `FILTER` inside `NOT EXISTS` sees a parameter and a sub-select's projection on both, by text and by initial binding | H2.5-T12 to T14, TSD-15, TSD-20 |
| 5 | **Oxigraph 0.5.11 groups a chain of same-precedence operators from the right** (`10 - 3 + 2` is 5, `8 / 4 / 2` is 4). The gap scan's `?S - ?L + 1` then reported every complete stream as a gap. Found by running the audit, and fixed in the renderer | H2.5-T44, TSD-17 |
| 6 | **rdflib's `MIN` and `MAX` over IRIs return plain literals.** Merge-rewrite then wrote literal objects and a self-link for the canonical owner on rdflib, and IRIs and no self-link on Oxigraph. Both chose the same owner. **Fixed by decision 1 (option B)** | H2.5-T29, T30, T41, TSD-16 |
| 6 | `COUNT(DISTINCT)` counts `xsd:long` and `xsd:integer` terms apart on rdflib and together on Oxigraph. A duplicate `seq` written with another integer type is reported by the gap scan on rdflib only | H2.5-T42, T43, TSD-18 |
| 6 | `GROUP_CONCAT` keeps the stored order whatever the hash seed, for the duplicate audit's shape | H2.5-T45, TSD-19 |
| 4 | With the guards off, a missing parameter writes: a claim with no owner (`key-claim-write` without `$owner`), one claim of two (dual without `$claimCurrent` or `$claimNext`), and for a retire a half retirement with no time (`$now`), or the retirement of the claims of the owner it does name (no `$claim`). The two engines agree on all eight cases | H2.5-T22, T23 |

## Decisions needing confirmation

1. **Decided 2026-10-13: option B, built in this slice.** Merge-rewrite on rdflib (TSD-16). The port equalled its template, so on rdflib it wrote `"urn:o:1"` as a plain
   literal and linked the canonical owner to itself, and on Oxigraph it wrote IRIs. Both picked the same owner. Options were:

   | Option | Consequence |
   |---|---|
   | A. Keep it as a port, with the difference recorded | Nothing to build. A deployment on rdflib gets literal links and a self-link |
   | B. Compute the canonical owner as `IRI(MIN(STR(?owner)))` | An IRI on both, and the self-link goes since `?other != ?canonical` then compares two IRIs. A change and not a port (typed IR sketch §7.1), so the template changed with the builder and the harness still holds them equal |
   | C. As B, plus a shape that the merge relation's objects are IRIs | B, and the property is checked in the data. A shape on the adopter's merge relation belongs with H2.7's vocabulary |

   Built: the template and the builder project `IRI(MIN(STR(?owner)))`. The checker now lets an aggregate sit inside a scalar function of a projection (and still
   refuses one inside another aggregate), and the boundness rule follows the function (`IRI(MIN(...))` is bound with a `GROUP BY` and not without).
   H2.5-T29 and T30 now hold on both engines with no engine branch: links to the lowest owner, none to itself, all IRIs. Option C stays with H2.7.
2. **Decided 2026-10-13: option B, built in this slice.** How the builder and the template agree about arithmetic (TSD-17). Oxigraph groups `?S - ?L + 1` from the right, so the
   gap scan's template, written as a chain, counted wrongly there. We first made the renderer write the parentheses of every nested arithmetic operand and made the
   equivalence harness read a left-nested chain as the flat one it equals. Options for the template were:

   | Option | Consequence |
   |---|---|
   | A. Keep what was built | The harness keeps one normalisation beyond reordering what SPARQL leaves unordered, and the template stays wrong on Oxigraph until H2.9 |
   | B. Parenthesise the template as well, and remove the harness normalisation | Template and builder agree as text, the harness only reorders, and the known defect leaves the legacy path |
   | C. Render the chain flat, as the template had it | The gap scan reports every complete stream as a gap on Oxigraph |

   Built: the template says `(?S - ?L) + 1`, the harness normalisation is removed, and `test_h2_5_t47` now also fails a builder that groups the sum from the
   right. The alignment test that pins the template text follows. The renderer's rule stays.
3. **Decided 2026-10-13: fine for now.** `Select` carries `distinct`, `order_by`, `limit` and `offset` so that each can be refused with `FragmentLimit`.** That gives the plan's "each with a
   refusal test", at the price of four fields nothing uses. The alternative is no fields, and a limit that is simply unrepresentable and untested.

## Deviations from the plan

- **The harness gained no normalisation.** A first version read a left-nested arithmetic chain as the flat one, and decision 2 removed it by parenthesising the
  template. Aggregate names did not need one either, because the builders emit the aggregates in the template's order and the equivalence holds.
- **Gate 1, step 4:** the axis is a fixture and a marker, not a duplicate of each test. The behaviour tests that assert the guard itself take
  `guards=` explicitly and are unchanged.
- **The boundness table** names `SUM` and `AVG`, which are not in the fragment's function set, so only `COUNT`, `MIN`, `MAX`, `SAMPLE` and
  `GROUP_CONCAT` are implemented. Adding the other two is a line in `AGGREGATES` and a rule that their argument is numeric.
- **The four unknowns of the plan's fact 10 are answered** (`MIN` over IRIs, `COUNT(DISTINCT)` over mixed terms, the arithmetic, `GROUP_CONCAT`'s order) and `TSD-Q6` to `Q10` are closed. Two new questions, `TSD-Q11` and `Q12`, are open.

## Test cases

| ID | Given / When / Then | Level | Invariant | +/- |
|---|---|---|---|---|
| H2.1-T4, T4b (11 new rows in `test_ir.py`) | a projection that is not grouped, a `HAVING` over an ungrouped variable, an inner variable used outside a sub-select (twice), `ORDER BY`, `LIMIT`, `OFFSET`, `DISTINCT` in a sub-select, a sub-select in a sub-select / `check` and `render` / refused with the named rule | L1 | the four new rules | - |
| H2.5-T1, T2 | P5 / a `xsd:long` and a simple literal in five forms / one datatype each, per engine | L4 | guard D rests on a store treating a constant and a parameter alike | + |
| H2.5-T3, T4 | a bootstrap with the guard on and off, and with a missing, non-numeric, IRI and `xsd:integer` epoch / run / applies on both engines, refused for a bad epoch, an integer epoch only where datatypes are kept | L4 | TD-45 | ± |
| H2.5-T5 | a sub-select projecting each item of the boundness table, tagged `Bound` and `OptionalAllowed` / `check` / accepted or refused as the table says (9 rows) | L1 | boundness | ± |
| H2.5-T6 | `GRAPH ?g` inside a sub-select, `?g` bound outside / `check` / `UnboundGraphVariable` | L1 | a sub-select starts empty | - |
| H2.5-T7 to T9 | merge and quarantine, a guarded sub-select, a parameter-free audit / `access_sets`, `render` / roles hold inside a sub-select, the guard is first in the outer `WHERE` and never inside, no guard for no parameter | L1 | the walks enter a sub-select | + |
| H2.5-T10, T11 | 150 random queries and sub-selects, valid by construction / `render` and parse / exactly one operation, deterministic, with `GROUP BY`, `HAVING` and `DISTINCT` all generated | L2 | queries render and parse | + |
| H2.5-T12 to T14 | the scope of a sub-select, a sub-select in a `GRAPH` block, a `FILTER` in `NOT EXISTS` with a parameter / each engine / as TSD-15 and TSD-20 | L4 | what each engine does | + |
| H2.5-T15 to T18 | `key-claim-write` and `-dual` / a claim, a second owner, the same owner, an independent claim, a held current or next claim / written once, refused to another owner, dual all or nothing | L4 | key-claim monotonicity | ± |
| H2.5-T19 to T21 | retire / the owner, another owner, a timestamp of each datatype, an IRI, a language string / deleted and recorded, nothing, accepted or refused | L4 | retire by the owner only, `Literal` | ± |
| H2.5-T22, T23 | each key-claim operation with one parameter left out / guards on and off / nothing written with the guard, the recorded writes without (8 cases, both engines) | L4 | TD-34 | ± |
| H2.5-T24 | a stored literal owner / a write by an IRI owner / refused | L4 | the data invariant | - |
| H2.5-T25 to T28 | quarantine / duplicated claims, a second run, another constraint, a third owner joining / every owner recorded once, nothing deleted, nothing repeated | L4 | idempotent quarantine | ± |
| H2.5-T29, T30, T30b | merge-rewrite / owners 1 to 3, a second run, a lower owner joining later / links to the lowest, once, all IRIs, none to itself, the same on both engines | L4 | merge | ± |
| H2.5-T31 | merge-rewrite / a claim with one owner / nothing | L4 | scope of the merge | - |
| H2.5-T32, T33 | the duplicate audit / a clean store, a duplicate, another constraint / the claim, `n`, a set of owners, nothing | L4 | audit finds its defect | ± |
| H2.5-T34 | the fork audit / two transaction claims on one revision / reported | L4 | audit finds its defect | ± |
| H2.5-T35, T36b | the receipt audits / a merged fork and a request applied twice across buckets, the pinned graph, an unlisted bucket, one receipt held twice / reported, or not | L4 | audit finds its defect, `DISTINCT` | ± |
| H2.5-T36, T37, T38 | the gap scan / 8 shapes of receipts, rows and low-water marks, a receipt out of range, and an append then a replace / reported or clean | L4 | audit finds its defect | ± |
| H2.5-T39, T40 | the ten operations / roles of every access, the role table / as listed, no entry added | L1 | gate 3 | + |
| H2.5-T41 to T45 | `MIN` over IRIs (the store finding, kept), `COUNT(DISTINCT)` over mixed integers, a duplicate seq, a chain of operators, `GROUP_CONCAT` under hash seeds / each engine / as TSD-16 to TSD-19 | L4 | what each engine does | + |
| H2.5-T46 | `NOW()` bound to a parameter's name / `check` / `NameCollision` | L1 | gate 6 | - |
| H2.5-T47 | seven mutated queries or sub-selects, one of them a sum grouped from the right / the harness / `Mismatch` | L2 | the harness catches a changed query | - |
| H2.2-T1 to T6, T20, T21 and H2.3-T32 | the ported list, equality with every template (now 27), reads, roles, guard position / run / pass for the ten new operations too | L3 | the port | ± |

## One command

Run from the repository root. `check:persistence` is the gate.

```bash
mise run check:persistence                   # 2597 passed, 1 xfailed here (2111 before this slice)
mise run check:persistence-oxigraph          # 5 adapter tests and 189 Oxigraph cases, about 15 s (66 before this slice)
```

## Artefacts to inspect

- `tools/persistence/src/persistence/builders.py` from `_key_claim_write`, and `ir_render.py` from `_check_select`.
- `tools/persistence/tests/test_select_fragment.py`, `test_key_claims_and_audits.py` and the engine tests of `test_store_probes.py`.
- `docs/architecture/triple-store-discovery.md`, TSD-15 to TSD-20.
- The golden files in `tools/persistence/tests/fixtures/ir/`, one changed line each.

## Adversarial probes

Run on 2026-10-13 on the committed slice, each file restored from git afterwards. Seven probes, the six of the plan and one more.

| Mutation | Result |
|---|---|
| the guard reverted to a fixed `DATATYPE($p) = xsd:long` | 2 of the 5 P5 cases fail on Oxigraph (H2.5-T3 and T4), as TD-45 predicted |
| an aggregate with no `GROUP BY` counted as bound | H2.5-T5 fails on the `MIN` with no `GROUP BY` row |
| a sub-select that leaks an inner variable accepted (`SubSelectLeak` skipped) | 4 refusal cases fail |
| the `NOT EXISTS` of `key-claim-write` correlated to nothing | 4 cases fail (T15, T16, on both engines) |
| `revision-multi-txn-audit` without its `DISTINCT` | H2.5-T36b fails on both engines |
| `MIN` replaced by `MAX` in merge-rewrite | the merge cases fail (H2.5-T29, T30b), run again after decision 1 |
| the parentheses dropped from the gap scan's chain | 7 cases fail (the gap-scan cases on Oxigraph and T44) |

## Deliberate non-coverage

- `cas-replace-value-guard` (TD-43, H2.7's vocabulary).
- The caller-side checks, including the strict `xsd:long` check (NQ6) and `logGraphs`, in H2.8. An empty `logGraphs` makes the gap scan check only the
  pinned graph, and it reports clean for a stream whose receipts are all in buckets. A caller obligation for H2.8 and an applicability label for H9.
- An ill-typed literal such as `"99999999999999999999"^^xsd:long`, which keeps its datatype on rdflib and passes the guard. H2.8's check.
- Binding over the SPARQL 1.1 Protocol, which no engine here offers in process.
- `COUNT(?owner)` in quarantine counts solutions and not distinct owners, which is right while one keys graph holds the claims (TD-06, TD-41).
- How the canonical owner of a merge is chosen beyond `MIN` (NQ5). T30b records the property that a lower owner joining later changes it and earlier links stay.
- `SUM`, `AVG`, `ORDER BY`, `LIMIT`, `OFFSET`, `DISTINCT` inside a sub-select, and nested sub-selects, which the fragment refuses.
- Stores other than rdflib and Oxigraph (TSD-Q12).
