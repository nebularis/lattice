# FMH-TS-2. Validation Pack: Oxigraph as the default engine, conformance as a run of its own

Status: authored and run on 2026-10-21, on a machine shared with other agents (load average 10 to 14, 2.5 GB of memory available), so the times are upper bounds.

## What changed

The maintainer decided on 2026-10-21 that the persistence tests run their generated SPARQL on Oxigraph by default, and that conformance testing on other engines (rdflib now, Jena, GraphDB and RDFox later) runs on demand and before a merge, not in every build (ADR-A125 addendum, ADR-A124 for the precedent). rdflib stays the library the compiler, pySHACL and the expected-profile check are built on. Only the store that executes generated SPARQL in a behaviour test changed.

| Change | Where |
|---|---|
| The engines a test marked `each_engine` runs on come from `PERSISTENCE_ENGINES` (comma-separated, default `oxigraph`). `CURRENT`, the engine of a test that calls `engines.dataset()` without opting in, is the first of them. A new engine is one entry in `engines.REGISTRY` (its mark), one branch in `engines.dataset()`, and its name in the conformance task. An unknown name is an error | `tools/persistence/tests/engines.py` |
| Markers `oxigraph`, `rdflib` (new) and `conformance` (new) registered. `rdflib_only` / `RDFLIB_ONLY` mark a test hard-coded to rdflib (conformance plus `rdflib`), and an autouse fixture pins `CURRENT` to rdflib for a test marked `rdflib` that has no `engine` parameter | `engines.py`, `tools/persistence/tests/conftest.py` |
| `check:persistence`: `-m "not conformance"`, `PERSISTENCE_ENGINES` unset, `-n auto --dist loadgroup`, also runs `tools/testing/oxigraph/tests`, depends on `bootstrap:testing-oxigraph`, `bootstrap:testing-mem-check` and `check:persistence-expected-profiles` | `mise.toml` |
| New `check:persistence-conformance`: `PERSISTENCE_ENGINES=rdflib,oxigraph` through the task's `env` table (no shell prefix, so it works on Windows), no marker filter, same parallelism. On demand and before a merge, not part of `check` | `mise.toml` |
| `check:persistence-oxigraph` removed, and its references updated | `mise.toml`, `tools/testing/oxigraph/README.md`, `docs/developer/developer-guide.md`, `docs/architecture/triple-store-discovery.md` |
| Generated SPARQL run directly on `rdflib.Dataset()` now goes through `engines.dataset()`: `test_ir_render` (t16 to t18, t21, t22, t25, t25b, t26, t28), `test_graph_naming`, `test_terms` (H2.1 round trip) | the three test files |
| Two child-process scripts that import `engines` are told `PERSISTENCE_ENGINES=rdflib`, so they are rdflib whatever the parent selects | `test_append_events.py` (t2), `test_key_claims_and_audits.py` (t45) |
| `test_h2_4b_t12` (the Oxigraph cases skip where the package is absent) gives its child `PERSISTENCE_ENGINES=rdflib,oxigraph`, since it needs an rdflib case and an Oxigraph case | `test_engines.py` |

No assertion was deleted, weakened or changed. A test that asserts the same on every engine is not marked.

## The conformance rule used

A test is marked `conformance` when its subject is an engine's behaviour and not the generated SPARQL:

1. it records an engine difference in its body (`engines.CURRENT` or `_pick` branches, the TSD probes), so its Oxigraph case is a fact about Oxigraph and goes to the conformance run with the rdflib case, or
2. it has no engine parameter and is hard-coded to rdflib (a sweep over hash seeds in child processes, `Dataset()` with rdflib-specific assertions).

A test with an `engine` parameter that asserts the same thing on every engine, with the rdflib case a sweep or a branch (for example `test_h2_6g_t2` and the append, membership and key-claim behaviour tests), is not marked. Its Oxigraph case runs by default and its rdflib case exists only where `PERSISTENCE_ENGINES` names rdflib. The sixteen-seed sweeps of those tests therefore drop out of the default run without a mark.

## Tests marked conformance (27 tests, 57 cases in the conformance run)

| Test (file::name, abbreviated) | Cases | Why |
|---|---|---|
| `test_append_events::test_h2_6b_t2_..._every_hash_seed_on_rdflib` | 1 | eight hash seeds in child processes on rdflib (TSD-01), hard-coded to rdflib |
| `test_append_events::test_h2_6b_t6_an_empty_rows_slot_...` | 4 | TSD-21, rdflib raises on an empty VALUES where Oxigraph gives no solution |
| `test_builders::test_h2_2_t14_...` (two of four cases: `epoch as xsd:integer`, `target as a literal`) | 2 | the unguarded rows written differ by engine (datatype canonicalisation, a literal as a graph term), recorded for rdflib |
| `test_composite_builders::test_h2_4a_t3_...` | 1 | "what rdflib does, recorded": the unguarded sweep and the `xsd:long` seq terms |
| `test_composite_builders::test_h2_4a_t6_...` | 4 | a zero-length path from a term in no triple matches itself on rdflib and not on Oxigraph |
| `test_ir_render::test_h2_1_t17_...` (case `epoch as xsd:integer`) | 1 | a guard on `xsd:long` refuses an `xsd:integer` only where datatypes are kept (rdflib) |
| `test_ir_render::test_h2_1_t29_...` | 5 | the checker's model of BIND scope against rdflib's evaluation |
| `test_ir_render::test_h2_1_t29b_...` | 1 | NOT EXISTS sees the enclosing group, on rdflib |
| `test_ir_render::test_h2_3_t2_...` | 3 | a `GRAPH ?g` bound outside restricts an inner group, on rdflib (TD-Q2) |
| `test_key_claims_and_audits::test_h2_5_t41_...` | 2 | TSD-16, MIN and MAX over IRIs return an IRI on Oxigraph and a literal on rdflib |
| `test_key_claims_and_audits::test_h2_5_t42_...` | 2 | TSD-18, COUNT DISTINCT of `xsd:long` and `xsd:integer` terms |
| `test_key_claims_and_audits::test_h2_5_t43_...` | 2 | the gap scan reports a duplicate seq of another integer type on rdflib only |
| `test_key_claims_and_audits::test_h2_5_t44_...` | 2 | TSD-17, associativity of `a - b + c`, follows the installed pyoxigraph |
| `test_key_claims_and_audits::test_h2_5_t45_...` | 1 | TSD-Q7, GROUP_CONCAT keeps the store's scan order on six hash seeds, rdflib children |
| `test_membership::test_h2_8c_t6_...` | 1 | 24 random histories on sixteen hash seeds in rdflib children (TSD-34), 23 s alone |
| `test_named_graph_builders::test_h2_3_t23_...` (case `RdfLiteral(...)` as the graph) | 1 | a literal as `GRAPH` term: rdflib writes nothing, Oxigraph refuses the text at parse time (new finding, below) |
| `test_select_fragment::test_h2_5_t12_...` | 2 | TSD-15, a sub-select sees the outer binding on rdflib and not on Oxigraph |
| `test_store_probes::test_h2_4b_t1_p1_...` | 4 | P1 and TSD-01, update order of DELETE/INSERT WHERE, twelve hash seeds on rdflib |
| `test_store_probes::test_h2_4b_t2_p1_...` | 2 | P1, snapshot semantics (rdflib sweep, Oxigraph version flag) |
| `test_store_probes::test_h2_4b_t3_p2_...` | 2 | P2, a request that fails at its second operation |
| `test_store_probes::test_h2_4b_t5_p4_...` | 2 | P4 and TD-44, an unbound graph variable in a template |
| `test_store_probes::test_h2_4b_t6_p5_...` | 2 | P5, an integer-derived literal keeps its datatype on rdflib only |
| `test_store_probes::test_h2_5_t1_p5_...` | 2 | the datatype of a long in five forms, per engine |
| `test_store_probes::test_h2_5_t4_...` | 2 | guard D with an integer epoch, per engine |
| `test_store_probes::test_tsd_34_a_filter_not_exists_...` | 4 | TSD-34, sixteen hash seeds on rdflib, once on Oxigraph |
| `test_tsd_34_builders::test_h2_6g_t3_...` | 1 | rdflib's `evalGraph` shares one context across the solutions of a block (patches rdflib) |
| `test_tsd_34_builders::test_h2_6g_t4_...` | 1 | the `members` read on sixteen hash seeds in rdflib children |

Not marked, although they mention an engine: `test_store_probes` t4 (the P3 cost ratio), h2_5_t2 (a simple literal stays `xsd:string`), h2_5_t3 (a guarded write applies) and the TSD-34 sub-select variable test, which assert the same on every engine. `test_tsd_34_builders::t2` keeps its Oxigraph case in the default run.

## Measured

Before the change (maintainer's serial measurements, same suite): engine tests 8.8 s on Oxigraph (368 cases, 347 MB peak) and 39.8 s on rdflib (372 cases, 403 MB peak). The rdflib hash-seed sweeps took about 37 s (test_membership t6 alone 23 s). Whole suite 161.6 s serial, 95 s with `-n auto`, 649 MB peak, 4346 passed and 1 xfailed.

After:

| Run | Result | Wall |
|---|---|---|
| `mise run check:persistence`, run 1 | 3956 passed, 1 xfailed | pytest 70.10 s, task 75.3 s |
| run 2 | 3956 passed, 1 xfailed | 59.92 s, task 64.8 s |
| run 3 | 3956 passed, 1 xfailed | 59.70 s, task 64.4 s |
| `PYTEST_XDIST_AUTO_NUM_WORKERS=4 mise run check:persistence` | 3956 passed, 1 xfailed | 39.42 s, task 44.1 s |
| default selection, `-n 0` (one process) | 3956 passed, 38 deselected, 1 xfailed | 97.7 s, peak 597 MB |
| `mise run check:persistence-conformance` | 4352 passed, 1 xfailed | 106.65 s |

3956 is 3950 persistence cases and 6 Oxigraph adapter tests. 4352 is 4346 and the same 6. The 38 deselected cases in the serial run are the conformance-marked cases that exist with Oxigraph alone selected (57 exist when both engines are named).

Worker counts: `-n auto` is decided by `mem_check` through the hook in `conftest.py`. The machine has 8 CPUs, and during the runs 2.5 to 2.9 GB were available, so `workers(8, 700 MiB)` returned 2 (checked before and after the conformance run, not printed per run, since `-q` hides the count). The three default runs therefore used two workers. With 4 workers the run took 39 s, which is what the machine gives with enough free memory (peak per worker 597 MB, 700 MiB assumed in `PER_WORKER`, still sound).

The serial peak fell from 649 MB to 597 MB. The default selection is 97.7 s serial against 161.6 s, and about 60 s on two workers against 95 s on the eight the machine would use.

## Coverage of the union

Before: `pytest --collect-only` of `tools/persistence/tests` gave 4347 ids (4346 passed and the xfail). After: `PERSISTENCE_ENGINES=rdflib,oxigraph pytest --collect-only` (what the conformance task collects) gives the same 4347 ids, with no id missing and none added (`comm` of the sorted lists is empty both ways), and the conformance task passed 4346 and 1 xfailed.

The default run (Oxigraph alone) collects 3951 of them. The other 396 are the 339 rdflib cases of tests that opt in with `each_engine` and the 57 conformance-marked cases of the two-engine collection, counted once each (3951 + 396 = 4347 hold, and the two sets share no id outside the 57 that the marker removes from the default). Every test that ran before runs in the conformance run, and nothing runs in neither.

What the default run no longer does: run the rdflib case of an `each_engine` test (these always ran on rdflib before), and the Oxigraph case of a conformance-marked test. Both are in the conformance run. Generated SPARQL is checked on rdflib before a merge by that task.

## Decisions taken alone

- Where an `each_engine` test asserts the same on every engine and only its rdflib branch sweeps or differs (`test_h2_6g_t2`), it is not marked. The engine selection already removes the rdflib case from the default run, and the Oxigraph case is a test of the generated SPARQL.
- Where an `each_engine` test records an engine difference in its body, the whole test is marked, so the default run also loses its Oxigraph case (for example the TSD-01 and TSD-17 probes, which follow the installed pyoxigraph). The decision follows the maintainer's definition of a conformance test, and it costs seconds. The cost of the opposite choice is a probe of Oxigraph that runs in every build.
- Tests that called `engines.dataset()` with no `each_engine` and had rdflib-specific assertions (`test_builders` t14 two cases, `test_composite_builders` t3, `test_named_graph_builders` t23 one case, `test_key_claims_and_audits` t45, `test_ir_render` t17 one case) are pinned to rdflib and marked conformance, per case where only some fail on Oxigraph. I did not add Oxigraph expectations to them, since those would be new assertions.
- `test_ir_render`, `test_graph_naming` and `test_terms` ran generated SPARQL on `rdflib.Dataset()`. They now use `engines.dataset()`, and pass on both engines apart from the cases above. `membership_fixtures.py` keeps `rdflib.Dataset()` because it also serialises TriG for the committed fixtures, which is library use.
- `CURRENT` is the first engine named, so the conformance run executes tests without `each_engine` on rdflib, and the default run on Oxigraph.
- A missing Oxigraph still skips its cases (the original behaviour, which `test_h2_4b_t12` asserts). `check:persistence` depends on the bootstrap, so a build has it.
- `check:persistence-conformance` runs the whole suite with no marker filter, so the engine-independent tests run a second time (about 40 s). A narrower filter (`conformance or oxigraph or rdflib`) would save that and miss the non-engine tests that now run on rdflib first, so the simpler form was kept.
- `.claude/skills/**`, the ADR, plans and status records were not edited, as asked. The skills `lattice-toolchain` (line 34) and `lattice-triple-stores` (line 61) still name `check:persistence-oxigraph`.

## Findings

- Oxigraph refuses `GRAPH "literal" { ... }` as a syntax error at parse time, where rdflib parses it and writes nothing (`test_named_graph_builders` t23, case with an `RdfLiteral` graph). The guard's outcome, nothing written, is the same, but the route differs. Not yet in `triple-store-discovery.md`.
- The sixteen-seed sweeps, `test_membership` t6 above all, now run only in the conformance task.

## The checks

| Task | Result |
|---|---|
| `mise run check:persistence` (three runs, and once with 4 workers) | 3956 passed, 1 xfailed each |
| `mise run check:persistence-conformance` | 4352 passed, 1 xfailed |
| `mise run check:persistence-library` | 113 passed |
| `mise run check:persistence-expected-profiles` | expected profiles are current |
| `mise run check:catalogue` | repository catalogue: 19 module(s) and 9 tool package(s) agree with the tree |
| `mise run check:deny-terms` | 0 finding(s) against 5 entries |
| `rm -rf ontology/persistence/execution && mise run check:ontology-catalog` | 1171 passed, ontology catalog consistent, 2 known defect(s) reported |

Commands for the maintainer: `mise run check:persistence` for the default run, and `mise run check:persistence-conformance` before a merge. Both pass on this checkout.
