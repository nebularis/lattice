<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-P3, the persistence simulation executor

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-P3, built on 2026-11-19 in autonomous mode, under ADR-A154 decisions 1, 7, 9, 11 and 12 and section 8.2 of the [sketch](../sketches/studio-visual-authoring.md).

## Invariant

A persistence step is a function of its request. The run worker reads the finished compile job the request names, binds the step's operation with the Java caller library, replaces every `NOW()` in the parsed update with the step's stated transaction time, runs it on a fresh in-memory Jena dataset holding the step's sample world, and answers with four parts: the checks, the update as it ran, the quads added and removed in each graph grouped by the compiled profile's landing places, and the outcome. No dataset is shared between steps, nothing is stored, and the same request gives the same frames on a repeat and under any order of its quads. A graph that matches no place is reported as unplaced and never dropped.

## What changed

- `platform/config-studio-transforms`: `PersistenceStep` runs a step, `StepRequest` reads it, `LandingPlaces` assigns each changed graph to a place by equality, with a template rendered from the step's own `{root}`, `{newRev}` and `{month}`, `NowPinning` replaces each `E_Now` through Jena's update and expression transforms (TSD-76), and `QuietErrors` keeps Jena's parser from logging. `RunWorker` runs a `simulate` run of `persistence` and still fails one of `surface`, which is SVA-S2's. `RunFrames.ofStep` makes the frames.
- The contract's Runs section defines a persistence step, with nine terms in `studio-vocabulary.ttl` and two samples. The class is `cst:forClass`, since `cst:target` already names a job's part. Each payload parameter has a graph of its own, the one the payload contract names at `<urn:lattice:studio:step/payload>` and any other at `<urn:lattice:studio:step/payload/{name}>`, since the facility's replaces take two or three.
- The facility job's SPARQL artefacts are a test fixture of the run worker, kept equal to the compiler's output by `workers/tests/test_config_studio_compiled_fixture.py`.
- `NowPinningProbeTest` checks that no time equals the stated one and that the operations' times differ, in place of a check of the current year that failed at a new year.
- `test/studio-integration/test_runs.py` gains a persistence step on the interactive queue.

## Tests

| ID | Given / When / Then | Level | The break tried | The failure it gave |
|---|---|---|---|---|
| P3-T1 | the facility sample / a create, a delta replace, a tombstone, and a replace with a stale expected position / the exact quads of each graph with each place's role, and the stale replace changes nothing and is a lost race. The expectations follow `test_composite_lifecycle.py` HO7-T2, T4 to T6 and `test_patch_log.py` H2.6d-T1, T3, T4 and T6, since no conformance test names the facility | L1 | | |
| P3-T2 | a step at `2026-03-31T23:59:58Z`, and one at `2031-12-31T23:59:59+02:00` / run / the receipt lands in `urn:g:txlog/2026-03`, and in `2031-12`, and in no other month | L1 | | |
| P3-T3 | five steps, a refused one among them / repeated, and under six permutations of the world's blocks, lines and graphs / the same parts, and the same frames on a repeat | L1 | | |
| P3-T4 | every SPARQL artefact of the facility job, and a request with `FILTER`, `NOT EXISTS`, a sub-select, `OPTIONAL` and several operations / transformed / no `NOW()` left | L1 | | |
| P3-T5 | a malformed step of each kind, a read operation, a stated digest, a redelivered message, a surface step, a body over 5 MiB / run / one failed frame each, in words an author reads | L1 | | |
| P3-T6 | a profile with its log place removed / a create / the log graph is reported as unplaced | L1 | | |
| P3-T7 | a step the caller check refuses / run / the checks and a refused outcome, and no update run | L1 | | |
| P3-T8 | a world of 150,000 triples and a deadline of 1 ms / run / Jena's timeout ends the update, and the worker sends nothing after the deadline | L1 | | |
| P3-T9 | a result over 128 frames / run / one failed last frame saying the result is too large | L1 | | |
| P3-T10 | two handler threads, then one / a slow step and a fast one / with two the fast one is answered while the slow one runs, with one it waits | L1 | | |
| P3-T11 | the facility sample on the real stack / a step on the interactive queue / the four parts | L3 | | run on 2026-11-20 after its fixture was fixed, passed (see below) |

## Checks run

| Command | Result |
|---|---|
| `mise exec -- mvn -o -f platform/pom.xml -pl config-studio-transforms -am verify` | BUILD SUCCESS. The caller library 119, the outbox 2, the MORK transforms 7, the studio's core 24 and the run worker 60 tests, 0 failures. Run by the delegated developer twice and by the reviewer |
| `mise exec -- python -m pytest tools/test_config_studio_contract.py tools/test_config_studio_stage.py workers/tests/test_config_studio_compiled_fixture.py -q` | 53 passed |
| `mise run check:persistence-library` | exit 0, vectors 94 passed, Python 127 passed, run by the delegated developer |
| `mise run check:identifiers`, `mise run check:catalogue` | passed, and agrees with the tree, run by the delegated developer |
| `mise run studio:integration` | not run. The stack does not start in this container, since Erlang is not on the path, so P3-T11 is written and not run. SVA-V1 runs it |

## Left open

- The caller library has no confirmation read that classifies an outcome, so `PersistenceStep.confirm` classifies it from the claim and the guards' graphs, after section 15.2 of the patterns guide, with two classifications of its own, `AlreadyExists` and `NotApplied`. TD-173.
- The generated writes still read `NOW()`, TD-171. The simulator shows the update with the time it replaced.

**Follow-up, 2026-11-20.** P3-T11's fixture created its workspace with the facility sample's name, which the service records and does not fill parts from, so the persistence part was empty and its compile was refused. It now creates the workspace with the facility baseline and saves the persistence part, as the app does. With Erlang on the path, the runs' real-stack suite gave 11 passed in 188 s, P3-T11 among them, and the liveness suite 5 passed.

## Placement

T0. The run worker, the studio's contract and its vocabulary are open.
