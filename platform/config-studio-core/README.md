<!-- SPDX-License-Identifier: MPL-2.0 -->

# Configuration Studio core

What the [service](../config-studio-service/README.md) and the [store writer](../config-studio-writer/README.md) share ([ADR-A136](../../docs/architecture/decisions/ADR-A136-configuration-studio.md)). It runs nothing by itself.

| Package | Holds |
|---|---|
| `store` | `StudioStore` over Jena's `RDFConnection`, in memory or on Fuseki, the graph IRIs (`Graphs`) and the `cst:` terms (`Cst`) |
| `model` | `Workspace`, the description in a workspace's own graph, and `Parts`, which decides which part a subject belongs to |
| `writes` | `Command` and `Codec` (AMQP headers and N-Quads), `Reply`, `Writer`, which checks a batch of commands and applies it in one guarded, receipted request, `DirectWrites` in process, and `RabbitWrites`, which publishes a command to its partition of the writes super stream and waits for the reply |
| `jobs` | `Topology`, the exchanges, queues and super stream every component declares, and `Amqp`, named connections |

The rules a write follows are in the [contract](../../contracts/config-studio/README.md#writes). The service's tests exercise `Writer` and `RabbitWrites`' codec through the API, with every request sent as SPARQL text.
