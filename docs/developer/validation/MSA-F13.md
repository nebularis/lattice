<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: MSA-F13, the Java topology refuses a queue bound to an exchange it does not declare

**Unit:** [`multi-store-architecture`](../status/multi-store-architecture.md)
**Plan:** [multi-store-architecture](../plans/multi-store-architecture.md), MSA-F13, from the review of [MSA-F4](MSA-F4.md), and the first of the three points for other work in section 4.7 of the [brief of 2026-11-19](../notes/machine-s-brief-2026-11-19-multi-store.md)
**Machine:** machine S, Windows, Java 25 through mise, Maven 3.9.16, Python from the worktree's `.venv`. **Placement:** T0, public. The studio's broker topology, nothing domain-specific.
**Status:** built 2026-11-19, not verified.

## Invariant

The Python worker and the Java service refuse the same topologies. Since MSA-F4 the worker's `declare_topology` refuses a queue whose `bindsTo` or `deadLettersTo` names an exchange the topology does not declare. The service's `Topology.declare` declared such a queue and bound it, and the broker then answered with a channel error at the bind. It now refuses the queue as the worker does, with the same exception class in kind, an `IllegalArgumentException` for Python's `ValueError`, and the same message, before it declares that queue.

## Change

- `jobs/Topology.java`. `declare(Channel)` calls a new public `declare(Channel, JsonObject)` with the contract on the classpath, as the worker's `declare_topology` takes its topology as an argument. The new method checks both fields of each queue against the two exchanges before it declares the queue. The message is the worker's: `queue <name>: <field> names <exchange>, which the topology does not declare`.
- `TopologyTest.java`. The recording channel is now a helper both tests use, and one test is added.
- `workers/tests/test_config_studio_worker.py`. One test is added with the same case. The brief has the worker's refusal tested already. It was not: `git grep -n "bindsTo" -- workers tools` finds the check in `config_studio_worker.py` and no test of it, so this slice adds it.
- `spikes/multi-store-emitted-topology/compare.py`. Its reader of `Topology.java` looked for the declaring rule in `declare(Channel)`, which now only delegates. It now reads `declare(Channel, JsonObject)` when that exists, and looks for the rule's parts anywhere in that method, since the list of exchanges is now built before the loops.
- `docs/operator/configuration-studio-operations.md`. The topology section says both runtimes refuse such a queue.

## Tests

| ID | Given / When / Then | Level | Invariant | Pass criterion | Kind |
|---|---|---|---|---|---|
| F13-T1 | Given the contract with the transforms queue's `bindsTo` set to `lattice.studio.nowhere`, when the service declares it on a recording channel, then `IllegalArgumentException` is thrown with the message `queue lattice.studio.transforms: bindsTo names lattice.studio.nowhere, which the topology does not declare`, and no call names the transforms queue | L3 | the service refuses as the worker does | `TopologyTest.theServiceRefusesAQueueBoundToAnExchangeItDoesNotDeclare` passes | negative |
| F13-T2 | Given the packaged topology with the same change, when the worker declares it on a recording channel, then `ValueError` is raised with the same message, and no call names the transforms queue | L3 | the worker's refusal, the same case | `test_the_worker_refuses_a_queue_bound_to_an_exchange_it_does_not_declare` passes | negative |
| existing | F4-T1 to F4-T3, the declared calls and the constants, unchanged | L3 | MSA-F4's | pass | positive |

F13-T2 could not fail first. The worker's refusal is MSA-F4's, and the test only pins it with the case F13-T1 uses.

## Commands and results

Run on 2026-11-19.

| Command | Result |
|---|---|
| `mise exec -- mvn -f platform/pom.xml -pl config-studio-service -am test -Dtest=TopologyTest -Dsurefire.failIfNoSpecifiedTests=false`, before any change to `Topology.java` | BUILD FAILURE at test compilation: `method declare in class org.nebularis.lattice.studio.jobs.Topology cannot be applied to given types; required: com.rabbitmq.client.Channel; found: com.rabbitmq.client.Channel,org.apache.jena.atlas.json.JsonObject` |
| the same, with `declare(Channel, JsonObject)` added and no check | Tests run: 4, Failures: 1. F13-T1: `Expected java.lang.IllegalArgumentException to be thrown, but nothing was thrown.` |
| the same, after the fix | Tests run: 4, Failures: 0, Errors: 0. BUILD SUCCESS |
| `mise exec -- python -m pytest workers/tests/test_config_studio_worker.py -q -k "refuses_a_queue_bound or declares_each_queue"` | 2 passed, 72 deselected |
| `mise exec -- python spikes/multi-store-emitted-topology/compare.py`, after the change and before the reader's change | exit 1, `Topology.java` read as declaring nothing, every call listed as only in the declaration and the worker |
| the same, after the reader's change | exit 1 on the two differences MSA-F4's pack names, which are not this slice's: the events exchange that only the declaration holds, and the reader group that `Topology.java` does not hold. The declaration, the worker and the service make the same 27 calls |
| `mise run check:workers` | exit 0, 214 passed |
| `mise run check:config-studio` | exit 0. pytest 159 passed, JUnit 253 tests across the studio's modules with 0 failures and 0 errors (the service's 198, the core's 24, the writer's 20, the authoring module's 9, the transforms module's 2), the browser checks `Tests 121 passed (121)` |

The one command for the slice is `mise run check:config-studio`, with `mise run check:workers` for the worker.

## What an upgrade has to unbind

A broker that a worker from before MSA-F4 declared holds one binding the contract no longer has. That worker read `deadLetter: false` as "bind to the dead-letter exchange", so it bound the transforms queue there. The service bound the same queue to `lattice.studio`, so such a broker holds both bindings.

| Source exchange | Destination queue | Routing key | Arguments |
|---|---|---|---|
| `lattice.studio.dlx` | `lattice.studio.transforms` | `lattice.studio.transforms` | none |

The operator guide's table of the topology has the transforms queue bound to `lattice.studio` with key `lattice.studio.transforms` only. Declaring again adds what is missing and removes nothing, so the old binding stays after an upgrade. The queue's own arguments did not change, since both the old and the new declaration give it none, so the upgrade meets no conflicting declaration.

Read from the code, the binding routes nothing the studio sends. The jobs queues dead-letter with their own routing keys, and the transforms queue dead-letters nowhere. A message published to `lattice.studio.dlx` with key `lattice.studio.transforms` would reach the transforms queue as well as `lattice.studio.dead`. This was not observed on a broker.

An operator sees the binding with the command the guide's health table uses:

```
mise exec -- .build/config-studio/infra/rabbitmq_server-4.4.0/sbin/rabbitmqctl -n studio@localhost list_bindings source_name destination_name routing_key
```

and finds a line with `lattice.studio.dlx`, `lattice.studio.transforms` and `lattice.studio.transforms`. We know of no `rabbitmqctl` command that deletes a binding. The stack's RabbitMQ is not installed on this machine, so its help was not read. Where the management interface runs, in the Docker setup on `127.0.0.1:15673`, the binding is deleted through the HTTP API as the broker's user `studio`. A binding with no arguments has its routing key as its properties key:

```
curl -u studio -X DELETE http://127.0.0.1:15673/api/bindings/%2F/e/lattice.studio.dlx/q/lattice.studio.transforms/lattice.studio.transforms
```

`curl` asks for the password, which the stack keeps in `.build/config-studio/infra/broker`. Without the management interface, an AMQP client connected as `studio` sends `queue.unbind` with the same three names, for example pika's `channel.queue_unbind(queue="lattice.studio.transforms", exchange="lattice.studio.dlx", routing_key="lattice.studio.transforms")`.

Removing the binding is the unit [component-administration](../plans/component-administration.md)'s, which is planned. This slice builds no removal, no command and no step in `studio:up`, and changes no topology on a broker.

## Deliberate non-coverage

- No broker was run. Both refusals are recorded on a channel. Neither command for the stale binding was run.
- The `deadLettersTo` half of the check has no case of its own on either side. The same loop checks both fields in each runtime, and the brief names `bindsTo`.
- Neither runtime checks the whole topology before it declares anything. The exchanges and the queues before a refused queue are declared, in both, as the worker did before this slice. F13-T1 and F13-T2 assert only that the refused queue is not declared.
- A missing field, as against a null one, is not handled alike. The worker raises `KeyError` and the service a `NullPointerException`. Both read a contract that `test_topology_copy_equals_contract` and `theConstantsEqualTheContractFile` hold to the file.

## Decisions taken

- **An argument, not a second resource.** The test needs a contract with a fault in it. A public `declare(Channel, JsonObject)` gives the service the worker's shape, where the topology is an argument, and keeps `declare(Channel)` for every caller.
- **The worker's message, word for word.** The two refusals then read alike in a log, and the two tests assert the same string.
