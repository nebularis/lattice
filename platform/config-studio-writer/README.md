<!-- SPDX-License-Identifier: MPL-2.0 -->

# Configuration Studio store writer

The only component that writes the Configuration Studio's store ([ADR-A136](../../docs/architecture/decisions/ADR-A136-configuration-studio.md)). Each instance joins the single-active-consumer group `lattice.studio.writers` on the writes super stream, so RabbitMQ gives it a share of the 8 partitions and moves them when an instance joins or leaves. It applies the writes waiting for it in one request, replies to the service on direct reply-to, stores each partition's offset, and deletes jobs finished longer ago than the retention. The rules it applies are in the [contract](../../contracts/config-studio/README.md#writes).

| Class | Holds |
|---|---|
| `StreamWriter` | the super stream consumer, the batch loop, the replies and the offsets |
| `Sweeper` | the hourly deletion of finished jobs, sent through the partitions like any write |
| `WriterConfig`, `WriterMain` | the settings and the wiring |

| Variable | Default | Meaning |
|---|---|---|
| `LATTICE_FUSEKI_URL` | required | Fuseki's base URL |
| `LATTICE_FUSEKI_WRITE_DATASET` | `studio-write` | the Fuseki service that updates. The service and the worker are given the one that reads |
| `LATTICE_FUSEKI_USER`, `LATTICE_FUSEKI_PASSWORD` | none | basic authentication to Fuseki |
| `LATTICE_AMQP_URI` | required | RabbitMQ's AMQP URI, for replies and the sweep |
| `LATTICE_STREAM_URI` | required | RabbitMQ's stream URI, for example `rabbitmq-stream://guest:guest@127.0.0.1:5553/%2f` |
| `LATTICE_STUDIO_JOB_RETENTION_DAYS` | `30` | days a finished job is kept |

`LATTICE_FUSEKI_PASSWORD`, `LATTICE_AMQP_URI` and `LATTICE_STREAM_URI` may each be read from a file instead, by setting `NAME_FILE` to its path, as the [operations guide](../../docs/operator/configuration-studio-operations.md#secrets-in-files) describes.

`mise run studio:up` starts one instance, and `mise run studio:writer` runs one in a terminal. Run several to share the partitions. Its tests run with `mise run check:config-studio`.
