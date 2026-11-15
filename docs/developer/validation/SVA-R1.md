<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-R1, the contract for runs

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-R1 of the [plan](../plans/studio-visual-authoring.md), from section 4 of the [sketch](../sketches/studio-visual-authoring.md), written on 2026-11-15 in autonomous mode.

## Invariant

The contract states every rule of [ADR-A154](../../architecture/decisions/ADR-A154-runs-in-the-configuration-studio.md) that a client, a service or a worker must keep, in the Runs section of `contracts/config-studio/README.md`, so SVA-R2, SVA-R3 and SVA-R4 build against the contract and never against the decision. A frame is one wire type with one schema, `run-frame.schema.json`, used by both ways a result arrives, as the body of a `run.frame` event and as an element of a `wait=true` response. The limits are in one table, each with where it is enforced. The topology's copies are identical, and name the two queues of runs beside the transforms queue with the same settings. Nothing here runs a run, since the service, the run worker and the browser are later slices.

## What changed

- **`contracts/config-studio/README.md`.** The HTTP row for `runs`, the new Runs section after Completion events, the deprecation on the transforms row and in the Transforms section, the two queues and the new files in the file table, and a sentence in Completion events that a run's frames are the one event that holds content.
- **`contracts/config-studio/run-frame.schema.json`.** The frame, strict, with the role enumeration, the rules on `last`, `status` and `message`, and the text limit in characters.
- **`contracts/config-studio/samples/run-frames.example.json`, `run-frames-failed.example.json`.** A complete small `sample` run and a run that could not start.
- **`contracts/config-studio/studio-vocabulary.ttl`.** `cst:Run`, a subclass of `cst:Job`, the kinds `cst:SampleRun` and `cst:SimulationStep`, and `cst:deadline`. The two kinds join the enumeration of `cst:JobKind`, and the domain of `cst:compileJob` is widened to a union of `cst:Transform` and `cst:Run`.
- **`contracts/config-studio/amqp-topology.json` and `workers/src/lattice_workers/config-studio-topology.json`.** The queues `lattice.studio.runs.interactive` and `lattice.studio.runs`, each with its name as its routing key, not dead-lettered.
- **`tools/test_config_studio_contract.py`, `mise.toml`.** The contract test, in the pytest list of `check:config-studio`.
- **`apps/config-studio/e2e/fake-service.ts`.** `POST …/runs` checks its parameters as the contract says, answers `202` without `wait`, and answers a canned `sample` run with `wait=true`.
- **`docs/architecture/configuration-studio.md`.** The run queues and the events exchange in the components diagram, and the transforms worker's second role.

## Tests

| ID | Given / When / Then | Level | Pass |
|---|---|---|---|
| R1-T1 | the schema / checked against the 2020-12 metaschema / valid, and its text limit is 49,152 | L1, positive | `test_the_schema_is_a_valid_2020_12_schema` |
| R1-T2 | each example file / each frame validated / no error | L1, positive | `test_each_example_frame_validates_against_the_schema` |
| R1-T3 | each example file / read as a run / `seq` counts from 0 without a gap, one run, `last` only on the final frame, part indexes count from 0, and no text over 49,152 bytes | L1, positive | `test_an_example_is_a_whole_run` |
| R1-T4 | the sample run / the parts assembled from their frames / a report part and an artefact part, the report parses as Turtle and the artefact, split across two frames, as N-Triples | L1, positive | `test_the_parts_of_the_sample_run_read_back_as_rdf` |
| R1-T5 | a last frame with no status, a failed one with no message, a succeeded one with a message, a failed one with `conforms`, a frame that is not last with a status, a last one with `more`, an unknown status, a negative `seq`, a `seq` that is not whole, an extra property, no run, a run that is not a run IRI, an unknown role, a part with no media type, role or index, a negative index, an extra part property, a negative step, and text of 49,153 characters / each validated / each refused | L1, negative | `test_a_bad_frame_is_refused` |
| R1-T6 | text of exactly 49,152 characters / validated / accepted | L1, positive | `test_text_of_exactly_the_limit_is_accepted` |
| R1-T7 | each of the six roles / validated / accepted | L1, positive | `test_each_role_of_a_part_is_accepted` |
| R1-T8 | the contract's topology / the two queues of runs / each has its name as its routing key and the transforms queue's setting, not dead-lettered | L1, positive | `test_the_two_run_queues_sit_in_the_topology_with_the_transforms_queues_settings` |
| R1-T9 | the worker's packaged copy of the topology / compared with the contract's / byte-identical | L1, positive | `test_topology_copy_equals_contract` in `workers/tests/test_config_studio_worker.py` |
| R1-T10 | the service's constants / compared with the contract's file / equal, and every queue from the transforms queue to the dead-letter queue, the two queues of runs among them, not dead-lettered | L2, positive | `TopologyTest.theConstantsEqualTheContractFile` |
| R1-T11 | the vocabulary / read / `cst:Run` a subclass of `cst:Job`, both kinds typed `cst:JobKind` with a comment, `cst:deadline` on `cst:Run`, and no name shared with `cst:Sample` | L1, positive | `test_the_vocabulary_declares_a_run_and_its_two_kinds` |
| R1-T12 | the contract's text / read / it names the schema, the text limit, the frame limit and both queues | L1, positive | `test_the_contract_states_the_limits_the_schema_holds` |
| R1-T13 | every earlier test of the browser code and the fake / the whole suites / none is edited, and all pass with the new route in the fake | L3, positive | the vitest suite and the 31 browser tests of `e2e/studio.spec.ts` |

The fake's `runs` route has no browser test of its own, since no view uses runs yet. Its parameter checks and its frames were exercised once by a throwaway script that is not kept, and its frames were validated against the schema in the same way.

**The one command:** `mise run check:config-studio`, from the repository root. The contract test is in its pytest list.

## Artefacts to inspect

- The Runs section of `contracts/config-studio/README.md`, and the two HTTP rows it adds and changes.
- `contracts/config-studio/run-frame.schema.json` and the two examples under `contracts/config-studio/samples/`.
- The run terms after `cst:compileJob` in `contracts/config-studio/studio-vocabulary.ttl`.
- The two new queues in `contracts/config-studio/amqp-topology.json`.
- The `run` method of `apps/config-studio/e2e/fake-service.ts`.

## Deliberate non-coverage

- **The service** accepting, checking, publishing and relaying a run is SVA-R2.
- **The run worker** consuming the queues, running a run and publishing frames is SVA-R3. The Java `Topology` class and the studio's own tooling name the queues separately from the JSON, and do not declare the two queues of runs until that slice.
- **The browser** assembling frames, deadlines and one run a pane is SVA-R4.
- **The failure cases on the real stack**, a worker that stops, an instance that stops, a tab that reconnects and a workspace locked during a run, are SVA-R5.
- **What a `simulate` body and the four parts `check`, `request`, `delta` and `outcome` hold** is for the slices that build the simulators. The contract says only that the body is TriG and names the roles.
- **The byte limit of a frame's text.** A schema states a length in characters, so the schema holds 49,152 characters and the worker holds the byte rule.
- **The limits against a real network.** They are held to what the probes of the broker observed on loopback, and may be tightened.

## Results

What the builder ran on 2026-11-15, in autonomous mode, each read in full:

| Command | Result |
|---|---|
| `mise exec -- python -m pytest tools/test_config_studio_contract.py -q` | 31 passed |
| `mise exec -- python -m pytest tools/test_config_studio_contract.py workers/tests/test_config_studio_worker.py -q` | 103 passed, which includes `test_topology_copy_equals_contract` |
| `mise exec -- mvn -q -o -pl config-studio-core,config-studio-service,config-studio-writer -am test`, from `platform` | exit 0. Surefire totals core 24, service 204, writer 10, each with 0 failures and 0 errors, as before the change, so `TopologyTest` passes with the two queues in the file |
| `mise exec -- yarn workspace @lattice/config-studio exec vitest run` | 19 files, 308 tests passed, as before |
| `mise exec -- yarn workspace @lattice/config-studio exec tsc --noEmit` | exit 0, no output |
| the browser suite, `playwright test` on the system Chromium, with a temporary config that was deleted afterwards | 31 passed, as before |
| `mise run check:config-studio`, output in full | exit 0. The pytest step 284 passed. `mvn verify` over authoring, service, writer and transforms passed, and the Surefire totals are authoring 9, core 24, service 204, writer 10 and transforms 2, each with 0 failures and 0 errors. The browser code's check 308 passed. The authoring domain's check 21 passed. The one `ERROR` with a stack trace in the log is the logged `broker down` of `aBusThatThrowsStillAnswers202WithAFailedJob`, which that test provokes |
| `mise exec -- node mm.js docs/architecture/configuration-studio.md` | `ok` for both diagrams |

`mise run check:config-studio` rewrote `ontology/mork/mtp/data/pins.lock.json` by one line, through its build of the MORK teaching pack. It is left as it is, and is not part of this slice.
