<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Graph naming cost

A benchmark under [ADR-A124](../../docs/architecture/decisions/ADR-A124-benchmark-root.md). It measures what a `GRAPH ?g` inside an `OPTIONAL` costs on rdflib and Oxigraph, and what that makes the generated named-graph replace cost under each graph naming of the persistence compiler. The finding it supports is [TSD-45](../../docs/architecture/triple-store-discovery.md), and the decision it informs is PDD-17 in the pending design decisions register.

## What it measures

**Forms.** A `SELECT (COUNT(*) …)` with `?g` bound by a constant `BIND`, a constant `VALUES`, or an expression computed as the compiler computes the root's graph name, inside an `OPTIONAL` or in the enclosing group, over 100 graphs of 3,000 triples against 1 graph. A ratio near 1 means the store passed `?g` into the pattern and read one graph. A ratio near 100 means it read every graph. The last form binds nothing and is the scale.

**Replace.** The generated `cas-replace-named-graph` with `graph_names="query"` (the default, where the query computes `?g` from `$root`) and `graph_names="caller"` (the caller passes `$g`), against a store that also holds ballast, which is aggregates of 100 triples each in other graphs. The report fits the cost to the ballast.

## Pass criterion

At every size, on every engine, each replace leaves exactly the payload in the root's graph, the ballast untouched and the version row at the next sequence, and every form counts the triples it should. **A wrong result fails the check. Time never does.** No budget exists before H5, and a check that fails on time depends on the machine.

## Run it

```bash
mise run check:persistence-graph-naming-cost                       # ballast up to 1,000,000 quads (rdflib stops at 100,000), about 2 minutes
GRAPH_NAMING_QUICK=1 mise run check:persistence-graph-naming-cost  # the smallest sizes
GRAPH_NAMING_MAX=100000 mise run check:persistence-graph-naming-cost
```

It is never a dependency of `check`. The task installs the Oxigraph test-support package ([ADR-A125](../../docs/architecture/decisions/ADR-A125-test-support-tooling.md)) and runs the check's own tests first. The timings go to `report.md` and `report.json` here, which are generated and git-ignored, and the first line of the report carries the date, the Python version and the versions of the engines (ADR-A124 decision 5).

## Other stores

`check.py --emit <file>` writes the forms and the generated operations, with every parameter substituted, so that a runtime other than Python can repeat the measurements. [benchmark/persistence-graph-naming-cost-jvm](../persistence-graph-naming-cost-jvm/README.md) does it for Jena and RDF4J.

## Another Oxigraph version

The task runs the version the checkout has. TSD-45 compares 0.5.11, 0.5.12 and 0.5.13. To repeat that, make a scratch environment per version with `mise exec -- python -m venv <dir>`, install `pyoxigraph==<version>`, `rdflib` and `pytest` into it with `<dir>/bin/python -m pip install`, and run `PYTHONPATH=tools/persistence/src:packages/persistence/python/src:tools/testing/oxigraph/src mise exec -- <dir>/bin/python benchmark/persistence-graph-naming-cost/check.py` from the repository root. Never install another version into the checkout's own `.venv`.

| File | Role |
|---|---|
| `check.py` | the forms, the engines, the generated operations, the pass criterion and the report |
| `test_check.py` | the check's own tests: it passes on a right result, fails on a wrong one, and does not fail on time |
