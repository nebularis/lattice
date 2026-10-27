<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Configuration Studio - Plan

**Unit ID:** `config-studio`
**Sketch:** [config-studio.md](../sketches/config-studio.md), the design and decisions CS-D1 to CS-D14
**Status record:** [config-studio.md](../status/config-studio.md)
**ADR:** [A-136](../../architecture/decisions/ADR-A136-configuration-studio.md), Proposed

## Scope

A web application in which an author opens an applied ontology as a baseline, authors `dal:` persistence and `srf:` surface configuration against it with forms derived from the LATTICE vocabularies, sees SHACL and compiler findings on the fields that caused them while editing, saves under optimistic concurrency, and compiles to the compiled profile, its SPARQL and the generated surfaces. A proof of concept per ADR-A136.

CS5 and CS6 were added at the maintainer's request on 2026-10-27 (sketch §8).

**Out of scope.** Projection contracts, authentication and several users, the store SPI, a revision ledger, housekeeping, running generated SPARQL against a store. See sketch §7.

## Dependencies

`tools/persistence` (`compile_to_graph`, `instantiate_by_target`, `find_gaps`), `tools/surface` (`read_contracts`, `SurfaceCompiler`, `render`), `tools/vocabulary` (`resolve`), `tools/mork_compilers` (`compile_any_condition`, `compile_profile`, the SPARQL and SHACL backends), the `dal:`, `srf:`, `fnd:`, `voc:`, `qnt:` and `elg:` specifications, the repository catalogue reader, Fuseki and RabbitMQ.

## Slices

The unit was briefed and built autonomously at the maintainer's request on 2026-10-27, so each slice records its decisions in the status record instead of waiting for them.

| Slice | Delivers | Modules | Validation |
|---|---|---|---|
| CS0 | sketch, this plan, ADR-A136 Proposed, the `cst:` vocabulary, AMQP topology and samples in `contracts/config-studio`, `tools/config_studio_stage.py` | contracts, tools | [Validation Pack](../validation/config-studio.md) §CS0 |
| CS1 | the worker job: SHACL validation, compilation of both targets, findings as `sh:ValidationResult`, artefacts, gaps, the RabbitMQ adapter | workers | §CS1 |
| CS2 | the service: HTTP API of `contracts/config-studio/README.md`, Jena store over Fuseki or memory, revisions and `If-Match`, the job bus, static files and security headers | platform | §CS2 |
| CS3 | the browser application: workspaces, overview, baseline, ontology-derived editors, read path builder, live validation, save and conflict, undo, build view, command palette | apps | §CS3 |
| CS4 | the stack: mise tasks, an optional compose file, Fuseki and RabbitMQ run by hand, a browser test over the live stack, the dependency audit | deployment, apps | §CS4 |
| CS5 | three more graphs and targets: contract, service, staging, samples, and the worker's vocabulary resolution table, quantification validation and eligibility compilation, expansion and tests | contracts, platform, workers | §CS5 |
| CS6 | the vocabulary, quantification and eligibility views: concept trees, binding validity, the resolution table, number lines and ranges, decision by concept, tests, under-construction notes | apps | §CS6 |
| CS7 | `studio:up`, `studio:down` and `studio:status` on every platform, with pinned downloads and each tool's own shutdown | tools, mise | §CS7 |

## Roadmap

Recorded 2026-10-27 at the maintainer's request, toward making the studio a supported part of LATTICE once it merges. Each slice waits on the decisions it names, and none is authorised until they are recorded.

| Slice | Delivers | Waits on |
|---|---|---|
| CS8 | the service on a portable HTTP server | CS-Q1, the server |
| CS9 | the studio supported: an ADR replacing ADR-A136's proof-of-concept status, register entries (capability, mechanisms, patterns, standards it follows), a published architecture and design document drawn from the sketch and the READMEs, an operations guide configuring every part, and runbooks | CS-Q2, which ADR and what "supported" commits us to. After CS8, so the operations guide describes the server once |
| CS10 | RDF/XML on the HTTP API by content negotiation, beside Turtle | CS-Q3, whether RDF/XML is the XML wanted, or XML documents such as LegalRuleML and InsurML |
| CS11 | the contract builder, CB0 to CB4 of the builder brief | the builder's own questions, and CS9 |
| CS12 | the Word add-in and the studio unified, see below | CS-Q4 |

**CS12, unifying the Word authoring proof of concept.** The Word add-in's plan proposes a separate web app in its tranche WA14 to WA16 (`apps/word-authoring-webapp`), awaiting decisions WA-D14 to WA-D20. A wording mode in the studio, which CS11 would build, does the same job, so we expect that tranche to be replaced by CS11 and CS12 rather than built. What CS12 must decide, as CS-Q4:

- the service. (a) the studio's service takes over the authoring service's endpoints, in RDF, and the add-in becomes a client of it. (b) both services stay, over one Fuseki dataset and one graph naming. The authoring service runs on Javalin (WA-D4), which ADR-A136 rejected for its advisories, so CS8's server choice should serve both
- the wire. The add-in's contracts are JSON (`contracts/authoring`), and the studio's are Turtle
- the shared code. The add-in's domain modules (the tag codec, offsets, snapshots) and the studio's graph model, in one package both apps depend on, as WA-D15 (a) proposes for the web app
- the stack. One `studio:up` for both, retiring `deployment/compose/authoring` or folding it in

### Open questions

| ID | Question |
|---|---|
| CS-Q1 | which HTTP server the service runs on |
| CS-Q2 | whether "supported" is a new ADR superseding ADR-A136 or an amendment to it, and what support covers: compatibility of the HTTP API and `cst:`, security, a shared deployment |
| CS-Q3 | which XML is wanted |
| CS-Q4 | the service, wire and shared-code choices for CS12 above |

## Planned validation

One command per slice, as each Validation Pack section names, and `mise run check:config-studio` for CS0 to CS3 together. CS4's browser test needs the stack up and runs on demand, never in `check`.
