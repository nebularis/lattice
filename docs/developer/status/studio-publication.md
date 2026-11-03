<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Publication from the Configuration Studio - Status

**Unit ID:** `studio-publication`
**Status:** built 2026-10-31. PB-1 to PB-17 built 2026-10-31, phase D done
**Last updated:** 2026-11-02
**Plan:** [studio-publication.md](../plans/studio-publication.md)
**Sketch:** [studio-publication.md](../sketches/studio-publication.md)
**ADR:** [A-149](../../architecture/decisions/ADR-A149-publication-from-the-studio.md), Proposed

## Current position

The maintainer answered PB-Q1 to PB-Q3, PB-Q6 and PB-Q7 on 2026-10-31, asked for pluggable authentication with a simple default now, and left PB-Q4's timing of workspace modes and PB-Q5 to the unit. The unit chose modes with authentication in phase B, and the studio's own store on persistence profiles after publication, in phase D. The maintainer asked for the whole plan to be built in order, with a Sonnet subagent for mechanical work.

**Decisions taken alone, for ratification:** PB-D1 to PB-D5 in the plan's §2, and ADR-A149 decisions 9 and 11.

PB-1 was built on 2026-10-31. A validation, compilation or dry run names the workspace's other parts as context graphs, which the worker reads like the baseline, reporting only on the target part. A concept goes with its scheme when the scheme went to mapping, in the browser and the service. TD-133 is closed. The `policies` sample's `Peril` writes both covers' perils live. Checks run 2026-10-31, all passing: `check:config-studio`, `check:workers` (163), `check:knowledge`, `check:identifiers`. The Java side was written by a Sonnet subagent and reviewed.

One Validation Pack holds every slice, each a section, as the `config-studio` unit's does.

PB-2 was built on 2026-10-31. The service authenticates every request but `/api/health` and `/api/session` through a pluggable `Authenticator`: `local`, the default, which offers the developer principals `developer`, who administers, and `reviewer`, and refuses any address but loopback, and `oidc`, which validates a provider's bearer tokens with `nimbus-jose-jwt` 10.3 against its published keys, for any provider such as Okta, Microsoft Entra ID or AWS Cognito. Every command carries its principal, which the writer records on its receipt. The browser signs in through `/api/session`, with a principal picker under `local` and the authorization code flow with PKCE under `oidc`. TD-134 records that the Word add-in sends no credentials. Checks run 2026-10-31, all passing: `check:config-studio`, `check:knowledge`, `check:identifiers`, and the service module's 101 tests. The tests were written by a Sonnet subagent and reviewed. Checked live under `local`: the header shows the principal, switching to `reviewer` signs in as reviewer, and an unknown name is refused.

PB-3 was built on 2026-10-31. A workspace's creator owns it and sets its mode, locked, read-only or shared, with `POST /api/workspaces/{ws}/access`. The service hides what a principal may not read, the writer refuses a write the mode does not allow, and the MCP server lists only readable workspaces. A workspace from before modes is shared with no owner. Checks run 2026-10-31, all passing: `check:config-studio`, `check:knowledge`, `check:identifiers`, and the service module's 112 tests. Checked live: the five existing workspaces read as shared to `reviewer`, and a locked workspace of `developer` is hidden from `reviewer`.

PB-4 and PB-5 were built on 2026-10-31. A publish job takes a unit's aggregate from the part as saved, by the units table `contracts/config-studio/publication-units.ttl`, digests it with RDFC-1.0 and names its version `{lineage}/rev/1-{digest}`. `POST /api/workspaces/{ws}/publications?job=…` sends a `publish` command, and the writer adds the version, its event and the current pointer to the lineage's registry graph, guarded on the current version, and changes nothing when the version is already current. The registry is read at `/api/registry`, `/api/registry/lineage` and `/api/registry/version` by any signed-in principal, and the browser's Publish view lists each part's units with their current version. The Java side was written by a Sonnet subagent and reviewed. It added the publish job's four result predicates to the writer's list of those a worker may write, without which no publish job could finish. Checks run 2026-10-31, all passing: `check:config-studio`, `check:workers` (169), `check:knowledge`, `check:identifiers`, and the service module's tests. Checked live: the employment sample's concept scheme published from the browser, republished unchanged with no second event, and read back with its six concepts. The test lineage was then dropped from the store by hand, since the registry has no deletion.

PB-6 was built on 2026-10-31. A workspace depends on published lineages, which it follows, or versions, which it pins, with `PUT /api/workspaces/{ws}/dependencies`. Its validation, compilation, dry run and publish jobs read what each resolves to as context, under the version's IRI and its lineage's. Publishing rewrites a reference to a followed lineage to its current version, keeps a reference to a member of a version, records each with `cst:pins`, and fails on a reference to an unpublished unit. The Publish view lists the dependencies and the registry to follow or pin from. The Java side was written by a Sonnet subagent and reviewed. Checked live, which found that the writer refused a job update carrying `cst:pins`, now fixed with a test. Checks run 2026-10-31, all passing: `check:config-studio`, `check:workers` (173), `check:knowledge`, `check:identifiers`, and the service module's tests. The live check's two workspaces and four registry graphs were removed.

PB-7 was built on 2026-10-31. A fence job digests an imported graph, and `POST /api/workspaces/{ws}/imports` stores it once at `urn:lattice:studio:import:{digest}`, held by the workspace with a label and read only. The workspace's jobs read its held imports as context, a unit may be published from an import, and releasing one leaves the graph for any other workspace that holds it. The Publish view imports a Turtle or RDF/XML file and lists held imports and their units. TD-135 records that an export omits its imports' content and that nothing removes an import no workspace holds. The Java side was written by a Sonnet subagent and reviewed. It also hides the import labels of a workspace a principal may not read. Checks run 2026-10-31, all passing: `check:config-studio`, `check:workers` (175), `check:knowledge`, `check:identifiers`, and the service module's 132 tests. Checked live, and the test data removed.

The worker side of PB-8, the provenance of compiled artefacts, went in with PB-7's commit, since it shares the worker's file.

PB-8 and PB-9 were built on 2026-10-31. A compile job may compile a published version, and each compiled artefact is a `fnd:DerivedArtefact` derived from what it compiled and every version it read. `GET /api/registry/bundle` gives a version with every version it pins as TriG, each graph named by its version, and the Publish view downloads it. The browser's world now holds what the workspace depends on and imports, so a reference field offers a followed scheme by its lineage, and a choice built from a range's individuals offers the world's members too, found live when a binding's scheme field offered only the layers' own schemes. The Java side of PB-8 was written by a Sonnet subagent and reviewed. Checks run 2026-10-31, all passing: `check:config-studio`, `check:workers` (175), `check:knowledge`, `check:identifiers`, and the service module's 136 tests. Checked live, and the test data removed.

PB-10's brief is the sketch's §9, PB-Q8 to PB-Q11: how the Java writer runs generated operations, what the studio's aggregates are, what its own surface contracts project, and how stores written before phase D move.

The maintainer answered PB-Q8 to PB-Q11 on 2026-10-31: a Java port of the caller library, the aggregates of ADR-A149 decision 13 with operations ordered so a partial write is harmless and every part's history in the patch log, five projections including the terms of published versions now, and an in-place migration with no compatibility path. The answers are ADR-A149 decisions 12 to 14, and the plan's phase D is PB-11 to PB-16. PB-D6 and PB-D7 were taken alone. Working that through raised PB-Q12, when a projection is brought up to date, in the sketch's §10.

PB-11 was built on 2026-10-31. `packages/persistence/java` ports ADR-A132's caller library to Java, depending on the JDK and Jena 5.1.0 (PB-D6), and passes every vector on its first run. Python's `$` accepts a trailing line feed where Java's whole-string match does not, so the Python library accepts a digest, a language tag or an `xsd:long` lexical form ending in one. No vector covers it. The library was written by a Sonnet subagent and reviewed. Checks run 2026-10-31, all passing: `check:persistence-library` (Java 104, Python 113, vectors 91).

PB-12 was built on 2026-10-31. `contracts/config-studio/persistence-profile.ttl` declares six named-graph families, which the stage compiles with the caller naming each graph and instantiates for the service (PB-D7). A blank node is stored as a skolem IRI named by what it says and where it is named from (PB-D8), and the service and the worker read it back as a blank node. Checks run 2026-10-31, all passing: `check:config-studio` (browser 109), the stage tests, `SkolemTest`, the worker's tests, `persistence hygiene` over the profile, `check:knowledge` and `check:identifiers`.

**Found while writing PB-12.** The generated named-graph `cas-replace` fills its whole payload once per stored triple, as TD-42 found for the composite replace, and took 28 s on Jena in memory for a 3,000-triple part, where two guarded operations in one request took 0.11 s. That is PB-Q13 in the sketch's §9, and PB-13 to PB-15 wait for it.

The maintainer answered PB-Q13 (b) and PB-Q12 (b) on 2026-10-31. The compiler is not changed until a linear replace is investigated, which the [linear replace sketch](../sketches/persistence-linear-named-graph-replace.md) briefs for another session. The writer replaces parts and documents by hand meanwhile, recorded as ADR-A149's addendum and TD-136. Projections are refreshed by worker jobs, and a surface backend that maintains them in the writer's request is BL-09.

PB-13 was built on 2026-10-31. `StudioOperations` loads the staged profile and operations, checks and binds each request through the Java caller library, and derives the linear replace of TD-136 from the generated replace's syntax tree, which leaves what the generated one leaves. A tombstoned root cannot be created again, so an import is never tombstoned. Written by a Sonnet subagent and reviewed. Checks run 2026-10-31, all passing: `check:config-studio`, with `StudioOperationsTest`'s 15 tests.

PB-14 was built on 2026-10-31. Every workspace command but publishing runs the generated operations in the order of ADR-A149 decision 13, with its receipt last and guarded on its last operation's claim. A part's revision is its version row's sequence, and an earlier revision is read from the patch log at `?revision=n`. Written by a Sonnet subagent and reviewed. The review tied the worker's reading of a job's baseline to the job's own workspace. Checks run 2026-10-31, all passing: `check:config-studio` (core 23, service 143, writer 3, browser 109) and `check:workers` (179). Not checked live, since the existing store needs PB-16's migration to open.

PB-15 was built on 2026-10-31. Publishing creates the version, then creates or replaces the lineage under the sequence it read, then writes its receipt guarded on the lineage's claim, so a lost race is stale and its orphaned version is reused. Written by a Sonnet subagent and reviewed. Checks run 2026-10-31, all passing: `check:config-studio` (core 24, service 147, browser 109) and `check:workers` (181).

PB-16 was built on 2026-10-31 and run on the maintainer's store. `mise run studio:migrate` backs the store up as TriG, then moves each workspace in one request, its baseline revisions replayed into the patch log, then the registry and the imports, and drops the old graphs and jobs. Its first live run stopped at the backup, which Fuseki's update service refused, and wrote nothing. Fixed, it moved 5 workspaces and 17 parts, every part isomorphic to the backup, and a second run found nothing. Saving, a stale save, an earlier revision and publishing were then checked live on a test workspace, since removed. Written by a Sonnet subagent and reviewed. Checks run 2026-10-31, all passing: `check:config-studio` (writer 10).

Trying the surface compiler on the projections raised PB-Q14 in the sketch's §10, how each projection is expressed, since the workspace summary joins rows by a root's prefix, which no read path expresses.

The maintainer answered PB-Q14 (b) on 2026-10-31.

PB-17 was built on 2026-10-31. Four surface promotions and the summaries query are rebuilt by one coalesced refresh job, whose update the writer takes as the projection graphs, and the service waits for it after commands a listing shows. The registry, the workspace listing and the jobs of a workspace read projections, and holders and terms have routes. Written by a Sonnet subagent and reviewed. Checked live on the migrated studio, which found that setting dependencies did not wait for its refresh, now fixed. Checks run 2026-10-31, all passing: `check:config-studio` (service 158) and `check:workers` (187).

**Next action, for the maintainer:** review ADR-A149 with its addendum and decision 14, PB-D1 to PB-D13, and TD-136. The linear replace sketch waits for its own session. For the maintainer, review ADR-A149 with its addendum, and PB-D1 to PB-D13.
## Slices

| Slice | Deliverable | State | Blocked on |
|---|---|---|---|
| PB-1 | a job's input and its findings | built 2026-10-31 |  |
| PB-2 | the `Authenticator` seam, `local` and `oidc` | built 2026-10-31 |  |
| PB-3 | a workspace's owner and mode | built 2026-10-31 |  |
| PB-4 | the `cst:` publication terms and the `publish` job | built 2026-10-31 |  |
| PB-5 | the registry's read API and browser | built 2026-10-31 |  |
| PB-6 | a workspace's dependencies, followed or pinned | built 2026-10-31 |  |
| PB-7 | fenced imports stored once by digest | built 2026-10-31 |  |
| PB-8 | artefacts naming their sources, the bundle export | built 2026-10-31 |  |
| PB-9 | vocabulary bindings that select a published edition | built 2026-10-31 |  |
| PB-10 | a brief, the working store as persistence profiles | built 2026-10-31 |  |
| PB-11 | the Java caller library | built 2026-10-31 |  |
| PB-12 | the studio's persistence profile | built 2026-10-31 |  |
| PB-13 | the operations layer, `StudioOperations` | built 2026-10-31 |  |
| PB-14 | the writer's workspace commands on PB-13 | built 2026-10-31 |  |
| PB-15 | the registry on PB-13 | built 2026-10-31 |  |
| PB-16 | the migration of a store written before phase D | built 2026-10-31 |  |
| PB-17 | the projections of ADR-A149 decision 14 | built 2026-10-31 |  |

## Log

- 2026-10-31: the maintainer challenged the part rule (MEC-94) and set out publication. Sketch, plan and ADR-A149 written. BL-08 added for uploaded files that are not graph data.
- 2026-10-31: PB-1 built. TD-133 closed. MEC-94 now says where a subject is saved, and MEC-97 records a job's context.
- 2026-10-31: PB-2 built. `nimbus-jose-jwt` 10.3 added to the service for token validation. TD-134 added.
- 2026-10-31: PB-3 built.
- 2026-10-31: PB-4 and PB-5 built. PB-D1 to PB-D3 revised to what was built. MEC-98 and MEC-99 added.
- 2026-10-31: PB-6 built.
- 2026-10-31: PB-7 built. TD-135 added.
- 2026-10-31: PB-8 and PB-9 built. PB-10's brief written, PB-Q8 to PB-Q11 raised.
- 2026-10-31: PB-Q8 to PB-Q11 answered, ADR-A149 decisions 12 to 14 added, phase D planned as PB-11 to PB-16, PB-Q12 raised.
- 2026-10-31: PB-11 and PB-12 built. TD-42 extended with the named-graph replace's cost on Jena. PB-Q13 raised.
- 2026-10-31: PB-Q12 and PB-Q13 answered (b). The linear replace sketch written, TD-136 and BL-09 added, ADR-A149 decision 12 narrowed by an addendum.
- 2026-10-31: PB-13 split from the writer's commands and built.
- 2026-10-31: PB-14 built.
- 2026-10-31: PB-15 built.
- 2026-10-31: PB-16 built, and the maintainer's store migrated.
- 2026-10-31: PB-17 built, phase D done.
- 2026-11-02: `main` merged in, with the work board. The plan declares the prefix PB, the slices are PB-1 to PB-17, and the record has a board.
