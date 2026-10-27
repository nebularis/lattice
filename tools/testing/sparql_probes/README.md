<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# lattice-testing-sparql-probes

Probes of how SPARQL engines behave, for questions that are not about one tool ([ADR-A125](../../../docs/architecture/decisions/ADR-A125-test-support-tooling.md)). Each probe runs on rdflib, Oxigraph and Apache Jena ARQ, and records what each engine is expected to return, so a divergence between engines shows, and an engine that changes shows too. The findings are in [the store-discovery record](../../../docs/architecture/triple-store-discovery.md).

| Module | Holds |
|---|---|
| `sparql_probes.engines` | the registry of engines (`REGISTRY`), `run_query(graph, text, engine)` with rows that read the same on each, and `available()` |
| `sparql_probes.aggregate_error_cases` | the aggregate-over-an-error matrix ([TSD-43](../../../docs/architecture/triple-store-discovery.md)): data states, 13 aggregates, four remedies and a three-group probe |
| `sparql_probes.aggregate_error_expected` | what each engine returned for every case |
| `tests/test_aggregate_errors.py` | AE-01 to AE-23 |

A probe takes the expected result per engine, so a test that cannot pass on one engine is an expectation for that engine with the finding's id, never a skip. To add an engine, add its name to `engines.REGISTRY` and a branch to `run_query`, then record its column.

```bash
mise run bootstrap:testing-sparql-probes   # this package, the Oxigraph and Jena engines and the Jena testkit jar
mise run check:sparql-probes-conformance   # every probe on all three engines (on demand and before a merge)
```
