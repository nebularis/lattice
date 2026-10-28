<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: config-studio CS0 to CS6

**Plan:** [config-studio](../plans/config-studio.md)
**Status record:** [config-studio](../status/config-studio.md)

One pack for the unit's seven slices, each a section, since they were built and are reviewed together (a deviation from one pack per slice, recorded in the status record).

## Invariant

An author's configuration reaches the compilers exactly as the forms show it, and every finding the repository's own checks would make reaches the author on the field that caused it. Three things hold that. First, **RDF end to end**: the browser edits a graph, sends Turtle, and reads findings as `sh:ValidationResult`s, so no translation layer can lose or invent a value (ADR-A136 decision 4). Second, **one engine per judgement**: validation and compilation run in the worker with pySHACL and the repository's compilers, never a second implementation (decision 3). Third, **no lost update**: a save carries the revision it read, and a stale one is refused with `412` and shown as a diff, never applied (decision 5, PAT-26).

## One command

```bash
mise run check:config-studio
```

It stages the assets, then runs the stage and worker tests, the service's Maven build and tests, and the browser code's type check and unit tests. A pass is exit status 0. The browser tests run separately, since they start a dev server and need Playwright's Chromium:

```bash
mise run test:config-studio
```

## CS0: contracts and staging

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| CS0-01 | the repository / staged / `vocabulary.ttl` holds the `dal:` and `srf:` terms | L1 | + | pass |
| CS0-02 | the samples manifest / staged / three samples listed without their parts, each merged, the lending baseline and profile together | L1 | + | pass |
| CS0-03 | a sample naming an absent file / staged / refused, naming the file | L1 | − | pass |

`python -m pytest tools/test_config_studio_stage.py`

## CS1: the worker

`workers/tests/test_config_studio_worker.py`, 18 cases.

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| CS1-01 | `baseline-single-class.ttl` / validate persistence / Succeeded, conforms | L4 | + | pass |
| CS1-02 | `invalid-lagwindow-missing.ttl` / validate / conforms false, each violation with a focus node | L4 | − | pass |
| CS1-03 | a profile declaring personal data with no erasure on a `dal:DataAccessProfile` / validate / conforms false, `CrossAxisViolation` focused on the class, though SHACL passes (CS-D9) | L4 | − | pass |
| CS1-04 | the employment example / validate surface / conforms | L4 | + | pass |
| CS1-05 | the lending profile / compile persistence / compiled profile, SPARQL per target, gaps | L4 | + | pass |
| CS1-06 | `invalid-personaldata-no-erasure.ttl` / compile / conforms false, a code, no artefacts | L4 | − | pass |
| CS1-07 | the employment example / compile surface / artefacts per contract | L4 | + | pass |
| CS1-08 | a job run twice, each target / the graphs / equal but for times | L2 | + | pass |
| CS1-09 | Queued / handled / Running then Succeeded | L1 | + | pass |
| CS1-10 | a missing input graph / handled / Failed with a message | L1 | − | pass |
| CS1-11 | wrong prefix, upper-case UUID, extra text, invalid UTF-8 / accepted / refused, nacked without requeue | L8 | − | pass |
| CS1-12 | a store error before the final write / handled / nacked with requeue | L1 | − | pass |
| CS1-13 | the packaged topology / compared / equal to the contract's | L3 | + | pass |

## CS2: the service

`platform/config-studio-service`, 29 cases in `StudioApiTest`, `StudioHttpServerTest` and `TopologyTest`.

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| CS2-01 | Turtle and a Slug / POST workspace / 201, Location, described, listed, baseline ETag "1", surface "0" | L1 | + | pass |
| CS2-02 | revision 0 / PUT with `If-Match: "0"` / 204, ETag "1", graph and revision stored together | L1 | + | pass |
| CS2-03 | a stale or missing `If-Match` / PUT / 412 or 428, nothing stored | L1 | − | pass |
| CS2-04 | a baseline PUT / revision 2 in a new graph, revision 1 kept | L1 | + | pass |
| CS2-05 | bad Turtle, a wrong content type, 5 MiB + 1 / any write / 400, 415, 413 | L8 | − | pass |
| CS2-06 | a job POST / the input and job graphs as the contract shows, exactly the IRI published, 202 | L3 | + | pass |
| CS2-07 | a bus that throws / job POST / 202 with a Failed job | L1 | − | pass |
| CS2-08 | the job listing / compile jobs only, no report or artefact triples | L1 | + | pass |
| CS2-09 | non-UUID ids, unknown routes, other methods / 404, 405 with `Allow` | L8 | − | pass |
| CS2-10 | over HTTP / security headers present, no `Access-Control-Allow-Origin`, SPA fallback, six traversal variants refused | L8 | − | pass |

`mise exec -- mvn -f platform/pom.xml -pl config-studio-service -am verify`

## CS3: the browser application

`apps/config-studio/src/rdf/rdf.test.ts`, 19 cases against the staged vocabulary, and `e2e/studio.spec.ts`, 7 cases against the fake service in `e2e/fake-service.ts`.

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| CS3-01 | the vocabulary / fields derived / `dal:strategy` a single choice of its three individuals with comments, numbers, switches, baseline pickers, lists, references | L1 | + | pass |
| CS3-02 | a data access profile / sections / one per dimension, each property once, read path kept out of contract fields | L1 | + | pass |
| CS3-03 | the employment and lending samples / split / contracts, path steps and RDF lists with their owner, nothing lost | L1 | + | pass |
| CS3-04 | edits / RDF list replaced, node removed / no orphaned cells, references removed | L1 | + | pass |
| CS3-05 | one graph built in two orders / Turtle / identical, prefixes sorted (a probe found them unsorted) | L2 | + | pass |
| CS3-06 | the read path / one forward hop, two hops, an inverse hop / `srf:readProperty` or ordered steps, never both | L1 | + | pass |
| CS3-07 | a term the baseline lacks, a reference to nothing, a SKOS term / checked / warnings for the first two only | L1 | +/− | pass |
| CS3-08 | the Lending sample / created / sorted into baseline and persistence, saved with `If-Match: "0"`, the profile on the overview | L6 | + | pass |
| CS3-09 | a profile / Personal data, No erasure clicked / the unsaved Turtle validated, a violation on the Privacy section, nothing saved | L6 | − | pass |
| CS3-10 | an edit / undo, redo, save / the field follows, the save sends the read revision | L6 | + | pass |
| CS3-11 | another author saved first / save / a dialog with the diff, Keep mine sends the new revision | L6 | − | pass |
| CS3-12 | a class row / Promotion / carrier set, two hops built, a hop reversed, validated as steps | L6 | + | pass |
| CS3-13 | the build view / compile / job states, the artefact shown | L6 | + | pass |
| CS3-14 | the palette / a class name / its baseline page | L6 | + | pass |

`mise exec -- yarn workspace @lattice/config-studio run check` and `mise run test:config-studio`

## CS4: the stack

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| CS4-01 | Fuseki 6.2.0, RabbitMQ 4.4.0, the service, the worker, the dev server / an author creates Lending, sets personal data with no erasure, sees the compiler's refusal, fixes it, saves, compiles / each step as described, SPARQL shown | L5 | +/− | pass, run 2026-10-27 by hand-started infrastructure |
| CS4-02 | the service's runtime dependencies, 40 Maven packages, and the worker's 8 PyPI packages / OSV query / no advisory | L7 | + | pass, 2026-10-27. A first run found `libthrift` 0.22.0 through Jena 5.6.0, fixed by Jena 6.2.0 |
| CS4-03 | the Yarn lockfile / `yarn npm audit --all --recursive` / no advisory | L7 | + | pass, one deprecation notice (`whatwg-encoding`, the Word add-in's `jsdom`), which is not an advisory |
| CS4-04 | the built application served by the service / loaded / no content security policy violation in the console | L6 | + | pass |

`mise exec -- yarn workspace @lattice/config-studio run test:stack`, with the stack up as the service's README says.

## CS5: vocabulary, quantification and eligibility, service and worker

`workers/tests/test_config_studio_layers.py`, 12 cases, and two more in `StudioApiTest`.

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| CS5-01 | conjunctive scopes / validate vocabulary / two segments by four scope sets, north and gold resolving to the tier scheme from 2026, everything before it falling back | L4 | + | pass |
| CS5-02 | an equal-specificity conflict / validate / a SHACL violation, and conflict rows naming both tied bindings | L4 | − | pass |
| CS5-03 | a temporal handover / validate / nothing before January, edition 1 from January, edition 2 from July | L4 | + | pass |
| CS5-04 | the quantification examples / validate / conform | L4 | + | pass |
| CS5-05 | a hierarchical condition / validate / the expansion Denied, Permitted, Permitted over the scheme, and its question decided Permitted | L4 | + | pass |
| CS5-06 | two questions expecting Permitted, one decided Denied / validate / one passes, one fails as a `TestFailed` violation, the job does not conform | L4 | − | pass |
| CS5-07 | an interval question / validate / decided by the compiled query | L4 | + | pass |
| CS5-08 | a hierarchical condition with no contract / validate / an `IRCompileError` violation | L4 | − | pass |
| CS5-09 | conditions on bound subjects / validate / an `EvidenceBindingNotTested` note, nothing decided | L4 | − | pass |
| CS5-10 | a hierarchical condition / compile eligibility / `decision.rq` and `shapes.ttl` per condition and profile | L4 | + | pass |
| CS5-11 | vocabulary / compile / Failed, nothing to compile | L4 | − | pass |
| CS5-12 | no baseline graph in the store / validate / Succeeded, the baseline read as empty | L4 | + | pass |
| CS5-13 | the service / each new configuration saved and validated, compile refused for vocabulary and quantification / revisions 1, 202, 400 | L1 | +/− | pass |
| CS5-14 | a workspace described before the new graphs / read and saved / their revisions read as 0 | L1 | + | pass |

## CS6: the new views

`src/rdf/rdf.test.ts`, 6 more cases, and `e2e/studio.spec.ts`, 6 more, against a fake service whose oracle answers resolutions, expansions and questions from the submitted Turtle.

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| CS6-01 | the lending eligibility sample / split / conditions, ranges and bindings each in their part, nothing in the baseline | L1 | + | pass |
| CS6-02 | the vocabulary / fields / a contract reference despite one individual of its range, several required concepts, a language-tagged label, decimal values | L1 | + | pass (a probe found every `elg:` property single-valued, fixed) |
| CS6-03 | a range written, read, tested for containment at both ends, and removed / nothing left behind | L1 | +/− | pass |
| CS6-04 | a concept test and a value test / written as questions, the value as a point range set, removed whole | L1 | + | pass |
| CS6-05 | the employment scheme / a forest by broader | L1 | + | pass |
| CS6-06 | a job graph / resolutions, expansions and tests read | L1 | + | pass |
| CS6-07 | the lending eligibility sample / created / three parts saved from revision 0 | L6 | + | pass |
| CS6-08 | a scheme contract / the resolution table, a moment and a scope tried / the winning binding, then the fallback before its start | L6 | + | pass |
| CS6-09 | a concept condition / its expansion counted, a test added expecting Permitted for an excluded concept / the body carries the expectation, the test fails | L6 | − | pass |
| CS6-10 | an interval condition / a value test added / a point range set in the body, the number line marks it outside | L6 | + | pass |
| CS6-11 | a scheme and a binding / a narrower concept added, a validity end set / a tagged label, a temporal scope in the body | L6 | + | pass |
| CS6-12 | an admission profile / opened / its tests marked as under construction | L6 | + | pass |
| CS6-13 | the live stack / an interval test failing then passing, a condition's expansion, a contract's table / each as the real engines decide | L5 | +/− | pass |

## CS7: starting and stopping the stack

`tools/test_config_studio_stack.py`, 2 cases, in `check:config-studio`, and the stack by hand.

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| CS7-01 | a spawned process with a child of its own / stopped / both gone, its process id file removed, a second stop reports nothing to stop | L1 | + | pass |
| CS7-02 | a download whose SHA-256 is not the pinned one / fetched / refused, nothing left behind, and accepted with the right one | L1 | +/− | pass |
| CS7-03 | a clean `.build` / `mise run studio:up` / Fuseki and RabbitMQ downloaded and checked, service and worker built and started, the service answering, in 17 s | L5 | + | pass, macOS, 2026-10-27 |
| CS7-04 | the stack from CS7-03 / `test:stack` / both live-stack browser tests pass against 8090 | L5 | + | pass. A first run failed: the tests pointed at the dev server, which `up` starts only with `--dev`. Now configurable, 8090 by default |
| CS7-05 | the stack / `mise run studio:down` / RabbitMQ shut down by `rabbitmqctl`, its log saying "Successfully stopped RabbitMQ and its dependencies", the others stopped within the grace period, every port free | L5 | + | pass, macOS |

Not run: Windows and Linux, and `--docker`, since Docker was not running. The Windows path is authored from the platform's documented behaviour.

## CS8: Helidon and the service's own membership check

`StudioHttpServerTest` and `StudioApiTest`, 34 cases in all, in `check:config-studio`, and the stack by hand.

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| CS8-01 | the service on Helidon 4.5.6 / every HTTP test of CS2 and CS4 / passes unchanged: security headers, the Turtle round trip, no cross-origin response, static files and the SPA fallback, path traversal | L2 | +/− | pass |
| CS8-02 | a HEAD request / sent raw / the file's `Content-Length` and no body. Found by hand: Helidon sends a HEAD response's body unless told otherwise | L2 | + | pass |
| CS8-03 | a surface graph holding a baseline subject, a surface graph holding a `dal:` profile, a baseline holding a SKOS scheme / `PUT` / `422` naming the subject and its part, the stored graph and its revision unchanged | L1 | − | pass |
| CS8-04 | an eligibility question naming a quantification range set, a SKOS `inScheme`, a plain triple, nested and orphan blank nodes / `Parts.owners` / the parts `split.ts` gives: eligibility, quantification, vocabulary, baseline, the referrer's part, baseline | L1 | + | pass |
| CS8-05 | the shaded jar / `--self-check` / passes, its `META-INF/helidon/manifest` listing all 15 registry files of the Helidon jars | L3 | + | pass. A first build kept one jar's manifest only, fixed with an appending transformer |
| CS8-06 | `studio:up` / `test:stack`, and a 6 MB body with and without a `Content-Length`, and `OPTIONS` / both browser tests pass, `413`, `413`, `405` | L5 | +/− | pass, macOS |

Probe P5: with `Parts.strangers` replaced by an empty list, CS8-03 failed (`aGraphHoldingAnotherPartsTermsIs422AndLeavesTheGraphUnchanged`). Restored, 34 pass.

## Dependency upgrades, 2026-10-28

Not a slice of the studio, recorded here because the studio's audit found them (TD-95).

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| UP-01 | `amqp-client` 5.37.0 in `authoring-service` and `platform-outbox` / `mise run check:java` / every module builds and its tests pass | L1 | + | pass, 85 authoring and 31 studio tests |
| UP-02 | RabbitMQ and Fuseki containers, RabbitMQ on `rabbitmq:4.4-management-alpine` / `mise run check:authoring-service-it` / the stack, bus and store integration tests pass | L4 | + | pass, 6 integration tests |
| UP-03 | OSV on 2026-10-28 / `amqp-client` 5.37.0 and `pika` 1.4.4 / no advisory | L0 | + | pass. RabbitMQ 4.4.0 lies outside every range in the server's GitHub advisories |

| UP-04 | the POC stack on `rabbitmq:4.4-management-alpine` (4.4.0) / `mise run check:authoring-stack` / every end-to-end test passes, a restart included | L5 | + | pass, 7 tests |

Not run: the platform's compose file, whose RabbitMQ no test starts.

## Artefacts to inspect

- The studio itself: `mise run studio:up`, then <http://127.0.0.1:8090>, and `mise run studio:down`.
- A job graph: `curl http://127.0.0.1:8090/api/jobs/<id>` after a compile.
- Browser test traces under `.build/config-studio-test-results` on a failure.

## Deliberate non-coverage

- The compose file was authored and not run, since Docker was not running. CS4-01 ran the same versions started by hand.
- `RabbitJobBus` and the Fuseki store have no automated integration test, only CS4-01. A Testcontainers suite like `check:authoring-service-it` would cover them.
- The worker's `main` and its reconnect loop are exercised only by CS4-01.
- Surface's `shapes/constraints.ttl` is not run (TD-11), and every surface validation says so as a warning.
- Accessibility was checked by role-based selectors in CS3 and CS6 and by hand, not by an audit tool.
- Under construction, shown as such in the studio: testing an admission profile's composed decision, testing a condition that reads bound subjects, and quantification's comparisons, conversions and canonical range sets. The last waits on a quantification reference implementation the repository does not have.
