<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: MSA-F4, each queue's binding and dead-lettering stated once

**Unit:** [`multi-store-architecture`](../status/multi-store-architecture.md)
**Plan:** [multi-store-architecture](../plans/multi-store-architecture.md), MSA-F4, from finding MSAI12-01 of [MSA-I12](MSA-I12.md)
**Machine:** machine S, Windows, Java 25 through mise, Maven 3.9.16, Python from the worktree's `.venv`. **Placement:** T0, public. The studio's broker topology, nothing domain-specific.
**Status:** built 2026-11-18, not verified.

## Invariant

The Python worker and the Java service declare the same broker objects, and both declare them from the contract. The contract's boolean `deadLetter` meant two things, so the worker bound `lattice.studio.transforms` to the dead-letter exchange, where nothing routes a transforms request, while the Java service bound it to `lattice.studio` (MSAI12-01). Each queue now has two fields whose names say what they mean, `bindsTo`, the exchange the queue is bound to, and `deadLettersTo`, the exchange it dead-letters to or null for none. The worker's `declare_topology` and the service's `Topology.declare` both declare each queue from them, and both refuse nothing new, since every queue names an exchange the contract declares. The operator guide's table of broker objects is what both are tested against.

## Change

- `contracts/config-studio/amqp-topology.json` and its packaged copy `workers/src/lattice_workers/config-studio-topology.json`, byte-identical as before, with `bindsTo` and `deadLettersTo` in place of `deadLetter`.
- `config_studio_worker.py`, `declare_topology` reads the two fields and refuses a field that names an exchange the contract does not declare.
- `jobs/Topology.java`, `declare` reads the contract, which `config-studio-core`'s build now puts beside the class, and declares the exchanges and queues from it. The names stay constants for the code that publishes and consumes. The super stream is declared as before.
- `TopologyTest.java`, which matched strings in the file, now parses it with Jena's JSON reader, and records what `Topology.declare` sends on a channel.
- `spikes/multi-store-emitted-topology`, whose emitter writes the new structure and whose comparison derives the Java service's queue calls from the contract by the rule `Topology.declare` implements.

## Tests

| ID | Given / When / Then | Level | Invariant | Pass criterion | Kind |
|---|---|---|---|---|---|
| F4-T1 | Given the packaged topology, when the worker declares it on a recording channel, then the ten exchange, queue and binding calls are the operator guide's, the transforms queue bound to `lattice.studio` with no dead-lettering | L3 | the worker declares what the contract says | `test_the_worker_declares_each_queue_where_the_contract_binds_it` passes | negative |
| F4-T2 | Given the contract on the classpath, when the service declares on a recording channel, then its first ten calls are the same list | L3 | the service declares the same objects | `TopologyTest.theServiceDeclaresEachQueueWhereTheContractBindsIt` passes | positive |
| F4-T3 | the Java constants against the parsed contract | L3 | the names agree | `TopologyTest.theConstantsEqualTheContractFile` passes | positive |
| F4-T4 | the packaged copy against the contract | L3 | one contract | `test_topology_copy_equals_contract` passes | positive |
| F4-T5 | the spike's comparison of the declaration, the three JSON files, the worker and the service | L3 | no difference for the queues' bindings | `compare.py` prints no difference for MSAI12-01 | positive |

## Commands and results

Run on 2026-11-18.

| Command | Result |
|---|---|
| `mise exec -- python -m pytest workers/tests/test_config_studio_worker.py -q -k "declares_each_queue or topology_copy"`, before the change | 1 failed, 1 passed. F4-T1 at the eighth call: the transforms queue bound to `lattice.studio.dlx` where `lattice.studio` was expected |
| the same, after the change | 2 passed |
| `mise exec -- mvn -q -f platform/pom.xml -pl config-studio-service -am test -Dtest=TopologyTest -Dsurefire.failIfNoSpecifiedTests=false` | 3 tests, 0 failures |
| `mise run check:workers` | exit 0, 213 passed |
| `mise run check:config-studio` | exit 0. pytest 158 passed, JUnit 235 tests across the studio's modules with 0 failures (the service's 186), the browser checks 121 passed |
| `mise exec -- python spikes/multi-store-emitted-topology/emit.py` | exit 0, both emitted JSON files byte-identical to the two hand copies |
| `mise exec -- python spikes/multi-store-emitted-topology/compare.py` | exit 1 on two differences that are not this slice's, the events exchange that only the declaration holds and the reader group that `Topology.java` does not hold. The declaration, the worker and the service make the same 27 calls, with no difference for the transforms binding |

The one command for the slice is `mise run check:config-studio`, with `mise run check:workers` for the worker.

## Deliberate non-coverage

- No broker was run. Both declarations are recorded on a channel, and what a broker does with them is RabbitMQ's.
- The types of the two exchanges are still not in the contract (MSAI12-03), and both runtimes declare them `topic`. The events exchange and the reader group remain outside the contract, as the comparison prints. They are not this slice's.
- The spike derives the service's queue calls from the contract and does not run the Java. The Java's own calls are F4-T2's.

## Decisions taken

- **Two fields, not a renamed boolean.** Where a queue binds and whether it dead-letters are two facts, and the defect came from reading one from the other.
- **The service reads the contract.** The brief asks that both declare from the contract. The names stay constants, since publishers and consumers use them, and F4-T3 holds them to the file.
