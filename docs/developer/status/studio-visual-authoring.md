<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Baseline management, canvases and run panes for the studio - Status

**Unit ID:** `studio-visual-authoring`
**Status:** building 2026-11-12. SVA-Q1, SVA-Q2 and SVA-Q4 to SVA-Q16 answered 2026-11-12, SVA-Q3 open
**Last updated:** 2026-11-12
**Plan:** [studio-visual-authoring.md](../plans/studio-visual-authoring.md)
**Sketch:** [studio-visual-authoring.md](../sketches/studio-visual-authoring.md)

## Current position

The maintainer asked on 2026-11-12 for enhancements to the studio: ontology imports resolved through an XML catalog with missing imports reported, a drawing of how ontologies and vocabularies relate, axiom forms, ontology views, an editable canvas and a simulator for persistence and for surface, and in mapping mode a list of schemes, reusable template libraries and a sample pane that runs on demand. A detailed sketch and plan come first. The maintainer also asked for care with the studio's concurrent flows, above all results streamed to the browser over the broker's MQTT, and for the mechanical work of each slice to be delegated to a second model with the design overseen.

The sketch and the plan were written the same day from a reading of the studio's architecture, contract and code. The design's centre is the run, section 4 of the sketch: a result that is not stored reaches the tab as frames relayed by the service instance that accepted it, checked at delivery, bounded by a deadline, with the tab holding a simulator's state. BL-20, a runtime for RML, was added to the backlog as asked.

The maintainer answered every question but SVA-Q3 on 2026-11-12, each as the sketch records, and asked for the unit to be built autonomously on its branch, committed and pushed there, with no merge from or into another branch. On SVA-Q3 the maintainer asked how many triples the body limit holds, how large a step is and whether the limit comes from the MQTT frames, which the sketch's section 8.2 now answers.

**Next action:** the first wave, the slices that wait on no other: SVA-B1, SVA-O1, SVA-O3, SVA-M1, SVA-M2a and SVA-R0. The maintainer confirms or changes SVA-Q3 before SVA-P3.

## Slices

| Slice | Deliverable | State | Blocked on |
|---|---|---|---|
| SVA-R0 | probes of the broker for content frames | building 2026-11-12 |  |
| SVA-R1 | the decision record, the contract's Runs section, the topology and the fake service's runs | building 2026-11-12 | SVA-R0 |
| SVA-R2 | the service's runs: pending entries, the relay's run sink, the waiting sink, the limits | planned | SVA-R1 |
| SVA-R3 | the run worker, from the transforms worker | planned | SVA-R1 |
| SVA-R4 | the browser's run controller and the dock's run pane | planned | SVA-R1 |
| SVA-R5 | the run protocol's failure cases on the real stack | planned | SVA-R2, SVA-R3, SVA-R4 |
| SVA-B1 | catalog reading, ontology headers, the import closure and its plan | built 2026-11-12, building 2026-11-12 |  |
| SVA-B2a | several imports held by one write, each with its ontology and version IRI | building 2026-11-12 |  |
| SVA-B2b | LATTICE's documents served by IRI, and the missing import warning | planned | SVA-B2a |
| SVA-B3 | the Baseline view's imports list, import dialog and missing report | planned | SVA-B1, SVA-B2a |
| SVA-B4 | the import graph | planned | SVA-B3, SVA-O1 |
| SVA-O1 | the canvas kit, with our own layered layout behind one function | built 2026-11-12, building 2026-11-12 |  |
| SVA-O2 | the class and object property view and the class hierarchy, with the shapes toggle | building 2026-11-12 | SVA-O1 |
| SVA-O3 | the axiom reader and the element forms | built 2026-11-12, building 2026-11-12 |  |
| SVA-P1 | landing places in a compile job, and the exploded view, read-only | planned | SVA-O1 |
| SVA-P2 | edits on the persistence canvas | planned | SVA-P1 |
| SVA-P3 | the persistence simulation executor | planned | SVA-R3 |
| SVA-P4 | the persistence simulator pane | planned | SVA-R4, SVA-P1, SVA-P3 |
| SVA-P5 | an object generated from the boundary shape | planned | SVA-P4 |
| SVA-S1 | the surface canvas | planned | SVA-O2 |
| SVA-S2 | the surface simulation executor | planned | SVA-P3 |
| SVA-S3 | the surface simulator pane | planned | SVA-S1, SVA-S2, SVA-P4 |
| SVA-M1 | the mapping schemes listed on the left | built 2026-11-12, building 2026-11-12 |  |
| SVA-M2a | MORK's template library, with `mork_rdf` | planned |  |
| SVA-M2b | template libraries in `mork2rml`, `mork_transforms` and MCN | planned | SVA-M2a |
| SVA-M2c | a library as a unit, and a compile that reads libraries | planned | SVA-M2a |
| SVA-M2d | the Libraries section | planned | SVA-M1, SVA-M2c |
| SVA-M2e | template cards for the proposer and the MCP server | planned | SVA-M2b, SVA-M2c |
| SVA-M3a | a mapping's queries over an RDF sample, as a run | planned | SVA-P3 |
| SVA-M3b | the sample pane | planned | SVA-R4, SVA-M3a |
| SVA-M4 | the output explorer | planned | SVA-O1, SVA-R4 |

## Knowledge index

Asked on 2026-11-12. It answered the studio's decisions and capabilities well (ADR-A136, ADR-A88, ADR-A149, CAP-70, CAP-100 to CAP-102, PM-Q18). It answered weakly on the studio's broker flows, where `find studio job worker rabbitmq websocket mqtt streaming results to the browser --quality concurrency` scored 0.72 at best and returned no mechanism for the relay, the transforms request and reply or the writer's events. Those are stated in the contract's Completion events and Transforms sections and in `Relay.java`, with no register entry, which is a gap under STD-272. It is recorded here for the maintainer, since a mechanism row for each would have carried the answer. XJ-Q8, the earlier answer SVA-Q1 reopens, was found only by asking with `--kind question` after the sketch was drafted, so a design question about the studio is asked that way first.

## Adversarial probes
- 2026-11-12, SVA-B1: the return that lets a catalog entry win was removed from `resolveImports`. Five tests failed, among them the precedence test and the run over LATTICE's own catalog. Restored, 33 passing.
- 2026-11-12, SVA-M1: `schemeSummary` was made to count every unreviewed mapping as to review. Three tests failed. Restored.
- 2026-11-12, SVA-O3: the depth cap of the expression reader was raised by five. The depth test failed. Restored.
- 2026-11-12, SVA-O1: the first sort of the layout was removed, so input order reached the result. The determinism test and the edgeless-nodes test failed. Restored.

## Log

- 2026-11-12: raised by the maintainer. Sketched and planned, SVA-Q1 to SVA-Q16 raised, the board written with 30 slices planned. BL-20 added to the backlog.
- 2026-11-12: SVA-Q1, SVA-Q2 and SVA-Q4 to SVA-Q16 answered by the maintainer. SVA-P5 added for SVA-Q12 (c). BL-21 to BL-24 added. The unit is to be built autonomously on its branch.
- 2026-11-12: SVA-B1, SVA-O3 and SVA-M1 picked up, three slices of the application that touch no file in common.
- 2026-11-12: SVA-R0 and SVA-R1 picked up. The decision record is drafted while the broker is installed for the probes, with the limits the probes decide marked as provisional.
- 2026-11-12: SVA-B1 built, [Validation Pack](../validation/SVA-B1.md). The catalog reader, the ontology header reader and the closure are pure functions, 33 tests passing. The plan's nodes are keyed by the import IRI as written, so an ontology IRI and its version IRI are two nodes of one file, which SVA-B2a joins by digest when it holds them.
- 2026-11-12: SVA-M1 built, [Validation Pack](../validation/SVA-M1.md). Every mapping scheme is a row of a list on the left, with its counts, and the select is gone. The fake service gained the mapping part, which a workspace made from a mapping sample needs to save. Selecting a scheme now also clears the selected source concept, which the select did not.
- 2026-11-12: SVA-O3 built, [Validation Pack](../validation/SVA-O3.md). `rdf/axioms.ts` reads a class's, a property's and an individual's statements into sections and puts the rest in a table, and the Baseline view shows them read-only. SVA-M1 and SVA-O3 are one commit, since both add to the stylesheet and the browser spec. Verified together: 205 unit tests, the type check, and the 24 browser tests on the fake service, run with this machine's Chromium through a configuration that was not committed, since the pinned Playwright expects a newer build than the machine has.
- 2026-11-12: SVA-O1 and SVA-B2a picked up. SVA-B2a also changes the worker's fence job, which reads the ontology IRI and version IRI a document declares, since the writer cannot take them from the browser.
- 2026-11-12: SVA-O1 built, [Validation Pack](../validation/SVA-O1.md). The kit is `src/canvas/`, the layered layout is one function others can replace (SVA-Q8), and the mapping canvas runs on it with its picture unchanged, held by a browser test written and passed on the old canvas first. Layout took 2 to 3 ms for 100 nodes, 5 to 7 ms for 500 and 15 to 20 ms for 2,000, over five runs, so no web worker is needed. Two faults of the old canvas are fixed: stored positions were read only on mount, and laying out again could do nothing under React's strict mode. Verified with 234 unit tests, the type check and 25 browser tests on the fake service.
- 2026-11-12: SVA-O2 picked up.
- 2026-11-12: work paused at the maintainer's request. SVA-R0, SVA-B2a and SVA-O2 were stopped mid-edit and their files committed as they stood, unverified and possibly not compiling, so nothing is lost. Each resumes from its files: SVA-R0 has its probe scripts and no record of results yet, SVA-B2a was part way through the service's route and its tests, and SVA-O2 had begun the graph derivation. None of the three has been run or reviewed.
