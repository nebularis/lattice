<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: MSA-I12, the studio's topology from one declaration

**Unit:** [`multi-store-architecture`](../status/multi-store-architecture.md)
**Plan:** [multi-store-architecture](../plans/multi-store-architecture.md), MSA-I12
**Machine:** a Windows laptop, Python from the worktree's `.venv` through mise, and the sibling `vyvid` checkout's interpreter for the quanta. **Placement:** T0, public. Platform configuration, nothing domain-specific.
**Status:** authored and run, not accepted. The maintainer's review is the sign-off.

## Scope

- `spikes/multi-store-emitted-topology/declaration.json`, the studio's broker topology stated once in logical terms, with its units and who publishes and consumes.
- `emit.py`, which emits both JSON copies and a Java fragment from it. `compare.py`, which runs the real Python worker's `declare_topology` and `declare_writes` against a recording channel, reads `Topology.java` and prints every difference from the declaration. `quanta.py`, which derives software quanta with vyvid's `software_quanta` from compose and from the declaration.
- Out of scope. Any change to the three hand copies, to `Topology.java` or to the worker. The emitted Java is not compiled, and no broker was run.

## Result in one paragraph

The falsifier does not fire for the topology the three copies state. The declaration expressed all 27 channel calls, the 8 partitions and their arguments, the partition function (checked on 2002 workspace ids), the reader group and its mode, the batch limit and each lane's prefetch, and the emitted JSON is byte-identical to both hand copies. It also expressed one binding that the existing JSON structure cannot, and that the hand copies disagree on: the Python worker binds `lattice.studio.transforms` to the dead-letter exchange and `Topology.java` binds it to the main exchange. The declaration does not carry what is not topology, among them a request's expiry, publisher confirms and the broker's plugins. The quanta from the declaration differ from those from compose, because compose cannot see the units that run on the host.

## Findings

| ID | Finding | Evidence |
|---|---|---|
| MSAI12-01 | The JSON `deadLetter` flag means two things. The Python worker reads `false` as "bind to the dead-letter exchange" and `Topology.java` as "declare without the dead-letter argument". When only the Python worker declares, nothing routes a transforms request to its queue | `declare_topology` in `workers/src/lattice_workers/config_studio_worker.py`, read and run against a recording channel, not on a broker |
| MSAI12-02 | The events exchange `lattice.studio.events` is declared in `Relay.java` and `WriterMain.java` and in no copy | `compare.py` |
| MSAI12-03 | The types of `lattice.studio` and `lattice.studio.dlx` are in neither JSON file | the JSON files |
| MSAI12-04 | The reader group `lattice.studio.writers` is in `StreamWriter.GROUP` and the JSON and not in `Topology.java`, and nothing checks the two against each other | `compare.py` |
| MSAI12-05 | The JSON's `bindingKey` and `bindingArguments` templates are unused, and the argument is a string in the template and an integer in both code paths | `compare.py` |
| MSAI12-06 | The partition function is a sentence in the JSON and code in two languages | `compare.py`, 2002 ids agree |
| MSAI12-07 | `RabbitMqEventPublisher.declareTopology` has no caller under `platform/src/main` | a search of callers |

## Commands and results

Run from the worktree on 2026-11-17.

| Command | Result |
|---|---|
| `mise exec '--' python spikes/multi-store-emitted-topology/emit.py` | exit 0, both JSON files byte-identical to the hand copies, `Topology.java.txt` written |
| `mise exec '--' python spikes/multi-store-emitted-topology/compare.py` | exit 1, "10 differences found, 6 distinct", MSAI12-01 among them in each Python view |
| `..\vyvid\.venv\Scripts\python.exe spikes/multi-store-emitted-topology/quanta.py` | exit 1 as designed when the two splits differ: 2 quanta from compose, 1 from the declaration, 5 without the store |

The quanta script runs under the sibling `vyvid` interpreter because it imports vyvid's own function, which needs PyYAML and pyoxigraph, and the mise interpreter has neither.

## Adversarial probes

1. The comparison runs the worker's own declaring functions against a recording channel rather than reading the JSON, so a disagreement in how the code reads a field shows, as MSAI12-01 does.
2. The emitted JSON reproduces the Python worker's binding of the transforms queue, because the JSON structure cannot say where a queue binds. The comparison reports this as a difference against the declaration and not as agreement.

## Decisions taken

- **The declaration is logical.** It names a hub, competing lanes, a failure sink, an ordered write stream and broadcasts, and the emitter maps them to RabbitMQ terms. This is D1's shape: the compiler emits and applies nothing.
- **Units and their traffic are in the declaration.** They are taken from the code, so their presence shows the declaration can hold them, not that it is where they belong.
- **The quanta from the declaration use a compose-shaped dictionary built from it.** This tests whether the declaration can carry what the function needs, not the function's accuracy.

## Open matters

- MSAI12-01 is a defect in running code, read from the code and not seen on a broker. It is for the maintainer to triage, and this slice changes no code.
- Compose's quanta miss the host-run units. Whether ADR-A134's quanta should come from the emitted declaration is a question for the sketch's §4.10.
- `fuseki` has no `image` in the compose file, so vyvid's function reads it as a component.
