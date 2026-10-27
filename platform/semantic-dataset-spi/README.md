<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Semantic dataset SPI

The store-neutral interface the other platform modules use to read a graph. It has no dependencies beyond the JDK. See [Semantic platform](../../docs/architecture/semantic-platform.md) and [ADR-A30](../../docs/architecture/decisions/ADR-A30-shared-semantic-platform-cross-runtime-boundary.md).

## What it provides

| Type | Role |
|---|---|
| `GraphReference` | A record of tenant ID, project ID, absolute HTTP(S) graph IRI and revision hash. All four must be present, and the IRI must be absolute. It is the scoped, immutable reference that crosses runtimes. |
| `ScopedDataset` | The interface an adapter implements. It reports its `capabilities()` and reads one graph with `read(GraphReference)`. |
| `DatasetCapability` | `NAMED_GRAPH_READ`, `NAMED_GRAPH_WRITE`, `REVISION_EXPORT` and `TRANSACTIONS`. |
| `DatasetSnapshot` | A record of the reference, the graph text and its content hash. |

## Build and test

The module is built by the platform Maven reactor, which `mise` runs.

```bash
mise run check:java
mise exec -- mvn -f platform/pom.xml -pl semantic-dataset-spi -am verify
```

The first command builds and tests every platform module. The second builds only this one. A pass is a Maven `BUILD SUCCESS`.

## Used by

`semantic-dataset-fuseki` implements the interface. `semantic-policy`, `release-integration` and `surface-workflow` take `GraphReference` from it.
