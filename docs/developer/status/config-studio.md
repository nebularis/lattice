<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Configuration Studio - Status

**Unit ID:** `config-studio`
**Status:** 🟡 CS0 to CS10 and CS12a to CS15 built and verified. ADR-A136 and ADR-A137 accepted 2026-10-28, and ADR-A136's second amendment (writers and the on-disk store) accepted the same day
**Last updated:** 2026-10-28
**Plan:** [config-studio.md](../plans/config-studio.md)
**Sketch:** [config-studio.md](../sketches/config-studio.md)
**ADR:** [A-136](../../architecture/decisions/ADR-A136-configuration-studio.md) and [A-137](../../architecture/decisions/ADR-A137-document-markup-vocabulary.md), Accepted 2026-10-28
**Validation Pack:** [config-studio.md](../validation/config-studio.md)
**Branch:** `claude/config-authoring-studio`, from `main` at `4dd39e4c`

## Current position

Built autonomously in one session at the maintainer's request, from sketch to a browser test over the live stack. Every check the Validation Pack lists was run and passed. The decisions below were taken alone and wait for ratification. ADR-A136 stays Proposed.

**Next action, for the maintainer:** accept ADR-A136's third amendment (the writers deployed apart on a super stream), review CS17 in the Validation Pack, and rule on CS-B35 to CS-B41.

## Decisions taken alone, for ratification

**Ruled 2026-10-28.** Ratified: CS-D1 to CS-D3, CS-D5 as amended by CS-Q7 (shapes first, then domain and range), CS-D8 to CS-D14, and CS-B14 to CS-B22. Superseded by the ADR-A136 amendment: CS-D6 (Helidon) and CS-D7 (supported). Reopened, then decided as CS-Q8: CS-D4, which ADR-A136's second amendment replaces with partitioned writers. Later the same day: CS-B23 and CS-B25 to CS-B34 ratified. CS-B24 replaced by CS-Q9's answer, writers deployed apart on super streams (CS17). On CS-B30 the maintainer confirmed that a lone write is applied at once: a writer waits only for the first write and takes what else is already queued.

CS-D1 to CS-D9 are in [sketch §6](../sketches/config-studio.md#6-decisions-taken-alone-for-ratification), and CS-D10 to CS-D14 in [sketch §8](../sketches/config-studio.md#8-vocabulary-quantification-and-eligibility-added-2026-10-27). Further decisions made while building:

| ID | Decision | Why |
|---|---|---|
| CS-B1 | Surface validation runs the surface specification and `shapes/structural.ttl` only, and adds a `ConstraintsNotRun` warning | pySHACL refuses `shapes/constraints.ttl` (TD-11) |
| CS-B2 | A compiler refusal's `cst:code` is the wrapped cause's class name, and its focus the target class | `CompileError` wraps the real exception, and names the target, not the configuration node. The browser maps a class focus onto the nodes that configure it |
| CS-B3 | The browser skips validation of an empty configuration and disables its compile | the store holds no graph for an empty configuration, so its job would fail on a missing input |
| CS-B4 | Jena 6.2.0 in the service, against the parent's 5.1.0 | Jena 5.6.0 brought `libthrift` 0.22.0, which carries two advisories (CS4-02) |
| CS-B5 | Turtle responses carry fixed prefixes, and the browser makes up one for any other namespace used twice | the store keeps no prefixes, and `lending:Thing` reads better than a full IRI |
| CS-B6 | The pyoxigraph pin in `requirements-lock.txt` and the root `pyproject.toml` moves from 0.5.11 to 0.5.13 | `main` could not bootstrap: `tools/testing/oxigraph` requires 0.5.13, and the lock pinned 0.5.11 |
| CS-B7 | The Word add-in's `vitest` moves to 4.1.12 and `mermaid` to 12.2.0 | both lockfile entries carried advisories that Dependabot reports against the shared `yarn.lock`. Its 69 unit tests pass |
| CS-B8 | One Validation Pack for the slices, a section each | they were built and are reviewed together |
| CS-B9 | The worker reads a missing baseline graph as empty | a workspace of vocabulary and eligibility alone has an empty baseline, which the store does not keep |
| CS-B10 | A field is single-valued where its property is functional, or is a `dal:` property | `srf:`, `voc:`, `qnt:` and `elg:` declare functionality, `dal:` does not. A unit test found the first rule treating every `elg:` property as single-valued |
| CS-B11 | An expansion and a question with no `cst:resolutionTime` resolve at the job's submission time with no scope | PRI-56 forbids reading the clock inside the logic, and the submission time is the job's input |
| CS-B13 | `studio:up` and `studio:down` run `tools/config_studio_stack.py`, which downloads Fuseki and RabbitMQ with pinned SHA-256s and stops each process through its own shutdown: `rabbitmqctl shutdown` for RabbitMQ, SIGTERM with a minute's grace for the rest. The worker now finishes its job on SIGTERM | the maintainer asked for start and stop scripts for every platform that stop the tools by the means they support. Python, since every platform the repository supports already runs it through mise |
| CS-B12 | Foundation's `vocab` is staged with the vocabularies | its governance states are what `fnd:hasGovernanceState` offers |
| CS-B14 | Helidon 4.5.6 in both services, not 27 | Helidon 27 is compiled for Java 27 (class file 71), and the platform is on 25 |
| CS-B15 | The service refuses with `422` a saved graph that holds another part's subjects, by the rule of the browser's `split.ts` | STD-279. The service cannot know the browser sorted the graph |
| CS-B16 | An RDF/XML body that declares a DTD is refused, and a graph RDF/XML cannot write answers `406` | Jena reads an external entity as an empty string rather than failing, which stores a value nobody wrote. RDF/XML never needs a DTD |
| CS-B17 | The `cst:` namespace drops `poc/` from its IRI | a supported contract should not carry it, and no workspace outlives an in-memory store, so nothing needs migrating. Before supporting it, since it is a breaking change afterwards |
| CS-B18 | ADR-A136 is amended in place rather than superseded | the maintainer left the choice to us. It is still Proposed, and supersession is for an Accepted record |
| CS-B19 | The worker reads only the job's own input graph and a workspace baseline | STD-279. The job graph names the graphs to read, so a forged job could name any graph in the store |
| CS-B20 | The authoring service moves to Jena 6.2.0 and Jackson 2.22.4 within CS12a | together with the move off Javalin, it clears every advisory OSV knew in both services on 2026-10-28, which closes TD-95 |
| CS-B21 | `studio:up` refuses a service or dev-server port another process holds, and no longer empties `loopback_users` for the downloaded RabbitMQ | the runbook's author found `up` reporting success while the service failed to bind, and the native node binds to loopback, so `guest` needs no exception |
| CS-B22 | The package `packages/authoring-domain` takes the add-in's `types.ts` and the studio's `ns.ts` whole | `graph.ts` needs `ns.ts`, and splitting either would leave a second file of the same kind. The JSON-contract types in `types.ts` go when the contracts are retired in CS12d |
| CS-B23 | The writers' partition count is 8, fixed in `amqp-topology.json`, and a deployment sets the number of writers, 1 by default, from `LATTICE_STUDIO_WRITERS` | the consistent-hash exchange binds a fixed set of queues, and changing their number moves workspaces between them, so it is a contract. The writer count is the pool size the maintainer asked to configure |
| CS-B24 | The writers run inside the service process, and a service without a broker writes through one in-process writer | one deployable (CS-Q4). The in-process writer behaves as one partition's writer, so tests and a broker-less run keep the same rules |
| CS-B25 | A command is AMQP headers and an N-Quads body, and a reply is headers alone. A write the writer did not answer in 10 s expires and answers `503` | N-Quads is line-based RDF both runtimes write without a library choice, and an expired write is never applied after the author was told it failed |
| CS-B26 | The writer compares a job update with the stored job by value, not by term | rdflib rewrites an `xsd:dateTime`'s `Z` as `+00:00` (TSD-43), which a term comparison read as tampering, found running the live stack |
| CS-B27 | Finished jobs are swept hourly after 30 days (`LATTICE_STUDIO_JOB_RETENTION_DAYS`), and the browser still deletes a validation job once it has read it, keeping compile jobs | jobs on disk keep compile history, which the build view lists, while a validation runs on every pause in typing and would fill the store |
| CS-B28 | A creation and an import refuse a baseline that holds another part's subjects, as a save does (`422`), and a workspace's identity references are no longer warned about as undeclared | the writer must check a creation like any write (STD-279). An identity is a name nothing need describe, as the repository's examples show, so the warning was noise on every sample |
| CS-B29 | Each write's first operation inserts its receipt where its precondition holds, and its other operations require the receipt. A workspace's receipts live in its own receipts graph, a job's in the job's, deleted with it, and a workspace's deletion in the store's receipts graph. No principal is recorded | one guard per write, as PAT-21 asks, without repeating it in every operation, and the receipt is both PRI-54's record and the proof a write applied. Job receipts go with their job so receipts grow with workspaces, not with every validation |
| CS-B30 | A writer takes up to 64 waiting writes as one request and retries a batch the store refuses whole, while refusing or answering each command on its own | TSD-44: one commit costs about 65 ms and an operation under one. One transaction makes a retry safe, and receipts make a redelivered command a no-op |
| CS-B31 | A save expecting revision 0 is guarded by the absence of any other revision | a description written before a part existed has no revision for it, which reads as 0. Found by an existing test |
| CS-B32 | The surface compiler refuses a promotion outside its target namespace onto a property the source graph does not declare as a property, and the studio's compile adds the substrate's specifications to its source | the maintainer's D. The surface README already says such a property is one an authored layer declares, so the law's text stands. A promotion onto `fnd:externalKey` finds it in Foundation's specification |
| CS-B33 | The studio does not warn that a promotion's property is undeclared when it lies in the contract's target namespace | the compiler mints that property itself (`compile.py`), so the warning was wrong |
| CS-B34 | A `NOT EXISTS` pattern is wrapped in a group, and the service's tests send every request as SPARQL text | Jena writes a bare `GRAPH` inside `NOT EXISTS` without braces, which Fuseki refuses while the in-memory store, running the algebra, accepts it. Found on the live stack |
| CS-B35 | A write's partition is its workspace id's first 32 bits modulo 8, and the service and the worker publish to the super stream over AMQP 0.9.1 with that key, so only the writer speaks the stream protocol | identical in Java and Python with no hash library, and even, since workspace ids are random. The stream client's own hash routing would need the worker to reproduce it |
| CS-B36 | Past its 10-second wait the service reads the write's receipt, answering as applied if it is there and `503` otherwise, and no write expires | a stream keeps a write until a writer reaches it, so the classic queue's expiry has no equivalent, and the receipt tells the truth either way |
| CS-B37 | Each partition keeps a week of writes or 1 GiB | the receipts in the store are the lasting record, and a writer's stored offset is never older than its last batch |
| CS-B38 | The writer decodes the reply-to the stream stores as an AMQP 1.0 address, `/queues/` and the percent-encoded name | found on the live stack: every reply was lost until then, and only receipts answered the saves |
| CS-B39 | Fuseki serves one TDB2 database as two services, `studio`, which reads, and `studio-write`, which updates, from a configuration the stack writes and the compose file mounts, and a test keeps the two alike | least privilege for the service and the worker. Without authentication on Fuseki the separation holds by endpoint, not by credential |
| CS-B40 | One writer thread per instance, and a deployment scales writers by instances. `LATTICE_STUDIO_WRITERS` is gone, and the sweep moved into the writer | TDB2 commits one write at a time (TSD-42), so threads in one instance add nothing, while instances add failover and spread checking |
| CS-B41 | The writer logs a write it refuses and passes over it | a stream has no dead letters. The absent receipt records that the write did not apply |

## Learnings

- **The studio shows eligibility law L11 at work.** In the lending sample a required concept (manufacturing) expands to Undetermined, because an excluded concept (textiles) lies beneath it, so a manufacturing candidate's admission depends on its sub-sector. Correct, and a good example for a guide.

- **The `dal:` shapes miss a convenience profile.** Personal data with no erasure on a `dal:DataAccessProfile` passes SHACL and is refused by the compiler. Recorded as TD-94, and covered in the studio by CS-D9.
- **The Word authoring POC service has nine dependencies with advisories.** Recorded as TD-95. `amqp-client` 5.22.0, in it and in `platform-outbox`, carried ten (four high, fixed by 5.37.0), and the `rabbitmq:3.13` image resolves to 3.13.7, below the community fixes for this year's server advisories. Both raised 2026-10-28.
- **Fuseki refuses `INSERT DATA` with blank nodes** in this setup, so the service writes with `INSERT { } WHERE { }` and an empty pattern. Not yet a triple-store discovery entry: it was observed through Jena's `RDFConnectionFuseki` only and not probed alone.

## Knowledge index

The index answered the architecture questions well (CAP-52, CAP-80, ADR-A38, ADR-A79, PAT-26, ADR-A30, ADR-A35). It answered weakly on dependency hygiene for a new app: nothing records how to audit an app's dependencies before adding them, which TD-90 names as a missing scheduled check. A standard such as "audit a new dependency set with the OSV database before committing it" would have answered.

## Adversarial probes

| Probe | Broken | Test that failed | Restored |
|---|---|---|---|
| P1 | the worker's validation no longer compiles (CS-D9 removed) | CS1-03, `test_persistence_validate_reports_a_refusal_the_shapes_cannot_see` | yes, 18 pass |
| P2 | the service's `If-Match` comparison always succeeds | CS2-03, `putWithStaleIfMatchIs412AndLeavesTheGraphUnchanged` | yes, 29 pass |
| P3 | found by the suite while building, not planted: Turtle prefixes in parse order | CS3-05 | fixed, prefixes sorted |
| P4 | a question's expectation always counts as met | CS5-06, `test_a_question_decided_against_its_expectation` | yes, 12 pass |

## History

- 2026-10-28, CS17: the store writer is a deployable of its own, `config-studio-writer`, on a RabbitMQ super stream whose partitions spread across writer instances and fail over, with the shared code in `config-studio-core`, and the service and worker reading through a Fuseki service that cannot update. Verified natively, with two writers sharing and handing over partitions, and in Docker.
- 2026-10-28, CS16: the maintainer accepted ADR-A136's second amendment, ratified CS-B23 to CS-B28 except CS-B24, which CS-Q9 reopens, and decided A to D. Writes are batched one request per batch (TSD-44), guarded in the update (PAT-21) and leave a receipt each (PRI-54), and the surface compiler refuses a promotion onto an undeclared authored property. The index review found PAT-55 stale and the writer to be PAT-18.
- 2026-10-28, latest: CS13 to CS15 under the maintainer's delegation. Forms read shapes first (CS-Q7, by a sub-agent on its own branch, reviewed and merged). Partitioned store writers, the store on TDB2 in the user's data folder, job retention, export and import, and samples recorded on the workspace (CS-Q8), with ADR-A136's second amendment drafted. A facility agreement sample in every part (by a sub-agent, reviewed and merged). TSD-42 and TSD-43 recorded, MEC-88 and TD-97 to TD-99 added, PDD-13 closed into CS-Q8. The maintainer ruled on CS-D5, CS-D10, CS-D12, CS-B14 (stay on JDK 25), CB-Q4 (ODRL) and decided CS-Q8.
- 2026-10-28, ratification: the maintainer accepted ADR-A136 as amended and ADR-A137 with DM-Q1 to DM-Q3 as recommended, ruled on the decisions as recorded above, and answered the builder's questions (CB-Q1 to CB-Q5 in the plan). CS-D4 reopened as PDD-13. CS-Q6 and CS-Q7 raised.
- 2026-10-28, latest: CS9, CS12a and CS12b, under the maintainer's delegation. ADR-A136 amended to make the studio supported, the `cst:` namespace renamed, a published architecture document, an operations guide and a runbook, register entries (CAP-86 updated, MEC-84 to MEC-87, PAT-55), the STD-279 review of both services with the worker's gap fixed, the authoring service on Helidon with Jena 6 and Jackson 2.22 (TD-95 closed), the shared package, and the stack's port check. Two sub-agents wrote CS12b and the operator documents on their own branches, which we reviewed and merged.
- 2026-10-28, later still: CS10. RDF/XML beside Turtle by content negotiation, chosen in one place, and accepted in bodies, with a DTD refused.
- 2026-10-28, later: CS8. The service on Helidon SE WebServer 4.5.6, since 27 needs Java 27, and a saved graph refused with `422` when it holds another part's subjects (STD-279). Verified with the unit tests, the shaded jar's self-check and the live stack.
- 2026-10-28: the maintainer answered CS-Q2 (an amendment to ADR-A136 in CS9) and CS-Q5 (the document vocabulary's own ADR, both schema languages, and delegated the choice of source, which we made: RELAX NG compact as source, XSD generated). `amqp-client` raised to 5.37.0 in `authoring-service` and `platform-outbox`, and RabbitMQ images from 3.13 to 4.4 in the POC's and the platform's compose files and the POC's integration tests. `check:java` and `check:authoring-service-it` pass. CS8 is next.
- 2026-10-27, latest: the maintainer decided CS-Q1 (Helidon), CS-Q3 and CS-Q4 (one deployable in steps, the document is XML and its meaning RDF, a shared domain package, one `studio:up`), and gave PRI-75 and STD-279. CS12 planned in steps CS12a to CS12e. CS8 is next.
- 2026-10-27, later still: CS7, start and stop scripts for every platform, verified on macOS. Roadmap CS8 to CS13 added to the plan at the maintainer's request.
- 2026-10-27, later: CS5 and CS6 at the maintainer's request: vocabulary, quantification and eligibility configurations, the resolution table, decision by concept and tests, with what waits on other work marked as under construction. Checked against the live stack.
- 2026-10-27: unit opened, oriented, branch `claude/config-authoring-studio` cut from `main`. Sketch, contracts, staging, worker, service, browser application, stack tasks, compose file, tests, audit and documents written and verified. Fuseki 6.2.0 and RabbitMQ 4.4.0 run by hand, since Docker was not running.
