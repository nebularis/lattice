<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Word authoring proof of concept - Status

**Unit ID:** `word-authoring-poc`
**Status:** built 2026-10-10. 🟡 Awaiting validation. WA-0 to WA-11 done (WA-11 is documentation and the manual Word
checklist, M1 to M14, which only the maintainer can run)
**Last updated:** 2026-10-02
**Plan:** [word-authoring-poc.md](../plans/word-authoring-poc.md)
**Sketch:** [word-authoring-poc.md](../sketches/word-authoring-poc.md)
**ADR:** [A-118](../../architecture/decisions/ADR-A118-word-authoring-proof-of-concept.md), Proposed
**Machine:** S. Branch `ux/auth-le`, local commits only

## Current position

The design and a one-shot plan of thirteen slices (WA-0 to WA-11, with WA-9a) are written. Decisions
WA-D1 to WA-D13 were recorded 2026-10-01: WA-D4 is Javalin, the rest follow the
recommendations. ADR-A118 stays Proposed. WA-0 to WA-9 are done: preflight, the WA-1 contracts, the
WA-2 service module that maps a snapshot to the Wording graph and validates it with SHACL, the WA-3
detection, template and conformance checks, the WA-4 HTTP API over Javalin with an in-memory store,
bus, registry and job tracking, WA-5's real Fuseki store, RabbitMQ bus, configuration and entry
point, WA-6's Logical English reading of the Wording graph (the Python worker's sentence-form
matcher, keyword fallback and proposal graph), WA-7's worker runtime (the Fuseki Graph Store
Protocol client, the RabbitMQ consumer/publisher adapter, and the `wording_analysis_main` entry
point that wires the WA-6 reading into a real job loop), WA-8's add-in domain (the OOXML
parser/writer, the tag codec, the hand-written contract types and Ajv validation, the HTTP client,
the `DocumentPort` seam, and the manifest), WA-9's task pane and harness (`App.tsx` and five
panels, `fakePort.ts`/`officePort.ts`, `main.tsx`/`harness.tsx`, the Playwright suite over a real
`msedge` channel), WA-9a's ribbon and right-click commands (`commands/ids.ts`/`handlers.ts`/
`register.ts`, the `uiBridge.ts` observable store, `domain/keys.ts`, the shared-runtime `V1_1`
manifest override with the ribbon group and context menu), and WA-10's compose stack
(`deployment/compose/authoring/` with its two Dockerfiles, compose file and Caddyfile,
`tools/authoring_stage.py`, the `authoring:*`/`check:authoring-tools`/`check:authoring-stack`
`mise` tasks, and `apps/word-authoring-addin/e2e-stack/stack.spec.ts` run for real against the live
stack). Browsing `https://localhost:3443` after `mise run authoring:up` is the demo: it redirects
to the harness, not the real Word task pane (that needs sideloading, which is WA-11). WA-11 itself
added "How the proof of concept fits together" and "Load the add-in in Word" to the add-in's
README (architecture, request-flow and data-construction Mermaid diagrams, plus sideloading for
Word on the web, desktop Word, and central deployment), re-ran every automated check
(`check:authoring`, `check:java`, `check:workers`, `check:ontology-versioning`,
`check:ontology-catalog`, `topology:links`), and recorded the manual Word checklist for the maintainer
to complete.

**Next action, for the maintainer:** complete the manual checklist (M1 to M14) in the
[WA-11 Validation Pack](../validation/WA-11.md), sign off, then decide whether to
push `ux/auth-le`. Separately, record decisions WA-D14 to WA-D20 (plan §3) if the follow-on
tranche below is to proceed.
**Next action:** none on WA-0 to WA11. WA12 onward wait on WA-D14 to WA-D20.

## Follow-on tranche drafted (2026-10-02)

At our request, the sketch and plan were extended with three further enhancements: richer,
more deeply nested sample data (deferred until the CCS workstream completes), a web authoring app
editing the same documents without Word, and parity brought back to the Word add-in. See
[sketch §8](../sketches/word-authoring-poc.md#8-follow-on-enhancements-proposed-2026-10-02) for the
design and the plan's §3/§4/§5 for decisions WA-D14 to WA-D20 and slices WA12 to WA20. No
implementation is authorised yet. Token estimates: about 3.15M for WA12 to WA19, plus WA20
(provisional, re-estimated when the CCS workstream completes and it is scheduled).

## Open question raised by WA-3

WA-3's prescribed self-probe ("change the overlap sort to start-first") does not fail any test, and
cannot, because the seven detection rules can overlap only by containment. A probe against the same
invariant was run instead and does fail. The detail is in the
[WA-3 Validation Pack](../validation/WA-3.md) under Self-probe. Nothing is blocked,
but later slices that prescribe a probe should be read with the same scepticism.

## Open question raised by WA-5

WA-5's prescribed self-probe (remove `ServicesResourceTransformer`, expect `--self-check` to fail)
also does not fail: the self-check's code path does not happen to need the two Jena subsystem
registrations (`InitJenaCore`, `InitShacl`) that a plain shade drops. Confirmed directly by running
the broken jar by hand, not only through the test. A second test was added that opens the jar and
asserts its merged `JenaSubsystemLifecycle` services file, which does fail correctly. Detail in the
[WA-5 Validation Pack](../validation/WA-5.md) under Self-probe. Two of two slices
with a prescribed probe have now needed a replacement; read every later one with the same scepticism
before trusting it.

## Open question raised by WA-6

WA-6's prescribed self-probe (in `best_match`, prefer the earliest form instead of the most fixed
words) also does not fail: for every ambiguous pair the three samples' 30 elements produce, the
more specific form already sits earlier in the profile's own table, independently of fixed-word
count, so neither S6-04 nor S6-08 can tell the two tie-break rules apart. A dedicated test with two
synthetic forms, deliberately ordered the other way round, was added and does fail correctly.
Detail in the [WA-6 Validation Pack](../validation/WA-6.md) under Self-probe.
Three of three slices with a prescribed probe have now needed a replacement.

## Note for WA-9 (done in WA-9)

WA-8 implements `writeTemplate` (plan WA-8 OOXML rules) but it has no dedicated test in WA-8, since
the "Apply template" flow it serves is a WA-9 UI feature with no committed golden yet. WA-9's S9-03
exercises it directly (Apply template on the licence). WA-9 also found and fixed a real defect in
`writeTemplate`'s own placeholder element (see "Open question raised by WA-9" below).

## Open question raised by WA-9

Unlike WA-3, WA-5 and WA-6, WA-9's prescribed self-probe ("render span text with
`dangerouslySetInnerHTML`, S9-13 fails") bites exactly as written: run against the real Playwright
suite, S9-13 fails (the malicious string stops appearing as text, since the browser parses it into
a real `<img>` instead), and passes again once reverted. No replacement test was needed, the third
such slice after WA-7 and WA8. Detail in the
[WA-9 Validation Pack](../validation/WA-9.md) under Self-probe.

Separately, WA-9 found and fixed two real defects discovered only by actually running the Playwright
suite in a real browser, not by static review:

1. `HttpApiClient`'s default `fetchImpl` was a bare reference to the global `fetch`, which threw
   "Illegal invocation" once extracted and called as `this.fetchImpl(...)` — the native `fetch`
   needs `window` as its receiver. Fixed by wrapping it in an arrow function.
2. `ooxml.ts`'s `writeTemplate` wrote a literally empty placeholder paragraph for each section's
   first element. WA-8's own parser drops a zero-parts element with a warning (confirmed by S8-04),
   so every section ended up with no element at all on round trip, silently contradicting WA-9's
   own "each element empty" expectation. Fixed by writing a single space instead, which is
   schema-valid (`LiteralPart` requires at least one character) and survives the round trip as one
   element with one (visually blank) part.

## Open question raised by WA-9a

WA-9a's prescribed self-probe ("move `event.completed()` out of the `finally` block into the
success path, S9a-03's throwing case fails") also bites exactly as written: run against
`handlers.test.ts` alone, the throwing-port test fails (`completedCount()` is `0`, not `1`), and
passes again once reverted. No replacement test needed, the fourth such slice after WA-7, WA-8 and
WA9. Detail in the [WA-9a Validation Pack](../validation/WA-9a.md) under
Self-probe.

Separately, WA-9a found and fixed a real defect only visible once the `analyse` ribbon command was
actually exercised end to end (S9a-08): `App.tsx`'s bridge subscription effect ran once (`[bridge]`
never changes) and called `handleAnalyse()` directly, closing over the *initial* (`null`)
`metadata` forever, so Analyse silently did nothing when triggered from the bridge. Fixed with the
standard ref pattern (`handleAnalyseRef`, kept fresh by an unconditional `useEffect`). WA-9a also
closed a gap WA-9 itself had flagged: `FakeWordPort.wrapSelectionAsElement` was a stub that always
returned `outside-section`, it now has a real implementation (`selectUnmarked`), since WA-9a's
`markClause`/`markDefinition` commands are the first thing in this unit to actually exercise it.

## Open question raised by WA-10

WA-10's prescribed self-probe (stop `authoring-worker`, confirm S10-06 fails, restart it, confirm
it passes again) bites exactly as written, confirmed by actually stopping and restarting the
container, not only by reasoning about it. The fifth slice running (after WA-7, WA-8, WA-9, WA-9a)
with no replacement test needed. Detail in the
[WA-10 Validation Pack](../validation/WA-10.md) under Self-probe.

Separately, WA-10 found and fixed two real defects that only running the real compose stack (not
mocked Playwright tests) could surface, both pre-dating this slice:

1. `HttpApiClient` was constructed with `"/api"` as its base URL in both `main.tsx` and
   `harness.tsx`, but every one of its own methods already includes `/api/...` in the path it
   requests. Every real request went to a doubled `/api/api/...` path, which Javalin correctly
   404s. Every earlier Playwright test used a `page.route("**/api/health", ...)` style wildcard
   glob, which matches a URL *containing* that suffix, including a doubled one, so none of them
   caught it. Fixed by constructing both clients with `""`.
2. The add-in's bundled Ajv compiles validators via `new Function` at runtime (the standard way
   Ajv achieves its speed), which the proxy's initial `script-src` (without `'unsafe-eval'`)
   silently blocked, throwing a `pageerror` that stopped the whole React app from rendering past
   catalogue load. No earlier test caught this either, since none of them ran the add-in behind a
   real CSP-enforcing proxy. Fixed by adding `'unsafe-eval'` to the proxy's `script-src` directive.

Neither bug is specific to the compose stack: both would affect the add-in running for real inside
Word too, once sideloaded (WA-11). Finding them here, rather than there, is the reason this slice's
tests run against a real stack (L5/L6) instead of stopping at mocked L1 tests.

## Note for WA-3 (done in WA-6)

WA-2's provisional vocabulary (`platform/authoring-service/src/main/resources/vocab/wording-provisional.ttl`)
declared only the `wrd:`/`wap:` terms WA-2 itself minted. WA-6 extended it with the `ins:` relation
classes and the `wap:` proposal-graph terms (sketch §4.4: `wap:proposalBasis`, `wap:activityText`,
etc.), adding `platform/authoring-service/**` to its own path list as this note asked.

## Note for WA-7 (done in WA-7)

WA-4's `GET .../graph/proposal` route reads `store.getGraph(minter.proposalGraph(...))`, but nothing
yet writes to that IRI: WA-6 only builds the `rdflib.Graph` in memory. WA-7's `fuseki_gsp.py` and
`wording_analysis_worker.py` are what `put_graph(proposalGraphIri, graph)` the request event
already carries. WA-4's tests cover only `wording` and an invalid kind (plan S4-12's own scope).
Exercising `proposal` end to end against the real Java HTTP route (replacing WA-5's S5-05 fixture
stand-in with the real worker's `consume()`) is left to WA-10's compose-stack suite, where a real
Fuseki and RabbitMQ are already wired up.

## Note for WA-7's self-probe

Unlike WA-3, WA-5 and WA-6, WA-7's prescribed self-probe ("make the adapter requeue on `ValueError`,
S7-03 fails") bites exactly as written: both S7-03 tests fail when tried, and pass again once
reverted. No replacement test was needed. Detail in the
[WA-7 Validation Pack](../validation/WA-7.md) under Self-probe.

## Preflight (WA-0, 2026-10-01)

| # | Check | Result | Detail |
|---|---|---|---|
| P1 | clean tree, branch, identity | pass | branch `ux/auth-le`, identity set. The only changes were this unit's planning documents, committed with WA-0 |
| P2 | `mise run check:java` | pass | BUILD SUCCESS, 8 modules. A warning that the `oss.sonatype.org` snapshots repository fails TLS (PKIX) did not affect the build |
| P3 | new Maven artefacts | pass | jena-arq, jena-shacl, jena-rdfconnection 5.1.0, jackson-databind 2.18.2, json-schema-validator 1.5.6, amqp-client 5.22.0, slf4j-simple 2.0.16, javalin 6.7.0, testcontainers 2.0.2, shade 3.6.0, failsafe 3.5.0 |
| P4 | Python packages through the mirror | pass | host: rdflib 7.6.0, pika 1.4.4, jsonschema 4.26.0 with attrs, referencing, jsonschema-specifications and rpds-py (cp314 win_amd64). Linux pure wheels: rdflib, pika, pyparsing 3.3.3 |
| P5 | Node, Yarn, npm registry | pass on re-run | first run failed (`NODE_EXTRA_CA_CERTS` unset). We set it at user level to the Zscaler root CA under `C:\Program Files (x86)\MSIRepair\`. Re-run: Yarn 4.6.0 runs, `yarn npm info vitest` answers. A shell opened before the change must load it from the user environment |
| P6 | Docker | pass on re-run | first run failed (engine not running). Re-run: Linux engine 29.8.0, API 1.56. All five images pulled. The Fuseki image has both `wget` and `curl`, so WA-10's health check stands as written |
| P7 | Edge for Playwright | pass | `msedge.exe` present |

## Slice board

| Slice | Deliverable | State | Blocked on | Commit |
|---|---|---|---|---|
| WA-0 | Preflight | built 2026-10-02 |  | `c82d019` |
| WA-1 | Contracts, templates and samples | built 2026-10-02 |  | `3db3911` |
| WA-2 | Service model, mapping and shapes | built 2026-10-02 |  | `52eae70` |
| WA-3 | Detection, templates and conformance | built 2026-10-02 |  | `8c4aa65` |
| WA-4 | API and HTTP adapter | built 2026-10-02 |  | `c82bcc2` |
| WA-5 | Fuseki, RabbitMQ and the runnable service | built 2026-10-02 |  | `187fea4` |
| WA-6 | Logical English reading | built 2026-10-02 |  | `0128ca2` |
| WA-7 | Worker runtime | built 2026-10-02 |  | `ab8e1a1` |
| WA-8 | Add-in domain | built 2026-10-02 | WA-1 | `451fc93` |
| WA-9 | Add-in task pane and harness | built 2026-10-02 | WA-8 | `e567990` |
| WA-9a | Ribbon and right-click commands | built 2026-10-02 | WA-9, WA-D13 | `d16c4e0` |
| WA-10 | Compose stack | built 2026-10-02 | WA-5, WA-7, WA-9a | `9a34ced` |
| WA-11 | Documentation and close-out | built 2026-10-10, pending the maintainer's sign-off | WA-10 | `678c9b9` |

## Token use

| Slice | Estimate | Actual |
|---|---|---|
| WA-0 to WA-11 | about 4.35M in total (plan §4) | |
| WA-0 | 60k | about 60k |
| WA-1 | 300k | about 220k |
| WA-2 | 450k | about 480k |
| WA-3 | 300k | about 230k |
| WA-4 | 450k | about 520k |
| WA-5 | 350k | about 400k |
| WA-6 | 450k | about 480k |
| WA-7 | 200k | about 230k |
| WA-8 | 450k | about 420k |
| WA-9 | 550k | about 600k |
| WA-9a | 250k | about 270k |
| WA-10 | 400k | about 550k |
| WA-11 | 150k | about 450k |

## History

- 2026-10-02: we reported that the POC runs successfully. At our request, a deferred
  published-Wording adoption assessment was added to sketch section 4.1.1 and the plan's
  deferred follow-up section. No runtime or ontology changes, no tranche scheduled, and no
  manual-checklist sign-off inferred. The maintainer will decide when to pick up the work.
- 2026-10-01: sketch, plan, status record and ADR-A118 (Proposed) written on `ux/auth-le`. No
  ontology change, so no release tag is due.
- 2026-10-01: slice WA-9a added at our request: ribbon group and right-click commands for
  marking text, decision WA-D13 (shared runtime), checklist steps M11 to M14, risk R8.
- 2026-10-01: decisions WA-D1 to WA-D13 recorded. WA-D4 is Javalin (pinned 6.7.0, the
  plan's WA-4 adapter rewritten for it), the rest as recommended. ADR-A118 decision 6 names Javalin.
- 2026-10-01: WA-0 preflight run in autonomous mode. P1 to P4 and P7 pass, P5 and P6 fail (above).
  Committed with the unit's planning documents as `[wap] WA-0: preflight` (`a0758ae`).
- 2026-10-01: P5 and P6 re-run after we set `NODE_EXTRA_CA_CERTS` and started Docker
  Desktop. Both pass. All preflight checks now pass.
- 2026-10-01: WA-1 done (`3db3911`, hash recorded `07acc66`).
- 2026-10-01: WA-2 done: `platform/authoring-service` (new Maven module: `json`, `model`, `rdf`,
  `validation`, `app` packages), the provisional vocabulary and 11 SHACL shapes, 48 tests, fixed
  fixtures regenerated and committed. Found and fixed a real defect: Jena reports a nested
  `sh:property [...]` blank node, not the enclosing named shape, as `sh:sourceShape`, so seven
  shapes were flattened to top-level named property shapes (Validation Pack "Implementer
  choices"). Self-probe confirmed (WS10's `OPTIONAL` removal breaks the zero case). `check:java`
  (all 8 modules) and `check:authoring-contracts` (WA-1) still pass.
- 2026-10-01: WA-1 done: `contracts/authoring` (12 schemas, templates, samples, fixtures,
  `amqp-topology.json`), `contracts/events` (2 event schemas), `contracts/openapi`, worker test
  `test_authoring_contracts.py` (35 tests, all pass), `check:authoring-contracts` wired into
  `mise.toml`. Validation Pack at `docs/developer/validation/WA-1.md`. Self-probe
  confirmed (AC-02 catches a missing `additionalProperties: false`). Full `check:workers` (73
  tests) still passes.
- 2026-10-01: the WA-2 Java sources reviewed for simplicity at our request, in "ponytail"
  mode (`.github/prompts/ponytail.md`). Seven files, 57 insertions and 91 deletions, no behaviour
  change: `WordingMapper` holds one `IriMinter`, `CanonicalHash.canonicalText` is the single place
  the fixture text is formed, `SnapshotReader` uses one list helper, `IriMinter` one validator.
  `check:authoring-service`, `check:java` and `check:authoring-contracts` all green, and
  `build:authoring-fixtures` reproduced the three `.nt` goldens byte for byte. Committed as
  `278f23e`.
- 2026-10-01: WA-3 done (`8c4aa65`): `detection` (`ConstructDetector`, `Detection`, `Suggestion`)
  and `template` (`TemplateCatalog`, `SampleCatalog`, `AuthoringTemplate`, `TemplateSection`,
  `TemplateFindings`, `ConformanceChecker`, `Finding`, the two summaries) packages, plus
  `ContractSchemas.readValidated` shared by the catalogs. 15 new tests, 63 in the module, all pass
  first run. Validation Pack at `docs/developer/validation/WA-3.md`. The plan's
  self-probe was found to be vacuous (see above) and a probe that bites was run in its place.
  `check:java` (9 modules) and `check:authoring-contracts` still pass.
- 2026-10-01: WA-4 done: `store`, `messaging`, `jobs`, `api` and `http` packages, Javalin 6.7.0
  added to the module, ten routes behind `AuthoringApi`, `AuthoringHttpServer`, `SampleSeeder`.
  `TemplateFindings` and `ConformanceChecker` changed from WA-3's static-utility shape to
  instantiable classes, since plan WA-4 holds them as `AuthoringApi` constructor collaborators
  (no behaviour change, WA-3 tests updated). `@JsonValue` added to `ValueType`, `ElementKind`,
  `Severity`, `TermKind`, `JobStatus`, needed now that these enums are written into HTTP response
  bodies. Found and fixed a real defect: `ApiResponse.TEXT_TURTLE` carried no charset, so the
  Servlet response encoded the Turtle body as ISO-8859-1, corrupting the samples' smart quotes;
  the tell was `Model.isIsomorphicWith` returning false while `Model.difference` was empty both
  ways. Fixed by setting `"text/turtle; charset=utf-8"` in the one shared constant, and S4-12 now
  compares `CanonicalHash.sortedNTriplesLines` rather than `isIsomorphicWith` (Validation Pack
  "Implementer choices"). 14 new tests, 77 in the module, self-probe confirmed (the prescribed
  409 removal fails S4-02 exactly as the plan predicts, unlike WA-3's probe). Docs delta:
  `solution-design-specification.md` \u00a74.7. Validation Pack at
  `docs/developer/validation/WA-4.md`. `check:java` (9 modules) and
  `check:authoring-contracts` still pass.
- 2026-10-01: WA-4 committed as `c82bcc2`.
- 2026-10-01: WA-5 done: `FusekiAuthoringStore` (Graph Store Protocol, retrying `ensureReady`),
  `Topology` and `RabbitMqAnalysisBus` (retrying connect, dead-lettering unparseable results),
  `AuthoringConfig`, `AuthoringServiceMain` (`--self-check` and the real entry point), `HealthProbe`.
  Testcontainers 2.0.2 added (test scope), `authoring-it` Maven profile with failsafe 3.5.0,
  `check:authoring-service-it` in `mise.toml`. 8 new unit tests (85 total) and 6 IT tests against
  real Fuseki and RabbitMQ containers, all green first run. The plan's self-probe (remove
  `ServicesResourceTransformer`, expect `--self-check` to fail) was found vacuous a second time:
  confirmed by running the broken jar directly, not just the test. A second test was added
  (`theShadedJarMergesEveryJenaSubsystemRegistration`) that opens the jar and checks the merged
  `JenaSubsystemLifecycle` services file directly; it fails correctly when the transformer is
  removed. Validation Pack at `docs/developer/validation/WA-5.md`. `check:java`
  (9 modules) and `check:authoring-contracts` still pass.
- 2026-10-01: WA-5 committed as `187fea4`.
- 2026-10-01: WA-6 done: `workers/src/lattice_workers/wording_le` (`namespaces`, `offsets`, `model`,
  `tokens`, `forms` plus the packaged `forms/sentence-forms.json`, `matcher`, `classify`,
  `analyse`, `render`, `proposal`), `check:authoring-worker` in `mise.toml`, `workers/README.md`
  created. 67 tests (33 new, plus WA-1's 34-test `test_authoring_contracts.py`), all pass first
  run against the real facility, software-licence and property-policy fixtures with no reading
  corrected: every element's class, basis and form matched plan WA-6's expected facility readings
  exactly, and all twelve forms were exercised across the three samples unprompted. Extended
  `platform/authoring-service/src/main/resources/vocab/wording-provisional.ttl` with the `ins:`
  relation classes and `wap:` proposal-graph terms, and `ins:`/`prov:`/`dcterms:` prefixes, per the
  WA-3 note above (path list amended to include `platform/authoring-service/**`). The plan's
  self-probe was found vacuous a third time (see "Open question raised by WA-6" above), a dedicated
  tie-break test using two synthetic forms was added and does fail correctly. Validation Pack at
  `docs/developer/validation/WA-6.md`. `check:java` (9 modules),
  `check:authoring-service` (85) and `check:authoring-contracts` still pass.
- 2026-10-01: WA-6 committed as `0128ca2`.
- 2026-10-01: WA-7 done: `workers/src/lattice_workers/fuseki_gsp.py` (`FusekiGraphStore`, Graph
  Store Protocol over `urllib.request`), `wording_analysis_worker.py` (`WordingAnalysisConsumer`,
  `RabbitMqResultPublisher`, `RabbitMqWordingAnalysisWorker`, `declare_topology`, the packaged
  `amqp-topology.json`), `wording_analysis_main.py` (`read_config`, retrying connect, the
  `python -m lattice_workers.wording_analysis_main` entry point). 16 new tests, `check:authoring-
  worker` now 83 (32 WA-6, 16 new, 35 contracts). WA-7 is the first slice whose prescribed self-probe
  bites exactly as written (see "Note for WA-7's self-probe" above): no replacement test needed, a
  first in this unit after WA-3, WA-5 and WA-6 all needing one. Validation Pack at
  `docs/developer/validation/WA-7.md`. `check:java` (9 modules),
  `check:authoring-service` (85) and `check:authoring-contracts` still pass.
- 2026-10-01: WA-7 committed as `ab8e1a1`.
- 2026-10-01: WA-8 done: new Yarn workspace `apps/word-authoring-addin` (`package.json`,
  `tsconfig.json`, `vite.config.ts`, `vitest.config.ts`, `manifest/manifest.xml`, four generated
  icon PNGs, `public/help.html`), `check:authoring-addin` in `mise.toml`, `yarn.lock` updated.
  Domain modules: `domain/types.ts` (hand-written, all 14 schemas), `domain/schemas.ts` (one Ajv
  2020-12 instance), `domain/tags.ts` (the content-control tag codec), `domain/offsets.ts`,
  `domain/xml.ts` (shared DOM helpers), `domain/ooxml.ts` (`parseBody`/`writeSections`/
  `writeTemplate`/`writePackage`), `domain/snapshot.ts` (`buildSnapshot`), `domain/metadata.ts`
  (the custom XML part codec), `domain/mermaid.ts` (`toMermaid`), `domain/poll.ts` (`pollJob`),
  `api/client.ts` (`HttpApiClient`, `ApiError`), `word/port.ts` (the `DocumentPort` interface).
  38 tests, all pass first run, including a full `writeSections` → `writePackage` → `parseBody` →
  `buildSnapshot` round trip against all three WA-1 samples (with headings looked up from their
  templates) reproducing each sample exactly byte-for-structure. Self-probe (make the parser read
  `w:delText`) bites exactly as written, the second slice running (after WA-7) with no replacement
  test needed. Validation Pack at `docs/developer/validation/WA-8.md`.
  `check:java`, `check:authoring-service`, `check:authoring-worker` and `check:authoring-contracts`
  were not re-run (WA-8 touches none of their paths), `yarn check` across all three workspaces
  (`mork-review-workbench`, `surface-contract-studio`, `word-authoring-addin`) passes.
- 2026-10-01: WA-8 committed as `451fc93`.
- 2026-10-02: WA-9 done: `src/app/App.tsx` and five panels (`DocumentPanel`, `MarkupPanel`,
  `AnalysePanel`, `LogicalEnglishPanel`, `GraphPanel`), `app.css`, `src/word/fakePort.ts`
  (an in-memory `DocumentPort`) and `officePort.ts` (a real one, over the actual `Word`/
  `OfficeExtension` ambient types `@types/office-js` declares), `src/main.tsx`/`harness.tsx`,
  `taskpane.html`/`harness.html`, `playwright.config.ts` (real `msedge` channel), `e2e/support.ts`
  and `e2e/taskpane.spec.ts` (mocking `/api/**` from the real WA-1 samples/templates and the WA-6
  goldens, validating request bodies with the WA-8 Ajv module), `test:authoring-addin` in
  `mise.toml`. `ux-design.md` section 4 added. 7 new Vitest tests (`fakePort.test.ts` 5,
  `main.test.ts` 2, 45 total with WA-8's 38), 11 new Playwright tests (S9-02 to S9-11, S9-13), all
  pass. Found and fixed two real defects only visible when actually running the suite in a real
  browser: `HttpApiClient`'s default `fetchImpl` threw "Illegal invocation" once detached from
  `window`; `writeTemplate`'s placeholder element round-tripped to zero parts and was silently
  dropped by WA-8's own "empty literals are dropped" rule. Self-probe (render span text with
  `dangerouslySetInnerHTML`) bites exactly as written, the third slice running (after WA-7, WA-8)
  with no replacement test needed. Validation Pack at
  `docs/developer/validation/WA-9.md`. `check:java`, `check:authoring-service`,
  `check:authoring-worker` and `check:authoring-contracts` were not re-run (WA-9 touches none of
  their paths).
- 2026-10-02: WA-9 committed as `e567990`.
- 2026-10-02: WA-9a done: `src/commands/ids.ts`, `handlers.ts` (`createHandlers`, no Office global
  touched), `register.ts` (the only module that calls `Office.actions.associate`),
  `src/app/uiBridge.ts` (the observable store), `src/domain/keys.ts` (`suggestKey`/
  `guessValueType`, ported from WA-3's Java `ConstructDetector` exactly), the nested
  `VersionOverridesV1_1` manifest override (`SharedRuntime` 1.1, one long-lived runtime, eight
  ribbon controls in `LatticeGroup`, six context-menu items, four new icon colour sets).
  `main.tsx`/`harness.tsx` updated to register commands and expose `window.__harness.command(id)`.
  `ux-design.md` §4.6 and the add-in README's command table added. 24 new Vitest tests
  (`keys.test.ts` 7, `register.test.ts` 1, `handlers.test.ts` 9, `manifest.test.ts` 7 new; 69
  total), 2 new Playwright tests (S9a-07, S9a-08; 13 total), all pass. Found and fixed two real
  defects: `App.tsx`'s bridge subscription closed over a stale (`null`) `metadata` forever (fixed
  with a ref kept fresh every render), `FakeWordPort.wrapSelectionAsElement` was a stub WA-9 left
  always failing, now genuinely implemented (`selectUnmarked`) since WA-9a's `markClause`/
  `markDefinition` are the first callers that need it to work. Self-probe (move `event.completed()`
  out of `finally`) bites exactly as written, the fourth slice running (after WA-7, WA-8, WA-9) with
  no replacement test needed. Validation Pack at
  `docs/developer/validation/WA-9a.md`. `check:java`, `check:authoring-service`,
  `check:authoring-worker` and `check:authoring-contracts` were not re-run (WA-9a touches none of
  their paths).
- 2026-10-02: WA-9a committed as `d16c4e0`.
- 2026-10-02: WA-10 done: `deployment/compose/authoring/` (`docker-compose.yml`, `service.Dockerfile`,
  `worker.Dockerfile`, `Caddyfile`, `README.md`), `tools/authoring_stage.py` and
  `test_authoring_stage.py` (4 tests), the `build:authoring`/`authoring:up`/`authoring:down`/
  `authoring:reset`/`authoring:ca`/`check:authoring-tools`/`check:authoring-stack` `mise` tasks
  (`check:authoring-tools` added to the root `check` task), `apps/word-authoring-addin/
  playwright.stack.config.ts` and `e2e-stack/stack.spec.ts` (7 tests, S10-03 to S10-09). Root
  `README.md` and the add-in's own `README.md` updated; new
  `deployment/compose/authoring/README.md`. The stack was actually built and brought up
  (`mise run authoring:up`), not just authored: all five containers healthy, every seeded sample
  analysed, a fresh snapshot submitted and analysed, the harness exercised in a real browser
  through the real proxy with no mocking, and `authoring-service` restarted mid-suite without
  losing or duplicating data. Found and fixed two real, pre-existing defects that only running the
  real stack (not mocked Playwright tests) could surface: `HttpApiClient` was constructed with a
  doubled `/api` base URL in both entry points, silently masked everywhere else by wildcard route
  mocks; the add-in's bundled Ajv needs `'unsafe-eval'` in `script-src`, which the proxy's CSP
  initially lacked, breaking the entire React app before the fix. Self-probe (stop
  `authoring-worker`, confirm S10-06 fails; restart it, confirm it passes again) bites exactly as
  written, the fifth slice running (after WA-7, WA-8, WA-9, WA-9a) with no replacement test needed.
  Validation Pack at `docs/developer/validation/WA-10.md`. `check:authoring-addin`
  (69 Vitest) and the mocked `e2e/` Playwright suite (13 tests) were re-run and still pass,
  confirming the `HttpApiClient` fix caused no regression.
- 2026-10-02: WA-10 committed as `9a34ced`.
- 2026-10-02: the stack taken down (`docker compose down`) at our request, then WA-11 done:
  the add-in's `README.md` gained "How the proof of concept fits together" (an architecture
  diagram, a request-flow sequence diagram, and a data-construction diagram, all Mermaid) and
  "Load the add-in in Word" (Word on the web, desktop Word's registry sideload, and central
  deployment, each with how to remove it). The Mermaid diagrams go beyond the plan's own WA-11
  scope, at our explicit request ("awash with mermaid diagrams... how everything is glued
  together... how the data has been constructed"). One-line cross-references added to
  `platform/authoring-service/README.md` and `workers/README.md`, pointing back to the add-in's
  diagrams rather than duplicating them. `mise run check:authoring` (contracts 35, tools 4, worker
  83, addin 69 Vitest + 13 Playwright, service BUILD SUCCESS), `check:java` (9 modules),
  `check:workers` (121), `check:ontology-versioning` (35 documents, none unbumped) and
  `check:ontology-catalog` (84) all pass. `topology:links` fails with 62 pre-existing broken links
  in unrelated sketches, status files and one ADR, none touched by this unit, recorded rather than
  silently dropped. Validation Pack at `docs/developer/validation/WA-11.md`,
  with the manual Word checklist (M1 to M14) left for the maintainer to complete and sign off.
- 2026-10-02: WA-11 committed as `678c9b9`.
