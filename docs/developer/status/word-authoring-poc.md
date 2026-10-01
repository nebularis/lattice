<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Word authoring proof of concept - Status

**Unit ID:** `word-authoring-poc`
**Status:** 🚧 In progress. WA0 to WA5 done. WA6 is next
**Last updated:** 2026-10-01
**Plan:** [word-authoring-poc.md](../plans/word-authoring-poc.md)
**Sketch:** [word-authoring-poc.md](../sketches/word-authoring-poc.md)
**ADR:** [A-114](../../architecture/decisions/ADR-A114-word-authoring-proof-of-concept.md), Proposed
**Machine:** S. Branch `ux/auth-le`, local commits only

## Current position

The design and a one-shot plan of thirteen slices (WA0 to WA11, with WA9a) are written. Decisions
WA-D1 to WA-D13 were recorded by the human on 2026-10-01: WA-D4 is Javalin, the rest follow the
recommendations. ADR-A114 stays Proposed. WA0 to WA5 are done: preflight, the WA1 contracts, the
WA2 service module that maps a snapshot to the Wording graph and validates it with SHACL, the WA3
detection, template and conformance checks, the WA4 HTTP API over Javalin with an in-memory store,
bus, registry and job tracking, and WA5's real Fuseki store, RabbitMQ bus, configuration and entry
point.

**Next action, for the human:** ask for WA6.
**Next action, for the agent:** WA6 (Logical English reading, the Python worker), when asked.

## Open question raised by WA3

WA3's prescribed self-probe ("change the overlap sort to start-first") does not fail any test, and
cannot, because the seven detection rules can overlap only by containment. A probe against the same
invariant was run instead and does fail. The detail is in the
[WA3 Validation Pack](../validation/word-authoring-poc-wa3.md) under Self-probe. Nothing is blocked,
but later slices that prescribe a probe should be read with the same scepticism.

## Open question raised by WA5

WA5's prescribed self-probe (remove `ServicesResourceTransformer`, expect `--self-check` to fail)
also does not fail: the self-check's code path does not happen to need the two Jena subsystem
registrations (`InitJenaCore`, `InitShacl`) that a plain shade drops. Confirmed directly by running
the broken jar by hand, not only through the test. A second test was added that opens the jar and
asserts its merged `JenaSubsystemLifecycle` services file, which does fail correctly. Detail in the
[WA5 Validation Pack](../validation/word-authoring-poc-wa5.md) under Self-probe. Two of two slices
with a prescribed probe have now needed a replacement; read every later one with the same scepticism
before trusting it.

## Note for WA3

WA2's provisional vocabulary (`platform/authoring-service/src/main/resources/vocab/wording-provisional.ttl`)
declares only the `wrd:`/`wap:` terms WA2 itself mints. When WA6 builds the worker that writes the
proposed meaning graph (sketch §4.4: `ins:` classes, `wap:proposalBasis`, `wap:activityText`, etc.),
add that file to WA6's own path list and extend it there.

## Note for WA5

WA4's `GET .../graph/proposal` route reads `store.getGraph(minter.proposalGraph(...))`, but nothing
in WA4 ever writes to that IRI: the worker writes the proposal graph directly to Fuseki, keyed by
the `proposalGraphIri` the request event already carries. WA4's tests cover only `wording` and an
invalid kind (plan S4-12's own scope). Exercise `proposal` end to end once the worker exists.

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
| WA0 | Preflight | done | `c82d019` | |
| WA1 | Contracts, templates and samples | done | `3db3911` | |
| WA2 | Service model, mapping and shapes | done | `52eae70` | |
| WA3 | Detection, templates and conformance | done | `8c4aa65` | |
| WA4 | API and HTTP adapter | done | `c82bcc2` | |
| WA5 | Fuseki, RabbitMQ and the runnable service | done | `187fea4` | |
| WA6 | Logical English reading | ready | | WA2 |
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
| WA1 | 300k | about 220k |
| WA2 | 450k | about 480k |
| WA3 | 300k | about 230k |
| WA4 | 450k | about 520k |
| WA5 | 350k | about 400k |

## History

- 2026-10-01: sketch, plan, status record and ADR-A114 (Proposed) written on `ux/auth-le`. No
  ontology change, so no release tag is due.- 2026-10-01: slice WA9a added at the human's request: ribbon group and right-click commands for
  marking text, decision WA-D13 (shared runtime), checklist steps M11 to M14, risk R8.
- 2026-10-01: decisions WA-D1 to WA-D13 recorded by the human. WA-D4 is Javalin (pinned 6.7.0, the
  plan's WA4 adapter rewritten for it), the rest as recommended. ADR-A114 decision 6 names Javalin.
- 2026-10-01: WA0 preflight run in autonomous mode. P1 to P4 and P7 pass, P5 and P6 fail (above).
  Committed with the unit's planning documents as `[wap] WA0: preflight` (`a0758ae`).
- 2026-10-01: P5 and P6 re-run after the human set `NODE_EXTRA_CA_CERTS` and started Docker
  Desktop. Both pass. All preflight checks now pass.
- 2026-10-01: WA1 done (`3db3911`, hash recorded `07acc66`).
- 2026-10-01: WA2 done: `platform/authoring-service` (new Maven module: `json`, `model`, `rdf`,
  `validation`, `app` packages), the provisional vocabulary and 11 SHACL shapes, 48 tests, fixed
  fixtures regenerated and committed. Found and fixed a real defect: Jena reports a nested
  `sh:property [...]` blank node, not the enclosing named shape, as `sh:sourceShape`, so seven
  shapes were flattened to top-level named property shapes (Validation Pack "Implementer
  choices"). Self-probe confirmed (WS10's `OPTIONAL` removal breaks the zero case). `check:java`
  (all 8 modules) and `check:authoring-contracts` (WA1) still pass.
- 2026-10-01: WA1 done: `contracts/authoring` (12 schemas, templates, samples, fixtures,
  `amqp-topology.json`), `contracts/events` (2 event schemas), `contracts/openapi`, worker test
  `test_authoring_contracts.py` (35 tests, all pass), `check:authoring-contracts` wired into
  `mise.toml`. Validation Pack at `docs/developer/validation/word-authoring-poc-wa1.md`. Self-probe
  confirmed (AC-02 catches a missing `additionalProperties: false`). Full `check:workers` (73
  tests) still passes.
- 2026-10-01: the WA2 Java sources reviewed for simplicity at the human's request, in "ponytail"
  mode (`.github/prompts/ponytail.md`). Seven files, 57 insertions and 91 deletions, no behaviour
  change: `WordingMapper` holds one `IriMinter`, `CanonicalHash.canonicalText` is the single place
  the fixture text is formed, `SnapshotReader` uses one list helper, `IriMinter` one validator.
  `check:authoring-service`, `check:java` and `check:authoring-contracts` all green, and
  `build:authoring-fixtures` reproduced the three `.nt` goldens byte for byte. Committed as
  `278f23e`.
- 2026-10-01: WA3 done (`8c4aa65`): `detection` (`ConstructDetector`, `Detection`, `Suggestion`)
  and `template` (`TemplateCatalog`, `SampleCatalog`, `AuthoringTemplate`, `TemplateSection`,
  `TemplateFindings`, `ConformanceChecker`, `Finding`, the two summaries) packages, plus
  `ContractSchemas.readValidated` shared by the catalogs. 15 new tests, 63 in the module, all pass
  first run. Validation Pack at `docs/developer/validation/word-authoring-poc-wa3.md`. The plan's
  self-probe was found to be vacuous (see above) and a probe that bites was run in its place.
  `check:java` (9 modules) and `check:authoring-contracts` still pass.
- 2026-10-01: WA4 done: `store`, `messaging`, `jobs`, `api` and `http` packages, Javalin 6.7.0
  added to the module, ten routes behind `AuthoringApi`, `AuthoringHttpServer`, `SampleSeeder`.
  `TemplateFindings` and `ConformanceChecker` changed from WA3's static-utility shape to
  instantiable classes, since plan WA4 holds them as `AuthoringApi` constructor collaborators
  (no behaviour change, WA3 tests updated). `@JsonValue` added to `ValueType`, `ElementKind`,
  `Severity`, `TermKind`, `JobStatus`, needed now that these enums are written into HTTP response
  bodies. Found and fixed a real defect: `ApiResponse.TEXT_TURTLE` carried no charset, so the
  Servlet response encoded the Turtle body as ISO-8859-1, corrupting the samples' smart quotes;
  the tell was `Model.isIsomorphicWith` returning false while `Model.difference` was empty both
  ways. Fixed by setting `"text/turtle; charset=utf-8"` in the one shared constant, and S4-12 now
  compares `CanonicalHash.sortedNTriplesLines` rather than `isIsomorphicWith` (Validation Pack
  "Implementer choices"). 14 new tests, 77 in the module, self-probe confirmed (the prescribed
  409 removal fails S4-02 exactly as the plan predicts, unlike WA3's probe). Docs delta:
  `solution-design-specification.md` \u00a74.7. Validation Pack at
  `docs/developer/validation/word-authoring-poc-wa4.md`. `check:java` (9 modules) and
  `check:authoring-contracts` still pass.
- 2026-10-01: WA4 committed as `c82bcc2`.
- 2026-10-01: WA5 done: `FusekiAuthoringStore` (Graph Store Protocol, retrying `ensureReady`),
  `Topology` and `RabbitMqAnalysisBus` (retrying connect, dead-lettering unparseable results),
  `AuthoringConfig`, `AuthoringServiceMain` (`--self-check` and the real entry point), `HealthProbe`.
  Testcontainers 2.0.2 added (test scope), `authoring-it` Maven profile with failsafe 3.5.0,
  `check:authoring-service-it` in `mise.toml`. 8 new unit tests (85 total) and 6 IT tests against
  real Fuseki and RabbitMQ containers, all green first run. The plan's self-probe (remove
  `ServicesResourceTransformer`, expect `--self-check` to fail) was found vacuous a second time:
  confirmed by running the broken jar directly, not just the test. A second test was added
  (`theShadedJarMergesEveryJenaSubsystemRegistration`) that opens the jar and checks the merged
  `JenaSubsystemLifecycle` services file directly; it fails correctly when the transformer is
  removed. Validation Pack at `docs/developer/validation/word-authoring-poc-wa5.md`. `check:java`
  (9 modules) and `check:authoring-contracts` still pass.
- 2026-10-01: WA5 committed as `187fea4`.
