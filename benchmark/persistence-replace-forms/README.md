<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Replace forms

A benchmark under [ADR-A124](../../docs/architecture/decisions/ADR-A124-benchmark-root.md). It measures what the persistence compiler's generated named-graph replace costs on rdflib and Oxigraph against a candidate form, the generated rows replace, which are linear in the payload, and the generated delta replace, which is linear in the change, and it probes how each engine applies an update, because both are right only on an engine that applies every deletion before any insertion ([TSD-01](../../docs/architecture/triple-store-discovery.md)). The cost it follows up is TD-42 in the technical debt register.

## What it measures

The generated whole-state `cas-replace-named-graph` (`dal:WholeState`, patch-log receipt, the caller names the graph) sweeps the aggregate's graph with `OPTIONAL { GRAPH $g { ?s ?p ?o } }`. Its `WHERE` gives one solution per stored triple (M), and an engine that fills the whole `INSERT` template for every solution pays M times the payload (N).

| Form | What it is |
|---|---|
| `R0` | the generated replace, rendered by the compiler |
| `R0-nodelta` | `R0` with empty `assertTriples` and `retractTriples`, to separate the payload's cost from the delta blocks' cost |
| `R1-candidate` | **a candidate, not generated.** Two operations in one request. The first deletes the aggregate's graph under `R0`'s whole `WHERE`, the second is `R0` without the sweep |
| `R2-candidate` | **a candidate, not generated.** One operation. The sweep becomes a `UNION` with one extra solution that alone binds every graph the `INSERT` writes to, so the `INSERT` is instantiated once |
| `R3-delta` | **generated.** The delta replace of `dal:ChangedTriples`, rendered from `cas-replace-named-graph-delta-patch-log` and `cas-replace-composite-property-delta-patch-log` as `R0` is. One operation with no sweep: its `DELETE` holds the triples the caller retracted, its `INSERT` the triples it asserted, and both are also written into the revision's delete and add graphs. It takes the two delta slots and no payload slot, needs no snapshot semantics, and is linear in the change on every engine. It runs a workload of its own, k = 1 below. The report labels it "R3 (generated delta, k = 1)" |
| `R2-values-candidate` | **generated.** The rows replace, rendered from `cas-replace-named-graph-rows-patch-log` and `cas-replace-composite-property-rows-patch-log` as `R0` is. One operation. The sweep is a `UNION` of the sweep, the payload, the assertions and the retractions as `VALUES` rows, and an empty group. The `INSERT` template holds three single quads over the row variables beside the row, claim and log blocks, so the solutions carry the payload. Its three payload slots are filled as rows `(s p o)` (`dal:TripleRows`), where `R0` fills them as N-Triples. The report labels it "R2 (generated rows)" |

`R1-candidate` and `R2-candidate` are derived from `R0`'s rendered text inside `check.py`, each with a comment saying so. Nothing in `tools/persistence` or `packages/` changes.

**Workload.** For each size M in 100, 300, 1,000, 3,000 and 10,000 the stored state at revision r holds M triples. The first half is the same at every revision and the second half carries the revision, so each payload holds N = M triples and half of them are already stored. That is the case that shows whether an engine applies its deletions before its insertions. Three replaces per size, the best time kept. `R3-delta` runs the same sizes with one changed triple per revision (k = 1): each replace retracts one triple and asserts one, the others staying as they were, and the check is that the aggregate equals the old state less the retracted triple plus the asserted one. It is a generated form, so a wrong result fails the run, and it is not held to `REPLACE_FORMS_MAX_R0`, since it does not sweep.

**Probe P1.** TSD-01's update in both row orders, run on each engine and recorded as `snapshot` (the triple is kept in both orders) or `per-solution`. rdflib's answer follows the process's hash seed, so it runs under seeds 0 to 11. `R2-candidate` and `R2-values-candidate` are run only on a `snapshot` engine.

**Witness.** `R2-candidate` at M = 100 on rdflib under each of the seeds 0 to 11, each in a child process, recording for each seed whether the result is right or which kept triple was lost. It is evidence and never fails the run.

## Two families

| Family | What is replaced |
|---|---|
| `named-graph` | an aggregate held in a graph of its own, as above |
| `composite` | a root and the members its owned path reaches, in one data graph shared with a **bystander** aggregate. The compiler's context is that of the project example, and the workload and the bystander are those of [benchmark/persistence-composite-cost](../persistence-composite-cost/check.py) |

The composite forms are rendered or derived exactly as the named-graph ones, with the sweep to move grabbed from the rendered text (`OPTIONAL { GRAPH <data> { $root <path> ?s . ?s ?p ?o } }`) and never retyped. The composite receipt block names `?logGraph2` and stays as rendered. `R2-candidate` is not derived for the composite family, since it is refuted there. The workload is M triples of root and members, about half kept and half replaced per revision, with the delta in the slots. After every replace the aggregate holds exactly the payload, the bystander holds exactly what it held, and the checks above hold. `--family named-graph|composite|both` (default both, or `REPLACE_FORMS_FAMILY`) selects the families.

## Edge cases

For each family and for `R0`, `R1-candidate` and `R2-values-candidate`, small cases with no timing, each on a fresh store and each checked by the same `verify` as the sized runs. Each is reported as `pass`, `wrong: <reasons>` or `error: <message>`, and a store that refuses an update, an empty `VALUES` block for example, is an error that is not worked around.

| Case | What it does |
|---|---|
| E1 | an empty aggregate (the create has an empty payload slot) replaced by 50 triples |
| E2 | 50 triples replaced by nothing. The report also says whether the store still lists the aggregate's graph afterwards (TSD-50) |
| E3 | an empty aggregate replaced by nothing. The row must still move, the claim and the receipt be written |
| E4 | 50 triples replaced by the identical 50, so both deltas are empty |
| E5 | composite only. E1 after checking that the root is in no triple of the data graph, and the bare sweep counted with and without `?s ?p ?o` (TSD-08 and TSD-51 record Jena and Oxigraph differing on a zero-length step) |

## The bare sweep

For the composite family at M = 3,000 and 10,000, the time of `SELECT (COUNT(*) AS ?n) WHERE { GRAPH <data> { $root <path> ?s . ?s ?p ?o } }` alone, best of three, with its count, so the path's own cost can be separated from the form's.

## Pass criterion

After every replace the root's graph holds exactly the payload (compared as a set), the version row is at the next sequence with the new head and not at the expected sequence, the add and delete graphs hold exactly the delta, the txn graph holds the claim, and no other graph changed. **A wrong result from `R0`, `R0-nodelta`, the generated rows replace or the generated delta replace fails the run. Time never does.** A wrong result from a candidate is recorded as `wrong: <reason>`, since finding that out is the purpose of running it. No budget exists before H5, and a check that fails on time depends on the machine.

Each measurement runs in a child process with a wall-clock limit. One that does not finish is recorded as `did not finish`, the larger sizes of that form as `not run`, and the run goes on.

## Run it

```bash
mise run check:persistence-replace-forms                       # sizes up to 10,000, R0 up to 3,000
REPLACE_FORMS_QUICK=1 mise run check:persistence-replace-forms  # sizes up to 1,000
REPLACE_FORMS_QUICK=named-graph mise run check:persistence-replace-forms  # sizes up to 1,000 for that family only
REPLACE_FORMS_MAX_R0=1000 mise run check:persistence-replace-forms
mise exec -- python benchmark/persistence-replace-forms/check.py --family composite
REPLACE_FORMS_TIMEOUT=300 mise run check:persistence-replace-forms
```

It is never a dependency of `check`. The task installs the Oxigraph test-support package ([ADR-A125](../../docs/architecture/decisions/ADR-A125-test-support-tooling.md)) and runs the check's own tests first. The results go to `report.md` here, which is generated and git-ignored, and its first line carries the date, the Python version and the versions of rdflib and pyoxigraph read at run time (ADR-A124 decision 5). `REPLACE_FORMS_MAX_R0` defaults to 3,000, since TD-42 recorded `R0` at 10,000 not finishing on Oxigraph in 8 GB.

## Other stores

`check.py --emit <file>` writes, for each family, every form's text for each size and replace, with every parameter substituted and every slot filled, the checks as count queries with their expected counts, the expected triples as N-Triples lines, the edge-case scenarios and the bare sweep queries. The index is `operations.json` and each sized run is a file of its own in `operations/` beside it, since all of them in one file came to 100 MB. [benchmark/persistence-replace-forms-jvm](../persistence-replace-forms-jvm/README.md) runs them on Jena (in memory, TDB2 on disk and Fuseki over HTTP) and RDF4J.

| File | Role |
|---|---|
| `check.py` | the forms, the workload, the engines, the checks, the probes, the witness and the report |
| `test_check.py` | the check's own tests: the workload is what it says, a right result passes, a wrong one fails, and time never does |
