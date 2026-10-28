<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Graph naming cost on Jena and RDF4J

A benchmark under [ADR-A124](../../docs/architecture/decisions/ADR-A124-benchmark-root.md). It repeats [benchmark/persistence-graph-naming-cost](../persistence-graph-naming-cost/README.md) on Jena (an in-memory dataset and an in-memory TDB2 store) and on RDF4J's `MemoryStore`, so that the cost of a `GRAPH ?g` inside an `OPTIONAL` and of the generated named-graph replace is known beyond rdflib and Oxigraph. The finding it supports is [TSD-45](../../docs/architecture/triple-store-discovery.md), and the decision it informs is PDD-17 in the pending design decisions register.

## How it runs

The Python benchmark renders the forms, the generated `cas-replace-named-graph` for each graph naming, and the checks that say each replace did what it should, with every parameter substituted into the text, and writes them to `operations.json` (`check.py --emit`). This module reads that file and runs the same text on each store, so no store runs SPARQL that the compiler did not generate. The JSON is generated and git-ignored.

## Limiting memory

**Each measurement runs in its own JVM with a hard heap cap,** `-Xmx4g` by default. A store that holds everything in memory does not give its heap back to the JVM that ran it, so one JVM for the whole table lost every store after the first that ran out of memory, and the first attempt at this benchmark did exactly that. A measurement that exceeds the cap is recorded as "did not finish: out of memory", the larger ballasts of that store are recorded as "not run", and the run goes on. **That is not a wrong result and does not fail the run.** The parent JVM needs little memory and the table is written after every row, so a stopped run keeps what it measured. Set the limits to suit the machine.

| Property | Default | Effect |
|---|---|---|
| `-Dgraphnaming.heap=<size>` | `4g` | the heap cap of each measurement. Jena's in-memory TDB2 store needs the most. On a 15 GB machine the whole table ran at `10g`, and at `4g` only that store at 1,000,000 quads did not finish |
| `-Dgraphnaming.max=<quads>` | `1000000` | the largest ballast. `100000` needs well under 2 GB |
| `-Dgraphnaming.quick=1` | off | 10 graphs of 300 triples for the forms, and ballast up to 10,000 quads |

Because each measurement starts a fresh JVM, the small timings include warm-up, and a ratio near 1 at a small size can read as 1.5 to 2. A scan costs orders of magnitude more at the larger ballasts, so the comparison between graph namings holds.

## Pass criterion

Every form counts the triples it should, and after every replace the root's graph holds exactly the payload, the version row is at the next sequence and the ballast is untouched. **A wrong result fails the run. Time never does.** No budget exists before H5, and a check that fails on time depends on the machine.

## Run it

```bash
mise run check:persistence-graph-naming-cost-jvm
```

```bash
mise exec -- mvn -q -f benchmark/persistence-graph-naming-cost-jvm/pom.xml compile exec:exec -Dgraphnaming.quick=1
mise exec -- mvn -q -f benchmark/persistence-graph-naming-cost-jvm/pom.xml compile exec:exec -Dgraphnaming.max=100000
```

The ballast goes up to 1,000,000 quads and the run takes about ten minutes. It is never a dependency of `check`. The timings go to `report.md` here, which is generated and git-ignored, and the first line carries the date, the Java version and the versions of the stores (ADR-A124 decision 5). Both stores run in memory, so the figures are the cost of the query plan and not of a disk.

| File | Role |
|---|---|
| `pom.xml` | Jena 5.1.0 (the platform's version) and RDF4J 6.1.0 |
| `src/main/java/org/nebularis/lattice/benchmark/graphnaming/GraphNamingCost.java` | the stores, the forms, the replace and the report |
| `src/main/java/org/nebularis/lattice/benchmark/graphnaming/Rdf4jCountProbe.java` | the probe behind TSD-48, which is not part of the benchmark's run |
