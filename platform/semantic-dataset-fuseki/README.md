<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Semantic dataset, Fuseki adapter

An adapter that implements the [semantic dataset SPI](../semantic-dataset-spi/README.md) over an Apache Jena Fuseki endpoint. See [Semantic platform](../../docs/architecture/semantic-platform.md).

## What it provides

`FusekiScopedDataset` takes the endpoint URL of a Fuseki dataset. Its `read` fetches the graph named by the `GraphReference` over the Graph Store Protocol with Jena's `RDFConnectionRemote`, writes it as N-Triples, and returns a `DatasetSnapshot` carrying the text and its SHA-256 hash.

It declares `NAMED_GRAPH_READ`, `NAMED_GRAPH_WRITE` and `TRANSACTIONS`. The `ScopedDataset` interface exposes only reads, so only reading is implemented. The adapter does not check the tenant or project of the reference. That check belongs to [`semantic-policy`](../semantic-policy/README.md).

## Build and test

```bash
mise run check:java
mise exec -- mvn -f platform/pom.xml -pl semantic-dataset-fuseki -am verify
```

The first command builds and tests every platform module. The second builds this module and the SPI it depends on. The module's one test checks the declared capabilities and needs no running Fuseki. A pass is a Maven `BUILD SUCCESS`.

## Depends on

`semantic-dataset-spi` and `org.apache.jena:jena-rdfconnection`, at the Jena version the platform parent POM sets.
