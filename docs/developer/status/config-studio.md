<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Configuration Studio - Status

**Unit ID:** `config-studio`
**Status:** 🟡 CS0 to CS4 built and verified. Awaiting the maintainer's review and ratification of CS-D1 to CS-D9
**Last updated:** 2026-10-27
**Plan:** [config-studio.md](../plans/config-studio.md)
**Sketch:** [config-studio.md](../sketches/config-studio.md)
**ADR:** [A-136](../../architecture/decisions/ADR-A136-configuration-studio.md), Proposed
**Validation Pack:** [config-studio.md](../validation/config-studio.md)
**Branch:** `claude/config-authoring-studio`, from `main` at `4dd39e4c`

## Current position

Built autonomously in one session at the maintainer's request, from sketch to a browser test over the live stack. Every check the Validation Pack lists was run and passed. The decisions below were taken alone and wait for ratification. ADR-A136 stays Proposed.

**Next action, for the maintainer:** review the Validation Pack, run `mise run check:config-studio` and `mise run test:config-studio`, try the studio (the service's README, "Run it"), and rule on CS-D1 to CS-D9.

## Decisions taken alone, for ratification

CS-D1 to CS-D9 are in [sketch §6](../sketches/config-studio.md#6-decisions-taken-alone-for-ratification). Further decisions made while building:

| ID | Decision | Why |
|---|---|---|
| CS-B1 | Surface validation runs the surface specification and `shapes/structural.ttl` only, and adds a `ConstraintsNotRun` warning | pySHACL refuses `shapes/constraints.ttl` (TD-11) |
| CS-B2 | A compiler refusal's `cst:code` is the wrapped cause's class name, and its focus the target class | `CompileError` wraps the real exception, and names the target, not the configuration node. The browser maps a class focus onto the nodes that configure it |
| CS-B3 | The browser skips validation of an empty configuration and disables its compile | the store holds no graph for an empty configuration, so its job would fail on a missing input |
| CS-B4 | Jena 6.2.0 in the service, against the parent's 5.1.0 | Jena 5.6.0 brought `libthrift` 0.22.0, which carries two advisories (CS4-02) |
| CS-B5 | Turtle responses carry fixed prefixes, and the browser makes up one for any other namespace used twice | the store keeps no prefixes, and `lending:Thing` reads better than a full IRI |
| CS-B6 | The pyoxigraph pin in `requirements-lock.txt` and the root `pyproject.toml` moves from 0.5.11 to 0.5.13 | `main` could not bootstrap: `tools/testing/oxigraph` requires 0.5.13, and the lock pinned 0.5.11 |
| CS-B7 | The Word add-in's `vitest` moves to 4.1.12 and `mermaid` to 12.2.0 | both lockfile entries carried advisories that Dependabot reports against the shared `yarn.lock`. Its 69 unit tests pass |
| CS-B8 | One Validation Pack for the five slices, a section each | they were built and are reviewed together |

## Learnings

- **The `dal:` shapes miss a convenience profile.** Personal data with no erasure on a `dal:DataAccessProfile` passes SHACL and is refused by the compiler. Recorded as TD-94, and covered in the studio by CS-D9.
- **The Word authoring POC service has nine dependencies with advisories.** Recorded as TD-95.
- **Fuseki refuses `INSERT DATA` with blank nodes** in this setup, so the service writes with `INSERT { } WHERE { }` and an empty pattern. Not yet a triple-store discovery entry: it was observed through Jena's `RDFConnectionFuseki` only and not probed alone.

## Knowledge index

The index answered the architecture questions well (CAP-52, CAP-80, ADR-A38, ADR-A79, PAT-26, ADR-A30, ADR-A35). It answered weakly on dependency hygiene for a new app: nothing records how to audit an app's dependencies before adding them, which TD-90 names as a missing scheduled check. A standard such as "audit a new dependency set with the OSV database before committing it" would have answered.

## Adversarial probes

| Probe | Broken | Test that failed | Restored |
|---|---|---|---|
| P1 | the worker's validation no longer compiles (CS-D9 removed) | CS1-03, `test_persistence_validate_reports_a_refusal_the_shapes_cannot_see` | yes, 18 pass |
| P2 | the service's `If-Match` comparison always succeeds | CS2-03, `putWithStaleIfMatchIs412AndLeavesTheGraphUnchanged` | yes, 29 pass |
| P3 | found by the suite while building, not planted: Turtle prefixes in parse order | CS3-05 | fixed, prefixes sorted |

## History

- 2026-10-27: unit opened, oriented, branch `claude/config-authoring-studio` cut from `main`. Sketch, contracts, staging, worker, service, browser application, stack tasks, compose file, tests, audit and documents written and verified. Fuseki 6.2.0 and RabbitMQ 4.4.0 run by hand, since Docker was not running.
