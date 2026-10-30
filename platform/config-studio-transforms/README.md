<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Configuration Studio transforms worker

Runs the mapping part's compiled XSLT 3.0 stylesheets and JOLT chains over a sample source in XML or JSON for the Configuration Studio, on the engines of [`platform/mork-transforms`](../mork-transforms/README.md) ([ADR-A148](../../docs/architecture/decisions/ADR-A148-mork-transform-backends.md)). It consumes `lattice.studio.transforms`, reads the compile job each request names from the store, which it never writes, and answers on the request's reply queue with a `cst:Transform` graph, each mapping's output an artefact. It stays running, so the engines and the stylesheets and chains they compiled stay warm, and a run takes milliseconds. The messages and the reply are in the [contract](../../contracts/config-studio/README.md#transforms).

| Variable | Required | Default | Meaning |
|---|---|---|---|
| `LATTICE_FUSEKI_URL` | yes | none | Fuseki's base URL |
| `LATTICE_FUSEKI_DATASET` | no | `studio` | The dataset that only reads, the service's |
| `LATTICE_FUSEKI_USER`, `LATTICE_FUSEKI_PASSWORD` | no | none | Basic authentication to Fuseki |
| `LATTICE_AMQP_URI` | yes | none | RabbitMQ's URI |

`LATTICE_AMQP_URI` and `LATTICE_FUSEKI_PASSWORD` may be read from a file named by the variable with `_FILE` added.

```bash
mise run studio:transforms
```

`mise run check:config-studio` runs its tests, which run the `policies` example's compiled transforms from `tools/mork_transforms`.
