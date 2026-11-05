## Recording a finding

- Turn the probe into a test, under `tools/persistence/tests/test_store_probes.py` or the tool it concerns, opting in to every engine with `@engines.each_engine`, so a change in a store fails a test. A probe of cost is not a test. It goes to a benchmark under `benchmark/`, which reports per engine and version and fails only on a wrong result, never on time (ADR-A124, STD-290), as `benchmark/persistence-store-probes` does for TSD-42.

## Tests that run SPARQL on an engine (replace)

- **Conformance is not part of `check`.** A test whose subject is one engine's behaviour, such as a sweep over hash seeds on rdflib or a
  probe of a TSD entry, is marked `conformance` and runs in the suite's `check:<suite>-conformance` task, with every engine we have, on
  demand and before a merge (skill `lattice-lifecycle`). A new engine joins that task and adds nothing to `check`.

A test that executes generated SPARQL opts in with `@engines.each_engine` (`tools/persistence/tests/engines.py`), so it runs on
the engines `PERSISTENCE_ENGINES` names. `check:persistence` leaves it unset, which means Oxigraph, and
`check:persistence-conformance` runs every engine we have, rdflib among them, with the tests marked `conformance`.
What the engines do differently is recorded in
[docs/architecture/triple-store-discovery.md](../../../docs/architecture/triple-store-discovery.md), and skill
`lattice-triple-stores` says how to probe and record a new difference. Two points from it matter for any such test.

- On rdflib, the order of solutions from a non-lazy join follows `PYTHONHASHSEED` (TSD-01). A test whose result depends on that
  order passes or fails by process. Fix the seed or sweep it in child processes.
- rdflib drops a result row whose projected variables are all unbound (TSD-10). Project a variable you know is bound.
- The cost of a query on rdflib depends on its form, and on Oxigraph it largely does not (TSD-22 to TSD-33). A cost measured on one
  engine is a hypothesis for the other. `mise run check:sparql-constraint-query-cost` runs the same forms on both.

**Prove conformance before trusting a new default (STD-274).** A suite that has only ever run on one engine is not known to agree with another, however routine switching its default sounds. Giving `tools/mork_compilers` an engine abstraction so its own `check:mork-compilers-conformance` could try Oxigraph found a real divergence on one of its 126 tests, a `GROUP_CONCAT` over a group with an unbound row that is unbound on Oxigraph and skips the row on rdflib (TSD-41, fixed 2026-10-27). Once the whole suite, its reasoner tests included, passed on both, Oxigraph became its default and the conformance task now runs rdflib. Run the whole suite on the candidate default first, with every test passing, before flipping it: where it does not, keep the suite's current engine as the default, add the conformance task anyway so the divergence stays visible, and record what you found as a store-discovery finding, not something the suite quietly works around.

## Stores and how to reach them

## Stores and how to reach them

| Store | Reached through | Install | Run its cases |
|---|---|---|---|
| rdflib | `rdflib.Dataset`, in the test process, parameters as `initBindings` | part of every Python bootstrap | `mise run check:persistence` |
| Oxigraph | `tools/testing/oxigraph` (ADR-A125), parameters substituted as text | `mise run bootstrap:testing-oxigraph` | `mise run check:persistence` (the default engine), `mise run check:persistence-conformance` |
| Apache Jena ARQ | `tools/testing/jena` (MSC-1), in-memory, one JVM per Python process from `platform/sparql-testkit`, parameters substituted as text, rdflib terms in and out | `mise run bootstrap:testing-jena` (builds the jar, needs Java) | conformance runs only: `mise run check:sparql-probes-conformance`, and `mise run check:conformance` for every conformance task |

Engine probes that are not about one tool (the aggregate matrix, TSD-43) live in `tools/testing/sparql_probes` and run on all three engines, with the expected result per engine recorded beside the cases.

## Measuring cost

`benchmark/sparql-constraint-query-cost` is the one for query forms, and `mise run check:sparql-constraint-query-cost` runs it.
