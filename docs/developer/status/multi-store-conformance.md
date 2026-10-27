<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Multi-store conformance: status

**Unit ID:** `multi-store-conformance`
**Plan:** [multi-store-conformance.md](../plans/multi-store-conformance.md)
**Branch:** `multi-store-conformance`, from `ccs-trunk` at `a31dd419`, the only branch this unit commits to.
**Mode:** autonomous across the whole plan, at the maintainer's request on 2026-10-27, with up to two sub-agents. The maintainer reviews before `main`.

## Position

| Slice | State |
|---|---|
| MSC-1 | built 2026-10-27: `platform/sparql-testkit`, `tools/testing/jena`, `tools/testing/sparql_probes` with the aggregate matrix executed on Jena (352 cells as recorded), `check:conformance`, CAP-91 to CAP-94, an ADR-A125 addendum proposed |
| MSC-2 | built 2026-10-27: Jena in the persistence engines, `check:persistence-conformance` on rdflib, Oxigraph and Jena (4727 passed), nine Jena failures triaged into TSD-50 to TSD-53 with expectations per engine, one upstream report drafted (Jena `CLEAR GRAPH`), CAP-95 |
| MSC-3 | built 2026-10-27: Jena in the compilers' engines, conformance per engine for the compilers and Eligibility's reference tests, all passing on Jena first time. TSD-60, TSD-61 (rdflib departures), TD-105 (the profile read set's `?decision`, owned by CCS C9b3b), CAP-96 |
| MSC-4 | built 2026-10-27: `benchmark/persistence-store-probes`, P3 out of `check:persistence`, TSD-42 rerun with rdflib, STD-290, CAP-97. Jena's column waits on MSC-1 |
| MSC-5 | in progress |

**Next action, for us:** MSC-5, then the unit's handoff. **For the maintainer, at review:** accept or reject the ADR-A125 addendum proposed 2026-10-27, and decide whether to file the upstream reports drafted under `.local/upstream/`.

## History

- 2026-10-27: unit planned from the CCS unit's C9b3 work, which found rdflib and Oxigraph disagreeing on aggregates over a row with no value (TSD-41, TSD-43) and Oxigraph 0.5.13 changing a left join's cost (TSD-42). The maintainer asked for Jena to join every conformance run in a unit of its own, isolated from CCS. CAP-90 registered
- 2026-10-27: the maintainer handed the whole plan over to be completed autonomously on the `multi-store-conformance` branch. MSC-Q1 to MSC-Q5 answered by us with the leanings, for review. MSC-1 and MSC-4 started
- 2026-10-27: MSC-4 built and reviewed. P3 is a benchmark now, so the CCS status record's request to countersign its strict expected failure is moot, to be cleared in the CCS unit. No other timing assertion was found in any check suite
- 2026-10-27: `ccs-trunk` merged in at `a12ec491` (TSD-42's P3 sentence and STD-279 resolved). MSC-1 built and reviewed: Jena runs from Python through a test kit, the aggregate matrix runs on three engines with no cell changed, the store-probes benchmark runs Jena (it passes the outer graph binding in, ratio 1.0). `check:reasoning-isolation` now refuses any test kit outside `test` scope. `check:mork-compilers` and its conformance task pass 164 each, the reasoner tests included
- 2026-10-27: MSC-3 built and reviewed. 169 compiler tests and 67 Eligibility reference tests pass on rdflib, Oxigraph and Jena. The `?decision` probe gives unbound on Oxigraph and Jena and raises on rdflib, so the dependence is the query's, passed to the CCS unit. Two rdflib upstream reports drafted, not filed
- 2026-10-27: MSC-2 built and reviewed. Nine tests failed on Jena at first: one Jena departure from the specification (`CLEAR GRAPH` of an absent graph fails, TSD-50), the rest Jena readings the specification leaves open (TSD-51, TSD-52) and one harness conversion. No generated persistence SPARQL relied on one engine's reading. `check:persistence` unchanged at 3975 passed
