<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: v-rig VR-5, P2 the generated theory and P3 the test vectors

**Unit:** `v-rig` ([plan](../plans/v-rig.md), [status](../status/v-rig.md)).
**Branch:** `docs/placement-vehicles-structure`. Commits by the agent under the maintainer's authorisation of 2026-11-07, one per slice.
**Plan and test cases:** [the plan](../plans/v-rig.md), VR-5 in detail, principles 3, 4 and 11, the Formal methods table's rows for P2 and P3.
**Decisions:** VR-Q6, VR-Q10, [ADR-A153](../../architecture/decisions/ADR-A153-verification-rig-module.md) decision 3.

## Invariant

Each case of a rig under each reading its documents state gives one generated theory section with `value` commands over the Ledger model and one JSON vector under the tracked schema, every fact in one of three states that never collapse, the keys of an event's facts reaching an evaluation only through the input bindings a rig's extension declares, and both projections byte for byte the same for a rig revision.

## Test cases

| Case | Expectation |
|---|---|
| VR5-01 | A case is a programme with the documents it places and the events put to it, its readings the distinct tokens per declared reading key with the documents that state each, and its digest over the rig digest and its members' digests |
| VR5-02 | The input bindings come from the extension's `vrig:InputBinding` nodes |
| VR5-03 | One vector per case and reading, each valid under `contracts/v-rig/vectors.schema.json` |
| VR5-04 | A stated, an unknown and an absent input are three shapes, and a stated negative is stated |
| VR5-05 | The vector carries the reading with its documents, the programme's period in order, each layer's documents, limit, attachment and placements, and each contract's own limit, attachment, position and layer share, a formula limit as its expression and inputs |
| VR5-06 | The vectors are byte for byte the same over two lifts |
| VR5-07 | A case with no reading gives one vector whose reading is null |
| VR5-08 | The theory has one section per case and reading, binds the reading as a string, imports Ledger, and evaluates each layer's pro-rata split and each event's draw on the primary |
| VR5-09 | The theory binds no number the rig did not give, says an unknown or absent input in words, and describes a formula limit without evaluating it |
| VR5-10 | The theory is byte for byte the same over two lifts |
| VR5-11 | The theory is written beside a copied Ledger theory and a ROOT whose session builds on HOL alone |

## One command

Run from the repository root.

```bash
mise run check:v-rig
```

The generated session builds, one build at a time and on HOL alone, with `ISABELLE=<path to isabelle> mise run v-rig -- --rig <rig> --extension <ttl> --build-theory`, which writes `p2/build.log`.

## Artefacts to inspect

`tools/v_rig/src/v_rig/cases.py`, `p2.py`, `p3.py`, `contracts/v-rig/vectors.schema.json` and its README, the input bindings at the end of `tools/v_rig/tests/mini-rig.extension.ttl`, `tools/v_rig/tests/test_p2_p3.py`, and a run's `p2/VRigP2.thy`, `p2/ROOT`, `p3/<case digest>/<key>=<token>.json` and `p3/index.json`.

## Deliberate non-coverage

A lemma per case, which waits for the layer theories to be stable (VR-Q6). Unifying the generated theory with the mechanised layer theories, which is track E's work when E4a and E4b start. Reading the `value` results out of a build, which the PIDE or `isabelle build_log` does. A reading that changes what is evaluated, since no layer theory yet takes a reading token, so the three sections of the mini-rig's case evaluate alike and differ in the reading they bind.

## Handoff

**Delivered 2026-11-08.** `cases.py` reads a case from the representation, its readings and the three states of a fact as JSON shapes, and the input bindings from an extension, through the vocabulary's new `vrig:InputBinding`. `p3.py` writes one vector per case and reading under `contracts/v-rig/vectors.schema.json`, `lattice-v-rig-vectors/1`, validated with jsonschema before it is written. `p2.py` writes a theory with one section per case and reading, a definition for every stated number, a `text` for every fact stated as not known or not stated, `value "parts …"` and `value "residual …"` over each layer's limit and its placements' shares as integer weights, and `value "settle_at_position …"` for each event's loss drawn on the primary layer, beside a copy of the spike's `Ledger.thy` and a `ROOT` whose session builds on HOL alone. The run prints the vector schema's version among its first lines.

**Built once, on this machine.** The generated session built in 2 seconds of elapsed time, `Finished VRigP2 (0:00:02 elapsed time, 0:00:05 cpu time)`, so every `value` command evaluates. The spike's own session needs `HOL-Library`, which this machine does not build, so the generated session imports the Ledger theory alone rather than `LatticeLayers`, and says so in its header.

**Where the three states show.** In the mini-rig's events the loss is stated for both, prior knowledge is stated as not known for the first and stated as false for the second, and the date of first notice is stated by neither, so the vectors carry `unknown`, `false` and `absent` side by side and the theory says each in words. A limit written as a formula is stated with its expression and inputs in the vector and described in the theory, and binds no number.

**Checks run, with their results.**
- `mise run check:v-rig`, `python -m pytest tools/v_rig -q`: 63 passed.
- `mise run check:catalogue`: passes, after the spike's and the contract's paths were taken from the catalogue reader's areas rather than written.
- `python -m pytest tools/test_v_rig.py -q`: 10 passed. `literate_extract.py ... --check`: `4 extracted artefact(s) consistent`.
- `mise run check:ontology-versioning -- --base-ref main`: `52 in-scope ontology document(s) checked against main: no unbumped changes`.
- `mise run v-rig -- --rig tools/v_rig/tests/mini-rig --extension tools/v_rig/tests/mini-rig.extension.ttl`: ran, one case, three readings, three vectors, a theory of 24 `value` commands, and the build above.

## Results

| Case | Result |
|---|---|
| VR5-01 | pass |
| VR5-02 | pass |
| VR5-03 | pass, three vectors |
| VR5-04 | pass |
| VR5-05 | pass |
| VR5-06 | pass |
| VR5-07 | pass |
| VR5-08 | pass, 6 draws, two events under three readings |
| VR5-09 | pass |
| VR5-10 | pass |
| VR5-11 | pass |
