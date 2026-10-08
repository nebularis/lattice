<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: Word authoring proof of concept

**Unit ID:** `word-authoring-poc` (WAP)
**Unit type:** multi-slice unit, run as one shot on machine S, with a human validation gate per slice
after the run
**Status:** Decisions WA-D1 to WA-D13 recorded 2026-10-01 (WA-D4 Javalin, the rest as recommended).
ADR-A118 Proposed. Execution started with WA0
**Sketch:** [word-authoring-poc.md](../sketches/word-authoring-poc.md) (the design, cited below as
"sketch §n")
**Status record:** [word-authoring-poc.md](../status/word-authoring-poc.md)
**ADR:** [A-118](../../architecture/decisions/ADR-A118-word-authoring-proof-of-concept.md), Proposed
**Depends on:** nothing merged. Uses the CCS sketch §4 and §5 as design input, not CCS slices
**Implementer:** Claude Sonnet 5 on machine S, autonomous mode, local commits only

This plan is written so that the code follows from it with as few choices as possible. Where it
fixes a name, a pattern, an order or a value, use it exactly. Where it does not, choose a plain option and record the choice in the slice's Validation Pack under "Implementer choices".

## Deferred follow-up: published Wording adoption

**Recorded 2026-10-02. Awaiting the human's scheduling decision.** The POC is reported running
successfully. Wording is now published and stable, superseding the availability assumption behind
WA-D3, but not automatically changing that decision or the completed WA0 to WA11 scope.

The impact assessment and candidate design are in
[sketch §4.1.1](../sketches/word-authoring-poc.md#411-deferred-adopt-the-published-wording-ontology).
The likely code changes are concentrated in the Java RDF mapping/validation and Python Wording
reader. Word markup, JSON contracts and LE matching can remain unchanged for bounded structural
adoption. Full alignment also requires decisions on variable value contracts/spaces, Foundation
version identity and existing Fuseki revisions.

Before starting this tranche:

1. Obtain human approval of a proposed ADR-A118 amendment covering WA-D3, the pinned release,
  the adopted semantic scope and the retained POC extensions.
2. Choose configured SKOS concept mappings and scheme validation, variable mappings, the
  immutable-version policy and the old-data policy. Do not silently reset the demo dataset.
3. Author a separate detailed tranche plan and Validation Packs, with slices touching at most
  two modules each. Include offline semantic packaging, Java producer/Python reader alignment,
  unchanged text and UTF-16 offsets, negative validation cases and stored-data compatibility.
4. Update the normative architecture documents only for the approved design delta. Consuming
  published ontology assets does not itself change their versions or require release tags.

No implementation is authorised by this note. The original decisions, mapping tables and
completed slice instructions below remain a record of the POC as implemented.

---

## Follow-on tranche: richer data, a web app, and add-in parity

**Recorded 2026-10-02. Awaiting the human's decisions.** The human asked for three further
enhancements once WA0 to WA11 were running and validated: deeper, more realistic sample data, a
web authoring app editing the same documents without Word, and parity brought back to the Word
add-in. The design is in
[sketch §8](../sketches/word-authoring-poc.md#8-follow-on-enhancements-proposed-2026-10-02).

This plan's §3 gains decisions WA-D14 to WA-D20, §4's slice overview gains WA12 to WA20, and §5
gains their slice instructions. None of WA12 to WA20 may start until its decisions are recorded,
exactly as WA0 could not start before WA-D1 to WA-D13 (stop rule S1). WA20 (the richer sample) is
additionally deferred until the CCS workstream completes, regardless of decisions.

No implementation is authorised by this note.

---

## 1. Goal and acceptance

A drafter opens Word (web or desktop), loads the add-in from the local stack without installing
anything, applies a template, writes or inserts a contract, marks variables and defined terms, and
presses Analyse. The task pane shows schema, SHACL and template findings, proposed markup to accept,
each clause read as Logical English with coloured spans, and the proposed `ins:` graph as a diagram
and as Turtle.

The unit is accepted when:

1. every slice's one command passes on machine S and its Validation Pack is signed in
   `docs/developer/validation/LOG.md`
2. `mise run check:authoring-stack` starts the stack from a clean checkout, seeds three samples and
   passes its end-to-end suite
3. the manual Word checklist (WA11, M1 to M14) is completed by the human in real Word
4. `mise run check:java`, `check:workers`, `check:ontology-versioning` and `check:ontology-catalog`
   pass, with no existing test weakened

---

## 2. Fixed facts

### 2.1 Machine, branch and commits

| Fact | Value |
|---|---|
| machine | S (Windows, PowerShell 5.1, mise, Docker Desktop with Linux containers) |
| branch | `ux/auth-le`, already checked out. Do not create or switch branches |
| commit | one local commit per slice, after its command passes, message `[wap] WA<n>: <slice title>` |
| staging | `git add` the slice's listed paths only, then `git status --short` must show nothing else staged |
| forbidden | `git push`, `git commit --amend`, `git reset --hard`, `git rebase`, force options, branch deletion, `--no-verify` |
| final push | left to the human (§9) |
| mode | autonomous: the agent runs builds and tests itself. Design decisions still go to the human |

### 2.2 Execution loop, per slice

1. Mark the slice in-progress in the status record.
2. Check the slice's preconditions (§5, each slice). If one fails, stop (rule S1).
3. Write the code and tests exactly as specified.
4. Run the slice's one command. Fix and re-run until it passes.
5. Run the slice's self-probe: make the named deliberate break, run the command, confirm the named
   test fails, undo the break (edit it back, or `git checkout -- <file>` for a file committed before
   the slice), run the command again and confirm it passes.
6. Write the Validation Pack from the skeleton (§7), with the command output summary, the probe
   result and any implementer choices.
7. Apply the slice's documentation deltas.
8. Update the status record (slice board, history line with the previous slice's commit hash, next
   action).
9. Commit (§2.1).

**Stop rules.**
- **S1.** A precondition fails. Record it in the status record as a blocker and stop.
- **S2.** The same test still fails after three distinct fix attempts. Leave the slice uncommitted,
  record the failure output and the attempts in the status record, and stop.
- **S3.** Passing would need a change to a decision, an ADR, a contract fixed by an earlier slice, a
  path outside the slice's list, or a weaker test. Stop and ask.
- **S4.** A package or image cannot be fetched. Do not route around the network. Stop and hand over
  (see `.github/copilot-instructions.md`, "Restricted or mirrored package registries").

### 2.3 Namespaces and IRIs

| Prefix | IRI | Use |
|---|---|---|
| `wrd:` | `https://www.nebularis.org/neuro-semantic/lattice/wording#` | provisional, CCS sketch §4 names only |
| `ins:` | `https://www.nebularis.org/neuro-semantic/lattice/instrument#` | existing namespace. CCS §5 names used provisionally |
| `wap:` | `https://www.nebularis.org/neuro-semantic/lattice/poc/word-authoring#` | POC terms and shapes |
| `prov:` | `http://www.w3.org/ns/prov#` | |
| `dcterms:` | `http://purl.org/dc/terms/` | |
| `rdfs:`, `xsd:`, `sh:`, `skos:` | standard | |

Instance IRIs, with `B` the configured base (default `https://example.org/lattice/authoring/`,
always ending in `/`) and `D` = `B` + `doc/` + documentId:

| Node | IRI |
|---|---|
| wording | `D/wording` |
| section | `D/section/<sectionKey>` |
| element | `D/element/<elementId>` |
| text part | `D/element/<elementId>/part/<index>` |
| variable | `D/variable/<variableKey>` |
| wording graph of revision n | `D/rev/<n>/wording-graph` |
| proposal graph of revision n | `D/rev/<n>/proposal-graph` |
| analysis graph of revision n | `D/rev/<n>/analysis-graph` |
| revision record | `D/rev/<n>` |
| registry graph | `B` + `registry` |
| proposed relation | `D/element/<elementId>/meaning` |
| parameter binding | `D/element/<elementId>/meaning/binding/<slotName>` |
| proposed party role | `D/role/<definition elementId>` |
| analysis activity | `<proposal graph IRI>#activity` |

Every IRI is built only from the base, fixed path words, and values that passed the patterns in
§2.4. No title, text or label ever enters an IRI. No blank node is ever created.

### 2.4 Identifiers

| Name | Pattern |
|---|---|
| Uuid (documentId, elementId, jobId) | `^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$` |
| Key (templateId, variableKey, sampleId) | `^[a-z][a-z0-9-]{0,39}$` |
| SectionKey | `^[a-z][a-z0-9-]{0,31}$` |
| revision hash | `^sha256:[0-9a-f]{64}$` |
| timestamp | `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,9})?Z$` |

Sample k (1 = facility agreement, 2 = software licence, 3 = property policy) has documentId
`0000000k-0000-4000-8000-000000000000` and element ids `0000000k-0000-4000-8000-0000000000NN`, NN
counting from 01 in document order.

### 2.5 Text offsets

All offsets (`start`, `end` of detections and spans) are **UTF-16 code units** into the **element
text**, the concatenation of the element's parts' texts in index order (a literal's `text`, a
variable's or reference's displayed `text`). Java and TypeScript strings already count this way.
Python converts with `offsets.utf16_len()` (WA6). `end` is exclusive.

### 2.6 Gaps for CCS C3

The mapping (WA2) uses `wap:` where the CCS sketch §4 names no term. These go to C3 as input:
`wap:hasPart` (text to part), `wap:displayText` (shown text of a variable or reference part),
`wap:DefinitionText` and `wap:definedTerm` (a definition and its term), `wap:valueType` (instead of
`wrd:valueContract`), `wap:sectionKey`, `wap:elementId`, `wap:plainText`.

### 2.7 Pinned versions

| Component | Version |
|---|---|
| Java, Maven | 25, 3.9 (mise) |
| Apache Jena (`jena-arq`, `jena-shacl`, `jena-rdfconnection`) | `${jena.version}` = 5.1.0 |
| Jackson databind | 2.18.2 |
| networknt json-schema-validator | 1.5.6 |
| RabbitMQ amqp-client | 5.22.0 (as `platform-outbox`) |
| slf4j-simple | 2.0.16 |
| Javalin (`io.javalin:javalin`) | 6.7.0, or the latest 6.x that P3 resolves (record it) |
| Testcontainers (core only) | 2.0.2. Fallback 1.21.4 if P3 cannot resolve 2.0.2 (record it) |
| maven-shade-plugin, maven-failsafe-plugin | 3.6.0, 3.5.0 |
| Python | 3.14 (mise) |
| pika, rdflib, jsonschema, pytest | `>=1.3,<2`, `>=7.1,<8`, `>=4.23,<5`, `>=8,<9` |
| React, Vite, TypeScript, Playwright | as `apps/surface-contract-studio`: 19.0.0, 6.0.5, 5.7.3, 1.50.1 |
| Vitest, jsdom, ajv, mermaid, @types/office-js | 3.0.x, 25.0.x, 8.17.x, 11.4.x, latest 1.0.x. Exact versions as resolved in WA8, pinned without ranges |
| images | `stain/jena-fuseki:5.1.0`, `rabbitmq:3.13-management-alpine`, `eclipse-temurin:25-jre`, `python:3.14-slim`, `caddy:2.10-alpine` |

---

## 3. Decisions

None of these may be taken by the agent. All were recorded by the human on 2026-10-01.

| # | Decision | Options | Recommendation | State |
|---|---|---|---|---|
| WA-D1 | Delivery | (a) Office web add-in, XML manifest, sideloaded, served from the stack over HTTPS. (b) VSTO or COM add-in. (c) Teams unified manifest | (a), the only one with no installation | **decided 2026-10-01: (a)** |
| WA-D2 | Markup in the document | (a) content controls with short tags, plus one custom XML part. (b) bookmarks. (c) hidden text markers | (a): visible, nestable, survives editing, readable from OOXML | **decided 2026-10-01: (a)** |
| WA-D3 | Vocabulary | (a) the CCS sketch's `wrd:` IRIs in a provisional resource outside `ontology/`, plus `wap:`. (b) wait for CCS C3 | (a): no ontology change, and the gaps feed C3 (§2.6) | **decided 2026-10-01: (a)** |
| WA-D4 | Java HTTP | (a) the JDK's `com.sun.net.httpserver` behind a framework-neutral API class, as `SurfaceRevisionApi`. (b) Javalin. (c) Spring Boot | (a): no framework imposed, few dependencies, the repository's existing pattern | **decided 2026-10-01: (b) Javalin**, behind the framework-neutral `AuthoringApi` (WA4) |
| WA-D5 | Store | (a) Fuseki over the Graph Store Protocol, with an in-memory test double. (b) embedded TDB2 in the service | (a): Fuseki is already in compose, and the worker reads graphs by reference | **decided 2026-10-01: (a)** |
| WA-D6 | Work split | (a) Java: mapping, SHACL, detection, template checks. Python job: LE reading, LE program, proposal graph. (b) detection in Python too. (c) detection in the add-in | (a): immediate structural feedback, linguistic work as a job | **decided 2026-10-01: (a)** |
| WA-D7 | Where highlighting shows | (a) task pane only, with control colours in the document. (b) also character highlighting in the document | (a): the document stays an ordinary contract | **decided 2026-10-01: (a)** |
| WA-D8 | Sentence forms | (a) a POC rendering profile in the worker, "shall" as fixed words (LE-Q2, LE-Q3 first thoughts). (b) forms in the T-Box | (a), local to the POC | **decided 2026-10-01: (a)** |
| WA-D9 | Sample domains | (a) facility agreement, software licence, property policy. (b) the two neutral ones only | (a): the insurance policy is where section term kinds are most familiar. ADR-A-C2 binds substrate text, not a POC | **decided 2026-10-01: (a)** |
| WA-D10 | Job state | (a) jobs in memory, analyses stored in Fuseki. (b) Postgres | (a): a restart loses only in-flight jobs | **decided 2026-10-01: (a)** |
| WA-D11 | Branch and commits | `ux/auth-le`, one local commit per slice, no push (§2.1) | as stated | **decided 2026-10-01: as stated** |
| WA-D12 | Graph drawing | (a) Mermaid, strict security level. (b) a hand-written SVG layout | (a): already the repository's diagram language | **decided 2026-10-01: (a)** |
| WA-D13 | How ribbon and right-click commands run (WA9a) | (a) a shared runtime: commands and task pane share one JavaScript context, so a command can open the pane with a form filled in. (b) a separate function file: commands cannot talk to the pane, so commands needing input only open the pane | (a). Where a Word build lacks the shared runtime, it ignores the ribbon and menu entries and the task pane still opens from the Add-ins list (R8) | **decided 2026-10-01: (a)** |

### Decisions for the follow-on tranche (sketch §8)

None of these may be taken by the agent. Recorded here 2026-10-02 as proposals, none decided.
WA12 to WA20 (§4, §5) may not start until the decisions they depend on are recorded.

| # | Decision | Options | Recommendation | State |
|---|---|---|---|---|
| WA-D14 | Web app stack | (a) React, Vite and TypeScript, matching the existing `apps/*` workspaces (`surface-contract-studio`, `mork-review-workbench`, `word-authoring-addin`): same Vitest/Playwright conventions, same `mise` task shape. (b) a different frontend stack | (a): no new tooling pattern to learn or maintain | proposed 2026-10-02, awaiting decision |
| WA-D15 | Web app workspace and code sharing | (a) a new workspace `apps/word-authoring-webapp`, sharing the add-in's domain modules (the tag codec, offsets, schema validation, snapshot types, API client) through a new package the two apps both depend on. (b) the same new workspace, but duplicating those modules instead of sharing them | (a): the two clients cannot silently diverge on what a valid document looks like, since they run the same code | proposed 2026-10-02, awaiting decision |
| WA-D16 | Nested element representation | (a) a recursive `children: Element[]` field on `Element`, the same shape at every depth. (b) a flat element list per section with an explicit `parentElementId` | (a): matches OOXML's own nested `w:sdt` shape, needs no separate tree-rebuild step in either client | proposed 2026-10-02, awaiting decision |
| WA-D17 | Nesting rules | (a) a clause may contain clauses as children, to a fixed maximum depth of 4. A definition is always a leaf. A section's direct children stay clauses and definitions only, as today | (a), the only option drafted (sketch §8.2) | proposed 2026-10-02, awaiting decision |
| WA-D18 | Versioning treatment | (a) a read-only revision list and picker: view an older revision's text and markup, no diff, no restore. (b) full diffing between two chosen revisions | (a): matches "some treatment", bounded scope for a POC | proposed 2026-10-02, awaiting decision |
| WA-D19 | Library wordings | (a) a static, read-only seed catalogue, `contracts/authoring/library/*.json`, of reusable clauses and definitions, searchable and insertable in both clients. Saving a drafter's own text into the library is out of scope. (b) a persisted, drafter-editable library stored in Fuseki | (a): no new storage concern, and matches the attached tool's library search without its save-back behaviour | proposed 2026-10-02, awaiting decision |
| WA-D20 | Theming | (a) CSS custom properties switched by one `data-theme` attribute and a header toggle, light by default, no new dependency. (b) a component or theming library | (a): consistent with the hand-rolled CSS already in `apps/word-authoring-addin` | proposed 2026-10-02, awaiting decision |

---

## 4. Slice overview

| Slice | Title | Paths | Levels | One command | Estimate (tokens) |
|---|---|---|---|---|---|
| WA0 | Preflight | status record only | L0 | the preflight script (§5 WA0) | 60k |
| WA1 | Contracts, templates and samples | `contracts/`, `workers/` (tests, pyproject), `mise.toml` | L1, L3 | `mise run check:authoring-contracts` | 300k |
| WA2 | Service model, mapping and shapes | `platform/authoring-service`, `platform/pom.xml`, `contracts/authoring/fixtures/wording` | L1, L2, L3 | `mise run check:authoring-service` | 450k |
| WA3 | Detection, templates and conformance | `platform/authoring-service` | L1 | `mise run check:authoring-service` | 300k |
| WA4 | API and HTTP adapter | `platform/authoring-service` | L1, L3 | `mise run check:authoring-service` | 450k |
| WA5 | Fuseki, RabbitMQ and the runnable service | `platform/authoring-service` | L1, L4 | `mise run check:authoring-service-it` | 350k |
| WA6 | Logical English reading | `workers/` | L1, L2, L3 | `mise run check:authoring-worker` | 450k |
| WA7 | Worker runtime | `workers/` | L1, L3 | `mise run check:authoring-worker` | 200k |
| WA8 | Add-in domain | `apps/word-authoring-addin` | L1, L2, L3 | `mise run check:authoring-addin` | 450k |
| WA9 | Add-in task pane and harness | `apps/word-authoring-addin` | L1, L6 | `mise run test:authoring-addin` | 550k |
| WA9a | Ribbon and right-click commands | `apps/word-authoring-addin` | L1, L3, L6 | `mise run test:authoring-addin` | 250k |
| WA10 | Compose stack | `deployment/compose/authoring`, `tools/`, `mise.toml`, add-in stack tests | L0, L5, L6 | `mise run check:authoring-stack` | 400k |
| WA11 | Documentation and close-out | docs only | paper, manual L6 | `mise run check:authoring` and the WA11 checks | 150k |

Total about 4.35M tokens for WA0 to WA11. Record the actual per slice in the status record.

```mermaid
flowchart LR
    WA0 --> WA1 --> WA2 --> WA3 --> WA4 --> WA5
    WA1 --> WA6 --> WA7
    WA1 --> WA8 --> WA9 --> WA9a
    WA5 & WA7 & WA9a --> WA10 --> WA11
```

Run them in numeric order. WA8 and WA9 need the frontend precondition P5. If P5 fails, finish WA1
to WA7 and stop (S1).

### Follow-on tranche: WA12 to WA20 (not started, sketch §8)

| Slice | Title | Paths | Levels | One command | Estimate (tokens) |
|---|---|---|---|---|---|
| WA12 | Nested clause data model | `contracts/authoring`, `platform/authoring-service`, `workers/`, `apps/word-authoring-addin` (parser, writer, fake port only) | L1, L2, L3 | `mise run check:authoring` | 550k |
| WA13 | Service read APIs for the web app | `platform/authoring-service`, `contracts/authoring` | L1, L3 | `mise run check:authoring-service` | 250k |
| WA14 | Web app shell, library and document list | `apps/word-authoring-webapp` (new), `packages/authoring-domain` (new, if WA-D15 (a)) | L1, L2, L6 | `mise run test:authoring-webapp` | 500k |
| WA15 | Web app text editor and markup panes | `apps/word-authoring-webapp` | L1, L6 | `mise run test:authoring-webapp` | 650k |
| WA16 | Web app versioning, library wordings and theming | `apps/word-authoring-webapp`, `contracts/authoring/library` (new) | L1, L6 | `mise run test:authoring-webapp` | 400k |
| WA17 | Word add-in parity | `apps/word-authoring-addin` | L1, L3, L6 | `mise run test:authoring-addin` | 350k |
| WA18 | Compose stack and cross-client integration | `deployment/compose/authoring`, `apps/word-authoring-webapp` (e2e only) | L0, L5, L6 | `mise run check:authoring-stack` | 300k |
| WA19 | Documentation and close-out (tranche 2) | docs only | paper, manual L6 | `mise run check:authoring` and the WA19 checks | 150k |
| WA20 | Binding authority agreement sample (**deferred on CCS**) | `contracts/authoring/**` | L1, L3 | `mise run check:authoring-contracts` | 350k (provisional) |

Total about 3.15M tokens for WA12 to WA19 (excluding WA20, deferred and re-estimated when
scheduled). Combined with WA0 to WA11, the unit totals about 7.5M tokens if both tranches run.

```mermaid
flowchart LR
    WA11 --> WA12 --> WA13
    WA12 --> WA14 --> WA15 --> WA16
    WA13 --> WA15
    WA12 & WA16 --> WA17
    WA17 --> WA18 --> WA19
    WA12 -.deferred.-> WA20
```

Run WA12 to WA19 in numeric order once their decisions (WA-D14 to WA-D20) are recorded. WA20 has no
place in that order: it starts only when the CCS workstream completes, independent of WA12 to WA19
having finished.

---

## 5. Slices


### WA0: Preflight

**Preconditions:** none.

Run each check and record the result as a table in the status record. Write a temporary script
under `.build/` if useful and delete it after. Do not install anything.

| # | Check | Command | Pass |
|---|---|---|---|
| P1 | clean tree on the branch, commit identity set | `git status --short`, `git branch --show-current`, `git config user.name`, `git config user.email` | empty, `ux/auth-le`, both non-empty |
| P2 | Java baseline | `mise run check:java` | BUILD SUCCESS |
| P3 | new Maven artefacts resolve | `mise exec -- mvn -q dependency:get -Dartifact=<g:a:v>` for each Java artefact of §2.7 not already used | each exits 0 |
| P4 | Python packages resolve through the mirror | `python -m pip download --no-deps -d .build/preflight "rdflib>=7.1,<8" "pika>=1.3,<2" "jsonschema>=4.23,<5"` and `python -m pip download --only-binary=:all: --platform any --python-version 3.14 --implementation py --abi none -d .build/preflight/linux "rdflib>=7.1,<8" "pika>=1.3,<2"` | both exit 0 |
| P5 | Node, Yarn and the npm registry | `$env:NODE_EXTRA_CA_CERTS` is set, `yarn --version` prints 4.6.0 without a prompt (run with `$env:COREPACK_ENABLE_DOWNLOAD_PROMPT = "0"`), `yarn npm info vitest --fields version` prints a version | all three |
| P6 | Docker | `docker info --format "{{.OSType}}"` prints `linux`, `docker version --format "{{.Server.APIVersion}}"` is 1.44 or higher, and `docker pull` succeeds for each image of §2.7 | all |
| P7 | Playwright browser | Microsoft Edge is installed (`Test-Path "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"`). Playwright uses `channel: "msedge"`, so no browser download is needed | True |

P5 runs with the prompt disabled because a corepack download prompt otherwise blocks the terminal.
Delete `.build/preflight` after P4.

**Output:** the status record's preflight table. No commit unless the status record changed, then
`[wap] WA0: preflight`.

---

### WA1: Contracts, templates and samples

**Preconditions:** P1, P4.

**Paths:** `contracts/authoring/**`, `contracts/events/wording-analysis-request.schema.json`,
`contracts/events/wording-analysis-result.schema.json`,
`contracts/openapi/authoring-service.openapi.json`, `workers/pyproject.toml`,
`workers/tests/test_authoring_contracts.py`, `mise.toml`, `README.md`, `REUSE.toml` if JSON
licensing needs a new path entry.

#### Schema rules (all schemas)

1. Draft 2020-12, `"$schema": "https://json-schema.org/draft/2020-12/schema"`.
2. `$id` = `https://schemas.nebularis.org/lattice/authoring/<name>/0.1.0` for files in
   `contracts/authoring`, `https://schemas.nebularis.org/lattice/events/<name>/0.1.0` for events,
   `<name>` the file name without `.schema.json`.
3. Every object has `"additionalProperties": false` and lists **every** property in `required`. A
   value that may be absent is `null`, typed `["string", "null"]` or with `oneOf` and
   `{"type": "null"}`. Producers always write every property.
4. No `format` keyword. Use the `pattern`s of §2.4.
5. Shared definitions live in `common.schema.json` under `$defs`. Other files reference them by
   absolute `$id` plus pointer, for example
   `"$ref": "https://schemas.nebularis.org/lattice/authoring/common/0.1.0#/$defs/Uuid"`. Every
   runtime preloads all schema files into its registry by `$id` and never fetches over the network.

#### `common.schema.json` `$defs`

| Def | Shape |
|---|---|
| `Uuid`, `Key`, `SectionKey`, `RevisionHash`, `Timestamp` | strings with the §2.4 patterns |
| `ValueType` | enum `money`, `percentage`, `date`, `duration`, `number`, `text`, `party` |
| `TermKind` | enum `Obligation`, `Prohibition`, `Permission`, `Exclusion`, `Power`, `Definition`, `Deeming` |
| `ElementKind` | enum `clause`, `definition` |
| `Severity` | enum `violation`, `warning`, `info` |
| `GraphRef` | `tenantId` (const `poc`), `projectId` (const `word-authoring`), `graphIri` (string 1..500), `revisionHash` |
| `VariableDeclaration` | `variableKey` Key, `label` (1..100), `valueType` |
| `ValidationResult` | `shapeId` (`^WS[0-9]{1,2}$`), `severity`, `focusNode` (string 1..500), `elementId` (Uuid or null), `message` (string) |
| `ValidationReport` | `conforms` (boolean), `results` (array of ValidationResult, max 1000) |
| `Suggestion` | `action` (enum `mark-variable`, `mark-reference`, `none`), `valueType` (or null), `suggestedKey` (Key or null), `targetElementId` (Uuid or null) |
| `Detection` | `elementId`, `partIndex` (integer ≥ 0), `start` (integer ≥ 0), `end` (integer ≥ 1), `text` (1..200), `kind` (enum `placeholder`, `money`, `percentage`, `date`, `duration`, `defined-term`, `cross-reference`), `suggestion` |
| `Finding` | `kind` (enum `unknown-section`, `required-section-empty`, `element-kind-not-allowed`, `unmarked-text`, `term-kind-not-allowed`, `no-term-kind`), `severity`, `sectionKey` (or null), `elementId` (or null), `message` |
| `Span` | `start`, `end`, `role` (enum `fixed`, `ignorable`, `slot-variable`, `slot-constant`, `slot-text`, `modal`, `connective`, `unmatched`), `partIndex` |
| `ElementAnalysis` | `elementId`, `objectId` (string), `sectionKey`, `kind` (ElementKind), `text`, `relationClass` (TermKind or null), `basis` (enum `form`, `keyword`, `none`), `formId` (string or null), `leTemplate` (string or null), `leSentence` (string or null), `spans` (array of Span) |
| `GraphNode` | `id` (string), `label` (string), `kind` (enum `relation`, `element`, `role`, `variable`) |
| `GraphEdge` | `from`, `to`, `label` (strings) |
| `GraphView` | `nodes`, `edges` |
| `FormsProfile` | `profileId` (string), `version` (string) |
| `Analysis` | `formsProfile`, `elements` (array of ElementAnalysis), `leProgram` (string), `graphView` |
| `JobStatus` | enum `queued`, `completed`, `failed` |
| `Job` | `jobId`, `status` |
| `TemplateSummary` | `templateId`, `title`, `domain`, `version` |
| `SampleSummary` | `sampleId` (Key), `title`, `templateId` |

#### Message schemas

| File | Top level |
|---|---|
| `document-snapshot` | `schemaVersion` (const `0.1.0`), `documentId`, `templateId` (Key), `title` (1..200), `sections` (≤ 50 Section), `variables` (≤ 200 VariableDeclaration), `unmarked` (≤ 500 Unmarked). Section: `sectionKey`, `elements` (≤ 200 Element). Element: `elementId`, `kind`, `definedTerm` (1..100 or null), `parts` (**1**..400 Part). `if kind = definition then definedTerm is a string, else null`. Part `oneOf`: literal `{kind: "literal", text: 1..10000}`, variable `{kind: "variable", variableKey: Key, text: 0..1000, pattern ^[^\n\r]*$}`, reference `{kind: "reference", targetElementId: Uuid, text: 1..200, pattern ^[^\n\r]*$}`. Unmarked: `sectionKey` (or null), `text` (1..10000) |
| `snapshot-submission` | `baseRevision` (integer ≥ 1 or null), `snapshot` (document-snapshot) |
| `snapshot-accepted` | `documentId`, `revision` (≥ 1), `wordingGraph` (GraphRef), `validation` (ValidationReport), `detections` (≤ 2000), `templateFindings` (array of Finding), `job` (Job) |
| `authoring-template` | `templateId`, `version` (`^\d+\.\d+\.\d+$`), `title`, `domain` (Key), `sections` (1..30 TemplateSection), `variables`. TemplateSection: `sectionKey`, `heading` (1..100), `elementKinds` (1..2, unique), `allowedTermKinds` (0..7, unique), `required` (boolean), `guidance` (0..1000) |
| `template-list` | array of TemplateSummary |
| `sample-list` | array of SampleSummary |
| `document-view` | `documentId`, `title`, `templateId`, `latestRevision` (≥ 1) |
| `job-view` | `jobId`, `documentId`, `revision`, `status`, `error` (string or null) |
| `analysis-view` | `documentId`, `revision`, `analysis` (Analysis), `conformance` (array of Finding), `proposalGraph` (GraphRef) |
| `health` | `status` (enum `ok`, `degraded`), `fuseki` (enum `up`, `down`), `amqp` (enum `up`, `down`) |
| `error` | `error` (string 1..1000), `details` (≤ 20 strings) |
| events `wording-analysis-request` | `jobId`, `correlationId` (1..100), `documentId`, `revision`, `wordingGraph` (GraphRef), `wordingIri` (1..500), `proposalGraphIri` (1..500), `requestedAt` (Timestamp) |
| events `wording-analysis-result` | `jobId`, `correlationId`, `documentId`, `revision`, `status` (enum `completed`, `failed`), `error` (string or null), `proposalGraph` (GraphRef or null), `analysis` (Analysis or null), `completedAt`. `if status = completed then error null, proposalGraph and analysis non-null. If failed then error string, the other two null` |

#### Other contract files

- `contracts/authoring/amqp-topology.json`, data read by both runtimes' tests (WA5, WA7):

  ```json
  {
    "exchange": "lattice.authoring",
    "deadLetterExchange": "lattice.authoring.dlx",
    "queues": [
      {"name": "lattice.authoring.analysis.requested", "routingKey": "lattice.authoring.analysis.requested", "deadLetter": true},
      {"name": "lattice.authoring.analysis.completed", "routingKey": "lattice.authoring.analysis.completed", "deadLetter": true},
      {"name": "lattice.authoring.dead", "routingKey": "#", "deadLetter": false}
    ]
  }
  ```

  Both exchanges are durable topic exchanges. Queues are durable. A `deadLetter: true` queue has the
  single argument `x-dead-letter-exchange = lattice.authoring.dlx` and is bound to
  `lattice.authoring`. `lattice.authoring.dead` has no arguments and is bound to the dead-letter
  exchange. Identical arguments on both sides avoid `PRECONDITION_FAILED`.
- `contracts/openapi/authoring-service.openapi.json`, OpenAPI 3.1.0, one operation per route of
  WA4's table, request and response bodies by `$ref` to the schema `$id`s, `text/turtle` for the
  graph route.
- `contracts/authoring/templates/<templateId>.json` for `facility-agreement`, `software-licence`,
  `property-policy`, with sections, admitted term kinds and variables as the sketch §3.2 table.
  Element kinds: `definitions` sections `["definition"]`, all others `["clause"]`. Every section is
  `required: true` except Events of Default, Warranty Exclusions and Claims. Guidance is one or two
  plain sentences per section.
- `contracts/authoring/samples/<templateId>.json`, one document snapshot per template, sample ids as
  template ids. Content below.
- `contracts/authoring/fixtures/valid/<schema>--<case>.json` and `.../invalid/<schema>--<case>.json`.
  At least one valid fixture per schema. Invalid fixtures, at least:
  `document-snapshot--zero-parts`, `--definition-without-term`, `--clause-with-term`, `--bad-uuid`,
  `--extra-property`, `--variable-text-newline`, `--key-uppercase`, `--missing-unmarked`,
  `snapshot-submission--revision-zero`, `authoring-template--no-sections`,
  `wording-analysis-result--completed-without-analysis`, `wording-analysis-result--failed-with-analysis`.
- `contracts/authoring/fixtures/suggested-keys.json`, cases shared by the Java detector (S3-02) and
  the add-in's commands (S9a-06): an array of `{ "text", "valueType", "suggestedKey" }`, at least
  `[Agent]` (text, `agent`), `GBP 250` (money, `gbp-250`), `2.5 per cent` (percentage,
  `percentage-2-5-per-cent`), `1 March 2027` (date, `date-1-march-2027`), `120 days` (duration,
  `duration-120-days`), `sixty (60) days` (duration, `sixty-60-days`) and `Facility Agent` (text,
  `facility-agent`). The value type is the one detection (or `guessValueType`) assigns.

#### Sample 1: facility agreement (exact text)

Variables: `facility-amount` (money, "Facility amount"), `margin` (percentage, "Margin"),
`notice-period` (duration, "Notice period"), `repayment-period` (duration, "Repayment period").
In the parts, `[R:Term]` is a reference part to that definition with text `Term`, `[V:key|text]` a
variable part, and everything else literal.

| Section | NN | Kind | Parts |
|---|---|---|---|
| definitions | 01 | definition, term `Borrower` | `“Borrower” means the company named as borrower in the schedule.` |
| | 02 | definition, `Lender` | `“Lender” means each bank listed in Part 1 of the schedule.` |
| | 03 | definition, `Loan` | `“Loan” means a loan made or to be made under the Facility.` |
| | 04 | definition, `Facility` | `“Facility” means the term loan facility made available under this Agreement.` |
| | 05 | definition, `Repayment Date` | `“Repayment Date” means the date falling ` [V:repayment-period\|five years] ` after the date of this Agreement.` |
| commitment | 06 | clause | [R:Lender] ` shall make available to ` [R:Borrower] ` a term loan facility in an aggregate amount equal to ` [V:facility-amount\|GBP 10,000,000] `.` |
| | 07 | clause | [R:Borrower] ` may cancel the whole or any part of the ` [R:Facility] ` on not less than ` [V:notice-period\|five Business Days'] ` prior notice.` |
| interest | 08 | clause | [R:Borrower] ` shall pay interest on each ` [R:Loan] ` at ` [V:margin\|2.5 per cent] ` per annum.` |
| | 09 | clause | `Interest shall be calculated on the basis of a 365 day year.` |
| repayment | 10 | clause | [R:Borrower] ` shall repay each ` [R:Loan] ` in full on the ` [R:Repayment Date] `.` |
| | 11 | clause | [R:Borrower] ` shall pay a prepayment fee of GBP 250 for each prepayment.` |
| undertakings | 12 | clause | [R:Borrower] ` shall not create any security over its assets.` |
| | 13 | clause | [R:Borrower] ` shall supply its annual financial statements to the [Agent] within 120 days of each financial year end.` |
| events-of-default | 14 | clause | `If ` [R:Borrower] ` does not pay any sum due under this Agreement, ` [R:Lender] ` may declare all Loans immediately due.` |
| | 15 | clause | `A Loan shall be deemed due on the date a demand is made.` |

`unmarked`: empty. Demo features: placeholder `[Agent]`, money `GBP 250`, duration `120 days`,
defined term `Loan` unmarked in 15 and `Loans` in 14, keyword-only clauses 09 and 15, a conditional
power in 14.

#### Samples 2 and 3 (content rules)

Write them to satisfy these rules, in the same style:

- **Software licence.** Definitions `Licensor`, `Licensee`, `Software`, `Documentation`.
  Variables `licence-fee` (money), `payment-days` (duration), `user-limit` (number). Grant holds
  `Licensee may use the Software for its internal business purposes.`,
  `Licensee may permit up to [V:user-limit] users to access the Software.` and the deliberate
  misplacement `Licensee shall not sublicense the Software.` Restrictions holds
  `Licensee shall not reverse engineer the Software.` Fees holds
  `Licensee shall pay the [V:licence-fee] annually in advance.`,
  `Licensee shall pay each invoice within [V:payment-days].` and one unmarked entry
  `Fees are exclusive of VAT.` Warranty Exclusions holds
  `Licensor is not liable for any loss of profits.` Termination holds
  `Licensor may terminate this Agreement if Licensee fails to pay any fee.` Parties and the
  Software are reference parts wherever named.
- **Property policy.** Definitions `Insurer`, `Insured`, `Premises`, `Damage`. Variables
  `sum-insured` (money), `excess` (money), `notification-days` (duration), `period-start` (date,
  declared and **never referenced**). Insuring Clause:
  `Insurer shall indemnify Insured against Damage to the Premises up to the [V:sum-insured].`
  Exclusions: `This policy does not cover Damage caused by wear and tear.` and
  `Insurer is not liable for the [V:excess] of each claim.` Conditions:
  `Insured shall take reasonable precautions to prevent Damage.` and
  `Insured shall not leave the Premises unoccupied for more than 30 days.` Claims:
  `Insured shall notify Insurer of any Damage within [V:notification-days].` and
  `A claim is deemed notified on the date Insurer receives written notice.`

#### Python setup

`workers/pyproject.toml`: add `"jsonschema>=4.23,<5"` to the `test` extra and a new extra
`authoring = ["rdflib>=7.1,<8"]`. `mise.toml`: `bootstrap:workers` becomes
`python -m pip install -e "./workers[test,authoring]"` (double quotes, see the toolchain rules),
and add:

```toml
[tasks."check:authoring-contracts"]
description = "Validate the word authoring POC contracts, templates, samples and fixtures"
run = "python -m pytest workers/tests/test_authoring_contracts.py -q"
```

Run `mise run bootstrap:workers` once before the slice command.

`test_authoring_contracts.py` loads every `*.schema.json` under `contracts/authoring` and the two
event schemas into a `referencing.Registry` keyed by `$id`, and validates with
`jsonschema.Draft202012Validator(schema, registry=registry)`. Repository paths come from
`Path(__file__).resolve().parents[2]`.

#### Tests

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AC-01 | every schema file / loaded / has the 2020-12 `$schema` and an `$id` of rule 2 | L1 | + |
| AC-02 | every object subschema, found recursively / inspected / has `additionalProperties: false` and `required` equal to its property names | L1 | + |
| AC-03 | every schema / scanned / contains no `format` keyword | L1 | + |
| AC-04 | every `$ref` in the schemas and the OpenAPI file / resolved in the registry / resolves, including its JSON pointer | L3 | + |
| AC-05 | each valid fixture / validated against the schema named by its prefix / passes | L3 | + |
| AC-06 | each invalid fixture / validated / fails | L3 | - |
| AC-07 | a snapshot whose element has zero parts, and a definition whose term is null / validated / both fail (zero cases) | L3 | - |
| AC-08 | each template / validated / passes, section keys and variable keys unique within it | L3 | + |
| AC-09 | each sample / validated and cross-checked / passes the schema, names an existing template, uses only that template's section keys, every reference targets a definition in the same sample, every definition's term occurs in one of its literal parts, documentIds follow §2.4 | L3 | + |
| AC-10 | the OpenAPI file / parsed / version `3.1.0` and exactly the routes and methods of WA4's table | L3 | + |
| AC-11 | the three samples / scanned / together contain each demo feature: a bracket placeholder, an unmarked money amount, an unmarked duration, an unreferenced variable, an unmarked entry, a clause with `shall not` in a section admitting only Permission | L1 | + |

**Self-probe:** remove `"additionalProperties": false` from the Part literal definition. AC-02
fails.

**Docs:** root `README.md` repository layout gains `contracts/authoring/  # Word authoring POC
contracts, templates and samples (ADR-A118)`.

---

### WA2: Service model, mapping and shapes

**Preconditions:** P2, P3, WA1 committed.

**Paths:** `platform/pom.xml` (module entry), `platform/authoring-service/**`,
`contracts/authoring/fixtures/wording/*.nt`, `mise.toml`, `README.md`,
`docs/architecture/data-architecture.md`.

#### Module

`platform/pom.xml` gains `<module>authoring-service</module>` after `reasoning-testkit`.
`platform/authoring-service/pom.xml`:

- parent `lattice-platform`, artifactId `authoring-service`
- dependencies: `org.apache.jena:jena-arq`, `jena-shacl`, `jena-rdfconnection` at `${jena.version}`.
  `com.fasterxml.jackson.core:jackson-databind`, `com.networknt:json-schema-validator`,
  `com.rabbitmq:amqp-client`, `org.slf4j:slf4j-simple` (scope runtime) at §2.7 versions.
  `org.junit.jupiter:junit-jupiter` (test). `org.testcontainers:testcontainers` (test, added in WA5)
- `<build><finalName>authoring-service</finalName>`
- resources: `src/main/resources`, plus `${project.basedir}/../../contracts` with targetPath
  `contracts`, includes `authoring/**/*.json` and `events/wording-analysis-*.schema.json`, excludes
  `authoring/fixtures/**`
- `maven-shade-plugin` 3.6.0 at `package`: `ServicesResourceTransformer` (Jena registers its
  subsystems through `META-INF/services`, so without it Jena fails to initialise in the jar),
  `ManifestResourceTransformer` with mainClass
  `org.nebularis.lattice.authoring.app.AuthoringServiceMain`, filter excluding `META-INF/*.SF`,
  `*.DSA`, `*.RSA`, `createDependencyReducedPom` false

Tests read repository files through a test helper `RepoPaths.contracts()` =
`Path.of(System.getProperty("user.dir")).resolve("../../contracts").normalize()` (Surefire runs
with the module directory as working directory).

#### Packages and classes (`org.nebularis.lattice.authoring`)

| Class | Responsibility |
|---|---|
| `json.Json` | one shared `ObjectMapper`: fail on unknown properties, `ALWAYS` inclusion, no default typing |
| `json.ContractSchemas` | loads the schema files named in a constant list from the classpath `contracts/...`, builds one networknt `JsonSchemaFactory` (V202012) whose schema loader maps each `$id` to its content (`schemaLoaders(l -> l.schemas(map))`). `List<String> validate(String schemaName, JsonNode node)` returns at most 20 messages, empty when valid |
| `model.*` records | `DocumentSnapshot(schemaVersion, documentId, templateId, title, List<Section> sections, List<VariableDeclaration> variables, List<Unmarked> unmarked)`, `Section(sectionKey, elements)`, `Element(elementId, ElementKind kind, String definedTerm, List<Part> parts)`, sealed `Part` permits `LiteralPart(text)`, `VariablePart(variableKey, text)`, `ReferencePart(targetElementId, text)`, each with `String displayText()`. `VariableDeclaration(variableKey, label, valueType)`, `Unmarked(sectionKey, text)`, enums `ElementKind`, `ValueType`, `TermKind`, `Severity` |
| `model.SnapshotReader` | `DocumentSnapshot read(JsonNode)` by hand from an already validated node, switching on `kind`. No Jackson polymorphism |
| `rdf.Vocab` | every IRI of §2.3 and every `wrd:`, `ins:`, `wap:` term used, as `Resource` and `Property` constants. The only place these IRIs are written in Java |
| `rdf.IriMinter` | the §2.3 IRI table as methods, constructed with the base IRI. Each method checks its argument against the §2.4 pattern and throws `IllegalArgumentException` otherwise |
| `rdf.WordingMapper` | `Model map(DocumentSnapshot snapshot, int revision)`, rules below |
| `rdf.CanonicalHash` | `String of(Model)`: N-Triples lines, sorted by `String.compareTo`, joined with `\n` plus a final `\n`, UTF-8, SHA-256, lower-case hex, prefixed `sha256:`. Throws if the model contains a blank node |
| `validation.WordingValidator` | loads `shapes/wording-poc-shapes.ttl` once, `ValidationReportView validate(Model)` with Jena `ShaclValidator.get().validate(shapes, model.getGraph())`. Each entry becomes a `ValidationResult`: `shapeId` from the source shape IRI by regex `shape-(WS\d{1,2})` (fallback `WS0`), severity lower-cased, focus node IRI, `elementId` by regex `/element/([0-9a-f-]{36})` on the focus node or null, message |
| `app.FixtureWriter` | `main(String[] args)`, args[0] the `contracts/authoring` directory: maps each sample at revision 1 with the default base and writes `fixtures/wording/<sampleId>.nt` as the canonical sorted lines |

Also `src/main/resources/vocab/wording-provisional.ttl`: an `owl:Ontology`
`wap:provisional-vocabulary` declaring every `wrd:`, `ins:` and `wap:` class and property the POC
uses, each with `rdfs:label` and `rdfs:comment` naming its CCS sketch section or "POC gap (plan
§2.6)", and the concepts `wap:Section`, `wap:Clause`, `wap:Definition`, `wap:Money`,
`wap:Percentage`, `wap:Date`, `wap:Duration`, `wap:Number`, `wap:Text`, `wap:Party` as
`skos:Concept`s.

#### Mapping rules

For sections at index s (0-based, snapshot order), elements at index e within their section, parts
at index i, variables at index v:

| Subject | Triples |
|---|---|
| wording | `a wrd:Wording`, `dcterms:title`, `wap:documentId`, `wap:templateId`, `wap:revisionNumber` (xsd:integer), `wrd:directlyComprises` each section and each variable |
| section | `a wrd:Element`, `wrd:elementType wap:Section`, `wap:sectionKey`, `wrd:rankKey` `s` + 4-digit s, `wrd:objectId` `(s+1)`, `wrd:directlyComprises` each element |
| element | `a wrd:Text`, plus `a wap:DefinitionText` for definitions. `wrd:elementType wap:Clause` or `wap:Definition`, `wap:elementId`, `wrd:rankKey` `e` + 4-digit e, `wrd:objectId` `(s+1).(e+1)`, `wap:plainText` (the element text of §2.5), `wap:definedTerm` (definitions only), `wap:hasPart` each part |
| literal part | `a wrd:TextPart`, `wrd:partIndex` (xsd:integer), `wrd:partText` |
| variable part | `a wrd:TextPart`, `wrd:partIndex`, `wrd:refersToVariable` the variable IRI for its key (declared or not), `wap:displayText` |
| reference part | `a wrd:TextPart`, `wrd:partIndex`, `wrd:refersToObject` the element IRI for its target (present or not), `wap:displayText` |
| variable | `a wrd:EmbeddedVariable`, `wrd:variableKey`, `rdfs:label`, `wap:valueType` (`wap:` + capitalised value type), `wrd:rankKey` `v` + 4-digit v |

Only the asserted types above. No inferred super-types, no blank nodes. The object id is derived
from position on every mapping and is never used to build an IRI (law W7).

#### Shapes (`src/main/resources/shapes/wording-poc-shapes.ttl`)

Every node shape and property shape has an IRI `wap:shape-WS<n>` or `wap:shape-WS<n>-<suffix>` and
an `sh:message`. SPARQL constraints declare `PREFIX` lines inside `sh:select` and follow the
repository's SHACL-SPARQL rules (`.github/copilot-instructions.md`).

| Shape | Target | Constraint | Severity |
|---|---|---|---|
| WS1 | class `wrd:TextPart` | `wrd:partIndex` exactly 1, `xsd:integer`, `sh:minInclusive 0` | violation |
| WS2 | class `wrd:TextPart` | `sh:xone` of three forms: (`wrd:partText` 1..1, `wrd:refersToVariable` 0, `wrd:refersToObject` 0), (`wrd:refersToVariable` 1..1, `wrd:partText` 0, `wrd:refersToObject` 0), (`wrd:refersToObject` 1..1, `wrd:partText` 0, `wrd:refersToVariable` 0). Law W2 | violation |
| WS3 | class `wrd:Text` | SPARQL: part indices are 0..n−1 when n > 0. Sub-query anchored by `$this a wrd:Text`, counted pattern `OPTIONAL { $this wap:hasPart ?p . ?p wrd:partIndex ?i }`, computing `COUNT(?p)`, `COUNT(DISTINCT ?i)` and `MAX(?i)`, then `FILTER (?n > 0 && (?d != ?n \|\| ?m != ?n - 1))`. n = 0 is WS4's case | violation |
| WS4 | class `wrd:Text` | `wap:hasPart` min 1 | violation |
| WS5 | classes `wrd:Element`, `wrd:Text`, `wrd:EmbeddedVariable` | `[ sh:inversePath wrd:directlyComprises ]` exactly 1. Law W1 | violation |
| WS6 | subjects of `wrd:refersToVariable` | its value has `sh:class wrd:EmbeddedVariable` | violation |
| WS7 | subjects of `wrd:refersToObject` | its value has `sh:class wap:DefinitionText` | violation |
| WS8 | class `wap:DefinitionText` | `wap:definedTerm` exactly 1, `xsd:string`, `sh:minLength 1` | violation |
| WS9 | class `wap:DefinitionText` | SPARQL: another `wap:DefinitionText` with the same `wap:definedTerm` | violation |
| WS10 | class `wrd:EmbeddedVariable` | SPARQL, one count, flat: `$this a wrd:EmbeddedVariable . OPTIONAL { ?part wrd:refersToVariable $this }` `GROUP BY $this HAVING (COUNT(DISTINCT ?part) = 0)` | warning |
| WS11 | class `wrd:EmbeddedVariable` | `wrd:variableKey` exactly 1, pattern of Key | violation |

`conforms` is computed as "no result of severity violation", not taken from Jena's report, which is
false for any result. Expected for the samples: facility and licence have no result. The property
policy has exactly one, a WS10 warning on `period-start`, and `conforms` true.

#### `mise.toml`

```toml
[tasks."check:authoring-service"]
description = "Build and unit-test the word authoring POC service"
run = "mvn -f platform/pom.xml -pl authoring-service -am verify"

[tasks."build:authoring-fixtures"]
description = "Regenerate the POC's generated wording fixtures from the samples"
run = "mvn -q -f platform/pom.xml -pl authoring-service -am package -DskipTests && java -cp platform/authoring-service/target/authoring-service.jar org.nebularis.lattice.authoring.app.FixtureWriter contracts/authoring"
```

Run `mise run build:authoring-fixtures` once to create the `.nt` files, read them, then commit them
as goldens.

#### Tests

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| S2-01 | each sample / mapped at revision 1 / its sorted N-Triples equal `fixtures/wording/<sample>.nt` | L2 | + |
| S2-02 | a mapped sample / its triples added to a new model in reverse order / the canonical hash is unchanged | L2 | + |
| S2-03 | a sample with one literal character changed / mapped / the hash differs | L2 | + |
| S2-04 | an element inserted before element 2 of a section / mapped / its siblings' object ids shift and their IRIs do not (W7) | L1 | + |
| S2-05 | the facility sample / mapped / literal parts carry `wrd:partText` only, variable and reference parts carry their reference and `wap:displayText` and no `wrd:partText` | L1 | + |
| S2-06 | a snapshot whose title and texts contain `>`, `"`, `\n`, `{`, `#` / mapped / every IRI in the model starts with the base followed by `doc/<uuid>/` or with a vocabulary namespace, and the model has no blank node | L1 | - |
| S2-07 | `ContractSchemas` / each valid and invalid snapshot fixture / valid ones give no message, invalid ones at least one | L3 | +/- |
| S2-08 | each sample's graph / validated / facility and licence give no result, the policy exactly one WS10 warning on `period-start`, all three `conforms` | L1 | + |
| S2-09 | a part with both `wrd:partText` and `wrd:refersToVariable` / validated / one WS2 violation | L1 | - |
| S2-10 | a text with part indices {0, 0} and another with {0, 2} / validated / one WS3 violation each | L1 | - |
| S2-11 | a text with zero parts / validated / one WS4 violation, and no WS3 result (zero case) | L1 | - |
| S2-12 | an element with zero parents, and one with two / validated / one WS5 violation each (zero case) | L1 | - |
| S2-13 | a reference part to a clause, and one to an absent element / validated / one WS7 violation each | L1 | - |
| S2-14 | two definitions of `Loan` / validated / WS9 violations. A variable with zero references / WS10 at warning severity, `conforms` true (zero case) | L1 | - |
| S2-15 | `FixtureWriter` / run into a temporary directory / its files equal the committed fixtures | L2 | + |

**Self-probe:** in WS10 replace the `OPTIONAL { … }` with the bare pattern. S2-14's zero case fails
(the unreferenced variable produces no row).

**Docs:** root `README.md` layout gains `platform/authoring-service/  # Word authoring POC service
(ADR-A118)`. `docs/architecture/data-architecture.md` gains a short "Word authoring POC graphs"
section with the §2.3 graph table, stating that it is outside ADR-A54's layout by ADR-A118.
`platform/authoring-service/README.md` created: purpose, ADR, the commands, the provisional
vocabulary and the gaps of §2.6.

---

### WA3: Detection, templates and conformance

**Preconditions:** WA2 committed.

**Paths:** `platform/authoring-service/**`.

#### Classes

| Class | Responsibility |
|---|---|
| `detection.ConstructDetector` | `List<Detection> detect(DocumentSnapshot)`, rules below |
| `template.TemplateCatalog` | loads `contracts/authoring/templates/<id>.json` for the three ids in a constant list, validates each with `ContractSchemas` (`authoring-template`), throws `IllegalStateException` naming the file on failure. `List<TemplateSummary> list()`, `Optional<AuthoringTemplate> get(String id)`, `JsonNode raw(String id)` |
| `template.SampleCatalog` | the same for samples (`document-snapshot`), `List<SampleSummary> list()`, `Optional<JsonNode> raw(String id)`, `Optional<DocumentSnapshot> get(String id)` |
| `template.TemplateFindings` | `List<Finding> check(DocumentSnapshot, AuthoringTemplate)`, rules below |
| `template.ConformanceChecker` | `List<Finding> check(JsonNode analysis, AuthoringTemplate)`, rules below |
| records | `AuthoringTemplate`, `TemplateSection`, `TemplateSummary`, `SampleSummary`, `Detection`, `Suggestion`, `Finding` |

#### Detection rules

Scan **literal parts only**, of every element, in document order. For each part, find matches of
the patterns below in the part's text. Offsets are converted to element-text offsets (§2.5) by
adding the length of the preceding parts' display texts.

| Kind | Java pattern | Flags | Suggestion |
|---|---|---|---|
| placeholder | `\[[^\[\]\n]{1,60}\]\|\{[^{}\n]{1,60}\}\|«[^«»\n]{1,60}»\|_{3,}` | | mark-variable, `text` |
| money | `(?:GBP\|USD\|EUR\|£\|\$\|€)\s?\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?(?:\s?(?:million\|bn\|m)\b)?` | | mark-variable, `money` |
| percentage | `\d+(?:\.\d+)?\s?(?:%\|per cent\b\|percent\b)` | case-insensitive | mark-variable, `percentage` |
| date | `\b\d{1,2}(?:st\|nd\|rd\|th)?\s(?:January\|February\|March\|April\|May\|June\|July\|August\|September\|October\|November\|December)\s\d{4}\b\|\b\d{4}-\d{2}-\d{2}\b` | | mark-variable, `date` |
| duration | `\b(?:\d{1,4}\|one\|two\|three\|four\|five\|six\|seven\|eight\|nine\|ten\|eleven\|twelve\|fourteen\|fifteen\|twenty\|thirty\|sixty\|ninety)(?:\s\(\d{1,4}\))?\s(?:business\s\|calendar\s\|banking\s)?(?:days?\|weeks?\|months?\|years?)\b` | case-insensitive | mark-variable, `duration` |
| defined-term | per document: each definition's term quoted with `Pattern.quote`, longest first, joined by `\|`, wrapped as `(?<![\p{L}\p{N}])(?:TERMS)(?:s\|'s\|’s)?(?![\p{L}\p{N}])` | case-sensitive | mark-reference, target the definition |
| cross-reference | `\b(?:clause\|section\|schedule\|paragraph\|article)\s\d+(?:\.\d+)*(?:\([a-z0-9]+\))?` | case-insensitive | none |

- In a definition element, skip matches of its own term.
- Overlaps: collect all matches of all kinds in an element, sort by length descending, then by the
  table's kind order, then by start. Accept a match unless it overlaps an accepted one. Return the
  accepted matches sorted by element order, then start.
- Suggested key: lower-case the match, replace each run of `[^a-z0-9]+` with `-`, trim `-`, cut to 40
  characters and trim `-` again. If the result is empty or starts with a digit, prefix the value
  type and `-`, cut to 40, trim. Examples: `[Agent]` → `agent`, `GBP 250` → `gbp-250`, `120 days` →
  `duration-120-days`.
- Non-variable suggestions set `valueType` and `suggestedKey` null. Non-reference suggestions set
  `targetElementId` null.

#### Template findings (at snapshot time)

| Kind | Severity | When |
|---|---|---|
| `unknown-section` | warning | a snapshot section key that the template does not name |
| `required-section-empty` | warning | a required template section absent from the snapshot or with zero elements |
| `element-kind-not-allowed` | warning | an element whose kind is not in its section's `elementKinds` (not checked in unknown sections) |
| `unmarked-text` | info | each `unmarked` entry, with its section key |

Order: template section order, then snapshot order. Messages are one plain sentence naming the
section heading (or key) and, where relevant, the element's object id.

#### Conformance (on an analysis)

For each element of `analysis.elements` whose `sectionKey` the template names:
`relationClass` non-null and not in the section's `allowedTermKinds` gives `term-kind-not-allowed`
(warning). `relationClass` null in a section with a non-empty `allowedTermKinds` gives
`no-term-kind` (info). Unknown sections give nothing here (reported at snapshot time).

#### Tests

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| S3-01 | facility element 13 / detected / placeholder `[Agent]` at the UTF-16 offsets of its position in the element text, suggestion `mark-variable`, `text`, `agent` | L1 | + |
| S3-02 | facility elements 11 and 13 / detected / money `GBP 250` (`gbp-250`) and duration `120 days` (`duration-120-days`). Every case of `contracts/authoring/fixtures/suggested-keys.json` gives its value type and key | L1, L3 | + |
| S3-03 | literal `within [5 days] and 5 days` / detected / the placeholder `[5 days]` and the later `5 days`, and no duration inside the placeholder | L1 | - |
| S3-04 | facility elements 14 and 15 / detected / `Loans` in 14 and `Loan` in 15 as defined-term with the Loan definition as target. In `Loaner` nothing. In definition 03 its own `Loan` is not reported | L1 | +/- |
| S3-05 | facility element 08 / detected / nothing from the variable part `2.5 per cent` | L1 | - |
| S3-06 | a literal `𝑥 costs GBP 5` / detected / money starts at offset 9 (the astral character counts 2) | L1 | + |
| S3-07 | literal `subject to clause 4.1(a)` / detected / cross-reference with action `none` | L1 | + |
| S3-08 | the catalog / loaded / three templates. A template resource missing `sections` / loading throws naming the file | L1 | +/- |
| S3-09 | a licence snapshot without Restrictions, with Fees empty, a section `misc`, and a definition inside Grant / checked / one finding each: `required-section-empty` ×2, `unknown-section`, `element-kind-not-allowed` | L1 | - |
| S3-10 | a snapshot with zero sections / checked / one `required-section-empty` per required template section (zero case) | L1 | - |
| S3-11 | an analysis with a Prohibition in licence `grant` and a Permission in `grant` / conformance / one `term-kind-not-allowed` only | L1 | +/- |
| S3-12 | an analysis with `relationClass` null in `interest`, and one element in an unknown section / conformance / one `no-term-kind`, nothing for the unknown section | L1 | +/- |
| S3-13 | the licence sample / template findings / exactly one `unmarked-text` for `Fees are exclusive of VAT.` | L1 | + |

**Self-probe:** change the overlap sort to start-first instead of length-first. S3-03 fails.

**Docs:** the service README gains the detection table (kinds and actions only).

---

### WA4: API and HTTP adapter

**Preconditions:** WA3 committed.

**Paths:** `platform/authoring-service/**`, `docs/architecture/solution-design-specification.md`.

#### Classes

| Class | Responsibility |
|---|---|
| `store.AuthoringStore` | interface: `void ensureReady()`, `boolean ping()`, `void putGraph(String graphIri, Model model)`, `Optional<Model> getGraph(String graphIri)`. A test seam, not an SPI (ADR-A118) |
| `store.InMemoryAuthoringStore` | over `DatasetFactory.createTxnMem()`, copying models in and out |
| `store.DocumentRegistry` | over the store's registry graph: `int latestRevision(String documentId)` (0 if none), `Optional<DocumentView> find(String documentId)`, `void record(String documentId, int revision, String title, String templateId, GraphRef wordingGraph)`, `List<String> documentIds()`. Read the registry graph, change it in a Jena model, put it back, all inside `synchronized` methods. Triples: the document IRI `a wap:AuthoringDocument`, `wap:documentId`, `dcterms:title`, `wap:templateId`, `wap:latestRevision`. The revision record `D/rev/n` `a wap:Revision`, `wap:revisionOf`, `wap:revisionNumber`, `wap:wordingGraph`, `wap:revisionHash`, `dcterms:created` (xsd:dateTime) |
| `messaging.AnalysisBus` | interface: `void publish(JsonNode request)`, `void onResult(Consumer<JsonNode> handler)`, `boolean ping()` |
| `messaging.InMemoryAnalysisBus` | records published requests, `deliver(JsonNode result)` calls the handler, a flag to make `publish` throw |
| `jobs.JobRegistry` | `ConcurrentHashMap<String, JobView>`: `queue`, `complete`, `fail`, `get` |
| `api.ApiResponse<T>` | record `(int status, T body, String contentType)`, factories `ok`, `notFound`, `badRequest(String, List<String>)`, `conflict`, `unavailable`, with error bodies of the `error` schema |
| `api.AuthoringApi` | framework-neutral, one method per route, plus `void onAnalysisResult(JsonNode)`. Constructed with `ContractSchemas`, `TemplateCatalog`, `SampleCatalog`, `IriMinter`, `WordingMapper`, `WordingValidator`, `ConstructDetector`, `TemplateFindings`, `ConformanceChecker`, `AuthoringStore`, `DocumentRegistry`, `AnalysisBus`, `JobRegistry`, `Clock` |
| `http.AuthoringHttpServer` | Javalin (WA-D4). `Javalin.create(config -> …)` with virtual threads on, the banner off, request size capped at 1 MiB, 405 preferred over 404 for a known path with another method (`config.http.prefer405over404` in 6.x), and `JavalinJackson` over `Json`'s mapper. One handler per route of the table below, each only reading path parameters and the body, calling `AuthoringApi` and writing its `ApiResponse` (status, content type, body). A `before` handler gives 415 and 413 (below) with `error` bodies, an `after` handler sets the headers, `error(404)` and `error(405)` write `error` bodies, `exception(Exception.class)` gives 500. `start(int port)` (0 for an ephemeral port in tests), `stop()`, `int port()`. No business logic in this class |
| `app.SampleSeeder` | `int seed()`: for each sample whose documentId the registry does not hold, submit it as revision 1 through `AuthoringApi.submitSnapshot`. Returns the number seeded |

#### Routes

| Method, path | API method | Success | Errors |
|---|---|---|---|
| GET `/api/health` | `health()` | 200 `health` | 503 `health` with `degraded` when the store or bus ping fails |
| GET `/api/templates` | `listTemplates()` | 200 `template-list` | |
| GET `/api/templates/{templateId}` | `getTemplate(id)` | 200 `authoring-template` | 400 bad key, 404 |
| GET `/api/samples` | `listSamples()` | 200 `sample-list` | |
| GET `/api/samples/{sampleId}` | `getSample(id)` | 200 `document-snapshot` | 400, 404 |
| GET `/api/documents/{documentId}` | `getDocument(id)` | 200 `document-view` | 400, 404 |
| PUT `/api/documents/{documentId}/snapshot` | `submitSnapshot(id, body)` | 200 `snapshot-accepted` | 400, 404 template, 409, 413, 415 |
| GET `/api/jobs/{jobId}` | `getJob(id)` | 200 `job-view` | 400, 404 |
| GET `/api/documents/{documentId}/revisions/{revision}/analysis` | `getAnalysis(id, n)` | 200 `analysis-view` | 400, 404 |
| GET `/api/documents/{documentId}/revisions/{revision}/graph/{kind}` | `getGraph(id, n, kind)` | 200 `text/turtle` | 400 (kind not `wording` or `proposal`), 404 |

Path parameters are checked against §2.4 before the API is called (`revision` is `^[1-9][0-9]{0,8}$`).
Unknown paths give 404 and a known path with another method 405, both with an `error` body. Every
response carries `X-Content-Type-Options: nosniff` and `Cache-Control: no-store`, and no CORS
header. Request bodies are read up to 1 MiB (1,048,576 bytes), beyond which the answer is 413. A PUT
whose `Content-Type` does not start with `application/json` gets 415. Unexpected exceptions give 500
with the body `{"error": "internal error", "details": []}` and the stack trace goes to the log only.

#### `submitSnapshot`, in this order

1. Validate the body against `snapshot-submission`. Failures give 400 with the messages as details.
2. Read the snapshot. A `documentId` different from the path gives 400.
3. Look up the template. Absent gives 404.
4. `latest = registry.latestRevision(documentId)`. If `baseRevision` is null and `latest > 0`, or
   `baseRevision` is non-null and differs from `latest`, answer 409 naming `latest`.
5. `revision = latest + 1`. Map, hash, `store.putGraph(wordingGraph, model)`.
6. Validate with SHACL, detect, check template findings.
7. `registry.record(...)`.
8. `jobId` = random UUID, `jobs.queue(...)`, build the request event (`correlationId` = jobId,
   `wordingIri`, `proposalGraphIri`, `requestedAt` from the clock), validate it against
   `wording-analysis-request` and publish. If publishing throws, `jobs.fail(jobId, "analysis queue
   unavailable")` and continue.
9. Answer 200 with `snapshot-accepted`, the job's current status included.

#### `onAnalysisResult`

Validate against `wording-analysis-result`. Invalid: log and return (the bus dead-letters it, WA5).
Unknown jobId: log and return. Failed: `jobs.fail`. Completed: look up the document's template
through the registry, compute conformance, build the `analysis-view` node, store it as one triple
`<D/rev/n> wap:analysisJson "<json>"` in the analysis graph, cache it in memory, then
`jobs.complete`.

`getAnalysis` answers from the cache, then from the analysis graph, else 404 with "analysis not
available".

#### Tests

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| S4-01 | the in-memory wiring / a new facility snapshot submitted / 200, revision 1, the wording graph stored under its IRI, registry latest 1, one request published whose graph reference and IRIs match, job `queued` | L1 | + |
| S4-02 | revision 1 exists / submitted with base 1 / revision 2. With base null / 409. With base 5 / 409 | L1 | +/- |
| S4-03 | path and body document ids differ / 400. A path id that is not a UUID / 400. A body with an extra property / 400 with details | L1 | - |
| S4-04 | a snapshot naming template `nope` / 404 | L1 | - |
| S4-05 | the bus set to throw / submitted / 200 with job `failed` | L1 | - |
| S4-06 | a completed result for the job / delivered / job `completed`, analysis view with conformance, and a second `AuthoringApi` over the same store serves the same view | L1 | + |
| S4-07 | a failed result / delivered / job `failed` with the error, analysis 404 | L1 | - |
| S4-08 | a result for an unknown job, and an invalid result / delivered / no exception, nothing changes | L1 | - |
| S4-09 | the HTTP server on an ephemeral port / each route called once with valid input / the status of the table, and each JSON body validates against its response schema | L3 | + |
| S4-10 | a 1 MiB + 1 byte body, and a PUT with `text/plain` / 413 and 415. An unknown path / 404. POST to `/api/templates` / 405 | L1 | - |
| S4-11 | any response / headers / `nosniff` and `no-store` present, no `Access-Control-Allow-Origin` | L1 | + |
| S4-12 | a stored revision / graph `wording` / Turtle that parses to a model isomorphic to the stored one. Kind `other` / 400 | L1 | +/- |
| S4-13 | a store whose ping fails / health / 503 `degraded` with `fuseki: down` | L1 | - |
| S4-14 | an empty registry / seeded twice / three documents at revision 1 and three requests the first time, nothing the second | L1 | + |

**Self-probe:** remove the 409 check for `baseRevision` null on an existing document. S4-02 fails.

**Docs:** `solution-design-specification.md` gains a short "Word authoring POC" section: the
component table of sketch §2, the route table above (methods and paths only), a link to the sketch
and ADR-A118, and the statement that it is not a platform contract.

---

### WA5: Fuseki, RabbitMQ and the runnable service

**Preconditions:** P6, WA4 committed.

**Paths:** `platform/authoring-service/**`, `mise.toml`.

#### Classes

| Class | Responsibility |
|---|---|
| `store.FusekiAuthoringStore` | `RDFConnectionRemote.service(url + "/" + dataset).gspEndpoint("data")` per operation, with an `HttpClient` whose `java.net.Authenticator` answers with the admin credentials. `getGraph` maps HTTP 404 to empty. `ensureReady`: up to 30 attempts 2 seconds apart, `GET {url}/$/datasets/{dataset}` with basic auth. 404 → `POST {url}/$/datasets` form `dbName={dataset}&dbType=tdb2`. `ping`: `GET {url}/$/ping` is 200. Uses `java.net.http.HttpClient` for the admin calls, timeouts 10 seconds |
| `messaging.Topology` | constants equal to `contracts/authoring/amqp-topology.json`, `declare(Channel)` |
| `messaging.RabbitMqAnalysisBus` | one connection from `ConnectionFactory.setUri(uri)`, automatic recovery on. `declare` at start. `publish`: to `lattice.authoring` with routing key `lattice.authoring.analysis.requested`, properties content type `application/json`, message id and correlation id the jobId, delivery mode 2, type the routing key. `onResult`: `basicConsume` on the completed queue with manual ack. Parse JSON and pass to the handler, then ack. Unparseable JSON or a handler exception: `basicNack(tag, false, false)`, which dead-letters it. `ping`: connection open. Connects with up to 30 attempts 2 seconds apart |
| `app.AuthoringConfig` | record from a `Map<String, String>` (the environment): `LATTICE_AUTHORING_PORT` (8080), `LATTICE_AUTHORING_BASE_IRI` (`https://example.org/lattice/authoring/`, must end with `/`), `LATTICE_FUSEKI_URL` (`http://localhost:3030`), `LATTICE_FUSEKI_DATASET` (`authoring`), `LATTICE_FUSEKI_ADMIN_USER` (`admin`), `LATTICE_FUSEKI_ADMIN_PASSWORD` (no default, required), `LATTICE_AMQP_URI` (no default, required), `LATTICE_AUTHORING_SEED_SAMPLES` (`false`). Invalid values throw `IllegalArgumentException` naming the variable, never echoing a secret |
| `app.AuthoringServiceMain` | `main`: with `--self-check`, load the vocabulary, shapes, schemas, templates and samples, map and validate each sample, print `self-check ok`, exit 0. Otherwise build config, store (`ensureReady`), bus, API, seeder (if enabled), server, register the result handler and a shutdown hook, then block |
| `app.HealthProbe` | `main(url)`: GET with a 3 second timeout, exit 0 on 200, else 1 |

#### Maven

Add `org.testcontainers:testcontainers` (test). Add profile `authoring-it` running
`maven-failsafe-plugin` 3.5.0 goals `integration-test` and `verify` for `**/*IT.java`. ITs use
`GenericContainer` only: `stain/jena-fuseki:5.1.0` with `ADMIN_PASSWORD=lattice`, port 3030, wait
for HTTP `/$/ping`. `rabbitmq:3.13-management-alpine` with `RABBITMQ_DEFAULT_USER` and
`RABBITMQ_DEFAULT_PASS` `lattice`, port 5672, wait for log `Server startup complete`. Containers start
in `@BeforeAll` and stop in `@AfterAll`.

```toml
[tasks."check:authoring-service-it"]
description = "Integration-test the word authoring POC service against Fuseki and RabbitMQ containers"
run = "mvn -f platform/pom.xml -pl authoring-service -am -Pauthoring-it verify"
```

#### Tests

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| S5-01 | `AuthoringConfig` / defaults, overrides, port `abc`, base without `/`, missing password / values, then three exceptions naming the variable, none containing the password value | L1 | +/- |
| S5-02 | Fuseki container / `ensureReady` twice, put then get a graph, get an absent graph / no error, isomorphic, empty | L4 | + |
| S5-03 | RabbitMQ container / declare twice, publish a request / no error, the message on the requested queue with the four properties | L4 | + |
| S5-04 | RabbitMQ container / a valid result and a malformed one on the completed queue / the handler gets the first, the second lands on `lattice.authoring.dead` | L4 | +/- |
| S5-05 | both containers, the real store, bus and API, and an in-test consumer that answers each request with a completed result from a fixture / a sample submitted / the job completes within 10 seconds and the analysis view and the wording Turtle are served | L4 | + |
| S5-06 | `HealthProbe` against a stub server answering 200, then 503, then a closed port / exit codes 0, 1, 1 | L1 | +/- |
| S5-07 | the shaded jar / `java -jar target/authoring-service.jar --self-check` run from an IT / exit 0 and `self-check ok` (proves Jena initialises from the jar) | L4 | + |
| S5-08 | `Topology` / compared with `amqp-topology.json` / equal | L3 | + |

**Self-probe:** remove `ServicesResourceTransformer` from the shade configuration. S5-07 fails.

**Docs:** service README gains configuration (the variables above) and the IT command.

---

### WA6: Logical English reading

**Preconditions:** WA1 committed (fixtures), WA2 committed (the `.nt` fixtures).

**Paths:** `workers/src/lattice_workers/wording_le/**`, `workers/tests/test_wording_le.py`,
`workers/tests/fixtures/wording_le/**`, `workers/pyproject.toml` (package data), `mise.toml`.

#### Modules

| Module | Contents |
|---|---|
| `namespaces.py` | `WRD`, `INS`, `WAP`, `PROV`, `DCTERMS` as `rdflib.Namespace`, and the base-free IRI helpers of §2.3 that derive from a wording IRI (`doc_base(wording_iri)` strips the trailing `/wording`) |
| `offsets.py` | `utf16_len(s) = len(s.encode("utf-16-le")) // 2`, `utf16_index(s, i)` = `utf16_len(s[:i])` |
| `model.py` | frozen dataclasses `Part(index, kind, text, variable_key, target_element_id)`, `Element(element_id, iri, object_id, section_key, kind, defined_term, parts)`, `Variable(key, iri, label, value_type)`, `Wording(iri, document_id, title, template_id, revision, elements, variables)`. `load_wording(graph, wording_iri) -> Wording` walks `wrd:directlyComprises` from the wording, sorts by `wrd:rankKey`, reads parts by `wap:hasPart` sorted by `wrd:partIndex`. A part's text is `wrd:partText` or `wap:displayText`. Raises `ValueError` when the wording node is absent |
| `tokens.py` | `Token(text, norm, start, end, part_index, kind)` with `kind` in `word`, `punct`, `variable`, `constant`; offsets per §2.5. `tokenise(element)`: a variable part is one `variable` token, a reference part one `constant` token. Literal text splits by regex `[\w’'-]+\|[,;:]` (Unicode `\w`), `norm` lower-cased with `’` → `'`. Quotes, brackets and the final full stop make no token. Each regex match becomes a token at its offsets |
| `forms.py` | `FormProfile(profile_id, version, ignorable, forms)`, `Form(form_id, relation_class, template, items)`, `Item` one of `Fixed(words)`, `Slot(name, type, value_types)`. `load_profile()` reads `forms/sentence-forms.json` (package data) |
| `matcher.py` | `match(tokens, form, ignorable) -> Match \| None`, `best_match(tokens, profile) -> Match \| None`, rules below |
| `classify.py` | `keyword_class(tokens, element_kind) -> str \| None`, rules below |
| `analyse.py` | `analyse_wording(wording, profile) -> dict` (the `Analysis` shape without `graphView`) |
| `render.py` | `le_program(wording, element_analyses, profile) -> str` |
| `proposal.py` | `proposal_graph(wording, element_analyses, proposal_graph_iri, profile) -> rdflib.Graph`, `graph_view(wording, graph) -> dict` |

`workers/pyproject.toml`: `[tool.setuptools.package-data]` `"lattice_workers.wording_le" =
["forms/*.json"]`.

#### Sentence-form profile (`forms/sentence-forms.json`)

`profileId` `wap-le-forms`, `version` `0.1.0`, `ignorable` `["the", "a", "an", "each", "any"]`.
Forms in this order:

| formId | relationClass | template | items |
|---|---|---|---|
| `pay-interest-at-rate` | Obligation | `*a party* shall pay interest on *a thing* at *a rate* per annum` | party, `shall pay interest on`, text(thing), `at`, variable(rate: percentage), `per annum` |
| `deemed-shall` | Deeming | `*a thing* shall be deemed *a state*` | text(thing), `shall be deemed`, text(state) |
| `deemed-is` | Deeming | `*a thing* is deemed *a state*` | text(thing), `is deemed`, text(state) |
| `obligation-within` | Obligation | `*a party* shall *an activity* within *a period*` | party, `shall`, text(activity), `within`, variable(period: duration) |
| `prohibition` | Prohibition | `*a party* shall not *an activity*` | party, `shall not`, text(activity) |
| `obligation` | Obligation | `*a party* shall *an activity*` | party, `shall`, text(activity) |
| `power-terminate` | Power | `*a party* may terminate *an activity*` | party, `may terminate`, text(activity) |
| `power-on-condition` | Power | `if *a condition*, *a party* may *an activity*` | `if`, text(condition), `,`, party, `may`, text(activity) |
| `permission` | Permission | `*a party* may *an activity*` | party, `may`, text(activity) |
| `exclusion-not-liable` | Exclusion | `*a party* is not liable for *a matter*` | party, `is not liable for`, text(matter) |
| `exclusion-not-cover` | Exclusion | `this policy does not cover *a matter*` | `this policy does not cover`, text(matter) |
| `definition` | Definition | `*a term* means *a description*` | term, `means`, text(description) |

#### Matching rules

1. Drop tokens whose `norm` is in `ignorable` from the sequence to match (they keep the role
   `ignorable` in spans). Drop ignorable words from each `Fixed` item too.
2. `Fixed(words)` consumes word or punct tokens whose `norm`s equal the words in order.
3. `party` consumes exactly one `constant` token. `variable` consumes exactly one `variable` token,
   whose declared value type is in `value_types` when given. `term` consumes the word tokens equal,
   in order, to the element's defined term's tokens, and only in definition elements. `text`
   consumes one or more tokens of any kind, as few as possible first (backtracking).
4. A match must consume every token.
5. `best_match` tries every form. Among matches it keeps the one with the most fixed word tokens,
   then the earliest in the profile. The result is deterministic.

#### Keyword rules (when no form matches)

On the `norm`s of word tokens, the first rule that applies gives the class:

1. element kind `definition` and the word `means` or `includes` → Definition
2. the phrase `shall be deemed`, `is deemed` or `are deemed` → Deeming
3. `does not cover`, `is not liable`, `are not liable` or the word `excluded` → Exclusion
4. `shall not`, `must not` or `may not` → Prohibition
5. `may terminate` or `may declare` → Power
6. `shall` or `must` → Obligation
7. `may` → Permission
8. otherwise none

#### Spans

Each token gets one role. Variable tokens `slot-variable`, constant tokens `slot-constant`, ignorable
tokens `ignorable`. Other tokens: in a form match, tokens consumed by a `Fixed` item are `fixed` and
tokens consumed by a `text` or `term` slot are `slot-text`. Without a form match, `unmatched`. Then
overrides, in order: a word in `{shall, must, may, not}` that is `fixed` or `unmatched` becomes
`modal`. A word in `{if, unless, provided, save, subject, where, when}` that is `fixed` or `unmatched`
becomes `connective`. Adjacent tokens with the same role in the same part merge into one span from
the first start to the last end. Spans are sorted by start and never overlap.

#### Element analysis fields

`elementId`, `objectId`, `sectionKey`, `kind`, `text` (the element text), `relationClass`, `basis`
(`form`, `keyword` or `none`), `formId`, `leTemplate` (the form's template plus `.`, or null),
`leSentence` (the element text with whitespace collapsed and a final `.` ensured, or null when
`basis` is `none`), `spans`.

#### LE program

```text
% Logical English reading of "<title>", revision <n>, generated by the word authoring POC.
% Profile <profileId> <version>. Not checked by an LE parser.

the templates are:
    <each distinct matched form's template plus ".", in profile order, 4-space indent>

the knowledge base <templateId with - replaced by _> includes:

% <objectId> <relationClass> (form <formId> | keyword)
<leSentence>

% <objectId> unmatched: <element text>
```

Elements appear in document order, separated by one blank line, with `\n` line ends and one final
newline.

#### Proposal graph

For each element with a `relationClass` (R = `D/element/<id>/meaning`):

- `R a ins:<relationClass>`, `ins:expressedIn` the element IRI, `wap:proposalBasis` `form` or
  `keyword`, `prov:wasGeneratedBy` the activity, and `wap:sentenceForm` the form id for form matches.
- The party: the first `constant` token consumed by a `party` slot (form basis), or the first
  non-ignorable token when it is a `constant` (keyword basis). Obligation, Prohibition and
  Exclusion use `ins:obligor`. Permission and Power use `ins:holder`. The role node
  `D/role/<target id>` is `a wap:PartyRole`, `rdfs:label` the target definition's term,
  `wap:namedBy` the definition element.
- Each `variable` slot: `R ins:hasParameterBinding B`, `B a ins:ParameterBinding`,
  `ins:parameterKind wap:<slotName>`, `ins:fromVariable` the variable IRI.
- The `activity` text slot: `R wap:activityText` the element-text substring from the slot's first
  token start to its last token end.
- Definitions: `R wap:definesTerm` the term.
- The activity: `a prov:Activity`, `prov:used` the wording IRI, `wap:formsProfile`
  `"<profileId> <version>"`.

`graph_view`: nodes for relations (label `<relationClass> <objectId>`), elements
(`Clause <objectId>` or `Definition <objectId>`), roles (the term) and variables (the key). Edges
relation → element `expressedIn`, relation → role `obligor` or `holder`, relation → variable
`<slotName>` (binding nodes collapsed). Nodes sorted by kind order (relation, element, role,
variable) then id. Edges sorted by from, label, to.

#### Goldens

`workers/tests/fixtures/wording_le/<sample>.analysis.json` (the `Analysis` object with `graphView`),
`facility-agreement.le`, `facility-agreement.proposal.ttl`. Generate them with a test helper run
once, read them in full against the sample texts, correct the code (not the golden) where a reading
is wrong, and commit them. The Validation Pack lists, for the facility sample, each element's class,
basis and form, so the human can check the reading.

Expected facility readings: 01 to 05 Definition (form), 06 Obligation (form `obligation`), 07
Permission (form `permission`), 08 Obligation (form `pay-interest-at-rate`), 09 Obligation
(keyword), 10 to 11 Obligation (form), 12 Prohibition (form), 13 Obligation (form `obligation`, the
literal `120 days` is not a variable token), 14 Power (form `power-on-condition`), 15 Deeming (form
`deemed-shall`).

#### Tests (`workers/tests/test_wording_le.py`)

```toml
[tasks."check:authoring-worker"]
description = "Test the word authoring POC worker"
run = "python -m pytest workers/tests/test_wording_le.py workers/tests/test_wording_analysis_worker.py workers/tests/test_authoring_contracts.py -q"
```

In WA6 the task lists only `test_wording_le.py` and `test_authoring_contracts.py`. WA7 adds
`test_wording_analysis_worker.py`.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| S6-01 | `utf16_len` and `utf16_index` / `"abc"`, `"𝑥a"` / 3, and index 1 → 2 | L1 | + |
| S6-02 | facility element 06 / tokenised / constant, words, variable tokens with element-text offsets. Quotes and the final full stop give no token. A comma gives a punct token | L1 | + |
| S6-03 | the profile / loaded / form ids unique, classes in TermKind, each template's slots match its items. Every form matches at least one element of the three samples | L1 | + |
| S6-04 | `Borrower shall not create …` / `best_match` / `prohibition`, not `obligation` | L1 | + |
| S6-05 | a party slot over a literal, a text slot with zero tokens, a rate slot over a duration variable / matched / no match each | L1 | - |
| S6-06 | keyword rules / a table of nine sentences, one per rule and two with competing words (`shall be deemed`, `shall not`) / the table's classes | L1 | +/- |
| S6-07 | every element of the three samples / analysed / spans sorted, non-overlapping, each word token inside exactly one span | L2 | + |
| S6-08 | each sample / analysed / equals its committed `.analysis.json` | L2 | + |
| S6-09 | the facility sample / LE program / equals `facility-agreement.le` | L2 | + |
| S6-10 | the facility proposal / built / isomorphic (`rdflib.compare.isomorphic`) to the golden. Each relation has one `ins:expressedIn`. Each `ins:fromVariable` names a declared variable | L2 | + |
| S6-11 | each sample's analysis / validated against `common` `#/$defs/Analysis` / passes | L3 | + |
| S6-12 | every IRI constant in `namespaces.py` / looked up in `platform/authoring-service/src/main/resources/vocab/wording-provisional.ttl` / declared there | L3 | + |
| S6-13 | a wording graph where one text has zero parts / analysed / that element has basis `none` and no spans, the rest are unaffected (zero case) | L1 | - |

**Self-probe:** in `best_match`, prefer the earliest form instead of the most fixed words. S6-04
fails (and S6-08).

**Docs:** `workers/README.md` is created if absent, or extended: the authoring job, its modules and
the command.

---

### WA7: Worker runtime

**Preconditions:** WA6 committed.

**Paths:** `workers/src/lattice_workers/fuseki_gsp.py`,
`workers/src/lattice_workers/wording_analysis_worker.py`,
`workers/src/lattice_workers/wording_analysis_main.py`,
`workers/tests/test_wording_analysis_worker.py`, `mise.toml`.

#### Modules

| Module | Contents |
|---|---|
| `fuseki_gsp.py` | `FusekiGraphStore(base_url, dataset, user=None, password=None, timeout=10)`. `get_graph(iri) -> rdflib.Graph` via `GET {base}/{dataset}/data?graph=<urlencoded iri>` with `Accept: text/turtle`, 404 raises `GraphNotFound`. `put_graph(iri, graph)` via `PUT` with `Content-Type: text/turtle`. Basic auth header when a user is given. `urllib.request` only |
| `wording_analysis_worker.py` | `TOPOLOGY` loaded from the packaged copy of `amqp-topology.json` (copy it into the package as data in this slice, test S7-05 keeps them equal). `WordingAnalysisConsumer(store, publisher, profile, clock)` with `consume(message: dict) -> dict`. `RabbitMqResultPublisher(channel, properties_factory)`. `RabbitMqWordingAnalysisWorker(consumer)` with `handle(channel, delivery_tag, body)` in the shape of `RabbitMqSurfaceWorker` |
| `wording_analysis_main.py` | reads `LATTICE_AMQP_URI` (required), `LATTICE_FUSEKI_URL` (required), `LATTICE_FUSEKI_DATASET` (`authoring`), `LATTICE_FUSEKI_USER`, `LATTICE_FUSEKI_PASSWORD` (optional). Connects with `pika.BlockingConnection(pika.URLParameters(uri))`, retrying every 2 seconds on `AMQPConnectionError`, declares the topology, `basic_qos(prefetch_count=1)`, consumes the requested queue with manual ack. `python -m lattice_workers.wording_analysis_main` |

#### `consume`, in this order

1. Check the message has every key of `wording-analysis-request` with the right JSON types.
   Otherwise raise `ValueError` (the adapter nacks without requeue).
2. `get_graph(wordingGraph.graphIri)`. `GraphNotFound` → a `failed` result with error
   `wording graph not found`.
3. `load_wording`. `ValueError` → a `failed` result with the message.
4. Analyse, build the proposal graph and the graph view, `put_graph(proposalGraphIri, graph)`.
   `OSError` (including `URLError`) propagates (the adapter nacks with requeue).
5. Build the `completed` result: the request's ids, `proposalGraph` with `tenantId` `poc`,
   `projectId` `word-authoring`, the IRI and `sha256:` over the graph's sorted N-Triples lines (a
   worker-local hash, not comparable with Java's), `analysis`, `completedAt` from the clock.
6. Publish to `lattice.authoring` with routing key `lattice.authoring.analysis.completed`, content
   type `application/json`, message id and correlation id the jobId, delivery mode 2, body
   `json.dumps(result, sort_keys=True, separators=(",", ":"))`.

The adapter acks after a successful publish, nacks without requeue on `ValueError`,
`UnicodeDecodeError` and `json.JSONDecodeError`, and with requeue on any other exception.

#### Tests

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| S7-01 | a fake store holding the facility `.nt` fixture as the wording graph / a valid request consumed / the proposal graph put under its IRI, one `completed` result published that validates against `wording-analysis-result`, ack | L1 | + |
| S7-02 | an empty fake store / consumed / one `failed` result with `wording graph not found`, ack | L1 | - |
| S7-03 | malformed JSON, and a message missing `proposalGraphIri` / handled / nack without requeue, nothing published | L1 | - |
| S7-04 | a store whose `put_graph` raises `OSError` / handled / nack with requeue, nothing published | L1 | - |
| S7-05 | the packaged topology / compared with `contracts/authoring/amqp-topology.json` / equal | L3 | + |
| S7-06 | a local `http.server` stub in a thread / `get_graph` and `put_graph` / the URL carries the encoded graph IRI, the basic auth header is present when configured, 404 raises `GraphNotFound` | L1 | +/- |
| S7-07 | `wording_analysis_main`'s config reader / required variables missing / `ValueError` naming the variable | L1 | - |
| S7-08 | the publisher / one result / the four message properties set | L1 | + |

**Self-probe:** make the adapter requeue on `ValueError`. S7-03 fails.

**Docs:** `workers/README.md`: how the job runs, its environment variables.

---

### WA8: Add-in domain

**Preconditions:** P5, P7, WA1 committed.

**Paths:** `apps/word-authoring-addin/**` (domain, config, manifest, unit tests), `yarn.lock`,
`.gitignore`, `.build/word-authoring-addin-test-results/.gitkeep`, `mise.toml`, `README.md`.

#### Workspace

`apps/word-authoring-addin/package.json`, name `@lattice/word-authoring-addin`, private, type
module. Scripts: `dev` `vite`, `build` `tsc --noEmit && vite build`, `check`
`tsc --noEmit && vitest run`, `test` `playwright test`, `test:stack`
`playwright test -c playwright.stack.config.ts`. Dependencies: `react`, `react-dom`, `mermaid`.
Dev dependencies: `@playwright/test`, `@types/react`, `@types/react-dom`, `@types/office-js`,
`@vitejs/plugin-react`, `ajv`, `jsdom`, `typescript`, `vite`, `vitest`. Run `yarn install` (not
`--immutable`) once to update `yarn.lock`.

- `vite.config.ts`: `base: "/addin/"`, React plugin, `build.rollupOptions.input` with
  `taskpane.html` and `harness.html`, dev server port 4175 strict, dev proxy `/api` →
  `http://127.0.0.1:8088`.
- `vitest.config.ts`: environment `jsdom`, include `src/**/*.test.ts` and `src/**/*.test.tsx`, no
  globals (tests import `describe`, `it`, `expect` from `vitest`).
- `tsconfig.json`: as the studio's, plus `"types": ["office-js"]`.
- `.gitignore` gains `.build/word-authoring-addin-test-results/*` and its `.gitkeep` exception, and
  `.build/authoring/`.

#### Files under `src/`

| File | Contents |
|---|---|
| `domain/types.ts` | TypeScript types for every schema of WA1, by hand, names as the `$defs` |
| `domain/schemas.ts` | imports every schema JSON from `../../../../contracts/...`, one `Ajv2020` instance (`ajv/dist/2020`, `allErrors: true`, `strict: true`), `addSchema` each, `validate(name, value): string[]` |
| `domain/tags.ts` | the codec below |
| `domain/ooxml.ts` | `parseBody(ooxml: string): ParsedDocument` and `writeSections(...)`, `writePackage(bodyXml)`, rules below |
| `domain/snapshot.ts` | `buildSnapshot(parsed, metadata): { snapshot, warnings }` |
| `domain/offsets.ts` | `occurrenceIndex(elementText, start, text)`, `escapeWordSearch(text)` (`^` → `^^`) |
| `domain/mermaid.ts` | `toMermaid(graphView): string` |
| `domain/metadata.ts` | the custom XML part: `toXml(metadata)`, `fromXml(xml)` |
| `domain/poll.ts` | `pollJob(api, jobId, { intervalMs = 500, timeoutMs = 20000 })` resolving to the final `JobView` or rejecting with `timeout` |
| `api/client.ts` | `ApiClient` interface (one method per route) and `HttpApiClient(baseUrl, fetchImpl = fetch, timeoutMs = 10000)` with `AbortController`. Non-2xx answers reject with `ApiError(status, error, details)` |
| `word/port.ts` | the `DocumentPort` interface below |

#### Tag codec

| Kind | Tag | Title | Appearance | Colour |
|---|---|---|---|---|
| section | `lat:s:<sectionKey>` | `Section: <heading>` | BoundingBox | `#5B6B7F` |
| clause | `lat:e:<uuid>` | `Clause` | BoundingBox | `#1F6FB2` |
| definition | `lat:d:<uuid>` | `Definition` | BoundingBox | `#6A3FB5` |
| term | `lat:term` | `Term` | Tags | `#6A3FB5` |
| variable | `lat:v:<variableKey>` | `Variable: <label>` | Tags | `#C46A00` |
| reference | `lat:r:<uuid>` | `Defined term: <term>` | Tags | `#2E7D32` |

`encode(kind, value)` checks the value against §2.4 and the whole tag against 64 characters (Word's
limit for a content control tag), throwing otherwise. `decode(tag)` returns `{ kind, value }` or
null for anything else. Titles are cut to 64 characters. The appearance shows the title, so colour
is never the only cue.

#### OOXML rules

Namespaces: `w` = `http://schemas.openxmlformats.org/wordprocessingml/2006/main`, `w15` =
`http://schemas.microsoft.com/office/word/2012/wordml`, `pkg` =
`http://schemas.microsoft.com/office/2006/xmlPackage`. Parse with `DOMParser`
(`application/xml`), find the `pkg:part` named `/word/document.xml` (or accept a bare `w:document`),
and walk `w:body` by `namespaceURI` and `localName`.

- Text: `w:t` gives its text, `w:tab` `\t`, `w:br` and `w:cr` `\n`, `w:noBreakHyphen` `‑`.
  Descend into `w:hyperlink`, `w:ins`, `w:smartTag`, `w:fldSimple`, `w:customXml`, `w:r`. Skip
  `w:del`, `w:delText`, `w:instrText`, `w:rPr`, `w:pPr`, `w:proofErr`, `w:bookmarkStart`,
  `w:bookmarkEnd`, `w:commentRangeStart`, `w:commentRangeEnd`, `w:footnoteReference`.
- A block `w:sdt` with a section tag opens a section. Its first `w:p` whose `w:pStyle` value starts
  with `Heading` is the heading and is not read as text.
- A block `w:sdt` with a clause or definition tag inside a section is an element. Its paragraphs are
  joined with `\n`. Inline `w:sdt`s inside it: variable → a variable part (`text` its content),
  reference → a reference part, term → literal text that also sets `definedTerm` (the first one
  wins). An inline `w:sdt` inside an inline `w:sdt` is read as literal text, with a warning.
- Other paragraphs in a section, and paragraphs outside all sections, are `unmarked` entries when
  their trimmed text is non-empty (section key null outside sections).
- Adjacent literal texts merge. Empty literals are dropped. An element with no parts is dropped,
  with a warning.
- The writer emits the same structure: per section a block `w:sdt` (`w:alias`, `w:tag`, `w:id`,
  `w15:color`, `w15:appearance`), a `Heading1` paragraph, then per element a block `w:sdt` with one
  `w:p` per `\n`-separated line, literal runs `<w:r><w:t xml:space="preserve">…</w:t></w:r>`, and
  inline `w:sdt`s. In a definition, the first occurrence of the defined term inside a literal part
  is wrapped in a term `w:sdt`. XML-escape `&`, `<`, `>`, `"`. `writePackage` wraps a body in the
  flat-OPC package with the `/_rels/.rels` and `/word/document.xml` parts.
- `writeTemplate(template)`: per section, the section `w:sdt` with the heading and one empty
  element `w:sdt` of the section's first element kind and a fresh UUID.

#### `DocumentPort`

```ts
export type MarkResult =
  | { ok: true }
  | { ok: false; reason: "no-selection" | "outside-element" | "outside-section" | "already-marked" | "spans-parts" };

export interface DocumentPort {
  readBodyOoxml(): Promise<string>;
  readMetadata(): Promise<AuthoringMetadata | null>;
  writeMetadata(metadata: AuthoringMetadata): Promise<void>;
  insertOoxml(packageXml: string): Promise<void>;
  readSelection(): Promise<{ text: string; elementId: string | null }>;
  wrapSelectionAsElement(kind: "clause" | "definition", elementId: string): Promise<MarkResult>;
  markSelection(mark: InlineMark): Promise<MarkResult>;
  markOccurrence(elementId: string, text: string, occurrence: number, mark: InlineMark): Promise<boolean>;
  unmarkSelection(): Promise<MarkResult>;
}
```

`readSelection` returns the selected text and the id of the clause or definition that contains it
(null outside one). `InlineMark` is `{ kind: "variable"; variableKey; label } | { kind: "reference"; targetElementId;
term } | { kind: "term" }`. `AuthoringMetadata` is `{ documentId, templateId, title, revision:
number | null, variables: VariableDeclaration[] }`, stored as XML in namespace
`urn:nebularis:lattice:authoring:1`.

#### Snapshot builder

Fills `schemaVersion`, `documentId`, `templateId`, `title` and `variables` from the metadata and
the sections and unmarked entries from the parse. A variable part whose key the metadata does not
declare adds `{ variableKey, label: variableKey, valueType: "text" }` and a warning. The result is
validated with `schemas.validate("document-snapshot", …)` before it is returned.

#### Manifest (`manifest/manifest.xml`)

XML add-in-only manifest, `OfficeApp` `xsi:type="TaskPaneApp"`, `Id` a fixed GUID generated once in
this slice, `Version` `0.1.0.0`, `ProviderName` `Nebularis`, `DefaultLocale` `en-GB`,
`DisplayName` `LATTICE Authoring`, `Description`, `IconUrl` and `HighResolutionIconUrl`
(`https://localhost:3443/addin/assets/icon-32.png` and `icon-80.png`), `SupportUrl`
`https://localhost:3443/addin/help.html`, `AppDomains` `https://localhost:3443`, `Hosts`
`Document`, `Requirements` set `WordApi` `1.4`, `DefaultSettings/SourceLocation`
`https://localhost:3443/addin/taskpane.html`, `Permissions` `ReadWriteDocument`, and
`VersionOverrides` with one ribbon button on the Home tab that shows the task pane (WA9a adds the
other commands). Icons
(`public/assets/icon-16.png`, `-32`, `-64`, `-80`) are solid `#1F6FB2` squares written once with a
standard-library Python snippet (`zlib`, `struct`), not committed as a script. `public/help.html` is
a short static page.

#### `mise.toml`

```toml
[tasks."check:authoring-addin"]
description = "Type-check and unit-test the Word authoring add-in"
run = "yarn workspace @lattice/word-authoring-addin run check"
```

#### Tests (Vitest)

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| S8-01 | the codec / each kind encoded and decoded / round trip. A 65-character tag, an upper-case key, `lat:x:1` / throw, throw, null | L1 | +/- |
| S8-02 | each sample / written as OOXML then parsed and built with the sample's metadata / equals the sample | L2 | + |
| S8-03 | `fixtures/word-like-facility.xml`, hand-written in Word's style (`w:rPr`, `w:proofErr`, `w:bookmarkStart`, `w:hyperlink`, `w:ins`, `w:del`, `w:smartTag`, `w:tab`, split runs) / parsed / the expected model in `fixtures/word-like-facility.expected.json` | L1 | + |
| S8-04 | a section with a heading, an unmarked paragraph and an empty element, and a paragraph outside sections / parsed / two unmarked entries (one with null section), the empty element dropped with a warning (zero case) | L1 | - |
| S8-05 | a variable `w:sdt` inside a reference `w:sdt` / parsed / literal text and a warning | L1 | - |
| S8-06 | a parse with an undeclared variable key and adjacent literal runs / built / the declaration added with a warning, literals merged, the snapshot validates | L1 | + |
| S8-07 | ajv / the valid and invalid fixtures and the samples of WA1 / same outcomes as AC-05 to AC-07 | L3 | +/- |
| S8-08 | `occurrenceIndex` with repeated text and an astral character, `escapeWordSearch("a^b")` / expected indices, `a^^b` | L1 | + |
| S8-09 | the facility graph view golden of WA6 / `toMermaid` / deterministic text, node ids `n0…`, quotes escaped as `#quot;` | L1 | + |
| S8-10 | `HttpApiClient` with a fake fetch / a PUT, a 409 answer, a fetch that never settles / the right URL, method, headers and body, an `ApiError` with status 409, a timeout rejection | L1 | +/- |
| S8-11 | the manifest / parsed / a GUID `Id`, every URL under `https://localhost:3443/addin/`, `ReadWriteDocument`, `WordApi` 1.4 | L1 | + |
| S8-12 | `pollJob` with fake timers / completed after three polls, never completing, failed / resolves completed, rejects `timeout`, resolves failed at once | L1 | +/- |

**Self-probe:** make the parser read `w:delText`. S8-03 fails.

**Docs:** root `README.md` layout gains `apps/word-authoring-addin/  # Word add-in, proof of concept
(ADR-A118)`. `apps/word-authoring-addin/README.md` created: purpose, commands, the tag table.

---

### WA9: Add-in task pane and harness

**Preconditions:** WA8 committed.

**Paths:** `apps/word-authoring-addin/**`, `docs/architecture/ux-design.md`.

#### Files

| File | Contents |
|---|---|
| `taskpane.html` | loads `https://appsforoffice.microsoft.com/lib/1/hosted/office.js`, then `src/main.tsx` |
| `harness.html` | loads `src/harness.tsx` only |
| `src/main.tsx` | `Office.onReady`. If `Office.context.requirements.isSetSupported("WordApi", "1.4")` is false, render the "unsupported Word version" message. Else render `<App port={new OfficeWordPort()} api={new HttpApiClient("/api")} />` |
| `src/harness.tsx` | renders `<App port={fakePort} api={new HttpApiClient("/api")} options={{ pollTimeoutMs }} />`, `pollTimeoutMs` from the query string (default 20000). Exposes `window.__harness = { model(), ooxml(), metadata(), select(elementId, start, end) }` |
| `src/word/officePort.ts` | `DocumentPort` over Office.js, rules below |
| `src/word/fakePort.ts` | `DocumentPort` over an in-memory `ParsedDocument` and metadata. `readBodyOoxml` writes the model with the WA8 writer. `insertOoxml` parses and appends. Selections are `(elementId, start, end)` in element-text offsets. Marking splits the literal part. Reasons: no selection, a selection crossing a part boundary (`spans-parts`), inside a variable or reference (`already-marked`), an element id not found (`outside-element`) |
| `src/app/App.tsx` | tabs Document, Markup, Analyse, Logical English, Graph, and an error banner |
| `src/app/*.tsx` | one component per panel, below |
| `src/app/app.css` | role colours, legend, layout for a 320 to 450 pixel wide pane |

#### Office port rules

All calls inside `Word.run`. `readBodyOoxml`: `context.document.body.getOoxml()`. Metadata:
`context.document.customXmlParts.getByNamespace(ns)`, replace by delete then `add`. `insertOoxml`:
`body.insertOoxml(xml, "End")`. `markSelection`: `getSelection()`, load `text` and
`parentContentControlOrNullObject` (`tag`). Empty text → `no-selection`. Parent null or not a
clause or definition tag → `outside-element`, or `already-marked` when it is an inline tag. Else
`insertContentControl()` and set tag, title, appearance and colour from the codec.
`wrapSelectionAsElement`: the selection's paragraphs, first to last via `expandTo`, parent must be a
section tag (`outside-section`). `markOccurrence`: `contentControls.getByTag(elementTag)`,
`search(escapeWordSearch(text), { matchCase: true })`, item `occurrence`, then as `markSelection`.

#### Panels

| Tab | Shows and does |
|---|---|
| Document | connection status from `/api/health`. Template list and "Apply template" (writes metadata with a new documentId, title from the template, revision null, the template's variables, then inserts `writeTemplate`). Sample list and "Insert sample" (a new documentId, the sample's variables, inserts the sample's sections). The current template's sections with heading, admitted term kinds and guidance |
| Markup | "Clause", "Definition", "Term" buttons. A variable form (key, label, value type, existing keys offered) and "Mark variable". A definitions list from the last parse and "Mark defined term". "Unmark". Each shows the `MarkResult` reason in plain words |
| Analyse | "Analyse": read OOXML and metadata, build, PUT with `baseRevision` = metadata revision, store the new revision in metadata, show validation results (grouped by element object id), template findings and detections. Each detection with an action has "Accept", which calls `markOccurrence` (declaring the suggested variable first, for variables). Then poll the job |
| Logical English | for each element in the analysis: object id, class, basis, form, and the element text with spans coloured by role, plus a legend. The LE program in a `<pre>` with "Copy" |
| Graph | the Mermaid diagram (`securityLevel: "strict"`, `startOnLoad: false`, rendered with `mermaid.render`) and a "Turtle" toggle fetching `graph/proposal` as text |

A debug "Copy body OOXML" button on the Document tab copies `readBodyOoxml()` to the clipboard (risk
R2). All text from the document or the API is rendered as React text, never as HTML.

#### Playwright

`playwright.config.ts`: `testDir` `./e2e`, `outputDir`
`../../.build/word-authoring-addin-test-results`, `use.baseURL` `http://127.0.0.1:4175/addin/`,
`use.channel` `msedge` on Windows, `webServer` `yarn dev --host 127.0.0.1` on port 4175. Tests mock
`/api/**` with `page.route`, answering from the WA1 samples and templates and the WA6 goldens, and
validate request bodies with the WA8 ajv module.

```toml
[tasks."test:authoring-addin"]
description = "Type-check, unit-test and run the harness tests of the Word authoring add-in"
depends = ["check:authoring-addin"]
run = "yarn workspace @lattice/word-authoring-addin run test"
```

#### Tests

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| S9-01 | the fake port (Vitest) / mark inside a literal, across two parts, inside a variable, with no selection, unknown element / ok and the part split, `spans-parts`, `already-marked`, `no-selection`, `outside-element` | L1 | +/- |
| S9-02 | the harness with health ok / loaded / "Connected", three templates, three samples | L6 | + |
| S9-03 | Apply template on the licence / the model / six sections in template order, each element empty. The Document tab shows each section's guidance | L6 | + |
| S9-04 | Insert sample facility / the model and metadata / the sample's sections and variables, a new documentId | L6 | + |
| S9-05 | the facility sample, `select` over `GBP 250` in element 11, key `prepayment-fee`, money / Mark variable / that part becomes a variable part and the declaration is added | L6 | + |
| S9-06 | the facility sample / Analyse / one PUT to `/api/documents/<id>/snapshot` whose body validates against `snapshot-submission` with `baseRevision` null, then validation, findings and detections shown | L6 | + |
| S9-07 | the detections of S9-06 / Accept on `[Agent]` / the model's element 13 has a variable part with text `[Agent]` and key `agent` | L6 | + |
| S9-08 | a completed job / Logical English tab / one row per element, span elements carry role classes, the legend lists the eight roles, the program text equals the golden | L6 | + |
| S9-09 | Graph tab / rendered / one SVG whose node count equals the graph view's, and the Turtle toggle shows the mocked text | L6 | + |
| S9-10 | `/api/health` failing, then a PUT answering 500 / the UI / "Disconnected", then an error banner with the message | L6 | - |
| S9-11 | `?pollTimeoutMs=1000` and a job that stays queued / Analyse / a timeout message after about a second | L6 | - |
| S9-12 | `main.tsx`'s requirement check with an `Office` stub answering false (Vitest) / rendered / the unsupported message and no `App` | L1 | - |
| S9-13 | a mocked analysis whose element text is `<img src=x onerror="window.__xss=1">` / Logical English tab / the text shows literally and `window.__xss` stays undefined | L8 | - |

**Self-probe:** render span text with `dangerouslySetInnerHTML`. S9-13 fails.

**Docs:** `ux-design.md` gains "4. Word authoring add-in (proof of concept)": the tabs, the tag
colours, the role colours, the accessibility rule (title text with every colour), anti-patterns
(writing formatting into the document, rendering document text as HTML).

---

### WA9a: Ribbon and right-click commands

**Preconditions:** WA9 committed, decision WA-D13 recorded.

**Paths:** `apps/word-authoring-addin/**`, `contracts/authoring/fixtures/suggested-keys.json` (read
only, created in WA1), `docs/architecture/ux-design.md`.

The author can mark text without the task pane open: select words, then right-click and choose from
a LATTICE submenu, or click a button in a LATTICE group on the Home tab. Commands that need input
(a variable's key and type, or which definition a term refers to) open the task pane with the form
filled in, and the author confirms there. Keyboard shortcuts are not in this unit (Word's support
for add-in shortcuts would need checking first).

#### Commands

| Id | Ribbon | Right-click | Does |
|---|---|---|---|
| `showPane` | Show pane | | opens the task pane (the WA8 button, moved into the group) |
| `markClause` | Clause | Mark as clause | `wrapSelectionAsElement("clause", new UUID)` |
| `markDefinition` | Definition | Mark as definition | `wrapSelectionAsElement("definition", new UUID)` |
| `markTerm` | Term | Mark as defined term (in its definition) | `markSelection({ kind: "term" })` |
| `markVariable` | Variable… | Mark as variable… | `readSelection()`. Empty text: the `no-selection` message. Otherwise post a variable draft to the bridge (key `suggestKey(text, type)`, label the trimmed text cut to 100 characters, type `guessValueType(text)`), switch to the Markup tab and open the pane. The author edits and clicks Mark variable |
| `markDefinedTerm` | Defined term… | Mark as reference to a defined term… | `readSelection()`, parse the body, find definitions whose term equals the text, or the text without a final `s`, `'s` or `’s`. Exactly one: `markSelection({ kind: "reference", … })`. None: post a reference draft (the text) to the bridge, switch to the Markup tab and open the pane, where the author picks the definition |
| `unmark` | Unmark | Remove LATTICE mark | `unmarkSelection()` |
| `analyse` | Analyse | | switches to the Analyse tab, opens the pane and starts the analysis |

A `MarkResult` that is not ok, or an exception, posts the reason as a message to the bridge,
switches to the Markup tab and opens the pane, so the author always sees why. Every handler calls
`event.completed()` in a `finally` block, since Word waits for it.

#### Files

| File | Contents |
|---|---|
| `src/commands/ids.ts` | `COMMAND_IDS`, the eight ids above |
| `src/commands/handlers.ts` | `createHandlers(deps: { port, bridge, showPane, newUuid })` returning one `(event) => Promise<void>` per id. No Office global is touched here, so the handlers run under Vitest and in the harness |
| `src/commands/register.ts` | `registerCommands(handlers)`: `Office.actions.associate(id, handler)` for each id. `showPane` is `() => Office.addin.showAsTaskpane()` |
| `src/app/uiBridge.ts` | a small observable store: `{ tab, variableDraft, referenceDraft, message, runAnalyse }`, `post(partial)`, `subscribe(listener)`. `App` subscribes. The Markup panel fills its forms from the drafts and shows the message. The Analyse panel runs once when `runAnalyse` is set, then clears it |
| `src/domain/keys.ts` | `suggestKey(text, valueType)` with WA3's rule, and `guessValueType(text)`: the WA3 money, percentage, date and duration patterns (JavaScript syntax, `u` flag) matched against the whole trimmed text, in that order, else `text` |
| `src/main.tsx` | after `Office.onReady`, `registerCommands(createHandlers(...))` before rendering, sharing one bridge and port with `App` |
| `src/harness.tsx` | adds `window.__harness.command(id)`, which runs the handler with a fake event and a `showPane` that records calls |

#### Manifest

Inside the existing `VersionOverrides` (V1_0), add a nested `VersionOverrides` of type
`VersionOverridesV1_1` (namespace
`http://schemas.microsoft.com/office/taskpaneappversionoverrides/1.1`), which Office reads in
place of the outer one when it understands it. In it:

- `Requirements`: `bt:Sets` with `SharedRuntime` 1.1.
- `Hosts/Host xsi:type="Document"` with `Runtimes` holding one `Runtime` with
  `resid="Taskpane.Url"` and `lifetime="long"`.
- `DesktopFormFactor`: `FunctionFile resid="Taskpane.Url"` (the shared runtime requires the same
  page for the pane, the function file and every `ShowTaskpane` action).
- `ExtensionPoint xsi:type="PrimaryCommandSurface"`: on `TabHome`, a `Group` id `LatticeGroup`,
  label `LATTICE`, with the eight ribbon controls of the table. `showPane` is a `ShowTaskpane`
  action. The others are `ExecuteFunction` actions whose `FunctionName` is the command id.
- `ExtensionPoint xsi:type="ContextMenu"`: `OfficeMenu id="ContextMenuText"` holding one `Menu`
  control, label `LATTICE`, with the six right-click items of the table as `ExecuteFunction`
  actions.
- `Resources`: every image, URL, short and long string referenced, each `resid` 32 characters or
  fewer. Icons per command are solid squares in the tag colours of WA8 (clause blue, definition and
  term purple, variable orange, defined term green, unmark and analyse grey), 16, 32 and 80 pixels,
  written with the same standard-library snippet as WA8.

The outer V1_0 overrides keep only the WA8 "Show pane" button, for Word builds without the shared
runtime.

#### Tests

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| S9a-01 | the manifest (Vitest) / parsed / a V1_1 override requiring `SharedRuntime` 1.1, one long-lived runtime, the function file and every `ShowTaskpane` on `Taskpane.Url`, eight controls in `LatticeGroup`, six items under `ContextMenuText`, the set of `FunctionName`s equal to `COMMAND_IDS` without `showPane`, every `resid` defined and at most 32 characters | L1 | + |
| S9a-02 | `registerCommands` with an `Office.actions.associate` stub / called / one association per id, none twice | L1 | + |
| S9a-03 | the handlers over the fake port / `markClause`, `markDefinition`, `markTerm`, `unmark` with a valid selection / the port changes and `event.completed` is called once. A port that throws / a message posted, the pane opened, `completed` still called once | L1 | +/- |
| S9a-04 | a selection `GBP 250` / `markVariable` / a draft with key `gbp-250`, type `money`, label `GBP 250`, Markup tab, pane opened, nothing marked yet. An empty selection / the `no-selection` message | L1 | +/- |
| S9a-05 | the facility sample / `markDefinedTerm` on `Loans` / a reference part to the Loan definition. On `Agent` / a reference draft, pane opened, nothing marked | L1 | +/- |
| S9a-06 | `suggestKey` and `guessValueType` / every case of `suggested-keys.json` / the same key and type as the Java detector (S3-02) | L3 | + |
| S9a-07 | the harness with the facility sample, a selection over `GBP 250` / `__harness.command("markVariable")`, then Mark variable / the Markup tab shows the filled form, then element 11 has a variable part `gbp-250` | L6 | + |
| S9a-08 | the harness / `__harness.command("analyse")` / the Analyse tab is active and one PUT is sent | L6 | + |

**Self-probe:** move `event.completed()` out of the `finally` block into the success path. S9a-03's
throwing case fails.

**Docs:** `ux-design.md` section 4 gains the command table and the rule that a command never fails
silently. The add-in README gains the commands.

---

### WA10: Compose stack

**Preconditions:** P6, WA5, WA7 and WA9a committed.

**Paths:** `deployment/compose/authoring/**`, `tools/authoring_stage.py`,
`tools/test_authoring_stage.py`, `apps/word-authoring-addin/playwright.stack.config.ts`,
`apps/word-authoring-addin/e2e-stack/**`, `mise.toml`, `README.md`.

#### Staging (`tools/authoring_stage.py`, standard library only)

`python tools/authoring_stage.py [--root .]`:

1. Remove and recreate `.build/authoring/` (only that directory).
2. Require `platform/authoring-service/target/authoring-service.jar` and
   `apps/word-authoring-addin/dist/taskpane.html`. A missing input exits 2 with a message naming
   the `mise` task that builds it.
3. Copy the jar and `deployment/compose/authoring/service.Dockerfile` (as `Dockerfile`) into
   `.build/authoring/service/`.
4. Run `sys.executable -m pip wheel --no-deps -w .build/authoring/worker/wheelhouse ./workers` and
   `sys.executable -m pip download --only-binary=:all: --platform any --python-version 3.14
   --implementation py --abi none -d .build/authoring/worker/wheelhouse "pika>=1.3,<2"
   "rdflib>=7.1,<8"`. Copy `worker.Dockerfile` as `Dockerfile`.
5. Copy `apps/word-authoring-addin/dist/` to `.build/authoring/addin/`.

The pip runner is a function parameter so tests replace it. Paths printed use `.as_posix()`.

#### Images

`service.Dockerfile`:

```dockerfile
FROM eclipse-temurin:25-jre
COPY authoring-service.jar /app/authoring-service.jar
USER 10001
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/authoring-service.jar"]
```

`worker.Dockerfile`:

```dockerfile
FROM python:3.14-slim
COPY wheelhouse /wheels
RUN pip install --no-index --find-links /wheels pika rdflib \
 && pip install --no-index --no-deps --find-links /wheels lattice-workers
USER 10001
ENTRYPOINT ["python", "-m", "lattice_workers.wording_analysis_main"]
```

The worker image installs `lattice-workers` without its other dependencies (`psycopg`), which the
authoring job does not import. Images build with no network access beyond the base image pull.

#### `deployment/compose/authoring/docker-compose.yml`

| Service | Image or build | Host ports (all `127.0.0.1`) | Environment | Health | Depends on |
|---|---|---|---|---|---|
| `fuseki` | `stain/jena-fuseki:5.1.0` | 3130 → 3030 | `ADMIN_PASSWORD: lattice` | `wget -qO- http://localhost:3030/$$/ping` (the image has `wget`, checked in WA0) | |
| `rabbitmq` | `rabbitmq:3.13-management-alpine` | 5673 → 5672, 15673 → 15672 | `RABBITMQ_DEFAULT_USER`, `_PASS`: `lattice` | `rabbitmq-diagnostics -q ping` | |
| `authoring-service` | build `../../../.build/authoring/service`, `platform: linux/amd64` | 8088 → 8080 | the WA5 variables: Fuseki `http://fuseki:3030`, AMQP `amqp://lattice:lattice@rabbitmq:5672/%2F`, admin password `lattice`, seed `true` | `java -cp /app/authoring-service.jar org.nebularis.lattice.authoring.app.HealthProbe http://localhost:8080/api/health`, interval 10s, retries 12, start period 20s | fuseki, rabbitmq healthy |
| `authoring-worker` | build `../../../.build/authoring/worker` | none | AMQP and Fuseki as the service, dataset `authoring`, `LATTICE_FUSEKI_USER` `admin`, `LATTICE_FUSEKI_PASSWORD` `lattice` | none | rabbitmq healthy, authoring-service healthy |
| `authoring-proxy` | `caddy:2.10-alpine` | 3443 → 3443 | | none | authoring-service healthy |

Volumes: named `authoring-fuseki` at `/fuseki`, `authoring-caddy-data` at `/data` (keeps the local
CA across restarts). The proxy mounts `./Caddyfile` at `/etc/caddy/Caddyfile` and
`../../../.build/authoring/addin` at `/srv/addin`, both read-only. `restart: unless-stopped` on the
service and worker. The credentials are local development defaults, as in the existing compose file.

`Caddyfile`:

```caddyfile
{
	local_certs
	skip_install_trust
	admin off
}

https://localhost:3443 {
	tls internal
	header {
		X-Content-Type-Options nosniff
		Referrer-Policy no-referrer
		Content-Security-Policy "default-src 'self'; script-src 'self' https://appsforoffice.microsoft.com; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'self' https://*.officeapps.live.com https://*.office.com https://*.microsoft365.com https://*.sharepoint.com https://*.cloud.microsoft"
	}
	handle /api/* {
		reverse_proxy authoring-service:8080
	}
	handle_path /addin/* {
		root * /srv/addin
		file_server
	}
	redir / /addin/harness.html
}
```

The policy is a starting point. If Word fails to load the pane because of it, the manual checklist
(WA11 M2) records the change needed, and the change is a follow-up commit.

#### `mise.toml`

```toml
[tasks."build:authoring"]
description = "Build the POC service jar and add-in, and stage the image inputs"
run = "mvn -q -f platform/pom.xml -pl authoring-service -am package -DskipTests && yarn workspace @lattice/word-authoring-addin run build && python tools/authoring_stage.py"

[tasks."authoring:up"]
description = "Start the Word authoring POC stack and seed the samples"
depends = ["build:authoring"]
run = "docker compose -f deployment/compose/authoring/docker-compose.yml up -d --build --wait"

[tasks."authoring:down"]
run = "docker compose -f deployment/compose/authoring/docker-compose.yml down"

[tasks."authoring:reset"]
description = "Stop the POC stack and delete its data and local CA"
run = "docker compose -f deployment/compose/authoring/docker-compose.yml down -v"

[tasks."authoring:ca"]
description = "Copy the POC proxy's local root certificate to .build/authoring"
run = "docker compose -f deployment/compose/authoring/docker-compose.yml cp authoring-proxy:/data/caddy/pki/authorities/local/root.crt .build/authoring/lattice-authoring-root.crt"

[tasks."check:authoring-tools"]
run = "python -m pytest tools/test_authoring_stage.py -q"

[tasks."check:authoring-stack"]
description = "Start the POC stack and run its end-to-end suite"
depends = ["authoring:up"]
run = "yarn workspace @lattice/word-authoring-addin run test:stack"

[tasks."check:authoring"]
description = "All Word authoring POC checks that need no running stack"
depends = ["check:authoring-contracts", "check:authoring-service", "check:authoring-worker", "check:authoring-addin", "test:authoring-addin", "check:authoring-tools"]
```

Also add `check:authoring-tools` to the aggregate `check` task's `depends`. The other authoring
tests already run under `check:java`, `check:workers`, `check:frontend` and `test:frontend`.

#### Stack tests

`playwright.stack.config.ts`: `testDir` `./e2e-stack`, `baseURL` `https://localhost:3443`,
`ignoreHTTPSErrors: true`, `channel` `msedge` on Windows, `timeout` 90000, no web server, workers 1.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| S10-01 | `authoring_stage.py` over a temporary tree with a fake pip runner / run / the staged layout. Without the jar / exit 2 naming `build:authoring` | L1 | +/- |
| S10-02 | the compose file / `docker compose -f … config -q` from a pytest test (skipped when `docker` is absent) / exit 0 | L0 | + |
| S10-03 | the stack / GET `/api/health` / 200 `ok`, and the CSP and `nosniff` headers present | L5 | + |
| S10-04 | the stack / templates, samples, and `GET /api/documents/<sample documentId>` for the three samples / three, three, each `latestRevision` ≥ 1 | L5 | + |
| S10-05 | the seeded facility and licence / analysis polled for up to 60 seconds / the facility has an Obligation with basis `form`, the licence's conformance has a `term-kind-not-allowed` in `grant` | L5 | + |
| S10-06 | a new snapshot (the facility sample with a new documentId) / PUT, poll the job / `completed` within 20 seconds, `graph/proposal` Turtle contains the `ins:` namespace and `Obligation` | L5 | + |
| S10-07 | the proxy / GET `/addin/taskpane.html`, `/addin/harness.html`, the manifest's icon and help URLs / 200 each | L5 | + |
| S10-08 | the harness through the proxy with the real API / Insert sample, Analyse, open the Logical English tab / rows appear with coloured spans | L6 | + |
| S10-09 | the stack / `docker compose restart authoring-service` run from the test, health polled / the seeded facility analysis is still served (from Fuseki) and no sample is seeded twice | L5 | + |

**Self-probe:** stop the worker (`docker compose stop authoring-worker`) and run S10-06. It fails on
the job timeout. Start the worker again.

**Docs:** root `README.md` layout gains `deployment/compose/authoring/  # Word authoring POC stack
(ADR-A118)` and a "Run the Word authoring POC" subsection under Developer Setup: the one command,
trusting the certificate, sideloading (pointing to the add-in README). `deployment/compose/authoring/README.md`
created: services, ports, volumes, commands, trusting the CA (`mise run authoring:ca`, then
`Import-Certificate -FilePath .build\authoring\lattice-authoring-root.crt -CertStoreLocation
Cert:\CurrentUser\Root`, which asks for confirmation and needs no administrator), and reset.

---

### WA11: Documentation and close-out

**Preconditions:** WA10 committed.

**Paths:** documentation only.

1. `apps/word-authoring-addin/README.md` gains "Load the add-in in Word": Word on the web (Home,
   Add-ins, More add-ins, My add-ins, Upload My Add-in, choose `manifest/manifest.xml`), desktop Word
   on Windows (one user-level registry value under
   `HKCU\Software\Microsoft\Office\16.0\WEF\Developer`, name `LatticeAuthoring`, data the full path
   of the manifest, then restart Word, given as a command for the human to run), central
   deployment by an administrator, and how to remove each.
2. The manual checklist below goes into the WA11 Validation Pack, to be completed by the human.
3. `docs/developer/INDEX.md` entry updated with slice states and links to the Validation Packs.
4. The status record set to "awaiting human validation", with the actual token use per slice.
5. Run `mise run check:authoring`, `mise run check:java`, `mise run check:workers`,
   `mise run check:ontology-versioning`, `mise run check:ontology-catalog`,
   `mise run topology:links`, and record the results. No ontology file changed, so no release tag
   is due.
6. Prose check of every changed Markdown file: no semicolons in English text, no superlatives.

**Manual checklist (human, real Word):**

| # | Step | Pass |
|---|---|---|
| M1 | trust the CA, open `https://localhost:3443/addin/harness.html` in Edge | no certificate warning |
| M2 | sideload in Word on the web or desktop | the ribbon button opens the pane, "Connected" shows |
| M3 | new document, Apply template (facility) | headings and section boxes appear |
| M4 | Insert sample (facility) | the sample text with coloured, titled controls |
| M5 | select `GBP 250`, Mark variable | an orange `Variable:` control |
| M6 | Analyse | findings and detections, then the LE and Graph tabs fill |
| M7 | Accept the `[Agent]` detection | the text becomes a variable control |
| M8 | save, close, reopen, Analyse | markup and metadata survive, revision 2 |
| M9 | type a new clause inside a section, mark it Clause, Analyse | the new clause is read |
| M10 | Copy body OOXML, save it as `apps/word-authoring-addin/src/domain/fixtures/word-captured-1.xml` | the file exists for a later parser test |
| M11 | close the pane, select words in a clause, right-click, LATTICE, Mark as variable… | the pane opens on Markup with the form filled in, and confirming marks the words |
| M12 | select two paragraphs in a section, Home, LATTICE, Clause | a blue Clause box wraps them |
| M13 | right-click with the selection outside any clause, Mark as variable… | the pane opens and says the selection is not inside a clause |
| M14 | repeat M11 in the other Word client (web or desktop) | record whether the ribbon group and the right-click submenu appear there |

**Commit:** `[wap] WA11: documentation and close-out`.

---

## Follow-on tranche slices: WA12 to WA20

These are drafted to the level the plan's stop rule S3 allows before their decisions (WA-D14 to
WA-D20) are recorded: scope, paths, the design points sketch §8 already fixes, and a token
estimate. Where a decision is still open, the slice says so rather than guessing a field name, a
route shape or a file layout the human has not confirmed. The detailed, field-by-field instruction
WA0 to WA11 have is written into each slice once its decisions land, following the same process
(§2.2) that produced WA0 to WA11.

### WA12: Nested clause data model

**Preconditions:** WA11 committed. Decisions WA-D16, WA-D17 recorded.

**Paths:** `contracts/authoring/**` (schemas, templates, samples, fixtures), `platform/authoring-service/**`,
`workers/src/lattice_workers/wording_le/**`, `apps/word-authoring-addin/src/domain/ooxml.ts`,
`apps/word-authoring-addin/src/word/fakePort.ts` and their tests only (no task pane or command
changes here, those are WA17's).

The foundational slice the rest of the tranche depends on: every runtime's `Element` gains a
`children` field of the same shape (WA-D16), so a clause can contain clauses. Scope:

- `document-snapshot.schema.json`: `Element.children` (array, same `Element` schema, present and
  possibly empty on every element, consistent with WA1 rule 3). A definition's `children` is always
  empty, checked at the application level (WA-D17), since JSON Schema's own recursion cannot by
  itself bound depth or restrict which kind may nest.
- `rdf.WordingMapper`: a child element is `wrd:directlyComprises` **of its parent element**, not of
  the section, with its rank key and object id extended one level per the existing pattern (plan
  §2's WA2 object id rule, generalised recursively: `(s+1).(e+1).(c+1)` for the c-th child of
  element e of section s, and so on to WA-D17's maximum depth).
- Two new SHACL shapes in `wording-poc-shapes.ttl`: one bounding nesting depth at the WA-D17 maximum
  (a SPARQL property-path count over `wrd:directlyComprises`/`wap:elementType`), one forbidding a
  non-empty `children` on anything typed `wap:Definition`.
- `detection.ConstructDetector`, `template.TemplateFindings`, `template.ConformanceChecker`: recurse
  into `children`, carrying the section's admitted term kinds down to every depth (a nested clause
  is still "in" its section for conformance purposes).
- `wording_le/model.py`'s `Element` gains `children: tuple[Element, ...]`. A clause with children
  may also carry its own parts (an introductory sentence before its nested sub-clauses), so both the
  parent and each child are analysed as their own sentence-form candidates, independently. A
  sentence form never spans a parent and a child.
- The add-in's OOXML parser and writer: a block `w:sdt` tagged as a clause may itself contain
  further block `w:sdt`s tagged as clauses (not definitions, WA-D17), read and written recursively.
  `fakePort.ts`'s in-memory model and its `selectUnmarked`-style test seams grow a nested case.

Test approach: extend WA2's N-Triples fixture regeneration and SHACL tests with a nested fixture (a
clause two and three levels deep); extend WA6's sentence-form tests with a parent-plus-children
reading; extend WA8's OOXML round-trip tests with a nested `w:sdt` fixture. A self-probe candidate:
remove the depth-bound SHACL shape and confirm a five-level fixture, which should fail, no longer
does.

**Docs:** service README's mapping table gains the child-element row. `data-architecture.md`'s
"Word authoring POC graphs" section notes that `wrd:directlyComprises` now nests under elements too.

---

### WA13: Service read APIs for the web app

**Preconditions:** WA12 committed.

**Paths:** `platform/authoring-service/**`, `contracts/authoring/**` (new response schemas only).

Three additive read routes, no existing route changed:

| Route | Reads | New schema |
|---|---|---|
| `GET /api/documents` | every document the registry holds (already written by both clients' submissions) | `document-list` (array of the existing `document-view`) |
| `GET /api/documents/{documentId}/revisions` | every revision record the registry already writes per submission (plan §2.3's "revision record") | `revision-list` (`revision`, `createdAt`, `wordingGraph` per entry) |
| `GET /api/library` | the packaged library catalogue (WA-D19), resourced the same way templates and samples already are | `library-list` / `library-entry` |

`DocumentRegistry` gains `List<DocumentView> all()` and `List<RevisionSummary> revisions(documentId)`
over data it already stores; no new write path. `template.SampleCatalog`'s loading pattern is
reused for a new `template.LibraryCatalog` over `contracts/authoring/library/*.json` (WA16 is where
the catalogue's content is authored. This slice only needs the loader and the route to exist, over
an initially empty or placeholder catalogue, since WA16 depends on this route existing first, not
the reverse).

Test approach: as WA4's route tests (each route's schema, a 200 over the seeded samples, an empty
case for a fresh store).

**Docs:** service README's route table gains the three entries.

---

### WA14: Web app shell, library and document list

**Preconditions:** WA12, WA13 committed. Decisions WA-D14, WA-D15, WA-D20 recorded.

**Paths:** `apps/word-authoring-webapp/**` (new workspace), `packages/authoring-domain/**` (new, only
if WA-D15 chooses shared modules over duplication), `mise.toml`, `README.md`.

Scaffolds the new workspace exactly as WA8 scaffolded the add-in (`package.json`, `vite.config.ts`,
`vitest.config.ts`, `tsconfig.json`, Playwright config, `mise run check:authoring-webapp` and
`test:authoring-webapp`), and builds the left-hand pane of sketch §8.2's screen: the document list
(from WA13's new route) and the library browser (from WA13's route, over WA16's eventual content),
plus the theme toggle (WA-D20). Opening a document loads its tree (built from the nested `Element`
shape WA12 added) into a skeleton middle pane, without yet supporting selection or editing (WA15).

If WA-D15 chose shared modules, this slice is also where `packages/authoring-domain` is carved out
of the add-in's existing `domain/` modules (tags, offsets, schema validation, snapshot types, API
client) with both the add-in and the new web app depending on it, and a parity test confirming
both apps resolve to the same module instance's behaviour.

**Docs:** root `README.md` layout gains the new workspace (and package, if carved out). A new
`apps/word-authoring-webapp/README.md`, matching the add-in's own style.

---

### WA15: Web app text editor and markup panes

**Preconditions:** WA14 committed.

**Paths:** `apps/word-authoring-webapp/**`.

The middle text pane (continuous prose per section, marked spans in the plan §2.3 tag colours) and
the right-hand pane's segregated panels from sketch §8.2's table: Markup (selection), Definitions,
Variables, Scope, each wired to one consistent selection model shared by the tree, text and panel
panes. The tree's "add below" affordance, filtered to the kinds WA-D17 allows at that position. This
is the tranche's largest slice, comparable to WA9: a selection anywhere in the three panes must
update all three consistently, and every edit (mark, unmark, edit a part's text, a variable's
label, a definition's term) round-trips through the same snapshot submission WA4's API already
accepts, unchanged by this tranche.

Test approach: as WA9's Playwright harness pattern, mocking `/api/**` from WA1's samples and WA12's
nested fixtures, covering selection-drives-markup, add-below's kind filtering (including the
zero-case: a definition offers nothing), and a part edited on the right updating the text pane.

**Docs:** `ux-design.md` gains a section for the web app's screen, panels and selection model,
cross-referenced from the add-in's own "how it fits together" section rather than repeated there.

---

### WA16: Web app versioning, library wordings and theming

**Preconditions:** WA15 committed. Decisions WA-D18, WA-D19 recorded.

**Paths:** `apps/word-authoring-webapp/**`, `contracts/authoring/library/**` (new).

The Versions panel (WA-D18: a list from WA13's revision route, selecting an older one re-renders
the tree and text panes read-only, no diff, no restore). The library catalogue's real content
(WA-D19: a handful of seed clauses and definitions with a kind and tags) and the library browser's
search and insert-at-tree-position behaviour, which copies a library entry's parts into the open
document exactly as "Insert sample" already does (plan WA9). Theming's dark variant, if WA14 only
wired the toggle and not every component's dark styles.

Test approach: a revision picker test (seed two revisions, confirm the older one renders its own
text), a library insert test (confirm the inserted parts match the catalogue entry and the kind
filter at the drop position is respected), a theme toggle test (the `data-theme` attribute flips,
no component left unstyled).

**Docs:** the web app README gains the library catalogue's format and the versioning behaviour.

---

### WA17: Word add-in parity

**Preconditions:** WA12 committed. WA16 committed (library content to insert from).

**Paths:** `apps/word-authoring-addin/**`.

Brings the add-in's own editing experience into parity with the web app's, per sketch §8.3: a
command to mark the current selection as a sub-clause of the clause it is inside (to WA-D17's
depth, `outside-clause` or `max-depth` reasons on failure, mirroring the existing `MarkResult`
reason pattern), a command to insert a library entry at the current position (reusing WA16's
catalogue route), and the Markup tab reorganised into the same segregated panels (Markup,
Definitions, Variables, Scope, Versions) sketch §8.2 gives the web app, rather than the single
mixed tab WA9 built. No new backend behaviour: every command here submits the same snapshot shape
WA12 already extended.

Test approach: as WA9a's handler tests (the new commands over the fake port, including the
`max-depth` and `outside-clause` reasons as explicit negative cases) and new Playwright cases for
the reorganised panels.

**Docs:** the add-in README's commands table gains the two new commands. `ux-design.md`'s add-in
section is updated to describe the segregated panels, cross-referencing WA15's web app section
rather than repeating its rules.

---

### WA18: Compose stack and cross-client integration

**Preconditions:** WA14 (web app exists), WA17 (add-in parity) committed.

**Paths:** `deployment/compose/authoring/**`, `apps/word-authoring-webapp/e2e-stack/**` (new),
`mise.toml`.

Wires the web app into the running stack as a second static path behind the same proxy (`/webapp/*`,
alongside the add-in's `/addin/*`, sketch §8.2), with a staging step mirroring WA10's
`authoring_stage.py` for the web app's build output, and a stack-level Playwright suite proving the
sketch §8.3 claim empirically rather than by inspection: a document submitted through the add-in's
fake port (or the harness) is visible in the web app's document list and tree with no new backend
step, and a document edited in the web app is immediately visible through the add-in's own API
calls. This is the cross-client proof plan §8.3 promises, run against the real stack as WA10's own
suite already runs.

Test approach: as WA10's `e2e-stack` suite, adding cases for the web app's static paths and the
cross-client round trip above. Self-probe candidate: stop the `authoring-service` container mid-test
and confirm the cross-client case fails on the expected timeout, as WA10's own self-probe did for
the worker.

**Docs:** `deployment/compose/authoring/README.md` gains the web app's service entry and path.
Root `README.md`'s "Run the Word authoring POC" section gains the web app's URL.

---

### WA19: Documentation and close-out (tranche 2)

**Preconditions:** WA18 committed.

**Paths:** documentation only.

As WA11, for this tranche: a manual checklist (open the web app, open a document pushed from the
add-in's harness, mark up text in each of the three panes, view an older revision, insert a library
entry, switch themes, then confirm the same document still opens correctly from the add-in). Status
record set to "awaiting human validation" with actual token use per slice. `check:authoring`,
`check:java`, `check:workers`, `check:ontology-versioning`, `check:ontology-catalog`,
`topology:links` run and recorded. Prose check of every changed Markdown file.

**Commit:** `[wap] WA19: documentation and close-out`.

---

### WA20: Binding authority agreement sample (deferred)

**Preconditions:** WA12 committed (nesting exists). **The CCS workstream (Wording, Instrument and
Behaviour refactoring) complete.** Do not start before both, regardless of how much of WA12 to WA19
has run.

**Paths:** `contracts/authoring/**` (a `binding-authority` template and sample, fixtures).

Sketch §8.1's rough shape: sections for grant of authority, scope of cover, underwriting limits and
referrals, claims handling authority, remuneration and deductions, reporting, and termination, each
with the term kinds a real CBAA section would admit, and at least one clause nested three levels
deep. A content-authoring slice once WA12's mechanism exists and CCS's settled Party and Instrument
vocabulary gives real terms for the roles and limits involved, rather than inventing POC-only ones
now. The estimate is provisional: it assumes no new mechanism, only content, fixtures and the
existing contract tests (WA1's AC-01 to AC-11) extended to the new sample.

Test approach: as WA1, extended to the fourth sample, including nesting-specific cases (AC-09's
cross-checks over a nested element, a demo feature for the deepest nesting case).

**Docs:** `contracts/authoring`'s own documentation (if any exists by then) gains the sample.

---

## 6. Commands, consolidated

| Task | Runs |
|---|---|
| `check:authoring-contracts` | contract, template, sample and fixture tests (WA1) |
| `check:authoring-service` | the service's unit tests (WA2 to WA4) |
| `check:authoring-service-it` | the service's container tests and jar self-check (WA5) |
| `build:authoring-fixtures` | regenerates `contracts/authoring/fixtures/wording/*.nt` |
| `check:authoring-worker` | the worker's tests (WA6, WA7) |
| `check:authoring-addin`, `test:authoring-addin` | Vitest and harness Playwright (WA8, WA9) |
| `check:authoring-tools` | the staging tool's tests (WA10) |
| `build:authoring`, `authoring:up`, `authoring:down`, `authoring:reset`, `authoring:ca` | the stack |
| `check:authoring-stack` | builds, starts and tests the stack (WA10, extended WA18) |
| `check:authoring` | everything except the stack |
| `check:authoring-webapp`, `test:authoring-webapp` | Vitest and Playwright for the web app (WA14 to WA16) |

---

## 7. Validation Pack skeleton

`docs/developer/validation/word-authoring-poc-wa<n>.md`:

```markdown
<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: word-authoring-poc WA<n>, <title>

**Plan:** [word-authoring-poc](../plans/word-authoring-poc.md) §5 WA<n>
**Status record:** [word-authoring-poc](../status/word-authoring-poc.md) (holds the commit hash)

## Invariant
<one paragraph, from the slice's purpose, citing ADR-A118, the sketch and CCS laws where relevant>

## Test cases
<the slice's table, with a Result column: pass, or the failure>

## One command
<the command, the directory (repository root), and what a pass prints>

## Artefacts to inspect
<files or outputs the human should read>

## Self-probe
<the break made, the test that failed, the restore, the green re-run>

## Implementer choices
<anything this plan left open, and what was chosen>

## Deliberate non-coverage
<what is not tested, and where it is covered, or "not in this unit">
```

Non-coverage that applies to the whole unit, cited by every pack: CCS assembly, amendments, tables
and versioned elements. LE2 parsing of the generated program. Concurrent editing. Authentication.
Poison-message retry limits (a message that always fails transiently is requeued without end).
Real Word, except through WA11's manual checklist.

---

## 8. Risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | A package, image or browser is unavailable on S | preflight P3 to P7, stop rule S4, slices ordered so that Java and Python work completes first |
| R2 | Word's OOXML differs from the hand-written fixture | M10 captures a real document, and the parser test grows a case for it |
| R3 | Testcontainers fails against Docker 29's API | P6 checks the API version, §2.7 names the fallback |
| R4 | The CSP blocks Office.js | M2 records it, a follow-up changes the Caddyfile |
| R5 | The tenant blocks sideloading | desktop registry sideload, central deployment, or the harness |
| R6 | The goldens encode a wrong reading | the WA6 pack lists the facility readings for human review before sign-off |
| R7 | Scope grows into accepting proposals or editing meaning | out of scope by the sketch §1. A follow-up unit needs its own plan |
| R8 | A Word build or Word on the web lacks the shared runtime or the right-click extension point | Word then ignores those manifest entries. The task pane still marks everything, and M14 records which clients show the commands |
| R9 | The web app duplicates the add-in's marking or validation logic and drifts out of sync with it | WA-D15 decides whether to share the TypeScript modules outright, and WA14 adds a parity test either way |
| R10 | Deep nesting makes the existing SHACL laws (W1, W5) awkward to re-check, or admits a cycle | WA12 adds an explicit depth bound and an allowed-parent shape before any sample uses nesting (sketch R7) |

---

## 9. Handoff

After WA11 the agent's last message lists, in order: the commits made (`git log --oneline
<first>^..HEAD`), the Validation Packs, any blocker or deviation, the manual checklist, and:

> The branch `ux/auth-le` holds the commits locally. Push it when the slices are validated:
> `git push origin ux/auth-le`.

No ontology document changes in this unit, so no release tag is due.

If the follow-on tranche (WA12 to WA19) runs, WA19's handoff follows the same shape, covering the
commits from WA12 onward and its own manual checklist. WA20 has no handoff of its own: it folds
into whichever later slice or unit actually schedules it, once the CCS workstream completes.
