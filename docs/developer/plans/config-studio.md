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

## Planned validation

One command per slice, as each Validation Pack section names, and `mise run check:config-studio` for CS0 to CS3 together. CS4's browser test needs the stack up and runs on demand, never in `check`.
