<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Composite replace cost

The first benchmark under [ADR-A124](../../docs/architecture/decisions/ADR-A124-benchmark-root.md). It measures R0, the composite
replace as shipped, on rdflib and on Oxigraph ([TD-42](../../docs/developer/plans/technical-debt.md)).

The replace sweeps the root and every member of an aggregate (M stored triples) and writes a payload (N triples). Its `INSERT`
template holds the payload and is filled once per sweep solution, so a store builds M x N triples before the union removes the
copies. The check runs it with M = N from 10 to 10,000.

## Pass criterion

At every size, on every engine, the replace leaves exactly the payload where the aggregate was, the bystander aggregate and the
reference untouched, the version row at sequence 2 with the new head. **A wrong result fails the check. Time never does, and neither does memory.** No
budget exists before H5, and a check that fails on time depends on the machine. Each run is a child process under a memory cap
(`COMPOSITE_COST_MEMORY_GB`, default 8). A run that needs more is recorded as "did not finish" with its exit status. On Oxigraph 0.5.11
the replace at M = N = 10,000 is one: the engine collects the M x N insertion quads in memory before it removes the copies.

## Run it

```bash
mise run check:persistence-composite-cost             # sizes 10 to 10,000, takes about 25 minutes, most of it rdflib at 10,000
COMPOSITE_COST_MAX=1000 mise run check:persistence-composite-cost   # a quick run
```

It is never a dependency of `check`. The task installs the Oxigraph test-support package
([ADR-A125](../../docs/architecture/decisions/ADR-A125-test-support-tooling.md)) and runs the check's own tests first.

The timings and the fitted growth of each engine are written to `report.md` and `report.json` here, which are generated and
git-ignored. Both engines run the same query with the parameter guards off (Oxigraph cannot pass the guard's datatype test,
probe P5 in `tools/persistence/tests/test_store_probes.py`).

A figure quoted elsewhere states its run: the date, the engine and its version, the Python version and the kind of machine
(ADR-A124 decision 5). The report's first line carries them.

| File | Role |
|---|---|
| `check.py` | the aggregate builder, the engines, the pass criterion, the growth fit and the report |
| `test_check.py` | the check's own tests: it passes on a right result, fails on a wrong one, and does not fail on time |
