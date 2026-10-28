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
| CS8 | **done 2026-10-28.** The service on Helidon SE WebServer 4.5.6, replacing the JDK's HTTP server. Helidon 27 is compiled for Java 27 and the platform is on 25, so 4.5 until the platform moves. The service also checks that a configuration graph holds only its own part's terms, which today only the browser checks (`split.ts`), as STD-279 requires | nothing |
| CS9 | **done 2026-10-28.** The studio supported: ADR-A136 amended from a proof of concept to a supported component (CS-Q2), register entries (capability, mechanisms, patterns, the standards it follows), a published architecture and design document drawn from the sketch and the READMEs, an operations guide configuring every part, runbooks, and a review of every handler of both services against STD-279 | CS8, so the operations guide describes the server once |
| CS10 | **done 2026-10-28.** RDF/XML on the HTTP API by content negotiation, beside Turtle, for what a document means | nothing, CS-Q3 answered |
| CS11 | the contract builder, CB0 to CB4 of the builder brief, including the studio's wording mode | CS12c. The builder's questions are answered below |
| CS12 | the Word authoring proof of concept unified with the studio, in the steps below | CS8 for CS12a |
| CS13 | **done 2026-10-28.** Forms read SHACL shapes first, then `rdfs:domain` and `rdfs:range` (CS-Q7), with the layers' node and property shapes staged into the served vocabulary and a required marker | CS-Q7 |
| CS14 | **done 2026-10-28.** Partitioned store writers, the store on disk in TDB2, job retention, samples recorded on the workspace, and export and import as TriG (CS-Q8) | CS-Q8 |
| CS15 | **done 2026-10-28.** A facility agreement sample in every part over one baseline, the parts referring to one another, with deliberate resolution and decision cases | nothing |

### CS12, unifying the Word authoring proof of concept

Decided 2026-10-27 (CS-Q4). Wording becomes a mode of the studio, so the Word add-in plan's web app tranche (WA14 to WA16, `apps/word-authoring-webapp`) is replaced by CS11 and CS12 rather than built. The studio and the authoring service become one deployable service, reached in steps that each ship and test alone. Both clients share one domain package. One `studio:up` starts everything.

**The wire rule.** The document is XML, and what it means is RDF. Documents, with their clauses, definitions and marked spans, travel as XML and are validated against a schema in `contracts/`, which takes the place the JSON Schemas hold today, so contract first (PRI-53) still holds. Meaning, configuration, findings and jobs travel as RDF, Turtle by default and RDF/XML on request (CS10). JSON stays only where something generates it.

**The document vocabulary.** LATTICE's own, domain-neutral, extending the add-in's namespace and drawing on Akoma Ntoso for its structure, without depending on it. Akoma Ntoso and InsurML are targets reached by XSLT through the transformation sidecar (ADR-A119), never the base vocabulary. It has an ADR of its own, apart from Wording's (CS-Q5), since Wording is what a document means and the vocabulary is the markup that describes it.

| Step | Delivers | Waits on |
|---|---|---|
| CS12a | **Done 2026-10-28 for the server**, with Jena 6.2.0 and Jackson 2.22.4. The graph naming and revisions moved to CS12d, where the store is shared. The authoring service on Helidon SE WebServer, replacing Javalin (WA-D4), and on the studio's graph naming and per-graph revisions with `If-Match`, still speaking JSON. Every handler validates its input at the service (STD-279) | CS8 |
| CS12b | **done 2026-10-28**, with the document model, the tag codec, offsets and the graph model. The shared domain package, `packages/authoring-domain`: TypeScript with no UI and no Office.js, holding the document model, the tag codec, UTF-16 offsets, the document XML reader and writer once CS12c defines it, and the studio's graph model (`src/rdf/graph.ts`). Both apps depend on it as a Yarn workspace. The conversion between Word's OOXML and the document XML stays in the add-in, since only Word needs it. Moved with its tests, so both apps' suites pass unchanged | nothing |
| CS12c | the document XML vocabulary, its own ADR (ADR-A137, accepted 2026-10-28 with DM-Q1 to DM-Q3) and its schema in `contracts/`, in RELAX NG and XSD as CS-Q5 records, with an XSLT mapping to Wording RDF through the sidecar | nothing |
| CS12d | one deployable service: the authoring API folded into the studio's service as its own Maven module, sharing one Helidon server, store and job bus. The add-in sends documents as XML and reads meaning as RDF, and the authoring JSON Schemas are retired | CS12a, CS12b, CS12c |
| CS12e | one stack: `studio:up` and `studio:down` start and stop the add-in's dev server too, and `deployment/compose/authoring` is folded into the studio's compose file | CS12d |

Bundling and releasing the studio and the add-in are left until after CS12.

### The contract builder's questions

The builder brief's questions, answered 2026-10-28.

| ID | Question | Answer |
|---|---|---|
| CB-Q1 | a mode of the studio, or an app of its own | a mode of the studio, sharing its graph model, inspector, problems drawer and jobs, and `packages/authoring-domain` with the Word add-in |
| CB-Q2 | how far "see how a term would be applied" goes before instantiation | what each term reads, and a dry run on sample facts of its eligibility conditions and of one regime's triggers. No preview instantiation, which would be bound meaning arriving early. Eligibility runs through the compiled SPARQL, as the studio's tests do, and never the reference evaluator (ADR-A-FM3). Stepping a regime has no compiled path yet, so CB0 decides whether that is compiler work or is marked under construction |
| CB-Q3 | an LLM proposer in LATTICE | a public proposer interface, with manual entry as its trivial proposer, and an LLM proposer whose only pack in the repository is MTP, any other being loaded from outside it. Every proposal carries its span, its template and its provenance, and goes through one review queue (Confirm, Retarget, Decline, Defer) |
| CB-Q4 | which rule languages CB5 imports | ODRL and Logical English, each behind a feature flag. The brief's "OBRL" was a typo for ODRL |
| CB-Q5 | timing | a tag by the end of November 2026 carrying CB0 to CB2 and, from CB4, what each term reads. CB3's LLM proposer and the regime dry run follow if they slip |

CB0 is three ADRs rather than one: the builder, Wording's neutral assembly model, separated from the InsurML default the assembly-interface sketch records under IMA-D17, and the assembler's topology. Its examples are a facility agreement and a software licence. The brief's estimate of 6 to 8 hours for CB0 to CB4 is the low end, since the assembler is new substrate with strict laws.

### Open questions

| ID | Question |
|---|---|
| CS-Q1 | which HTTP server the service runs on. **Decided 2026-10-27: Helidon SE WebServer**, for its virtual threads, HTTP/2, its own NIO with no Netty, and no advisory known to OSV across its artefacts on that date |
| CS-Q2 | whether "supported" is a new ADR superseding ADR-A136 or an amendment to it, and what support covers. **Answered 2026-10-28:** supported means we develop and maintain the studio with the ontologies, and it becomes part of a release once the release policy is defined. An amendment to ADR-A136 in CS9, since it is still Proposed and supersession is for an Accepted record. Its decision 1 then makes the HTTP API, the job messages and `cst:` contracts that change only with deprecation, and ADR-A135 then governs any JSON they gain. Which software a release carries, and how it is versioned, is the release policy's own ADR, beside ADR-A129, and outside this unit |
| CS-Q3 | which XML is wanted. **Answered 2026-10-27:** both, by the wire rule above. RDF/XML for meaning (CS10), and a document XML vocabulary for documents (CS12c) |
| CS-Q4 | the service, wire and shared code for CS12. **Decided 2026-10-27:** one deployable reached in steps, the wire rule, the shared domain package, one `studio:up` |
| CS-Q5 | for CS12c, the schema language of the document vocabulary (XSD or RELAX NG), and which ADR defines the vocabulary. **Answered 2026-10-28:** an ADR of its own. Both schema languages, **decided 2026-10-28** under the maintainer's delegation: RELAX NG compact syntax is the source we write and review, and XSD 1.0 is generated from it with Trang, for the tools that expect XSD (the JDK's validator, Word's schema library, schema-aware XSLT). A check validates a corpus of valid and invalid fixtures against both and fails where their verdicts differ, which also keeps the RELAX NG within what XSD can express. RELAX NG is the source because it is the shorter and more readable of the two, composes by pattern, and is what LegalRuleML treats as normative, and XSD because our consumers' tools validate with it |
| CS-Q6 | whether the platform moves from JDK 25 to 27, so the services can take Helidon 27 (CS-B14). **Decided 2026-10-28:** the platform stays on JDK 25 and Helidon 4.5, and moves when Helidon supports the next long-term JDK, 29 |
| CS-Q7 | how a form places a property with no `rdfs:domain` (CS-D5). **Decided 2026-10-28:** forms read SHACL shapes first and fall back to `rdfs:domain` and `rdfs:range` where no shape names a property. Built as CS13 |
| CS-Q8 | how a job's status reaches the service without contention on the store (formerly CS-D4, then PDD-13), and whether the store is kept on disk. **Decided 2026-10-28:** one store writer per workspace through a consistent-hash exchange and partition queues with a single active consumer, a pool of writers sized per deployment, TDB2 on disk in the user's data folder, jobs on disk with a retention, samples copied on demand, and export and import as TriG. Recorded in ADR-A136's second amendment of 2026-10-28 (Proposed). Built as CS14 |

## Planned validation

One command per slice, as each Validation Pack section names, and `mise run check:config-studio` for CS0 to CS3 together. CS4's browser test needs the stack up and runs on demand, never in `check`.
