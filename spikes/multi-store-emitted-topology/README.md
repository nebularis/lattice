<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# The studio's broker topology from one declaration

Spike for investigation MSA-I12. The leaning under test is that one declaration can be the single source of the studio's broker topology and that a compiler can emit from it the declarations a provisioner applies (decision D1, the compiler emits and applies nothing). The falsifier is that the declaration cannot express the topology the studio runs. A second part compares the software quanta derived from the declaration with those derived from compose.

## What the spike shows

The studio's topology exists today as three hand copies and the code around them. `contracts/config-studio/amqp-topology.json` and `workers/src/lattice_workers/config-studio-topology.json` are byte-identical, and `platform/config-studio-core/src/main/java/org/nebularis/lattice/studio/jobs/Topology.java` holds the same facts as constants. `declaration.json` states the topology once, in logical terms (a hub, competing lanes, a failure sink, an ordered write stream, broadcasts, and the units that publish and consume). `emit.py` produces both JSON files and a Java fragment from it. `compare.py` compares the declaration, the emitted files, the two hand copies and the code that executes them.

The emitted JSON is byte-identical to the hand copies, so the JSON structure can be generated. The comparison of what the code actually declares found one disagreement among the hand copies (MSAI12-01), in a place the JSON structure of the time could not express. It was fixed by slice MSA-F4 on 2026-11-18, which replaced the per-queue `deadLetter` flag with the two fields `bindsTo` and `deadLettersTo`. The emitter now writes that structure and the comparison shows no difference for any queue binding.

## Files

| File | Purpose |
| --- | --- |
| `declaration.json` | The topology stated once, with its licence in `declaration.json.license` |
| `emit.py` | Emits `emitted/amqp-topology.json`, `emitted/config-studio-topology.json` and `emitted/Topology.java.txt` |
| `compare.py` | Compares semantically and prints every difference, exits 1 if there is one |
| `quanta.py` | Derives software quanta from compose and from the declaration with vyvid's own function |
| `emitted/` | Output of `emit.py`, regenerated on each run and not committed |

## How to run

From the worktree root.

```
mise exec '--' python spikes/multi-store-emitted-topology/emit.py
mise exec '--' python spikes/multi-store-emitted-topology/compare.py
mise exec '--' python spikes/multi-store-emitted-topology/compare.py --matrix
..\vyvid\.venv\Scripts\python.exe spikes/multi-store-emitted-topology/quanta.py
```

`quanta.py` needs PyYAML and pyoxigraph and the `vyvid` sources, none of which the `mise` interpreter has, so it runs with the interpreter of the sibling `vyvid` checkout. Set `VYVID_SRC` to a different `src` folder if needed. `compare.py` imports the real Python worker module (`lattice_workers.config_studio_worker`) and runs its `declare_topology` and `declare_writes` against a recording channel. It reads `Topology.java` without compiling or running it. Since MSA-F4 `Topology.declare` reads the exchanges and queues from the contract JSON, so `compare.py` derives those Java calls by applying the declaring rule that the source implements to the contract JSON (it first checks that the source still has that form), and reads only the super stream calls from the Java literals with a small evaluator built from regular expressions. The evaluator also reads the emitted Java fragment, which declares its queues as literals.

## Inventory

The three hand copies were read in full. Calls are those made on a channel, 27 in all once the exchanges, queues and bindings are counted, and the declaration implies the same 27 plus one more. The queue table shows the state before MSA-F4 where it says so.

### Exchanges

| Exchange | Type | Durable | Arguments | JSON contract | `Topology.java` | Python worker | Declaration |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `lattice.studio` | topic | yes | none | name only, type is not in the JSON | yes | yes | yes |
| `lattice.studio.dlx` | topic | yes | none | name only, type is not in the JSON | yes | yes | yes |
| `lattice.studio.writes` | direct | yes | `x-super-stream` true | yes, with type | yes | yes | yes |
| `lattice.studio.events` | topic | yes | none | no | no, declared in `Relay.java` and `WriterMain.java` | no | yes |
| `amq.topic` | built in | not applicable | not applicable | no | no, bound in `Relay.java` | no | listed under built-in routes |

### Queues and bindings

| Queue | Durable | Arguments | Binding in `Topology.java` and in the declaration | Binding in the Python worker before MSA-F4 |
| --- | --- | --- | --- | --- |
| `lattice.studio.jobs` | yes | `x-dead-letter-exchange` `lattice.studio.dlx` | `lattice.studio` with key `lattice.studio.jobs` | the same |
| `lattice.studio.jobs.long` | yes | `x-dead-letter-exchange` `lattice.studio.dlx` | `lattice.studio` with key `lattice.studio.jobs.long` | the same |
| `lattice.studio.transforms` | yes | none | `lattice.studio` with key `lattice.studio.transforms` | `lattice.studio.dlx` with key `lattice.studio.transforms` |
| `lattice.studio.dead` | yes | none | `lattice.studio.dlx` with key `#` | the same |
| `lattice.studio.writes-0` to `-7` | yes | `x-queue-type` stream, `x-max-age` 7D, `x-max-length-bytes` 1073741824 | `lattice.studio.writes` with key `i` and argument `x-stream-partition-order` `i` | the same |

After MSA-F4 the Python worker binds `lattice.studio.transforms` to `lattice.studio`, like the other views. None of the queues is exclusive or auto-delete. The JSON holds the partition arguments in `writes.partitionArguments` and the binding templates `bindingKey` and `bindingArguments`. The Python worker ignores the two templates and writes the key and the argument itself, and the argument is the string `"{i}"` in the template and an integer in both code paths.

### Consumers, publishers and settings

The JSON files and `Topology.java` list no consumer and no publisher. The declaration lists them, taken from the code, and `compare.py` checks the settings below against the source.

| Setting | Value | Where the code holds it |
| --- | --- | --- |
| Reader group of the writes | `lattice.studio.writers` | `StreamWriter.GROUP` and `writes.consumerGroup` in the JSON, not in `Topology.java` |
| Reader mode | super stream, single active consumer, first offset, manual tracking | `StreamWriter.java` |
| Batch limit | 64 | `StreamWriter.MAX_BATCH` |
| Prefetch of jobs and jobs.long | 1 | `config_studio_main.py` |
| Prefetch of transforms | 1 | `TransformsMain.java` |
| Expiry of a transforms request | set by the sender per request | `RabbitJobBus.java` |
| Reply path of transforms and writes | direct reply-to, `amq.rabbitmq.reply-to` | `RabbitJobBus.java` and `RabbitWrites.java` |
| Partition of a workspace | first 8 hex digits as an unsigned number, modulo 8 | `Topology.routingKey` and `routing_key`, only a sentence in the JSON |

| Unit | Publishes | Consumes |
| --- | --- | --- |
| `studio-service` | jobs, jobs.long, transforms, writes | events |
| `studio-writer` | events | writes |
| `studio-worker` | writes | jobs |
| `studio-worker-long` | writes | jobs.long |
| `studio-transforms` | none | transforms |

### Result of the comparison

Run on 2026-11-18 after MSA-F4, with `compare.py` exiting 1 because of the two differences listed below.

| View | Calls | Against the declaration |
| --- | --- | --- |
| declaration | 27 | not applicable |
| Python worker on the contract JSON | 27 | all 27 the same |
| Python worker on the packaged JSON | 27 | all 27 the same |
| Python worker on the emitted JSON | 27 | all 27 the same |
| `Topology.java`, exchanges and queues derived from the contract JSON, super stream read from its literals | 27 | all 27 the same |
| emitted Java | 28 | all the same once the events exchange is counted |

The Python worker on the contract JSON and `Topology.java` make the same 27 calls. The three JSON files agree on all 30 fields and are identical byte for byte, and the emitted `amqp-topology.json` and `config-studio-topology.json` have the same SHA-256 as the two hand copies. The partition function agrees on 2002 workspace ids between the Python code and the declared function, and the Java formula reads the same 8 digits, base 16 and modulus.

`compare.py` prints two differences, both unrelated to dead-lettering or to the binding of the four queues.

- The events exchange `lattice.studio.events` is in the declaration and in no hand copy of the topology, since `Relay.java` and `WriterMain.java` declare it
- `Topology.java` holds no reader group, which `StreamWriter.GROUP` and the JSON files hold

## Disagreements among the hand copies

1. MSAI12-01, fixed by MSA-F4 on 2026-11-18. The Python worker bound `lattice.studio.transforms` to `lattice.studio.dlx`, while `Topology.java` bound it to `lattice.studio`. The cause was the `deadLetter` flag of the JSON, which the Python worker read as "bind to the dead-letter exchange when false", and the Java constants read as "declare without the dead-letter argument". The flag carried two meanings and could not say where a queue binds. The effect was read from the code and was not observed on a broker. MSA-F4 replaced the flag with `bindsTo`, the name of the exchange the queue is bound to, and `deadLettersTo`, the name of the exchange it dead-letters to through `x-dead-letter-exchange` or null for none. The Python `declare_topology` and the Java `Topology.declare` both apply that rule to the contract, and `Topology.declare` reads the contract JSON that the build copies beside the class. The declaration can now be emitted faithfully for the transforms queue, which binds to `lattice.studio` and dead-letters nowhere, and `compare.py` shows no difference for the binding in any view.
2. The events exchange `lattice.studio.events` is declared in `Relay.java` and `WriterMain.java` and is in neither JSON file nor `Topology.java`.
3. The exchange types of `lattice.studio` and `lattice.studio.dlx` are in neither JSON file and exist only in code.
4. The reader group `lattice.studio.writers` is held by `StreamWriter.GROUP` and by the JSON files, and `Topology.java` does not hold it. Nothing checks the two against each other.
5. The `bindingKey` and `bindingArguments` templates are unused by the Python worker and differ in type from what both code paths send.
6. The partition function is a sentence in the JSON and code in the two implementations.
7. The queue, dead-letter exchange and binding of `RabbitMqEventPublisher.declareTopology` are declared by no caller under `platform/src/main`. The declaration does not include them.
8. Server-named queues in `Relay.java` and the passive declaration in `RabbitJobBus.java` are runtime calls that no copy of the topology holds. The declaration lists only the `amq.topic` route `studio.u.*.*.watch`.

## Did the falsifier fire

Not for the topology that the three copies state. The declaration expressed all 27 calls, the 8 partitions and their arguments, the partition function (checked on 2002 ids), the reader group and its mode, the batch limit, the prefetch of each lane, and the per-request expiry and reply path as rules. The one binding that the JSON structure of the time could not express (MSAI12-01) is expressed by the structure after MSA-F4 and by the declaration.

It does not follow that the declaration is complete for what the studio runs. It did not carry the following.

- The value of a request's expiry, which the caller chooses at publish time
- The stream client's credit strategy
- The mandatory flag, publisher confirms and delivery persistence, which are properties of a publisher and not of the topology
- The broker's plugins and stream configuration (`enabled_plugins` and `rabbitmq-stream.conf` under `deployment/compose/config-studio`)
- Server-named queues and passive declarations made at runtime
- The compose override files, which the quanta extractor does not read

The declaration also holds facts taken from the code and not from a copy, among them the units and who publishes and consumes. Expressing them shows the declaration can carry them and says nothing about whether it is the right place to keep them.

## Software quanta from the declaration and from compose

`quanta.py` calls vyvid's `software_quanta`, the function behind the ADR-A134 addendum, twice. Once on the compose file, and once on a compose-shaped dictionary built from the declaration, with an image where the declaration names a product and in each unit's environment the host of the store, the broker and any unit it calls. A third derivation takes the store away.

| Part | From compose | From the declaration | From the declaration without the store |
| --- | --- | --- | --- |
| `addin-proxy` | own quantum | one quantum with all the parts below | with `studio-service` |
| `fuseki` | own quantum | in the same quantum | not present |
| `studio-service` | not in compose | in the same quantum | with `addin-proxy` |
| `studio-writer` | not in compose | in the same quantum | own quantum |
| `studio-worker` | not in compose | in the same quantum | own quantum |
| `studio-worker-long` | not in compose | in the same quantum | own quantum |
| `studio-transforms` | not in compose | in the same quantum | own quantum |

The result is 2 quanta from compose, 1 from the declaration and 5 without the store, so the quanta from the declaration are not those from compose. Compose does not see the studio units, because they run on the host, and it does not see the proxy's call to the service, which the Caddyfile makes to the host on port 8090. With those facts and the shared Fuseki the declaration puts everything in one quantum coupled through `fuseki`, although a broker between the units would otherwise separate them. This follows the rule of the function that a shared store defeats a broker. The result without the store shows what the broker alone would give, which is the opposite of what the units share through Fuseki.

Three things limit the result. First, the declaration side takes its inputs from what the spike author wrote, so it tests what the declaration can carry and not whether those facts are right. Second, in the real compose file `fuseki` has `build` and no `image`, so the function reads it as a component and its claim never says "coupled through". Third, the function cuts the claim text at its length limit, so the printed claim ends before the words that name the broker.

## Doubts

- The Java side is not run. The exchanges and queues of `Topology.declare` are derived by applying the rule read from its source to the contract JSON, the super stream calls are read from literals by regular expressions and a small evaluator, and the emitted Java fragment was not compiled. `TopologyTest.java` and the Python test were not run by this spike.
- The effect of the former `transforms` binding was read from the code and not seen on a broker, and the fix was not observed on one either.
- `quanta.py` runs under another interpreter than the one the task named, because the `mise` interpreter lacks PyYAML and pyoxigraph.
- A `vyd` query made earlier built an index in the ignored `.local/` folder.
- `declaration.json` carries its licence in a sidecar file, and `REUSE.toml` has no entry that covers the spike and was not edited.
- `emitted/` is generated output and `__pycache__` appears beside the scripts after a run.
