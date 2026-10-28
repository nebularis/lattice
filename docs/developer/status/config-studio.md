<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Configuration Studio - Status

**Unit ID:** `config-studio`
**Status:** 🟡 CS0 to CS6 built and verified. Awaiting the maintainer's review and ratification of CS-D1 to CS-D14
**Last updated:** 2026-10-27
**Plan:** [config-studio.md](../plans/config-studio.md)
**Sketch:** [config-studio.md](../sketches/config-studio.md)
**ADR:** [A-136](../../architecture/decisions/ADR-A136-configuration-studio.md), Proposed
**Validation Pack:** [config-studio.md](../validation/config-studio.md)
**Branch:** `claude/config-authoring-studio`, from `main` at `4dd39e4c`

## Current position

Built autonomously in one session at the maintainer's request, from sketch to a browser test over the live stack. Every check the Validation Pack lists was run and passed. The decisions below were taken alone and wait for ratification. ADR-A136 stays Proposed.

**Next action, for the maintainer:** review the Validation Pack, run `mise run check:config-studio` and `mise run test:config-studio`, try the studio (the service's README, "Run it"), and rule on CS-D1 to CS-D14.

## Decisions taken alone, for ratification

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

- 2026-10-28, later: CS8. The service on Helidon SE WebServer 4.5.6, since 27 needs Java 27, and a saved graph refused with `422` when it holds another part's subjects (STD-279). Verified with the unit tests, the shaded jar's self-check and the live stack.
- 2026-10-28: the maintainer answered CS-Q2 (an amendment to ADR-A136 in CS9) and CS-Q5 (the document vocabulary's own ADR, both schema languages, and delegated the choice of source, which we made: RELAX NG compact as source, XSD generated). `amqp-client` raised to 5.37.0 in `authoring-service` and `platform-outbox`, and RabbitMQ images from 3.13 to 4.4 in the POC's and the platform's compose files and the POC's integration tests. `check:java` and `check:authoring-service-it` pass. CS8 is next.
- 2026-10-27, latest: the maintainer decided CS-Q1 (Helidon), CS-Q3 and CS-Q4 (one deployable in steps, the document is XML and its meaning RDF, a shared domain package, one `studio:up`), and gave PRI-75 and STD-279. CS12 planned in steps CS12a to CS12e. CS8 is next.
- 2026-10-27, later still: CS7, start and stop scripts for every platform, verified on macOS. Roadmap CS8 to CS13 added to the plan at the maintainer's request.
- 2026-10-27, later: CS5 and CS6 at the maintainer's request: vocabulary, quantification and eligibility configurations, the resolution table, decision by concept and tests, with what waits on other work marked as under construction. Checked against the live stack.
- 2026-10-27: unit opened, oriented, branch `claude/config-authoring-studio` cut from `main`. Sketch, contracts, staging, worker, service, browser application, stack tasks, compose file, tests, audit and documents written and verified. Fuseki 6.2.0 and RabbitMQ 4.4.0 run by hand, since Docker was not running.
