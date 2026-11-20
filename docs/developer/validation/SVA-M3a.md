<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-M3a, a mapping's run over an RDF sample

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-M3a, built on 2026-11-20 in autonomous mode, under ADR-A154 and its addendum of 2026-11-20.

## Invariant

A `sample` run of a mapping whose input is Turtle or N-Triples is answered by the studio's Python worker with `mork_rdf`'s driver over the compiled forms of the finished compile job it names, so its artefacts are what a dry run of the same scheme over the same sample writes. Every rule of a run holds as the Java run worker keeps it: the request checked again, a redelivered run failed, nothing sent past the deadline, frames valid against the contract and within its bounds, the result ordered canonically, and the message acknowledged only after its frames are confirmed. A sample in XML or JSON still reaches the Java run worker, and each worker refuses a run meant for the other.

## What changed

- A queue, `lattice.studio.runs.rdf`, not dead-lettered, with the sample queue's deadline, in the contract's topology, the worker's copy and `Topology.java`. The service routes a `sample` run of `mapping` by its input's media type.
- `config_studio_runs.py` handles a run, `config_studio_run_frames.py` builds its frames as `RunFrames` does, and `config_studio_run_consumer.py` consumes the queue on a connection, thread and channel of its own, with a bounded pool, started beside the jobs consumer. The dry run's recorder and artefact naming moved to module level in `config_studio_jobs.py` and are shared.
- A run reads the compiled forms the compile job holds, `{scheme}.compiled.ttl`, which `mork_rdf.from_rdf` refuses when its queries no longer give its digest, so a run is a function of the compile job and needs nothing else from the store.
- A closure writes an OWL list whose blank nodes Oxigraph labels at random, so an artefact holding blank nodes is written with canonical labels, equal to the dry run's up to those labels. Every other artefact is byte for byte the dry run's.
- The report names its engine, `cst:engine "mork_rdf 0.1.0 on Oxigraph 0.5.13, in memory"`, a term added to the studio's vocabulary.
- The Java run worker's failure naming this slice is gone, and a Turtle or N-Triples run that reaches it fails as sent to the wrong worker.
- The contract's Runs section says which worker answers which run, and the operator guide names the new queue and its setting, `LATTICE_RUNS_RDF_CONCURRENCY`.

## Tests

| ID | Given / When / Then | Level | The break tried | The failure it gave |
|---|---|---|---|---|
| M3a-T1 | the ODRL sample / run, and dry-run / 75 artefacts, the same mappings, strata and paths, identical text | L1 | | |
| M3a-T2 | a mapping with two strata, a lookup and a closure / run / artefacts isomorphic to the dry run's | L1 | | |
| M3a-T3 | a run, its repeat and three orderings of the sample / framed / identical frames | L1 | | |
| M3a-T4 | a success, a run that cannot start, a redelivered run, 128 frames and 129 / framed / each valid against the schema and shaped as the contract's examples, the 129th a failure saying the result is too large | L1 | | |
| M3a-T5 | Turtle, N-Triples, XML and JSON samples / submitted / the first two on the new queue, the others on the old | L1 | | |
| M3a-T6 | the consumer / a slow run, a deadline, a failed publish, a lost connection / no frame after the deadline, a requeue, and no success followed by a failure | L1 | | |
| M3a-T7 | the real stack with no Java run worker / an RDF run in Turtle and in N-Triples / answered on the new queue with two strata, a closure and the engine named, identical frames for both, and an XML run left waiting on the Java queue | L3 | | |

## Checks run

| Command | Result |
|---|---|
| `mise exec -- python -m pytest workers/tests -k config_studio -q` | 229 passed, 75 deselected |
| `mise exec -- python -m pytest tools/test_config_studio_contract.py tools/test_config_studio_stage.py tools/testing/studio_harness/tests -q` | 94 passed |
| `mise exec -- mvn -o -f platform/pom.xml -pl config-studio-service,config-studio-transforms -am verify` | BUILD SUCCESS, the service 250 and the run worker 61 tests, 0 failures |
| `mise run check:identifiers` | passed |
| the runs' real-stack suite and the liveness test, with Erlang on the path | 15 passed and 1 error, run by the delegated developer. M3a-T7 passed. The error is R5-T10's fixture, from SVA-P3, which creates its workspace with a sample name the service does not use to fill a workspace's parts, so its persistence part is empty and the compile is refused. Fixed in the change after this one, after which the runs suite gave 11 passed and the liveness suite 5 passed |

The first four were run by the delegated developer and again by the reviewer.

## Left open

- A run abandoned at its deadline keeps its thread until the query in hand returns, since Oxigraph cannot be interrupted inside a query, as the Java worker records for its engines.
- The ODRL instrument file cannot be saved as a mapping part, which refuses terms of another part, so the real-stack test runs a small mapping of its own.

## Placement

T0. The studio's worker, service and contract are open.
