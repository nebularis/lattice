<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Platform outbox

A transactional outbox for CloudEvents, and a relay that publishes pending records to a broker. See [Semantic platform](../../docs/architecture/semantic-platform.md) and [ADR-A30](../../docs/architecture/decisions/ADR-A30-shared-semantic-platform-cross-runtime-boundary.md).

## What it provides

| Type | Role |
|---|---|
| `CloudEvent` | A record of ID, source URI, type, subject, time, string extensions and string data. |
| `OutboxRecord` | A `CloudEvent` with an ID, a non-blank idempotency key, a creation time and a `PENDING` or `PUBLISHED` status. |
| `TransactionalOutbox` | `enqueue(idempotencyKey, event)`, `pending()` and `markPublished(record)`. |
| `InMemoryTransactionalOutbox` | The one implementation. Enqueueing again with the same idempotency key yields the existing record. It holds state in memory only. |
| `EventPublisher` | One method, `publish(CloudEvent)`. |
| `RabbitMqEventPublisher` | Publishes to a durable topic exchange with the event type as routing key. `declareTopology` declares the exchange, a dead-letter exchange and a queue bound to `#`. |
| `OutboxRelay` | `relayPending()` publishes each pending record and marks it published. A record whose publication throws stays pending for the next run. |

There is no durable persistence in this module. A SQL-backed outbox would implement `TransactionalOutbox`.

## Build and test

```bash
mise run check:java
mise exec -- mvn -f platform/pom.xml -pl platform-outbox -am verify
```

The first command builds and tests every platform module. The second builds this one. The tests cover idempotent enqueue and a failed publication staying pending, and use no broker. A pass is a Maven `BUILD SUCCESS`.

## Depends on

`com.rabbitmq:amqp-client`. It has no dependency on the other platform modules.
