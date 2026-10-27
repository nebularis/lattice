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

Recorded 2026-10-27 at the maintainer's request, toward making the studio a supported part of LATTICE once it merges. A slice whose "Waits on" names an open question is not authorised until that question is answered.

| Slice | Delivers | Waits on |
|---|---|---|
| CS8 | the service on Helidon SE WebServer, replacing the JDK's HTTP server. The service also checks that a configuration graph holds only its own part's terms, which today only the browser checks (`split.ts`), as STD-279 requires | nothing |
| CS9 | the studio supported: an ADR replacing ADR-A136's proof-of-concept status, register entries (capability, mechanisms, patterns, the standards it follows), a published architecture and design document drawn from the sketch and the READMEs, an operations guide configuring every part, runbooks, and a review of every handler of both services against STD-279 | CS-Q2. After CS8, so the operations guide describes the server once |
| CS10 | RDF/XML on the HTTP API by content negotiation, beside Turtle, for what a document means | nothing, CS-Q3 answered |
| CS11 | the contract builder, CB0 to CB4 of the builder brief, including the studio's wording mode | the builder's own questions, CS9 and CS12c |
| CS12 | the Word authoring proof of concept unified with the studio, in the steps below | CS-Q5 for CS12c |

### CS12, unifying the Word authoring proof of concept

Decided 2026-10-27 (CS-Q4). Wording becomes a mode of the studio, so the Word add-in plan's web app tranche (WA14 to WA16, `apps/word-authoring-webapp`) is replaced by CS11 and CS12 rather than built. The studio and the authoring service become one deployable service, reached in steps that each ship and test alone. Both clients share one domain package. One `studio:up` starts everything.

**The wire rule.** The document is XML, and what it means is RDF. Documents, with their clauses, definitions and marked spans, travel as XML and are validated against a schema in `contracts/`, which takes the place the JSON Schemas hold today, so contract first (PRI-53) still holds. Meaning, configuration, findings and jobs travel as RDF, Turtle by default and RDF/XML on request (CS10). JSON stays only where something generates it.

**The document vocabulary.** LATTICE's own, domain-neutral, extending the add-in's namespace and drawing on Akoma Ntoso for its structure, without depending on it. Akoma Ntoso and InsurML are targets reached by XSLT through the transformation sidecar (ADR-A119), never the base vocabulary. Its definition is a design decision and needs an ADR before CS12c.

| Step | Delivers | Waits on |
|---|---|---|
| CS12a | the authoring service on Helidon SE WebServer, replacing Javalin (WA-D4), and on the studio's graph naming and per-graph revisions with `If-Match`, still speaking JSON. Every handler validates its input at the service (STD-279) | CS8 |
| CS12b | the shared domain package, `packages/authoring-domain`: TypeScript with no UI and no Office.js, holding the document model, the tag codec, UTF-16 offsets, the document XML reader and writer once CS12c defines it, and the studio's graph model (`src/rdf/graph.ts`). Both apps depend on it as a Yarn workspace. The conversion between Word's OOXML and the document XML stays in the add-in, since only Word needs it. Moved with its tests, so both apps' suites pass unchanged | nothing |
| CS12c | the document XML vocabulary, its ADR and its schema in `contracts/`, with an XSLT mapping to Wording RDF through the sidecar | CS-Q5 |
| CS12d | one deployable service: the authoring API folded into the studio's service as its own Maven module, sharing one Helidon server, store and job bus. The add-in sends documents as XML and reads meaning as RDF, and the authoring JSON Schemas are retired | CS12a, CS12b, CS12c |
| CS12e | one stack: `studio:up` and `studio:down` start and stop the add-in's dev server too, and `deployment/compose/authoring` is folded into the studio's compose file | CS12d |

Bundling and releasing the studio and the add-in are left until after CS12.

### Open questions

| ID | Question |
|---|---|
| CS-Q1 | which HTTP server the service runs on. **Decided 2026-10-27: Helidon SE WebServer**, for its virtual threads, HTTP/2, its own NIO with no Netty, and no advisory known to OSV across its artefacts on that date |
| CS-Q2 | whether "supported" is a new ADR superseding ADR-A136 or an amendment to it, and what support covers: compatibility of the HTTP API and `cst:`, security, a shared deployment |
| CS-Q3 | which XML is wanted. **Answered 2026-10-27:** both, by the wire rule above. RDF/XML for meaning (CS10), and a document XML vocabulary for documents (CS12c) |
| CS-Q4 | the service, wire and shared code for CS12. **Decided 2026-10-27:** one deployable reached in steps, the wire rule, the shared domain package, one `studio:up` |
| CS-Q5 | for CS12c, the schema language of the document vocabulary (XSD or RELAX NG), and which ADR defines the vocabulary: a Wording ADR, since Wording owns documents, or one of its own |

## Planned validation

One command per slice, as each Validation Pack section names, and `mise run check:config-studio` for CS0 to CS3 together. CS4's browser test needs the stack up and runs on demand, never in `check`.
