<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# SPARQL constraint query cost

A benchmark under [ADR-A124](../../docs/architecture/decisions/ADR-A124-benchmark-root.md). It measures the forms of a
SHACL-SPARQL constraint query that mattered when we made the ontology tests faster, on rdflib and on Oxigraph, and is the
evidence for the rules in [Efficient queries and shapes](../../docs/architecture/efficient-queries-and-shapes.md)
([ADR-A128](../../docs/architecture/decisions/ADR-A128-efficient-queries-and-shapes.md)).

A SHACL-SPARQL constraint runs once per focus node, with `$this` bound to the node. Each experiment is a pair of queries
that return the same solutions, a naive form and an improved one, run for every focus node of a synthetic graph whose size
grows. The data is synthetic and domain-neutral, so the experiments reproduce a mechanism and not a particular shape.

| Experiment | The naive form | The improved form | Findings |
|---|---|---|---|
| E1 | a pattern that types a variable bound by an earlier pattern | the same test as `FILTER EXISTS`, once the variable is bound | TSD-25 |
| E2 | a uniqueness test that joins every other node | the same test as a lookup on the value, in `FILTER EXISTS` | TSD-25, TSD-26 |
| E3 | cheap guards in the same group as an enumeration | the guards in a group of their own, ahead of it | TSD-27 |
| E4 | an absence test as `OPTIONAL` and `FILTER(!BOUND)` | the same test as `FILTER NOT EXISTS` | TSD-28 |
| E5 | a constraint query handed over as text on every run | the same query parsed once | TSD-22 |

## Pass criterion

In every experiment, at every size, on every engine, the two forms return the same number of solutions for every focus
node, and the engines agree with each other. **A wrong result fails the check. Time never does.** What a form costs depends
on the engine and the machine, and that is what the check reports. The report is `report.md` and `report.json` here, which
are generated and git-ignored. Its first line gives the run: the date, the engines and their versions, Python, and the kind
of machine.

Each query projects `COUNT(*)`, not `$this`. The Oxigraph adapter substitutes the parameter as text, and `SELECT <iri>` is
not SPARQL. The count also makes the engine enumerate every solution, as a constraint does when it reports.

## Run it

```bash
mise run check:sparql-constraint-query-cost             # about one minute
SPARQL_COST_QUICK=1 mise run check:sparql-constraint-query-cost   # the two smallest sizes of each experiment
```

It is never a dependency of `check`. The task installs the Oxigraph test-support package
([ADR-A125](../../docs/architecture/decisions/ADR-A125-test-support-tooling.md)) and runs the check's own tests first.

| File | Role |
|---|---|
| `check.py` | the experiments, the two engines, the pass criterion, the growth fit and the report |
| `test_check.py` | the check's own tests: it passes when the forms agree, fails on a wrong result or a disagreeing engine, and does not fail on time |
