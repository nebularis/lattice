<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: word-authoring-poc WA4, API and HTTP adapter

**Plan:** [word-authoring-poc](../plans/word-authoring-poc.md) §5 WA4
**Status record:** [word-authoring-poc](../status/word-authoring-poc.md) (holds the commit hash)

## Invariant

Everything the add-in will eventually talk to over HTTP must already work with no HTTP in the
picture, so `AuthoringApi` carries every business rule and `http.AuthoringHttpServer` carries none:
it only reads path parameters and a body, calls `AuthoringApi`, and writes the `ApiResponse` it
gets back. This is what lets S4-01 to S4-08 and S4-13 to S4-14 exercise `submitSnapshot`,
`onAnalysisResult`, `health` and `SampleSeeder` directly, in memory, while S4-09 to S4-12 prove the
same behaviour survives going through Javalin, a real socket and a real JSON parse.

Two invariants hold across that boundary. First, **optimistic concurrency on `baseRevision`** is
the only way two submissions of the same document can be ordered: a submission with no base
revision against an existing document, or the wrong one, conflicts (409) rather than silently
clobbering or silently stacking. Second, **a snapshot is accepted and its job queued before
anything asks the analysis bus to do work**, and a bus that cannot publish still leaves the author
with a 200 and a `failed` job, never a submission that vanishes. Both invariants are what makes the
service usable from inside Word, where a drafter's "accept" click must have one unambiguous
outcome.

## Test cases

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| S4-01 | the in-memory wiring / a new facility snapshot submitted / 200, revision 1, the wording graph stored under its IRI, registry latest 1, one request published whose graph reference and IRIs match, job `queued` | L1 | + | pass |
| S4-02 | revision 1 exists / submitted with base 1 / revision 2. With base null / 409. With base 5 / 409 | L1 | +/− | pass |
| S4-03 | path and body document ids differ / 400. A path id that is not a UUID / 400. A body with an extra property / 400 with details | L1 | − | pass |
| S4-04 | a snapshot naming template `nope` / 404 | L1 | − | pass |
| S4-05 | the bus set to throw / submitted / 200 with job `failed` | L1 | − | pass |
| S4-06 | a completed result for the job / delivered / job `completed`, analysis view with conformance, and a second `AuthoringApi` over the same store serves the same view | L1 | + | pass |
| S4-07 | a failed result / delivered / job `failed` with the error, analysis 404 | L1 | − | pass |
| S4-08 | a result for an unknown job, and an invalid result / delivered / no exception, nothing changes | L1 | − | pass |
| S4-09 | the HTTP server on an ephemeral port / each route called once with valid input / the status of the table, and each JSON body validates against its response schema | L3 | + | pass |
| S4-10 | a 1 MiB + 1 byte body, and a PUT with `text/plain` / 413 and 415. An unknown path / 404. POST to `/api/templates` / 405 | L1 | − | pass |
| S4-11 | any response / headers / `nosniff` and `no-store` present, no `Access-Control-Allow-Origin` | L1 | + | pass |
| S4-12 | a stored revision / graph `wording` / Turtle that parses to a model isomorphic to the stored one. Kind `other` / 400 | L1 | +/− | pass |
| S4-13 | a store whose ping fails / health / 503 `degraded` with `fuseki: down` | L1 | − | pass |
| S4-14 | an empty registry / seeded twice / three documents at revision 1 and three requests the first time, nothing the second | L1 | + | pass |

Carried by five test classes: `SubmitSnapshotTest` (S4-01 to S4-05), `AnalysisResultTest` (S4-06 to
S4-08), `HealthAndSeedTest` (S4-13, S4-14), `AuthoringHttpServerTest` (S4-09, S4-10, S4-11, S4-12,
through a real Javalin server on an ephemeral port with Java's built-in `HttpClient`). The module
runs 77 tests in total: WA2's 48, WA3's 15, and WA4's 14 (one test method per row above; S4-09's
"each route" is one method making ten calls).

## One command

From the repository root:

```
mise run check:authoring-service
```

A pass prints `Tests run: 77, Failures: 0, Errors: 0, Skipped: 0` followed by `BUILD SUCCESS`.

Re-run `mise run check:java` (9 modules) and `mise run check:authoring-contracts` (35 tests) to
confirm nothing else moved.

## Artefacts to inspect

| What | Where | Look for |
|---|---|---|
| the route table and `submitSnapshot`'s nine steps | [AuthoringApi.java](../../../platform/authoring-service/src/main/java/org/nebularis/lattice/authoring/api/AuthoringApi.java) | the method order matches plan WA4's numbered list exactly |
| every handler reads, calls, writes, nothing else | [AuthoringHttpServer.java](../../../platform/authoring-service/src/main/java/org/nebularis/lattice/authoring/http/AuthoringHttpServer.java) | no business logic, no direct reference to `store`, `registry`, `bus` or `jobs` |
| the registry's triples | [DocumentRegistry.java](../../../platform/authoring-service/src/main/java/org/nebularis/lattice/authoring/store/DocumentRegistry.java) | the document and revision resources match plan WA4's class table |
| the charset defect and its fix | [ApiResponse.java](../../../platform/authoring-service/src/main/java/org/nebularis/lattice/authoring/api/ApiResponse.java) | `TEXT_TURTLE = "text/turtle; charset=utf-8"`, and §"Implementer choices" below |
| solution-design-specification's new section | [solution-design-specification.md](../../architecture/solution-design-specification.md) §4.7 | component table, route table, the not-a-platform-contract statement |

## Self-probe

The plan's prescribed break: remove the 409 check for `baseRevision` null against an existing
document (`AuthoringApi.submitSnapshot`'s `conflict` expression narrowed to drop its first
disjunct). `mvn -f platform/pom.xml -pl authoring-service test -Dtest=SubmitSnapshotTest` then
failed:

```
SubmitSnapshotTest.enforcesOptimisticConcurrencyOnBaseRevision:54
expected: <409> but was: <200>
```

exactly the case the plan names. The break was reverted and the full command re-run green at 77
tests. Unlike WA3's probe, this one is not vacuous: §"Deliberate non-coverage" has no note about it.

## Implementer choices

| Left open | Chosen | Why |
|---|---|---|
| `TemplateFindings` and `ConformanceChecker`'s shape | changed from WA3's static-utility classes to ordinary instantiable classes with instance `check` methods | plan WA4 lists both as constructor arguments of `AuthoringApi` ("Constructed with ... `TemplateFindings`, `ConformanceChecker` ..."), which only makes sense if they are held as fields. WA3's own tests were updated to `new TemplateFindings().check(...)`; no behaviour changed |
| Jackson serialisation of `ValueType`, `ElementKind`, `Severity`, `TermKind`, `JobStatus` | `@JsonValue` added to each enum's existing `toJson()`/`jsonValue()` method | WA4 is the first place these enums are written into an HTTP response body. Without it Jackson emits the Java constant name (`"MONEY"`), not the schema's string (`"money"`), and S4-09's schema validation would fail |
| where the per-route response types live | `GraphRef`, `JobStatus` in `model` (beside the existing schema-def enums); `JobSummary` in `jobs` (beside `JobView`); `ApiResponse`, `ErrorBody`, `HealthView`, `AnalysisView`, `SnapshotAccepted`, `PathParams` in `api` | each is a direct Java shape for one schema def or response, named by the package that owns the matching concept |
| `AnalysisView.analysis`'s Java type | `JsonNode`, not a Java `Analysis`/`ElementAnalysis`/`GraphView` model | building that model is WA6's job. WA4 stores and relays the worker's own, already schema-validated JSON unchanged, which is also strictly more faithful than re-deriving it |
| the document resource's IRI | a new public `IriMinter.document(documentId)` wrapping the existing private `doc(...)` | plan §2.3's IRI table has no row named "document", but `DocumentRegistry`'s own triples need one, and `doc(...)` already computes exactly that IRI |
| `dcterms:created` on a revision record | `Instant.now()`, read inside `DocumentRegistry.record`, not a parameter | `record(...)`'s plan signature carries no timestamp argument. Untested exactly, since no test case asks for a specific value |
| the 1 MiB / `application/json` checks | a `before` handler reading `HttpServletRequest.getContentLengthLong()` directly, with two private marker exceptions mapped to 413 and 415 | Javalin's own `config.http.maxRequestSize` enforcement path and its exact exception type were not confirmed from the plan text alone, and the manual check is dependency-free, runs before any body parsing, and is exactly what S4-10 proves |
| `ApiResponse.TEXT_TURTLE`'s exact string | `"text/turtle; charset=utf-8"`, not `"text/turtle"` | found by S4-12 (below): without an explicit charset the Servlet response defaults to ISO-8859-1 when turning the Turtle string into bytes, corrupting the samples' smart quotes. The constant is the single place this is set, so every caller gets the fix |
| S4-12's graph comparison | `CanonicalHash.sortedNTriplesLines` equality, not `Model.isIsomorphicWith` | `isIsomorphicWith` returned `false` for two models whose `Model.difference()` was empty in both directions once the charset defect above was fixed — a ground graph (no blank nodes, as `WordingMapper` never creates one) should never disagree between those two checks. The canonical-text comparison is the stronger, already-tested equivalence CanonicalHash exists for, and sidesteps whatever the isomorphism checker was doing |
| `SampleSeeder`'s existence check | `registry.documentIds().contains(documentId)` | matches the plan's own wording ("whose documentId the registry does not hold") literally, though `latestRevision(documentId) == 0` would answer the same question |

## Deliberate non-coverage

- **A malformed (non-parseable) JSON body on the PUT route.** Falls through to the generic
  `exception(Exception.class)` handler, giving 500. Not asserted; S4-03's "extra property" case is
  syntactically valid JSON that fails schema validation, a different path.
- **`GET .../graph/proposal`.** Nothing in WA4 writes to the `proposalGraphIri` named graph: that is
  written directly to Fuseki by the WA6/WA7 worker, not relayed through `AuthoringApi`. S4-12 tests
  only `wording` and the invalid kind `other`, matching the plan. Covered end to end once a real
  worker exists, at WA5 or WA10.
- **A real Fuseki-backed `AuthoringStore` and a real RabbitMQ-backed `AnalysisBus`.** WA5.
- **Two `submitSnapshot` calls for the same document racing each other.** `DocumentRegistry`'s
  `synchronized` methods make each read-modify-write atomic, but two concurrent callers can still
  both read the same `latestRevision` before either writes, each believing their submission is
  next. Not covered by a test; a known POC-grade limitation (no request-level locking per document).
- **CORS, authentication.** No header is ever set and no credential is ever checked; S4-11 proves
  only the header's absence.
- **A client that lies about or omits `Content-Length` while sending an oversized or chunked body.**
  The 413 check reads the header the client declares; it does not count bytes as they arrive.

Unit-wide non-coverage, cited by every pack: CCS assembly, amendments, tables and versioned
elements. LE2 parsing of the generated program. Concurrent editing. Authentication. Poison-message
retry limits. Real Word, except through WA11's manual checklist.
