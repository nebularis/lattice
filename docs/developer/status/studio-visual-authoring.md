<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Baseline management, canvases and run panes for the studio - Status

**Unit ID:** `studio-visual-authoring`
**Status:** building 2026-11-12. SVA-Q1 to SVA-Q16 answered
**Last updated:** 2026-11-12
**Plan:** [studio-visual-authoring.md](../plans/studio-visual-authoring.md)
**Sketch:** [studio-visual-authoring.md](../sketches/studio-visual-authoring.md)

## Current position

The maintainer asked on 2026-11-12 for enhancements to the studio: ontology imports resolved through an XML catalog with missing imports reported, a drawing of how ontologies and vocabularies relate, axiom forms, ontology views, an editable canvas and a simulator for persistence and for surface, and in mapping mode a list of schemes, reusable template libraries and a sample pane that runs on demand. A detailed sketch and plan come first. The maintainer also asked for care with the studio's concurrent flows, above all results streamed to the browser over the broker's MQTT, and for the mechanical work of each slice to be delegated to a second model with the design overseen.

The sketch and the plan were written the same day from a reading of the studio's architecture, contract and code. The design's centre is the run, section 4 of the sketch: a result that is not stored reaches the tab as frames relayed by the service instance that accepted it, checked at delivery, bounded by a deadline, with the tab holding a simulator's state. BL-20, a runtime for RML, was added to the backlog as asked.

The maintainer answered every question but SVA-Q3 on 2026-11-12, each as the sketch records, and asked for the unit to be built autonomously on its branch, committed and pushed there, with no merge from or into another branch. On SVA-Q3 the maintainer asked how many triples the body limit holds, how large a step is and whether the limit comes from the MQTT frames, which the sketch's section 8.2 now answers.

**Next action:** paused after SVA-B4 for the maintainer, who says when the next slice starts. The unit is built one slice at a time, with one delegated developer at most and a pause after each. Ready to start: SVA-B2c and SVA-B2d, which finish phase B, and SVA-R0's probes, which need a running stack, unblock phase R and are what the maintainer waits for before deciding ADR-A154.

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
| SVA-B2a | several imports held by one write, each with its ontology and version IRI | built 2026-11-12, building 2026-11-12 |  |
| SVA-B2b | LATTICE's documents served by IRI, and the missing import warning | built 2026-11-13, building 2026-11-13 | SVA-B2a |
| SVA-B2c | the browser's live validation takes the baseline | planned | SVA-B2b |
| SVA-B2d | the writer reads an import's content from its fence job, and the jobless fence command goes | planned | SVA-B2a |
| SVA-B3 | the Baseline view's imports list, import dialog and missing report | built 2026-11-13, building 2026-11-13 | SVA-B1, SVA-B2a |
| SVA-B4 | the import graph | built 2026-11-13, building 2026-11-13 | SVA-B3, SVA-O1 |
| SVA-O1 | the canvas kit, with our own layered layout behind one function | built 2026-11-12, building 2026-11-12 |  |
| SVA-O2 | the class and object property view and the class hierarchy, with the shapes toggle | built 2026-11-13, building 2026-11-12 | SVA-O1 |
| SVA-O2a | edge labels placed apart, and edges against the layout's direction attached by the sides that face | built 2026-11-13, building 2026-11-13 | |
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
- 2026-11-12, SVA-B2a: the writer's check that a fence job digested the import it names was removed. `theWriterChecksEachJobItselfWhateverTheServiceChecked` failed, expecting 400 and getting 200. Restored, 14 of 14 passing.
- 2026-11-13, SVA-O2: an edge both origins state was given the origin shape, and the hop limit was raised by one. Five tests failed, among them the toggle only adding edges and the facility file's four links. Restored, 20 of 20 passing.
- 2026-11-13, SVA-O2a: a label was left only the middle of its edge. Four tests failed, among them the two over the facility sample. Restored, 23 of 23 passing.
- 2026-11-13, SVA-B3: a held import's ontology and version IRI were left out of `heldByIri`. Six tests failed. Restored, 16 of 16 passing.
- 2026-11-13, SVA-B2b: the service's check that an index entry names a staged copy, 64 hexadecimal digits and `.ttl`, was removed. `aRequestCannotNameAFile` and the listing test failed, a file outside the copies being served. Restored, 37 of 37 passing.
- 2026-11-13, SVA-B4: a derived edge was drawn even where a stated edge joins the pair. The test that forbids it failed. Restored, 12 of 12 passing.

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
- 2026-11-12: SVA-O2 picked up. It wrote no file before the work paused, and was started again on 2026-11-13.
- 2026-11-12: work paused at the maintainer's request. SVA-R0, SVA-B2a and SVA-O2 were stopped mid-edit and their files committed as they stood, unverified and possibly not compiling, so nothing is lost. Each resumes from its files: SVA-R0 has its probe scripts and no record of results yet, SVA-B2a was part way through the service's route and its tests, and SVA-O2 had begun the graph derivation. None of the three has been run or reviewed.
- 2026-11-12: the paused slices were checked with no change to their code. SVA-B2a compiles and passes its modules' tests, 24 in core, 198 in the service and 10 in the writer, and the worker's 16 for the fence job, and still needs review, a Validation Pack and a probe. SVA-R0 has its probe scripts and no results. SVA-O2 wrote no file. The [handover](../notes/studio-visual-authoring-handover-2026-11-12.md) was written.
- 2026-11-12: SVA-Q3 answered (a) by the maintainer, so a simulator's state is the tab's and nothing waits on a question. The unit resumes one slice at a time with a pause after each.
- 2026-11-12: SVA-B2a built, [Validation Pack](../validation/SVA-B2a.md). One request holds several imports by one command, which stores each import and then replaces the description once, and a held import records the ontology IRI and version IRI its document declares, read by the worker and copied by the writer from the fence job in the store. Verified: 24 tests in core, 198 in the service and 10 in the writer, the worker's 16, and `mise run check:config-studio`, which exited 0 with 21, 157 and 234 tests passed in its three suites. An export still names held imports without their content, as before (TD-135). TD-164 records that nothing digests the content a fence command carries and that the older, jobless form of the command is still accepted.
- 2026-11-13: SVA-O2 built, [Validation Pack](../validation/SVA-O2.md). The Baseline view's detail pane switches to a drawing of classes and object properties or of the class hierarchy, around the selected class or of the whole ontology, on the canvas kit, which gained an `edgeTypes` property. The plan's acceptance was wrong about the sample: the facility sample's shapes state four links and each is already a domain and range, so the toggle adds no edge there and names the shape on four, and the plan's row now says so. A dashed edge is held by a unit test and was seen in a screenshot with one shape added. Two shortfalls seen in the screenshot and left: labels of edges that run against the layout's direction overlap where three meet, and a class with no link in a view sits alone in a last column. The shape reading repeats what `rdf/shapes.ts` does, since that module gives neither a shape's name nor `sh:node`. Verified with 254 unit tests, the type check and 26 browser tests on the fake service.
- 2026-11-13: the maintainer asked for the label placement seen in SVA-O2's screenshot to be fixed, and for SVA-B3 next. SVA-O2a added to the plan and picked up, with SVA-B3 to follow it.
- 2026-11-13: SVA-O2a built, [Validation Pack](../validation/SVA-O2a.md). `canvas/edges.ts` routes each edge from the node boxes and places each label at the first of seven points of its curve that covers no node and no other label, and the ontology canvas uses it. In the facility sample's drawing no label covers another or a class, and the edge from Facility back to Drawdown no longer loops behind its node. Left as it is: an edge that spans several ranks is still drawn straight through the classes between its ends, with only its label kept off them, which bending edges around nodes would fix and no slice plans. The mapping canvas keeps its own edges. Following a dragged node holds by construction and was not tried in a browser. Verified with 277 unit tests, the type check and 26 browser tests on the fake service.
- 2026-11-13: SVA-B3 picked up. LATTICE's staged documents are SVA-B2b and not built, so the dialog resolves from dropped files and held imports and passes no staged document.
- 2026-11-13: SVA-B3 built, [Validation Pack](../validation/SVA-B3.md). The Baseline view lists the workspace's own ontology, each held import and each missing one, and its dialog takes files or a folder, shows how every import of the baseline resolves, and on confirmation digests each file by a fence job, four at once, then holds them all in one request. A missing import never blocks. `rdf/held.ts` derives the list and what is missing from the baseline and the held imports. The fake service had no fence job or import route, so all of it was added there. The dialog has no drop area, only the two inputs, since the kit's file reader gives no relative path. Verified with 293 unit tests, the type check and 29 browser tests on the fake service. The real service has not been driven from this dialog.
- 2026-11-13: SVA-B2b picked up. It also touches the service, which serves the staged documents, and the browser, whose dialog offers them, beyond the staging tool and the worker the plan named.
- 2026-11-13: SVA-B2b built, [Validation Pack](../validation/SVA-B2b.md). Staging copies each of the 48 documents LATTICE's catalog names under its content digest with an index, the service lists them at `/api/ontologies` and serves one by its ontology IRI or version IRI, found through the index alone, and the import walk and the dialog continue through them. A decision taken alone, for the maintainer to ratify: `baseline` is now a target of `validate`, and of nothing else, so that a validation can report an import no held document declares as the warning `ImportNotHeld`. One test that asserted that target was refused now asserts it for `compile` and `propose`. Left undone: the browser's live validation does not submit the baseline, since it runs over the configuration parts and the baseline is not one, so the warning reaches a client that asks and the Baseline view shows what is missing from its own list. `check:config-studio` gained the new worker test file. Verified with `mise run check:config-studio`, which exited 0 with 21, 171 and 296 tests passed in its three suites, 24, 204 and 10 in the three Java modules, and 30 browser tests on the fake service.
- 2026-11-13: the maintainer ratified `baseline` as a target of `validate`, asked for the browser's live validation to take the baseline (SVA-B2c added), chose for TD-164 that the writer reads an import's content from its fence job in the store (SVA-B2d added, and TD-164 leaves the debt register for it), and will decide ADR-A154 after SVA-R0's probes. SVA-B4 picked up.
- 2026-11-13: SVA-B4 built, [Validation Pack](../validation/SVA-B4.md). The diagram's third view draws the workspace's ontology, each held and each missing import and each concept scheme, with imports as stated, a binds edge from the ontology that declares the property a scheme contract constrains to each scheme its bindings or its fallback name, and a dashed edge derived from the terms a document uses, never where a stated edge joins the pair. The plan's acceptance was wrong about the sample again: the facility sample imports nothing, so it draws five binds edges and no other kind, and the plan's row now says so. The derived edge is held by unit tests and was seen in no picture. Left as it is: a graph of more than five nodes opens at a fixed zoom, so the sixth scheme of the facility sample is cut at the pane's edge until the author pans, and the view fetches the workspace's dependencies itself while it is open, since the studio's state keeps them only merged. Verified with 308 unit tests, the type check and 31 browser tests on the fake service.
