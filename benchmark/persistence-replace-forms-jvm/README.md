<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Replace forms on Jena, Fuseki and RDF4J

A benchmark under [ADR-A124](../../docs/architecture/decisions/ADR-A124-benchmark-root.md). It repeats [benchmark/persistence-replace-forms](../persistence-replace-forms/README.md) on Jena (in memory, TDB2 on disk and Fuseki over HTTP on TDB2) and on RDF4J's `MemoryStore`, and it probes how each store applies an update. The forms are the generated named-graph replace (`R0` and `R0-nodelta`) and three **candidates the compiler does not generate yet** (`R1-candidate`, `R2-candidate` and `R2-values-candidate`). The finding it follows up is TD-42 in the technical debt register, and the update order it probes is [TSD-01](../../docs/architecture/triple-store-discovery.md).

## How it runs

The Python benchmark renders the forms of both families (named graph and composite) for each size and replace, and the checks that say each replace did what it should, with every parameter substituted and every payload slot filled, and writes them to `operations.json` and to one file per family and size in `operations/` beside it (`check.py --emit`). The edge-case scenarios and the composite family's bare sweep queries are in `operations.json`. This module reads that file and runs the same text on each store, so no store runs SPARQL that the compiler did not generate or that the candidate derivation in `check.py` did not write. The JSON is generated and git-ignored.

| Store | How it is run |
|---|---|
| `jena in-memory` | `DatasetFactory.createTxnMem()`, each update in `Txn.executeWrite` |
| `jena tdb2 (disk)` | `TDB2Factory.connectDataset` over a fresh temporary directory, deleted afterwards |
| `fuseki http (tdb2 disk)` | a `FusekiServer` in this JVM on a free port over a TDB2 dataset on disk. The update goes to the dataset's update endpoint as one HTTP request, so a two-operation form travels as one request, and queries go to the query endpoint |
| `rdf4j memory` | `MemoryStore` through a `SailRepository`, each update in its own transaction |

## Probes

The probes run first for each store and are printed as a table before the forms.

| Probe | Question |
|---|---|
| P1 | does the store remove every deletion before it adds any insertion (TSD-01's update in both row orders)? Recorded as `snapshot` or `per-solution` |
| P4 | a template quad whose graph variable is unbound. Is anything written, anywhere? |
| P2 | a request whose second operation fails. Did it fail, and is the first operation's insert kept (TSD-06, TSD-Q13)? On Fuseki the HTTP status is recorded too |
| P6 | Jena only. How many distinct blank nodes does a template with one blank node write for three solutions? |
| P7 | Fuseki only. `R0` at M = 3,000 sent with a 50 ms client timeout, so the client abandons it. Is the graph then at the old state, the new state or neither, at 2 s and later? |

`R2-candidate` and `R2-values-candidate` are run only on a store whose P1 says `snapshot`, since they are right only if the store removes every deletion before it adds any insertion.

## Edge cases and the bare sweep

For each family and for `R0`, `R1-candidate` and `R2-values-candidate`, five small cases with no timing, each on a fresh store and each checked by the same `verify` as the sized runs, reported as `pass`, `wrong: <reasons>` or `error: <message>`, one table per family with the stores as columns. E1 replaces an empty aggregate by 50 triples, E2 replaces 50 by nothing (and records whether the store lists the graph afterwards, TSD-50), E3 replaces an empty aggregate by nothing, E4 replaces 50 by the identical 50, and E5 (composite only) is E1 after checking that the root is in no triple of the data graph. A store that refuses an update is recorded as an error and not worked around. RDF4J runs `R0` only. The composite family also records how many solutions the bare sweep gives with the root in no triple, and, at M = 3,000 and 10,000, the time of the bare sweep alone, best of three.

## Limiting memory and time

**Each measurement runs in its own JVM with a hard heap cap and a wall-clock limit.** A store that holds everything in memory does not give its heap back to the JVM that ran it. A measurement that exceeds the cap or the limit is recorded as `did not finish`, the larger sizes of that form as `not run`, and the run goes on. **That is not a wrong result and does not fail the run.**

| Property | Default | Effect |
|---|---|---|
| `-Dreplaceforms.heap=<size>` | `4g` | the heap cap of each measurement |
| `-Dreplaceforms.max=<size>` | `10000` | the largest M |
| `-Dreplaceforms.maxr0=<size>` | `3000` | the largest M at which `R0` and `R0-nodelta` run |
| `-Dreplaceforms.quick=1` | off | sizes up to 1,000 |
| `-Dreplaceforms.timeout=<seconds>` | `900` | the wall-clock limit of each measurement |

## Pass criterion

After every replace the root's graph holds exactly the payload (compared as a set), the version row is at the next sequence with the new head, the add and delete graphs hold exactly the delta, the txn graph holds the claim, and no other graph changed. **A wrong result from `R0` or `R0-nodelta` fails the run. Time never does.** A wrong result from a candidate is recorded as `wrong: <reason>`.

## Run it

```bash
mise run check:persistence-replace-forms-jvm
```

```bash
mise exec -- mvn -q -f benchmark/persistence-replace-forms-jvm/pom.xml compile exec:exec -Dreplaceforms.quick=1
mise exec -- mvn -q -f benchmark/persistence-replace-forms-jvm/pom.xml compile exec:exec -Dreplaceforms.maxr0=1000
```

It is never a dependency of `check`. The results go to `report.md` here, which is generated and git-ignored, and the first line carries the date, the Java version and the versions of the stores read from the jars actually loaded (ADR-A124 decision 5).

| File | Role |
|---|---|
| `pom.xml` | Jena 5.1.0 with `jena-fuseki-main` (the platform's version) and RDF4J 6.1.0 |
| `src/main/java/org/nebularis/lattice/benchmark/replaceforms/ReplaceForms.java` | the stores, the probes, the forms of both families, the edge cases, the checks and the report |
