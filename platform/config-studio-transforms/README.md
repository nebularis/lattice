<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Configuration Studio run worker

The transforms worker of ADR-A148, which is also the run worker of [ADR-A154](../../docs/architecture/decisions/ADR-A154-runs-in-the-configuration-studio.md). Runs the mapping part's compiled XSLT 3.0 stylesheets and JOLT chains over a sample source in XML or JSON for the Configuration Studio, on the engines of [`platform/mork-transforms`](../mork-transforms/README.md) ([ADR-A148](../../docs/architecture/decisions/ADR-A148-mork-transform-backends.md)). It consumes three queues, each on a channel and a pool of threads of its own. It reads the compile job each request names from the store, which it never writes. A request on `lattice.studio.transforms` is answered on the request's reply queue with a `cst:Transform` graph, each mapping's output an artefact. A request on `lattice.studio.runs` is a `sample` run, which it answers as numbered frames published to `lattice.studio.events`, a report part and one artefact part for each mapping, each frame at most 49,152 bytes of UTF-8 and a run at most 128 frames, and stops at its deadline. A run the broker redelivers is answered with a failed frame and not run again. A request on `lattice.studio.runs.interactive` is a `simulate` run. A step of target `persistence` is run over a fresh in-memory Apache Jena dataset made from the TriG's sample world, with the Java caller library of ADR-A132 checking and binding the generated operation, each `NOW()` of the update replaced by the step's stated time, and is answered as the four parts `check`, `request`, `delta` and `outcome`, defined in the contract's [A persistence step](../../contracts/config-studio/README.md#a-persistence-step). A step of target `surface` is answered with a failed frame until that simulator is built. Both ways run the same execution. It stays running, so the engines and the stylesheets and chains they compiled stay warm, and a run takes milliseconds. The messages and the reply are in the [contract](../../contracts/config-studio/README.md#transforms), and the runs and their frames in its [Runs](../../contracts/config-studio/README.md#runs) section.

| Variable | Required | Default | Meaning |
|---|---|---|---|
| `LATTICE_FUSEKI_URL` | yes | none | Fuseki's base URL |
| `LATTICE_FUSEKI_DATASET` | no | `studio` | The dataset that only reads, the service's |
| `LATTICE_FUSEKI_USER`, `LATTICE_FUSEKI_PASSWORD` | no | none | Basic authentication to Fuseki |
| `LATTICE_AMQP_URI` | yes | none | RabbitMQ's URI |
| `LATTICE_RUNS_INTERACTIVE_CONCURRENCY` | no | `2` | The requests handled at once from `lattice.studio.runs.interactive` |
| `LATTICE_RUNS_CONCURRENCY` | no | `2` | The requests handled at once from `lattice.studio.runs` |

`LATTICE_AMQP_URI` and `LATTICE_FUSEKI_PASSWORD` may be read from a file named by the variable with `_FILE` added.

```bash
mise run studio:transforms
```

`mise run check:config-studio` runs its tests, which run the `policies` example's compiled transforms from `tools/mork_transforms`.
