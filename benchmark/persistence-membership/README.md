<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Membership cost

A benchmark under [ADR-A124](../../docs/architecture/decisions/ADR-A124-benchmark-root.md), for formal-methods slice H2.6f. It keeps a set of 500
members across 1, 10 and 100 versions, one member replaced per version, in three ways, on rdflib and on Oxigraph.

| Strategy | Each version stores | A read of the current members |
|---|---|---|
| full (`dal:AppendVersions`, `dal:FullMembership`) | every member | one lookup |
| delta (`dal:DeltaMembership`, checkpoint every 16) | one add and one drop, and a full list every 16th version | the generated `members` query |
| in-place (a composite replace under `dal:PatchLog`) | the whole aggregate rewritten, with the add and del graphs logging the change | one lookup |

## Pass criterion

After the last version, on each engine, the members read equal the model's, and the stored triples have the count the strategy's arithmetic gives.
**A wrong member set or count fails the check. Time never does.** The seconds of the last write, of all the writes and of one read go to `report.md`
and `report.json` here, which are generated and git-ignored. A figure quoted elsewhere states its run (ADR-A124 decision 5), as the report's first line does.

## Run it

```bash
mise run check:persistence-membership
MEMBERSHIP_COST_MAX=10 mise run check:persistence-membership   # a quick run
```

It is never a dependency of `check`. The guards are off, as in the composite replace benchmark. The in-place replace is the composite
replace of TD-42, so its writes grow with the square of the aggregate.

| File | Role |
|---|---|
| `check.py` | the three histories, the pass criterion and the report |
| `test_check.py` | the check's own tests, including that a query that ignores drops and a wrong count fail it, and that time does not |
