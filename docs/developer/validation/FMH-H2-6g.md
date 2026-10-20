<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-H2.6g, every NOT EXISTS reads the graph it means

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice H2.6g, planned in
[plan §4.17](../plans/formal-methods-track-h.md#417-h26g-every-not-exists-reads-the-graph-it-means-planned-2026-10-20-tsd-34) for
[TSD-34](../../architecture/triple-store-discovery.md#tsd-34-rdflib-evaluates-a-filter-not-exists-in-a-graph-block-against-the-wrong-graph-for-some-solutions)
and TSD-Q19. Authored and run in autonomous mode, not committed. Versioning of the ontology is ignored on this branch (TD-64), and the builder versions,
which a golden check holds, moved.

**For the maintainer:** accept or change the ADR-A123 addendum (accepted with the slice's plan, so the decisions taken alone below are the part to read),
the TSD-34 additions and the narrowed TSD-Q19.

## Invariant

No generated operation and no template has a `FILTER NOT EXISTS` or `FILTER EXISTS` with no `GRAPH` of its own inside a `GRAPH` block, and the IR
checker refuses a new builder that writes one. Where the shape could change an outcome on rdflib, a test over a sweep of hash seeds holds the result to a
reference. Where it cannot, the test records why.

## What was exposed

A scan of the rendered text of every operation the examples generate (`_ported()`, 57 operations) found the shape in 29. `FILTER EXISTS` is not in the IR
and no builder uses it. The audits, the key claims, the creates and the transaction claim already named their graph.

| Builders | Body | Can the defect change an outcome |
|---|---|---|
| `append-version`, `append-version-delta`, `cas-replace-composite-property`, `cas-replace-named-graph`, `tombstone-delete-composite`, `tombstone-delete-named-graph`, each with its no-receipt and patch-log variants where it has them, and every dataset-guard variant (28 operations) | `$root pat:deleted true` in the row's graph | No. The body depends on `$root` alone, so every solution of the block passes or every one fails (TSD-34, under "Which generated operations had the shape") |
| `members` | the nearest-checkpoint test and the drop test | Possibly, since the bodies depend on `?cp`, `?w` and `?member`. No history we built exposed it |

## What changed

- **Builders and templates.** The 28 write operations (14 builders, each with a dataset-guard variant) state `GRAPH <meta> { $root pat:deleted true }` inside the
  deleted-row guard, and `members` states `GRAPH <data> { ... }` in both bodies. The 29 Mustache templates changed the same way, since the
  equivalence harness holds each to its builder. Fifteen builder versions moved up by one (`BUILDER_VERSIONS`, via `_NOT_EXISTS_NAMES_ITS_GRAPH`),
  `builder-goldens.json` and the 12 expected profiles follow. The profiles differ in `dal:templateVersion` only.
- **IR checker.** `NotExistsWithoutGraph` (new in `RULES`): a `NotExists` inside a `GraphBlock` whose body holds no `GraphBlock` is refused. The body is
  checked outside the enclosing block, so a `GRAPH` in it is not a `NestedGraph`. The fixture `where()` of the IR tests moved to the new shape.
- **Tests** (`test_tsd_34_builders.py`, support in `tsd34_support.py`, two refusals in `test_ir.py`).
- **Documents.** TSD-34 gained a subsection on which operations had the shape, TSD-Q19 is narrowed, the ADR-A123 addendum, the TD-68 row.

## Tests

| ID | Checks |
|---|---|
| H2.6g-T0 | the scan finds the shape in a query and a template, and passes a body that names its graph and a `NOT EXISTS` outside a block |
| H2.6g-T1 | no rendered operation (57) and no template file has the shape |
| H2.6g-T2 | on rdflib, 16 hash seeds each in a child process, and once on Oxigraph: a tombstoned row with three heads and three current versions is not written by any of the 28 operations, and the same row, live, is written by every one (the control) |
| H2.6g-T3 | on rdflib, the solutions of the row block share one context (a context yields three solutions), so the precondition of the defect holds and T2's argument is the reason for T2's result |
| H2.6g-T4, T4o | `members` against the reference of `test_membership.py` for nine versions with stray adds, on 16 seeds in child processes, and on each engine |
| H2.1-T2, T3, T4, T4b | the new rule has two refusals (a body with a triple, a body with only a filter), and is in `RULES` |

## Results

| Command, from the repository root | Result |
|---|---|
| `mise run check:persistence` (includes `check:persistence-expected-profiles`) | 3950 passed, 1 xfailed. The expected profiles are current |
| `mise run check:persistence-oxigraph` | 363 passed, including T2 and T4o on Oxigraph |
| `mise run check:ontology-catalog` | consistent, the 2 known defects reported |

A first run failed four tests that pin text or a version and were updated for the intended change, with no other test touched. `test_h2_1_t13` and
`test_h2_3_t29` pin rendered text in `fixtures/ir/*.rq` (regenerated, the only change in each is the `NOT EXISTS` line), and `test_h2_6f_t20` and
`test_h2_6c_t10` pin builder versions (`members` 1 to 2, `append-version` 2 to 3). No test was removed, skipped or loosened.

Before the change, on a copy of the original tree, the `members` read was right on 192 runs (random histories, checkpoint every 2, 3 and 4 versions, 16 seeds) and
on 16 seeds of the nine version history with stray adds. The write scenario never wrote a tombstoned row on 16 seeds, and wrote a live one every time. The sweep
of T2 takes about 35 s of the file's 40 s.

Authored and run, not committed. `build:persistence-execution` was not run.

## Probes

1. **A `GRAPH` removed from `tombstone-delete-named-graph.mustache`.** T1 fails (the scan), and so do the equivalence harness
   (`test_h2_2_t2`) and its self-check (`test_h2_2_t4`). **T2 still passes on all 16 seeds, as the argument says it must.** The seed sweep cannot
   see this removal, because no outcome depends on it. The guards against it are the scan, the harness and the checker rule. Reverted.
2. **The checker rule disabled** (its condition made `False`). The four refusal cases fail (`test_h2_1_t4` and `test_h2_1_t4b`, two each). Reverted.

The plan asked for a probe in which the seed sweep fails. For the write guards there is none, and that is the finding. For `members` the original text
passed every history we tried, so no probe of it fails either. TSD-34's own query (the probe `test_tsd_34_*`) is the case that fails a sweep.

## Decisions taken alone

1. **All 29 operations changed, not only the one where an outcome could change.** Plan §4.17 step 3 changes a builder where the defect can change an
   outcome, and the checker rule of step 4 refuses the shape everywhere, so the rule would refuse the 28 write operations unless they changed. The
   alternative was a rule with an exception for a body that depends on parameters only, which is more checker, a reasoning step in the code
   and a rule a future builder can satisfy wrongly. The cost is 15 builder versions, 29 templates and the profiles' `templateVersion`.
2. **The `GRAPH` is nested in the body and the filter stays where it was,** and was not moved to the group outside the block. Moving it
   would drop the nesting and need no checker change, but it changes the filter's position in the algebra and with it, on rdflib, the cost of `members`
   (TD-68), which is not this slice's question.
3. **The checker checks the body outside the enclosing block** (`graph=None`), which is what allows the nested `GRAPH`. A body with a bare triple is
   then a `DefaultGraphPattern` and a body with no `GRAPH` at all is the new rule.
4. **The new rule has no `EXISTS` form,** since the IR has only `NotExists`.
5. **The behaviour test for the write guards asserts "not written", and the reason is recorded** in the test, since the defect cannot change the outcome.
   T3 asserts the sharing of a context, which depends on rdflib's internals. If rdflib stops sharing, T3 fails and the entry of TSD-34 is revisited.
6. **The scan of T1 is a brace scanner over text,** so it also reads the Mustache templates, which the IR cannot. It is not a SPARQL parser.
7. **TSD-Q19 is narrowed, not closed.** The question about the generated operations is answered. Why the sub-select decides TSD-34, and Fuseki or Jena ARQ,
   stay open.
8. **TD-68 gets a note** that `members` is no longer blocked by TSD-34. The fast sub-select form was not retried here.

## Deviations

- The plan expected a seed-sweep test that fails when a `GRAPH` is removed. None can (above).
- The Oxigraph check of T2 runs the scenario once per operation, as the plan says, in the process of the test.
