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

## CS10: RDF/XML by content negotiation

`RdfXmlTest`, 6 cases, in `check:config-studio`, and the staged assets by hand.

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| CS10-01 | a saved surface graph with a blank node / `GET` with `Accept: application/rdf+xml` / RDF/XML isomorphic with the graph, the revision's ETag, `Vary: Accept` | L1 | + | pass |
| CS10-02 | ten `Accept` headers, a browser's default and an absent one among them / `GET` / Turtle unless RDF/XML ranks higher | L1 | +/− | pass |
| CS10-03 | every RDF route / `GET` as RDF/XML / RDF/XML that parses, plain text and `404` left alone | L1 | + | pass |
| CS10-04 | a graph with a predicate ending in a digit / `GET` as RDF/XML / `406`, and `200` as Turtle | L1 | − | pass |
| CS10-05 | the graph of CS10-01 as RDF/XML / `PUT` / the same graph stored. Truncated RDF/XML `400`, JSON `415` | L1 | +/− | pass |
| CS10-06 | RDF/XML declaring an external entity that names a local file / `PUT` / `400`, nothing stored. Found by the test's first run: Jena never read the file but stored the entity as an empty string, so a DTD is now refused | L1 | − | pass |
| CS10-07 | the staged vocabulary and the seven samples / `GET` as RDF/XML on the live stack / `200` each. The vocabulary takes about 60 ms against 3 ms as Turtle | L5 | + | pass, macOS |

## CS9: a supported component

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| CS9-01 | the `cst:` namespace without `poc/` / `check:config-studio` and `test:config-studio` / every suite passes: 39 Python, 40 service, 12 package and 23 browser unit tests, and 13 browser tests | L1 to L3 | + | pass |
| CS9-02 | the new and changed register entries / `check:knowledge`, `check:identifiers` / pass, every pointer resolving | L0 | + | pass, 84 and 9 tests |
| CS9-03 | the architecture document, the operations guide and the runbook / the pre-commit hooks (links, site sections, published decisions, writing, wrapping) / pass, citing only Accepted ADRs and no working document | L0 | + | pass |
| CS9-04 | the operations guide's procedures / run against the live stack by its author: up, status, down, every health check, `415`, `400`, `428`, `422`, `413`, `201`, `404`, a job from queued to succeeded, a port in use, a stale process id | L5 | + | pass, macOS. Not run: `--docker`, `--dev`, Windows, a refused checksum, a stale Erlang node |
| CS9-05 | another process on the service's port / `Stack.claim` / refused before anything starts, and accepted once the port is free. Found by the runbook's author: `up` reported success while the service failed to bind | L1 | − | pass |
| CS9-06 | the downloaded RabbitMQ without `loopback_users []` / `studio:up`, `test:stack`, a second `up`, `studio:down` / both browser tests pass, the second `up` skips what runs, RabbitMQ shuts down through `rabbitmqctl` | L5 | + | pass, macOS |

### STD-279 review of both services

| Component | Input | Validated at the component | Finding |
|---|---|---|---|
| studio service | every body | size, media type, syntax, part membership, no DTD in RDF/XML | CS8 added part membership, CS10 the DTD refusal |
| studio service | path, query, headers | workspace and job ids as lower-case UUIDs, part names from a fixed list, sample ids by pattern, the slug's encoding, the job's kind and target, `If-Match` | none |
| studio worker | AMQP message | a studio job IRI, whole and UTF-8 | none |
| studio worker | the job graph | a known kind, target and submission time, and, since this review, only the job's own input graph and a workspace baseline | fixed, CS-B19, tested by `test_a_job_naming_a_graph_outside_its_own_fails_without_reading_it` |
| authoring service | path parameters | UUID, key and revision patterns | none |
| authoring service | snapshot body | media type, size, JSON Schema, then SHACL. Since CS12a, a body that is not JSON is `400` | fixed in CS12a. Under Javalin it reached the general handler |
| authoring service | the worker's result event | its JSON Schema before it is stored | none |
| wording worker | AMQP message | the request's field set and types, and its graph reference | partial: not the whole JSON Schema. The JSON contract is retired in CS12d, so not fixed |

## CS12a: the authoring service on Helidon

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| CS12a-01 | the authoring service on Helidon 4.5.6, Jena 6.2.0, Jackson 2.22.4 / `mvn verify` / 85 unit tests, the HTTP ones unchanged but for two cases added: a body that is not JSON, and an empty body, `400` | L3 | +/− | pass |
| CS12a-02 | Fuseki and RabbitMQ 4.4 containers / `check:authoring-service-it` / 6 integration tests pass | L4 | + | pass |
| CS12a-03 | the POC stack / `check:authoring-stack` / 7 end-to-end tests pass, a restart included | L5 | + | pass |
| CS12a-04 | the runtime dependencies of both services, 82 and 74 / OSV's batch query on 2026-10-28 / no advisory | L0 | + | pass |

## CS12b: the shared domain package

Built by a sub-agent on its own branch, reviewed and merged.

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| CS12b-01 | the document model, tag codec, offsets and graph model moved to `packages/authoring-domain` / every suite / the totals unchanged: studio 23 plus 2 moved, add-in 59 plus 10 moved, the package 12 | L1 | + | pass |
| CS12b-02 | both apps importing the package / `check:authoring-addin`, `test:authoring-addin`, both production builds / pass, 59 unit and 13 harness tests | L1, L3 | + | pass |

## CS13: forms from shapes first

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| CS13-01 | the layers' node and property shapes staged into `vocabulary.ttl`, with SHACL-SPARQL stripped / `tools/test_config_studio_stage.py` / shapes present, constraints absent | L1 | + | pass. The file grew from 269,825 to 313,440 bytes |
| CS13-02 | a property placed by a shape with no domain, `sh:in` choices, `sh:maxCount 1`, `sh:minCount` as required, inheritance and the precedence override, shape, domain / `vocabulary.test.ts` / each as stated | L1 | + − | pass, 10 tests, one over the staged vocabulary (`qnt:onSpace` on `qnt:Range`) |
| CS13-03 | the studio's forms before and after / a count per layer / no field lost | L1 | + | pass. Counts unchanged in all five layers, which already had domains. Shapes add required markers and single values |
| CS13-04 | the browser suites / `mise run check:config-studio`, `mise run test:config-studio` / pass | L2, L3 | + | pass, 40 unit tests and 13 browser tests |

## CS14: partitioned store writers and the on-disk store

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| CS14-01 | a command / encoded as headers and N-Quads and decoded / the same command, and a malformed one decodes to nothing | L1 | + − | pass, `WritesTest` |
| CS14-02 | the writer / a save with a stale revision, a save to an unknown workspace, a bad id, an unknown part, another part's subject, a repeated creation, a sample id with a path / `412`, `404`, then `400` for each refusal | L1 | + − | pass |
| CS14-03 | a job update / changing the status, rewriting a dateTime from `Z` to `+00:00`, pointing the job at another graph, naming another workspace, after the job was deleted / applied, applied, refused, refused, dropped | L1 | + − | pass |
| CS14-04 | export, then import with a new label / the copy has its own id, the label, the revisions and the configuration, and the original is untouched. TriG of two workspaces, a stray graph, a default graph, no description, and syntax errors are refused | L1 | + − | pass |
| CS14-05 | a workspace from a sample, and a sample that is not staged or has a path in it / `cst:fromSample` recorded, `400` | L1 | + − | pass |
| CS14-06 | jobs finished 57 and 1 days ago, a 30-day retention / a sweep / deletes one | L1 | + | pass |
| CS14-07 | the worker's `WriterStore` / a job graph / published to `lattice.studio.writes` keyed by the workspace with a `job-update` header and the graph as N-Quads, the store untouched. A graph naming no workspace is never sent | L1 | + − | pass, 24 worker tests |
| CS14-08 | `data_dir` / each platform and `LATTICE_STUDIO_DATA` / the folders the operations guide names | L1 | + | pass, 4 stack tests |
| CS14-09 | the native stack on TDB2 in a scratch data folder / create, save, a stale save, a validation, export, import, delete, `studio:down` and `studio:up` / `201`, `204`, `412`, `cst:Succeeded`, `200`, `201`, `204`, and the workspaces still there after the restart | L5 | + − | pass. The first run found CS-B26 (rdflib's dateTime) and a curl of a whole sample into a baseline, now `422` (CS-B28) |
| CS14-10 | the Docker stack / the same, then `docker compose restart fuseki` / the workspace answers `200` after the restart, and RabbitMQ lists `rabbitmq_consistent_hash_exchange` among its plugins | L5 | + | pass. The first runs found the compose file had never run: the Fuseki jar was unreadable, `--loc` needed its folder, and Fuseki needs a writable base. Fixed, and `up --docker` now rebuilds |
| CS14-11 | probe P6, eight concurrent 20,000-triple inserts and a read during a 200,000-triple insert on Fuseki TDB2 / timed / concurrent no faster than sequential, the read not blocked | L5 | + | 0.94 and 1.06 of sequential, reads in 3 and 8 ms. TSD-42 |
| CS14-12 | the service suite / `mise run check:config-studio` / pass | L1 | + | pass, 50 Java tests |

## CS15: the facility agreement sample

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| CS15-01 | the sample's files / sorted by the Python port of `split.ts` and by `split.ts` itself / each subject in its intended part | L1 | + | pass |
| CS15-02 | each part / validated by the worker / no violation. The resolution table has its 11 expected rows, one Unresolved and one Conflict on purpose. All 17 questions decide as expected, and a wrong expectation fails with `TestFailed` | L1 | + − | pass, 10 tests in `test_config_studio_facility_sample.py` |
| CS15-03 | eligibility, persistence and surface / compiled / the expected artefacts, and personal data with `NoErasure` refused | L1 | + − | pass |
| CS15-04 | the live studio / the sample opened from the new-workspace dialog / created through the writer, 0 violations, 2 warnings | L5 | + | pass. The warnings are surface's `ConstraintsNotRun` (TD-11) and a promotion's target property the baseline does not declare, as in the repository's surface examples. 10 warnings that identity references were undeclared were removed (CS-B28) |
| CS15-05 | the whole worker suite / `mise run check:workers` / pass | L1 | + | pass, 167 tests |

## CS16: batched, guarded writes with receipts, and the surface refusal

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| CS16-01 | a save / applied / a receipt with its command, sender, requested and committed times, the graphs it wrote and its revision, beside the creation's | L1 | + | pass, `ReceiptsTest` |
| CS16-02 | the same command twice, as after a lost acknowledgement / applied / answered from its receipt, the revision moved once | L1 | + | pass |
| CS16-03 | a batch of saves expecting 0 and 1, a stale save and a bad id / applied as one request / `200 r1`, `200 r2`, `412 r2`, `400`, and the second graph stored | L1 | + − | pass |
| CS16-04 | another writer saving between this writer's read and its update / the update runs / `412`, nothing of the overtaken write stored, no receipt for it | L1 | − | pass. The interference is a proxy over the connection |
| CS16-05 | a workspace deleted / its graphs, jobs and receipts go / the receipt of the deletion is kept in the store's receipts graph | L1 | + | pass |
| CS16-06 | every update and query the tests send / sent as SPARQL text and parsed back, as Fuseki does / the suite passes, and fails without CS-B34's fix | L1 | + − | pass, 55 tests. With the fix undone, 41 fail. The live run found the fault the in-memory store had hidden |
| CS16-07 | the live stack / create, save, a stale save, a validation, deletions / `201`, `204`, `412`, `Succeeded`, `204`, receipts from the service and the worker in their graphs, the deletion's kept | L5 | + − | pass |
| CS16-08 | probe P7, 200 saves of 50 triples over HTTP from 16 clients across 20 workspaces / timed, twice / above TSD-44's 15 commits a second | L5 | + | 54 and 65 saves a second |
| CS16-09 | a promotion outside its target namespace onto a property the source graph does not declare, and the lossy promotion fixture with its property declared / compiled / refused naming the undeclared property, and refused under srf:X6 for lossiness | L1 | − | pass, 103 surface and keys tests, Phase 8 conformance |
| CS16-10 | the worker's job update / published / with an id and `sender` `worker` | L1 | + | pass, 24 worker tests |
| CS16-11 | `mise run check` | L1 | + | every task passes but `check:persistence`, whose probe of TSD-04 on Oxigraph fails alone and in the run, measuring 84 against a bound of 8. This branch changes nothing it reads, so it is recorded for a task of its own |

## CS17: the store writer deployed apart, on a super stream

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| CS17-01 | the three modules / `mvn test` / the service's suite, the writer's and the topology contract pass | L1 | + | pass, 55 service and 3 writer tests |
| CS17-02 | a workspace id / its routing key in Java and in Python / the same partition for the same ids | L1 | + | pass, `TopologyTest` and the worker's test |
| CS17-03 | the reply-to RabbitMQ 4.4 stores in a stream / decoded / the direct reply-to queue's name | L1 | + | pass |
| CS17-04 | the sweep in the writer / jobs finished 57 and 1 days ago / one deleted, with its receipts | L1 | + | pass |
| CS17-05 | the writer's 43 third-party runtime dependencies / OSV on 2026-10-28 / no advisory | L0 | + | pass, Netty resolved to one version, 4.2.19 |
| CS17-06 | the native stack with the writer as its own process / create, save, a stale save, a validation / `201`, `204` in 0.1 to 0.3 s, `412` in 0.02 s, `Succeeded` | L5 | + − | pass. The first run lost every reply (CS-B38), and the receipts answered the saves after 10 s |
| CS17-07 | Fuseki's `studio` service / an update and a graph store write / `405` | L5 | − | pass |
| CS17-08 | a second writer instance / started / the 8 partitions split 4 and 4, each with the other instance waiting | L5 | + | pass, by `list_stream_group_consumers` |
| CS17-09 | the first writer stopped / 200 saves over 20 workspaces from 16 clients / every partition active on the second, every save `204` | L5 | + | pass, 56 saves a second |
| CS17-10 | the Docker stack / the same operations, the read-only check, and a Fuseki restart / as natively, and the workspace still there | L5 | + − | pass, with the stream advertised as `localhost:5553` |

Not run: Windows and Linux, and a writer taking a partition over in the middle of a batch.

## CS12c: the document markup's schemas and the document-to-wording kit

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| CS12c-01 | `document.rnc` / Trang, in the test and by `mise run build:document-schema` / the committed `document.xsd`, byte for byte | L1 | + | pass |
| CS12c-02 | 2 valid fixtures, 2 samples and 9 invalid fixtures (a bad identifier, an empty title, a clause with a term, a definition without one, an upper-case key, an unknown value type, a variable's text on two lines, an unknown inline element, an empty reference) / validated by Jing against the RELAX NG and by the JDK against the XSD / each verdict as expected, the two schemas agreeing on all 13 | L1 | + − | pass |
| CS12c-03 | the facility agreement and software licence samples as markup / the kit run by Saxon-HE 12.5 / the graph the Java mapper gives for the same documents, its committed fixtures, sorted and the same on a repeat | L1 | + | pass, 374 and 320 triples. The same output from Saxon's command line |
| CS12c-04 | text with a quote, a backslash, a newline and a tab / the kit / N-Triples Jena parses back to the same text | L1 | + | pass |
| CS12c-05 | a document declaring a DTD with an external entity / the kit / refused before the stylesheet runs | L1 | − | pass |
| CS12c-06 | the authoring service's whole suite / `mise run check:authoring-service` / passes | L1 | + | pass, 92 tests |
| CS12c-07 | Saxon-HE 12.5, Jing and Trang 20241231, xmlresolver 5.2.2, isorelax / OSV on 2026-10-28 / no advisory | L0 | + | pass. Jing's Saxon-HE 9.6 is excluded, as RELAX NG validation does not use it |

Not run: the property policy sample, which stays a JSON snapshot until CS12d retires them, and the kit in the standalone sidecar process, which does not exist yet.

## CB1, part: the Wording assembler

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| CB1-01 | the facility form and a software licence form / `check`, `plan`, `assemble`, `reassemble` and `render` / admitted, denied and undetermined conditions, slots with no and two admitted variants refused, optional elements chosen and not, WA5 with permuted inputs and a repeat giving identical triples, WA6 no record on failure, reassembly sharing unchanged values, numbering after an omitted clause | L1 | + − | pass, `mise run check:wording-assembler`, 20 tests |
| CB1-02 | the rendered documents / `xmllint` against `contracts/document/document.xsd` / valid | L1 | + | pass, skipped where `xmllint` is absent |
| CB1-03 | Wording with `wrd:AssemblyModel`, `wrd:assembledUnder`, the baseline model and `wrd:WA1Shape` / the literate extraction check, the wording and catalogue tests, the ontology catalog / consistent, every example conforming | L1 | + | pass, 243 tests and the catalog. The release bump waits for the merge, so `check:ontology-versioning` reports it unbumped |

Not run: amendments assembled or rendered, and the `assemble` job kind, which the worker does not run yet.

## CS12d, part: documents in a workspace, and the add-in on the studio's API

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| CS12d-01 | the software licence sample / `PUT` with `If-Match: "0"`, then `GET` as XML and as Turtle / `204` with `ETag: "1"`, the markup back byte for byte, its `wrd:Wording` in the document's graph, the document listed | L1 | + | pass, `DocumentsTest` |
| CS12d-02 | a saved document / a stale `If-Match`, none, then the current one / `412` with the current ETag, `428`, `204` at revision 2 | L1 | + − | pass |
| CS12d-03 | another content type, XML that is not well formed, a DTD with an external entity, an empty title, an unknown template, a root id unlike the path's / `PUT` / `415`, `400`, `400`, `422`, `422`, `422`, and nothing stored | L1 | − | pass |
| CS12d-04 | a document graph with a persistence term, and one describing a node outside the document / sent to the writer directly / both refused | L1 | − | pass |
| CS12d-05 | a saved document / deleted, and its workspace deleted / its graph gone each time | L1 | + | pass |
| CS12d-06 | a workspace with a document / exported and imported / the copy's markup the same | L1 | + | pass |
| CS12d-07 | a saved document / `POST …/jobs?kind=analyse` / a `cst:Analyse` job whose input is the document's graph, published. Before the save, `404` | L1 | + − | pass |
| CS12d-08 | the software licence's Wording graph / the worker runs the analyse job / `cst:Succeeded`, with `analysis.json` holding the elements and the graph view, and `proposals.ttl` | L1 | + | pass. A graph with no wording fails the job |
| CS12d-09 | the markup reader and writer in `packages/authoring-domain` / both samples read and written / the same bytes, escaping, merged literals and unmarked text kept | L1 | + | pass, 19 domain tests |
| CS12d-10 | the add-in on the studio's client / its unit tests and its harness against a faked studio / pass | L1, L3 | + | pass, 63 unit and 14 harness tests |
| CS12d-11 | every module / `mise run check:config-studio`, `check:java`, `check:workers` / pass | L1 | + | pass, 63 service, 3 writer, 92 authoring, 48 studio Python, 40 browser and 170 worker tests. The first run found the templates unreadable from the packaged jar, now read as a stream |

Not run: the add-in against a live studio, Word itself, the old service's end-to-end stack, which now targets nothing, and Windows and Linux.

## CS12d, rest, and CS12e: the document report, the proof of concept retired, one stack

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| CS12d-12 | the software licence with a section its template lacks, unmarked text in it, a date and a duration / `GET …/report` / an `sh:ValidationReport` with `unknown-section`, `unmarked-text` and the `date` and `duration` detections, the duration's text and suggested key, the same bytes on a repeat, and `404` for a document the workspace lacks | L1 | + − | pass, `DocumentsTest` |
| CS12d-13 | the shared suggested-keys fixture, and a clause with a term, a variable, an amount, a date, a reference by number and a placeholder / the Java detector / every key as the fixture says, the kinds in order, the longer match winning, offsets into the element's text, and a definition not detecting its own term | L1 | + − | pass, `DetectorTest` |
| CS12d-14 | the schema and kit tests moved into `config-studio-authoring`, with the kit's expected outputs beside the kit / run there / pass | L1 | + | pass, 9 tests in the module |
| CS12d-15 | the add-in reading the report / its unit tests and harness / validation, template findings and detections shown, Accept marking a detection (S9-14), unmarked text kept in place through markup and through Word's OOXML | L1, L3 | + | pass, 21 domain, 65 unit and 15 harness tests |
| CS12d-16 | the reading's tests on the kit's expected outputs and the property policy's graph kept as a worker fixture / `check:workers` / every sentence form still matched, and the analysis valid against `contracts/config-studio/analysis.schema.json` | L1 | + | pass, 119 tests |
| CS12e-01 | the stack script / its tests / the add-in among the processes, on 4176 | L1 | + | pass, 5 tests |
| CS12d-17 | the repository without the proof of concept's service, worker, contracts and stack / `check:config-studio`, `check:java`, `check:knowledge`, `check:catalogue` and the reference scan / pass, with the knowledge test of the removed compose file dropped, since `test_quanta.py` keeps its rule, and the scan's known list one shorter | L1 | + | pass, 64 service, 3 writer and 9 authoring module tests, 48 studio Python and 40 browser |

Not run: `studio:up` with the add-in's development server, the Docker stack's HTTPS proxy, Word loading the add-in, the add-in against a live studio (TD-100), and Windows and Linux.

## CB1: builder mode, the library and assembly parts, and the assemble job

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| CB1-04 | a form, an assembly and its value record in one graph / sorted into parts by the service and by the browser / the form in library, the assembly and the value record in assembly | L1 | + | pass, `AssemblyTest` and the browser's unit tests |
| CB1-05 | both parts / saved under their own revisions, and an assembly saved as library / `204` each, `422` | L1 | + − | pass |
| CB1-06 | an assemble job, and one naming the library / `POST …/jobs` / `202` with `cst:Assemble` and the assembly target, `400` | L1 | + − | pass |
| CB1-07 | an assemble job's update with a record graph, a validation's with one, and one with a persistence term / sent to the writer / the record stored and deleted with the job, the other two refused | L1 | + − | pass |
| CB1-08 | the facility form and an assembly setting three lenders and two jurisdictions / the worker runs the job / `Succeeded` and conforming, `record.ttl` and `document.xml` in the markup's namespace, and the record written under the job's record prefix | L1 | + | pass |
| CB1-09 | the same job run again / the worker / the same record | L1 | + | pass |
| CB1-10 | an assembly with no lender count / the worker / not conforming, a violation naming the governing variable, no record graph | L1 | − | pass |
| CB1-11 | the library holding the facility form / a validation / conforming, the form checked against Wording's laws | L1 | + | pass |
| CB1-12 | the builder sample / staged and assembled / one assembly gives its record and document, the other is refused as Undetermined | L1 | + − | pass |
| CB1-13 | builder mode / the browser's unit tests and its Playwright test against the fake service / the outline ordered with slots, variants and modes, choices and settings written, an assembly run and its findings, document and record shown | L1, L3 | + | pass, 60 unit and 17 browser tests |
| CB1-14 | every studio suite / `mise run check:config-studio` / pass | L1 | + | pass, with 52 studio Python tests |

| CB1-15 | the native stack with a workspace from the builder sample / builder mode in the browser pane: the library outline, an element's editor, both assemblies, a new assembly with variant 5.2A, optional 5.3, one lender and France, then Assemble / the outline and editors as expected, two of three assembled, 9.1 left out where there is one lender, and the refusal named by its assembly's label | L5 | + − | pass after five fixes: the library's validation reported the assemblies' value records, a container showed "(no text)", the condition chip read "When when", the headline said Refused when some assembled, and the document card's title was squeezed. The studio's browser tests also shared port 4176 with the add-in's development server, and moved to 4177 |

Not run: a form created from scratch, which builder mode does not offer yet. A mandatory section whose only clause is left out is assembled empty, as the form states, which is the form's design rather than the assembler's.

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

- The compose file ran end to end for the first time in CS14-10.
- `RabbitJobBus`, `RabbitWrites`, `WriterPool` and the Fuseki store have no automated integration test, only the live runs CS4-01, CS14-09 and CS14-10. A Testcontainers suite like `check:authoring-service-it` would cover them, and a second service instance taking over a partition has not been tried.
- Windows and Linux were not run for CS13 to CS15, including the data folders CS14-08 tests by path only.
- The worker's `main` and its reconnect loop are exercised only by CS4-01.
- Surface's `shapes/constraints.ttl` is not run (TD-11), and every surface validation says so as a warning.
- Accessibility was checked by role-based selectors in CS3 and CS6 and by hand, not by an audit tool.
- Under construction, shown as such in the studio: testing an admission profile's composed decision, testing a condition that reads bound subjects, and quantification's comparisons, conversions and canonical range sets. The last waits on a quantification reference implementation the repository does not have.
