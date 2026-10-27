<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# lattice-testing-jena

An in-memory [Apache Jena](https://jena.apache.org/) ARQ quad store for LATTICE's tests, checks and benchmarks
([ADR-A125](../../../docs/architecture/decisions/ADR-A125-test-support-tooling.md)). It is the third engine of a conformance run, beside rdflib and
[Oxigraph](../oxigraph/README.md), so that a divergence between two engines can be told from a departure from the specification.

It is **not a store SPI** and **not a runtime backend**. Its methods carry no promise to adopters, and only tests, checks and benchmarks import it.

## What it does

`JenaStore` has the methods of `OxigraphStore` (`add`, `add_all`, `remove_graph`, `update`, `select`, `quads`, `count`, and the same `$name` parameter substitution),
and adds `load` (N-Quads or TriG), `ask`, `construct`, `reset` and `close`. It speaks rdflib terms in and out, where `OxigraphStore` speaks pyoxigraph's.
`quads()` returns `Quad(subject, predicate, object, graph)` with `graph` None for the default graph.

The engine is [`platform/sparql-testkit`](../../../platform/sparql-testkit/README.md), a Java program this package starts once per Python process (the pattern of the
reasoning kit, [ADR-A83](../../../docs/architecture/decisions/ADR-A83-test-only-reasoning-engine-isolation.md)). Each `JenaStore` has a dataset of its own in that JVM. An error
the engine reports, such as a query that does not parse, is a `JenaError`. A request that fails changes nothing.

`available()` is false when the jar is not built or there is no `java`, and a test skips. `LATTICE_SPARQL_TESTKIT` overrides the jar's path,
`LATTICE_SPARQL_TESTKIT_TIMEOUT` (seconds, default 300) bounds one call, and `LATTICE_SPARQL_TESTKIT_JVM_OPTIONS` replaces the JVM options.

## Install and run

```bash
mise run bootstrap:testing-jena   # builds the jar and installs this package
mise run check:testing-jena       # this package's own tests
```
