<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-S2, the surface simulation executor

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-S2, built on 2026-11-23 in autonomous mode, from section 9 of the [sketch](../sketches/studio-visual-authoring.md) and ADR-A154 decisions 1, 7, 9, 11 and 12.

## Invariant

A surface step is a function of its request. The run worker reads the finished surface compile job the request names, and over the world before and the world after the edit, each in a fresh in-memory Jena dataset, runs for each changed source the clear and every contract's fill that the studio's writer runs, with the writer's own maintenance code. It answers with each contract's rows before and after, the rows asserted and retracted, and each contract whose read set the edit touched, with the engine named. The same request gives the same frames on a repeat and under any order of its quads.

## What changed

- The step's TriG is the sample world before the edit and the edit as the quads added and removed, in `step/added` and `step/removed`, and `step/added/{graph}` and `step/removed/{graph}` for a named graph, so the surface simulator can take a persistence step's delta as it stands. The step graph names the surface part with `cst:forPart`, a new term, and the transaction time.
- `Maintenance` in `config-studio-core` gains the clear and fills by family, which the writer and the simulator share. `SurfaceStep` and `SurfaceStepRequest` in the run worker run a step, reusing the persistence step's reading of a step and its frames, and replacing any `NOW()` with the stated time.
- The surface compile job carries the maintenance the run worker needs, a `maintenance` group with the partition's clear, each contract's fill, its read-set query and a manifest, from the surface compiler. A contract with no fill is listed with its reason.
- The parts reuse the frame roles the contract has: two `artefact` parts per contract kept, its rows before and after as TriG, a `delta` part, and an `outcome` part with the engine and, per contract, whether it is kept, why not, whether its read set was touched and how many rows were asserted and retracted.
- Five sample steps, `contracts/config-studio/samples/facility-surface-step-*.trig`, each over three facilities.

## Tests

| ID | Given / When / Then | Level | The break tried | The failure it gave |
|---|---|---|---|---|
| S2-T1 | each sample step / run / each contract's rows equal the surface compiler's rebuild of the world after, from a fixture the compiler writes and its test keeps current | L1 | rows attributed to the wrong contract | a multi-contract test failed |
| S2-T2 | each sample step / run / the contracts touched are those the compiler's invalidation names | L1 | the touched rule changed | a test failed |
| S2-T3 | a step, its repeat and its quads permuted / run / the same frames | L1 | | |
| S2-T4 | a malformed step of each kind, a persistence step sent as a surface step, a redelivered step, a result over the frame bound / run / one failed frame each, in words an author reads | L1 | | |
| S2-T5 | the writer's maintenance / its existing tests and the shared code's new ones / unchanged behaviour | L1 | | |

## Checks run

| Command | Result |
|---|---|
| `mise exec -- mvn -o -f platform/pom.xml -pl config-studio-transforms,config-studio-service,config-studio-writer -am verify` | BUILD SUCCESS. The caller library 128, the outbox 2, the MORK transforms 7, the studio's core 26, the service 250, the writer 10, the run worker 77, 0 failures |
| `mise exec -- python -m pytest workers/tests -k config_studio -q` | 247 passed |
| `mise exec -- python -m pytest tools/test_config_studio_contract.py tools/test_config_studio_stage.py -q` | 58 passed |
| `python -m unittest surface.test_surface surface.test_maintenance`, through `mise exec` | OK |
| `mise run check:identifiers` | passed |

Each was run by the delegated developer and again by the reviewer. The real stack was not run.

## Left open

- The writer's fills and the compiler's rebuild agree on the five samples, and would differ where a read path leaves the source's graph or a carrier is typed by a subclass, since a fill reads one source graph and matches `rdf:type` exactly. The samples keep the borrowers in the facilities graph so the two agree, which the facility profile's own layout does not. TD-259.
- The compiler's invalidation records an instance only where the source already holds one of the carrier's class, so the first instance of a class asserts a row and touches no contract. The simulator shows it as the compiler gives it. TD-260.
- The surface compile job lowers no projection, so a step runs promotions and reports indexes as not kept, and no projection's queries run. TD-261.

## Placement

T0. The run worker, the studio's core, the contract and its vocabulary are open.
