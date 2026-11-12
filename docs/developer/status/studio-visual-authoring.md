<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Baseline management, canvases and run panes for the studio - Status

**Unit ID:** `studio-visual-authoring`
**Status:** planned. SVA-Q1 to SVA-Q16 open, each with a leaning, for the maintainer
**Last updated:** 2026-11-12
**Plan:** [studio-visual-authoring.md](../plans/studio-visual-authoring.md)
**Sketch:** [studio-visual-authoring.md](../sketches/studio-visual-authoring.md)

## Current position

The maintainer asked on 2026-11-12 for enhancements to the studio: ontology imports resolved through an XML catalog with missing imports reported, a drawing of how ontologies and vocabularies relate, axiom forms, ontology views, an editable canvas and a simulator for persistence and for surface, and in mapping mode a list of schemes, reusable template libraries and a sample pane that runs on demand. A detailed sketch and plan come first. The maintainer also asked for care with the studio's concurrent flows, above all results streamed to the browser over the broker's MQTT, and for the mechanical work of each slice to be delegated to a second model with the design overseen.

The sketch and the plan were written the same day from a reading of the studio's architecture, contract and code. The design's centre is the run, section 4 of the sketch: a result that is not stored reaches the tab as frames relayed by the service instance that accepted it, checked at delivery, bounded by a deadline, with the tab holding a simulator's state. BL-20, a runtime for RML, was added to the backlog as asked.

**Next action:** the maintainer answers SVA-Q1 to SVA-Q16. SVA-Q1 to SVA-Q4 decide phase R and the simulators, SVA-Q5 to SVA-Q7 phase B, SVA-Q14 the template libraries. No slice is briefed and no branch is due until then.

## Slices

| Slice | Deliverable | State | Blocked on |
|---|---|---|---|
| SVA-R0 | probes of the broker for content frames | planned |  |
| SVA-R1 | the decision record, the contract's Runs section, the topology and the fake service's runs | planned | SVA-R0 |
| SVA-R2 | the service's runs: pending entries, the relay's run sink, the waiting sink, the limits | planned | SVA-R1 |
| SVA-R3 | the run worker, from the transforms worker | planned | SVA-R1 |
| SVA-R4 | the browser's run controller and the dock's run pane | planned | SVA-R1 |
| SVA-R5 | the run protocol's failure cases on the real stack | planned | SVA-R2, SVA-R3, SVA-R4 |
| SVA-B1 | catalog reading, ontology headers, the import closure and its plan | planned |  |
| SVA-B2a | several imports held by one write, each with its ontology and version IRI | planned |  |
| SVA-B2b | LATTICE's documents served by IRI, and the missing import warning | planned | SVA-B2a |
| SVA-B3 | the Baseline view's imports list, import dialog and missing report | planned | SVA-B1, SVA-B2a |
| SVA-B4 | the import graph | planned | SVA-B3, SVA-O1 |
| SVA-O1 | the canvas kit, with layout in a web worker | planned |  |
| SVA-O2 | the class and object property view and the class hierarchy, with the shapes toggle | planned | SVA-O1 |
| SVA-O3 | the axiom reader and the element forms | planned |  |
| SVA-P1 | landing places in a compile job, and the exploded view, read-only | planned | SVA-O1 |
| SVA-P2 | edits on the persistence canvas | planned | SVA-P1 |
| SVA-P3 | the persistence simulation executor | planned | SVA-R3 |
| SVA-P4 | the persistence simulator pane | planned | SVA-R4, SVA-P1, SVA-P3 |
| SVA-S1 | the surface canvas | planned | SVA-O2 |
| SVA-S2 | the surface simulation executor | planned | SVA-P3 |
| SVA-S3 | the surface simulator pane | planned | SVA-S1, SVA-S2, SVA-P4 |
| SVA-M1 | the mapping schemes listed on the left | planned |  |
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

## Log

- 2026-11-12: raised by the maintainer. Sketched and planned, SVA-Q1 to SVA-Q16 raised, the board written with 30 slices planned. BL-20 added to the backlog.
