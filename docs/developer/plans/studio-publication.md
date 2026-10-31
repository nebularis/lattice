<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: publication from the Configuration Studio

**Unit ID:** `studio-publication` (PB)
**Unit type:** multi-slice unit in four phases, validation gate per slice
**Status:** PB-Q1 to PB-Q7 answered 2026-10-31. ADR-A149 Proposed. PB1 to PB9 built 2026-10-31. PB-Q8 to PB-Q11 answered 2026-10-31. PB-Q12 waits for the maintainer
**Sketch:** [studio-publication.md](../sketches/studio-publication.md)
**Status record:** [studio-publication.md](../status/studio-publication.md)
**ADR:** [A-149](../../architecture/decisions/ADR-A149-publication-from-the-studio.md), Proposed
**Depends on:** ADR-A136 and its amendments, the `config-studio` and `mork-transforms` units on the same branch
**Takes on:** TD-133, TD-99's missing principal

## 1. Goal and acceptance

A user signs in, makes a workspace with a mode, publishes a unit from it as a version, depends on that version from another workspace without copying it, and hands a deployment the version and every version it pins. Accepted when each phase's demonstration below runs live in the studio and every slice's Validation Pack passes.

## 2. Decisions

The answers are in the [sketch](../sketches/studio-publication.md) §8 and ADR-A149. The unit takes these smaller decisions alone and records them in the status record for ratification.

| ID | Decision |
|---|---|
| PB-D1 | A version's digest is computed by the Python worker in a `publish` job, with pyoxigraph's RDFC-1.0, as MORK's own digest is. The writer checks the version's form and that it names its lineage, not the digest, since the worker is trusted (ADR-A35) and the JVM side has no RDFC-1.0 implementation |
| PB-D2 | The registry's graphs are `urn:lattice:studio:pub:{hash of lineage}` for a lineage's versions, events and current pointer, and `…:rev:{digest}` for a version's content. A `publish` command is routed by the workspace it is published from, and the writer guards on the lineage's current version, so a race between two workspaces publishing one lineage is refused, not forked |
| PB-D3 | The units, their root classes and what each owns are one table in the contract, read by the browser, the service and the worker. Ownership is the nodes naming the root by the unit's member property, the blank nodes reached from either, and the named nodes minted under the root's IRI. The table is `contracts/config-studio/publication-units.ttl` |
| PB-D4 | A fenced import's graph is `urn:lattice:studio:import:{digest}`, shared by every workspace that holds it, and a workspace lists the imports it holds |
| PB-D5 | `local` authentication sends the principal's name in a header, from a picker in the browser. `oidc` takes a bearer token, which the browser obtains by the authorization code flow with PKCE |
| PB-D6 | The Java caller library depends on the JDK and Apache Jena 5.1.0, the version the platform uses, since it reads a compiled profile as RDF, as the Python one depends on rdflib. Its canonical N-Triples is its own encoder, never Jena's writer, so the vectors hold it byte for byte |
| PB-D7 | The studio's persistence profile is a contract, `contracts/config-studio/persistence-profile.ttl`, compiled and instantiated by the stage tool into the directory the service reads, so the service never runs the compiler and a stale operation cannot outlive a restart |
| PB-D8 | A blank node is stored as a skolem IRI named by the digest of what it says and where it is named from, never a random name, so a save that leaves a node and its ancestors unchanged names it as before and the patch log's delta holds only what changed. Every reader reads a skolem IRI back as a blank node |
| PB-D9 | Every family guards on its row's epoch only, the epoch a setting of the service, 1 until a restore. The store keeps the epoch (`dal:StoreLocalEpoch`'s warning), since the studio is restored by its operator, who bumps the setting |

## 3. Phases and slices

### Phase A, what a job reads

| Slice | What | Done when | Estimate |
|---|---|---|---|
| PB1 | a job's input is the target part and the workspace's other parts as context, findings kept on the target's subjects. When an import is sorted, a concept goes with its scheme, in `split.ts` and `Parts.java` | the `policies` sample's `Peril` writes its triples in the studio, and TD-133 is closed | 150k tokens |

### Phase B, who may do what

| Slice | What | Done when | Estimate |
|---|---|---|---|
| PB2 | the `Authenticator` seam in the service with `local` and `oidc`, the principal on every command, the browser's sign-in, the MCP server's bearer token | every route refuses an unauthenticated request, and an `oidc` token signed by a test key is accepted while an expired or foreign one is refused | 250k tokens |
| PB3 | a workspace's owner and mode, enforced by the service on reads and by the writer on writes, set in the browser | each mode's table row of the sketch §6 holds for an owner, another user and an administrator | 200k tokens |

### Phase C, publication

| Slice | What | Done when | Estimate |
|---|---|---|---|
| PB4 | the `cst:` terms for publication, the units table, and a `publish` job and command that mint a version, its event and its pointer in the registry | publishing a concept scheme twice unchanged names one version, and changed names a second that supersedes it | 300k tokens |
| PB5 | the registry's read API and browser: publish a unit, a lineage's history, read a version, fenced | a published version is listed and readable from another workspace | 200k tokens |
| PB6 | a workspace's dependencies, followed or pinned, read by its jobs, resolved and rewritten on publishing | a mapping in one workspace that follows a scheme in another is published pinned to that scheme's current version | 250k tokens |
| PB7 | fenced imports: an import stored once by digest, held read only, publishable | importing ODRL's vocabulary into two workspaces stores it once, and neither can edit it | 200k tokens |
| PB8 | artefacts naming their sources, and the bundle export of a version with what it pins | a compiled RML artefact names the mapping version it came from, and a bundle carries it with the scheme it pins | 150k tokens |
| PB9 | vocabulary bindings that select a published edition | a binding selects an edition from the registry and validation resolves it | 150k tokens |

### Phase D, the studio on its own substrate

| Slice | What | Done when | Estimate |
|---|---|---|---|
| PB10 | a brief: the studio's working store declared as persistence profiles, and how the Java writer calls generated operations (BL-06) | the maintainer has answered its questions | 80k tokens, done |
| PB11 | the Java caller library, `packages/persistence/java`, a port of ADR-A132's held to the same vectors | `check:persistence-library` passes every vector in both languages | 250k tokens |
| PB12 | the studio's persistence profile for the description, the parts, the documents, the versions and the lineages, compiled and instantiated by the stage tool, and the store's skolemisation of blank nodes on write and its reverse on read | the stage writes every family's operations with no refusal, and a part holding blank nodes reads back as it was saved | 150k tokens |
| PB13 | the writer's workspace commands on the generated operations: create, save with the patch log's delta, import, delete, documents, access, dependencies and imports, each confirmed by its claim, and ordered as ADR-A149 decision 13 says. A part's earlier revision read from the patch log | the service's tests pass with every guard in the generated SPARQL, a lost race reads as stale, and the baseline's earlier revisions read back from the log | 400k tokens |
| PB14 | the registry on the generated operations: a version created once, a lineage replaced under its current version | two workspaces racing to publish one lineage leave one current version, and publishing again after a lost race reuses the orphaned version | 150k tokens |
| PB15 | a task that migrates a store written before phase D in place, once | the five existing workspaces open, save and publish after the migration, and their baseline history reads back | 100k tokens |
| PB16 | the projections of ADR-A149 decision 14, maintained as PB-Q12 decides | waits for PB-Q12 | waits for PB-Q12 |

## 4. Demonstrations

- **Phase A.** The `policies` sample's XML and JSON runs show `Peril`.
- **Phase B.** Two developer principals see a locked workspace differently.
- **Phase C.** A scheme published in one workspace is followed by a mapping in another, the mapping is published pinned, and its bundle carries both.
- **Phase D.** The migrated store's workspaces are edited, published and listed through generated operations and projections, and a baseline's earlier revision is read from the patch log.
