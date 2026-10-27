<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Store probes: a graph variable bound outside an OPTIONAL

A benchmark under [ADR-A124](../../docs/architecture/decisions/ADR-A124-benchmark-root.md), for the store finding
[TSD-42](../../docs/architecture/triple-store-discovery.md#tsd-42-a-graph-variable-bound-outside-an-optional-makes-oxigraph-0513-read-every-graph)
and the open question TSD-Q22. It replaces probe P3 of `tools/persistence/tests/test_store_probes.py`, a timing assertion that
`check:persistence` no longer carries.

The named-graph replace's sweep reads one root's graph, with the graph IRI bound outside a left join. Whether an engine passes that
binding into the `GRAPH ?g` pattern decides if the sweep reads one graph or every graph in the store. Four forms count the 3,000 triples
of one graph.

| Form | Query shape |
|---|---|
| bind-optional | `BIND(<g> AS ?g) OPTIONAL { GRAPH ?g { ?s ?p ?o } }` |
| values-optional | `VALUES ?g { <g> } OPTIONAL { GRAPH ?g { ?s ?p ?o } }` |
| join | `BIND(<g> AS ?g) GRAPH ?g { ?s ?p ?o }` |
| constant | `GRAPH <g> { ?s ?p ?o }` |

Each form runs against a store of 1 graph and a store of 100 graphs of the same size, best of five. The two controls, join and constant,
show what a ratio looks like when the engine reads one graph.

## What a result means

The report gives, per form, engine and engine version, the **ratio** of the time over 100 graphs to the time over 1. About 1 means the
engine reads one graph. About 100 means it reads every graph. A ratio between 1 and 3 on rdflib comes from a larger dataset and appears in
the constant form too, so it is not a scan. A cost is a hypothesis across machines and across patch versions of one engine
(STD-176, TSD-40), so a figure quoted elsewhere states its run (ADR-A124 decision 5). The first line of the report gives it.

## Pass criterion

Every form returns the triple count of the graph, on every engine. **A wrong count fails the check. Time never does.** The report is
`report.md` and `report.json` here, which are generated and git-ignored.

## Run it

```bash
mise run check:persistence-store-probes
STORE_PROBES_QUICK=1 mise run check:persistence-store-probes   # 20 graphs of 500 triples
```

It is never a dependency of `check`. It runs rdflib and Oxigraph, and Jena when `tools/testing/jena` is importable and its
`available()` is true, and prints a note when Jena is skipped. To measure another Oxigraph release, install it outside the
repository and put it first on `sys.path`.

```bash
mise exec -- python -m pip install --target "$SCRATCH/ox" pyoxigraph==0.5.12
```

Then run `check.py` from a short script that inserts `$SCRATCH/ox` at the front of `sys.path` and calls `runpy.run_path` on it, under
`python -I`.

TSD-40's property path forms are not here. They need the ledger store of `benchmark/ledger-posting-cost`.

| File | Role |
|---|---|
| `check.py` | the four forms, the engine list, the pass criterion and the report |
| `test_check.py` | the check's own tests, including that a wrong count fails it, and that time does not |
