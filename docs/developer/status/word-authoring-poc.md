<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Word authoring proof of concept - Status

**Unit ID:** `word-authoring-poc`
**Status:** 🚧 In progress. WA0 to WA7 done. WA8 is next
**Last updated:** 2026-10-01
**Plan:** [word-authoring-poc.md](../plans/word-authoring-poc.md)
**Sketch:** [word-authoring-poc.md](../sketches/word-authoring-poc.md)
**ADR:** [A-114](../../architecture/decisions/ADR-A114-word-authoring-proof-of-concept.md), Proposed
**Machine:** S. Branch `ux/auth-le`, local commits only

## Current position

The design and a one-shot plan of thirteen slices (WA0 to WA11, with WA9a) are written. Decisions
WA-D1 to WA-D13 were recorded by the human on 2026-10-01: WA-D4 is Javalin, the rest follow the
recommendations. ADR-A114 stays Proposed. WA0 to WA6 are done: preflight, the WA1 contracts, the
WA2 service module that maps a snapshot to the Wording graph and validates it with SHACL, the WA3
detection, template and conformance checks, the WA4 HTTP API over Javalin with an in-memory store,
bus, registry and job tracking, WA5's real Fuseki store, RabbitMQ bus, configuration and entry
point, WA6's Logical English reading of the Wording graph (the Python worker's sentence-form
matcher, keyword fallback and proposal graph), and WA7's worker runtime (the Fuseki Graph Store
Protocol client, the RabbitMQ consumer/publisher adapter, and the `wording_analysis_main` entry
point that wires the WA6 reading into a real job loop).

**Next action, for the human:** ask for WA8.
**Next action, for the agent:** WA8 (add-in domain: TypeScript types, schemas, tag codec, OOXML parser/writer), when asked.

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

## Open question raised by WA6

WA6's prescribed self-probe (in `best_match`, prefer the earliest form instead of the most fixed
words) also does not fail: for every ambiguous pair the three samples' 30 elements produce, the
more specific form already sits earlier in the profile's own table, independently of fixed-word
count, so neither S6-04 nor S6-08 can tell the two tie-break rules apart. A dedicated test with two
synthetic forms, deliberately ordered the other way round, was added and does fail correctly.
Detail in the [WA6 Validation Pack](../validation/word-authoring-poc-wa6.md) under Self-probe.
Three of three slices with a prescribed probe have now needed a replacement.

## Note for WA3 (done in WA6)

WA2's provisional vocabulary (`platform/authoring-service/src/main/resources/vocab/wording-provisional.ttl`)
declared only the `wrd:`/`wap:` terms WA2 itself minted. WA6 extended it with the `ins:` relation
classes and the `wap:` proposal-graph terms (sketch §4.4: `wap:proposalBasis`, `wap:activityText`,
etc.), adding `platform/authoring-service/**` to its own path list as this note asked.

## Note for WA7 (done in WA7)

WA4's `GET .../graph/proposal` route reads `store.getGraph(minter.proposalGraph(...))`, but nothing
yet writes to that IRI: WA6 only builds the `rdflib.Graph` in memory. WA7's `fuseki_gsp.py` and
`wording_analysis_worker.py` are what `put_graph(proposalGraphIri, graph)` the request event
already carries. WA4's tests cover only `wording` and an invalid kind (plan S4-12's own scope).
Exercising `proposal` end to end against the real Java HTTP route (replacing WA5's S5-05 fixture
stand-in with the real worker's `consume()`) is left to WA10's compose-stack suite, where a real
Fuseki and RabbitMQ are already wired up.

## Note for WA7's self-probe

Unlike WA3, WA5 and WA6, WA7's prescribed self-probe ("make the adapter requeue on `ValueError`,
S7-03 fails") bites exactly as written: both S7-03 tests fail when tried, and pass again once
reverted. No replacement test was needed. Detail in the
[WA7 Validation Pack](../validation/word-authoring-poc-wa7.md) under Self-probe.

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
| WA6 | Logical English reading | done | `0128ca2` | |
| WA7 | Worker runtime | done | | |
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
| WA6 | 450k | about 480k |
| WA7 | 200k | about 230k |

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
- 2026-10-01: WA6 done: `workers/src/lattice_workers/wording_le` (`namespaces`, `offsets`, `model`,
  `tokens`, `forms` plus the packaged `forms/sentence-forms.json`, `matcher`, `classify`,
  `analyse`, `render`, `proposal`), `check:authoring-worker` in `mise.toml`, `workers/README.md`
  created. 67 tests (33 new, plus WA1's 34-test `test_authoring_contracts.py`), all pass first
  run against the real facility, software-licence and property-policy fixtures with no reading
  corrected: every element's class, basis and form matched plan WA6's expected facility readings
  exactly, and all twelve forms were exercised across the three samples unprompted. Extended
  `platform/authoring-service/src/main/resources/vocab/wording-provisional.ttl` with the `ins:`
  relation classes and `wap:` proposal-graph terms, and `ins:`/`prov:`/`dcterms:` prefixes, per the
  WA3 note above (path list amended to include `platform/authoring-service/**`). The plan's
  self-probe was found vacuous a third time (see "Open question raised by WA6" above); a dedicated
  tie-break test using two synthetic forms was added and does fail correctly. Validation Pack at
  `docs/developer/validation/word-authoring-poc-wa6.md`. `check:java` (9 modules),
  `check:authoring-service` (85) and `check:authoring-contracts` still pass.
- 2026-10-01: WA6 committed as `0128ca2`.
- 2026-10-01: WA7 done: `workers/src/lattice_workers/fuseki_gsp.py` (`FusekiGraphStore`, Graph
  Store Protocol over `urllib.request`), `wording_analysis_worker.py` (`WordingAnalysisConsumer`,
  `RabbitMqResultPublisher`, `RabbitMqWordingAnalysisWorker`, `declare_topology`, the packaged
  `amqp-topology.json`), `wording_analysis_main.py` (`read_config`, retrying connect, the
  `python -m lattice_workers.wording_analysis_main` entry point). 16 new tests, `check:authoring-
  worker` now 83 (32 WA6, 16 new, 35 contracts). WA7 is the first slice whose prescribed self-probe
  bites exactly as written (see "Note for WA7's self-probe" above): no replacement test needed, a
  first in this unit after WA3, WA5 and WA6 all needing one. Validation Pack at
  `docs/developer/validation/word-authoring-poc-wa7.md`. `check:java` (9 modules),
  `check:authoring-service` (85) and `check:authoring-contracts` still pass.
