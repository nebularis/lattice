<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Word authoring proof of concept - Status

**Unit ID:** `word-authoring-poc`
**Status:** 🚧 In progress. Decisions recorded, WA0 preflight passed (P5 and P6 on re-run). WA1 is
next
**Last updated:** 2026-10-01
**Plan:** [word-authoring-poc.md](../plans/word-authoring-poc.md)
**Sketch:** [word-authoring-poc.md](../sketches/word-authoring-poc.md)
**ADR:** [A-114](../../architecture/decisions/ADR-A114-word-authoring-proof-of-concept.md), Proposed
**Machine:** S. Branch `ux/auth-le`, local commits only

## Current position

The design and a one-shot plan of thirteen slices (WA0 to WA11, with WA9a) are written. Decisions
WA-D1 to WA-D13 were recorded by the human on 2026-10-01: WA-D4 is Javalin, the rest follow the
recommendations. ADR-A114 stays Proposed. WA0 (preflight) is done. No code exists yet.

**Next action, for the human:** ask for WA1 onward.
**Next action, for the agent:** WA1, when asked. No preflight blocker remains.

## Preflight (WA0, 2026-10-01)

| # | Check | Result | Detail |
|---|---|---|---|
| P1 | clean tree, branch, identity | pass | branch `ux/auth-le`, identity set. The only changes were this unit's planning documents, committed with WA0 |
| P2 | `mise run check:java` | pass | BUILD SUCCESS, 8 modules. A warning that the `oss.sonatype.org` snapshots repository fails TLS (PKIX) did not affect the build |
| P3 | new Maven artefacts | pass | jena-arq, jena-shacl, jena-rdfconnection 5.1.0, jackson-databind 2.18.2, json-schema-validator 1.5.6, amqp-client 5.22.0, slf4j-simple 2.0.16, javalin 6.7.0, testcontainers 2.0.2, shade 3.6.0, failsafe 3.5.0 |
| P4 | Python packages through the mirror | pass | host: rdflib 7.6.0, pika 1.4.4, jsonschema 4.26.0 with attrs, referencing, jsonschema-specifications and rpds-py (cp314 win_amd64). Linux pure wheels: rdflib, pika, pyparsing 3.3.3 |
| P5 | Node, Yarn, npm registry | pass on re-run | first run failed (`NODE_EXTRA_CA_CERTS` unset). The human set it at user level to the Zscaler root CA under `C:\Program Files (x86)\MSIRepair\`. Re-run: Yarn 4.6.0 runs, `yarn npm info vitest` answers. A shell opened before the change must load it from the user environment |
| P6 | Docker | pass on re-run | first run failed (engine not running). Re-run: Linux engine 29.8.0, API 1.56. All five images pulled. The Fuseki image has both `wget` and `curl`, so WA10's health check stands as written |
| P7 | Edge for Playwright | pass | `msedge.exe` present |

## Slice board

| # | Slice | State | Commit | Blocked on |
|---|---|---|---|---|
| WA0 | Preflight | done | this commit | |
| WA1 | Contracts, templates and samples | ready | | |
| WA2 | Service model, mapping and shapes | waiting | | WA1 |
| WA3 | Detection, templates and conformance | waiting | | WA2 |
| WA4 | API and HTTP adapter | waiting | | WA3 |
| WA5 | Fuseki, RabbitMQ and the runnable service | waiting | | WA4 |
| WA6 | Logical English reading | waiting | | WA2 |
| WA7 | Worker runtime | waiting | | WA6 |
| WA8 | Add-in domain | waiting | | WA1 |
| WA9 | Add-in task pane and harness | waiting | | WA8 |
| WA9a | Ribbon and right-click commands | waiting | | WA9, WA-D13 |
| WA10 | Compose stack | waiting | | WA5, WA7, WA9a |
| WA11 | Documentation and close-out | waiting | | WA10 |

## Token use

| Slice | Estimate | Actual |
|---|---|---|
| WA0 to WA11 | about 4.35M in total (plan §4) | |
| WA0 | 60k | about 60k |

## History

- 2026-10-01: sketch, plan, status record and ADR-A114 (Proposed) written on `ux/auth-le`. No
  ontology change, so no release tag is due.
- 2026-10-01: slice WA9a added at the human's request: ribbon group and right-click commands for
  marking text, decision WA-D13 (shared runtime), checklist steps M11 to M14, risk R8.
- 2026-10-01: decisions WA-D1 to WA-D13 recorded by the human. WA-D4 is Javalin (pinned 6.7.0, the
  plan's WA4 adapter rewritten for it), the rest as recommended. ADR-A114 decision 6 names Javalin.
- 2026-10-01: WA0 preflight run in autonomous mode. P1 to P4 and P7 pass, P5 and P6 fail (above).
  Committed with the unit's planning documents as `[wap] WA0: preflight` (`a0758ae`).
- 2026-10-01: P5 and P6 re-run after the human set `NODE_EXTRA_CA_CERTS` and started Docker
  Desktop. Both pass. All preflight checks now pass.
