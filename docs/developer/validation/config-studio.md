<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: config-studio CS0 to CS4

**Plan:** [config-studio](../plans/config-studio.md)
**Status record:** [config-studio](../status/config-studio.md)

One pack for the unit's five slices, each a section, since they were built and are reviewed together (a deviation from one pack per slice, recorded in the status record).

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

## Artefacts to inspect

- The studio itself: `mise run studio:service`, `studio:worker`, `studio:web`, then <http://127.0.0.1:4175>.
- A job graph: `curl http://127.0.0.1:8090/api/jobs/<id>` after a compile.
- Browser test traces under `.build/config-studio-test-results` on a failure.

## Deliberate non-coverage

- The compose file was authored and not run, since Docker was not running. CS4-01 ran the same versions started by hand.
- `RabbitJobBus` and the Fuseki store have no automated integration test, only CS4-01. A Testcontainers suite like `check:authoring-service-it` would cover them.
- The worker's `main` and its reconnect loop are exercised only by CS4-01.
- Surface's `shapes/constraints.ttl` is not run (TD-11), and every surface validation says so as a warning.
- Accessibility was checked by role-based selectors in CS3 and by hand, not by an audit tool.
