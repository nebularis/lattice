<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: studio-publication PB1 to PB11

**Plan:** [studio-publication](../plans/studio-publication.md)
**Status record:** [studio-publication](../status/studio-publication.md)

One pack for the unit, each slice a section, as the `config-studio` unit's is, since the slices are built in sequence on one branch and reviewed together.

## Invariant

What a workspace refers to is read, never copied, and what leaves the studio is a version anyone can name. A part decides only where a statement is saved, and every job reads the workspace around it (ADR-A149 decision 7). A published version is immutable and named under ADR-A51's IRIs, a reference from it is pinned (ADR-A142), and every command carries an authenticated principal (PRI-54), whose workspace mode the service and the writer both check (PRI-75).

## One command

```bash
mise run check:config-studio
```

It stages the assets, then runs the stage and worker tests, the service's Maven build and tests, and the browser code's type check and unit tests. A pass is exit status 0. The worker's own suite runs with `mise run check:workers`.

## PB1: what a job reads

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| PB1-01 | a graph with a representation scheme and a concept in it, and a concept scheme with a concept / sorted in the browser / the first concept goes to mapping, the second to vocabulary | L1 | + | pass |
| PB1-02 | the same graph / sorted by the service / the same parts, and saving the first concept with its scheme as the mapping part is accepted | L3 | + | pass |
| PB1-03 | a validation of the vocabulary part / submitted / its job names every other configuration part as a context graph and not its own | L3 | + | pass |
| PB1-04 | a job naming another workspace's part as context / submitted to the writer / refused | L8 | − | pass |
| PB1-05 | a job naming a graph outside its workspace's parts as context / run by the worker / fails without reading it | L8 | − | pass |
| PB1-06 | the `policies` XML scheme with its codes moved out / compiled alone / refused with `CorrespondenceKey`, and compiled with the codes as context / not refused | L4 | + | pass |
| PB1-07 | an invalid concept scheme / validated as the target / reported and not conforming, and held only as context / not reported and conforming | L4 | + | pass |
| PB1-08 | the sample "Policies from XML and JSON" in a running studio / its XML example run / `Peril` writes `tgt:peril` for both covers | L5 | + | pass, 2026-10-31 |

`apps/config-studio/src/rdf/rdf.test.ts`, `StudioApiTest`, `WritesTest`, `workers/tests/test_config_studio_worker.py` and `workers/tests/test_config_studio_mork_tools.py`. PB1-08 was run by hand in the browser pane.

**Not covered.** A job reads the other parts as saved, so an unsaved edit elsewhere is unseen until it is saved (MEC-97). The browser's cached compilation is keyed on the other parts' revisions, which PB1-08 exercises only through the first compilation.
