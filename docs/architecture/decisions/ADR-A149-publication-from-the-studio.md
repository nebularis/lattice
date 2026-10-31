<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A149: Publication from the Configuration Studio

**Status:** Proposed
**Date:** 2026-10-31 (proposed)
**Related:** ADR-A136 (the studio), ADR-A51 (IRIs and identity), ADR-A142 (meaning-bearing edges), ADR-A143 (one canonicalisation), ADR-A122 (aggregate ownership), ADR-A38 (the Surface output publisher), ADR-A13 (graph roles)
**Unit:** [`studio-publication`](../../developer/plans/studio-publication.md)

## Context

The studio keeps an adopter's configuration in workspaces, each part a named graph read only by that part's jobs. Nothing a workspace holds is versioned, no workspace reads another's content, and the service authenticates nobody. A deployment that takes a compiled artefact cannot say which configuration it came from, two workspaces that need one vocabulary each copy it, and a mapping cannot read the source codes another part holds.

Foundation's versions (MEC-01), the IRI policy's lineage, content revision and promotion IRIs (ADR-A51), one digest (ADR-A143) and the rule for meaning-bearing edges (ADR-A142) already say what a version is. The studio does not yet use them.

## Decision

1. **Publication is explicit.** A unit is published only when a user publishes it. Nothing is published by saving, compiling, importing or exporting.
2. **A unit is an aggregate, published on its own.** A concept scheme, a scheme contract, a binding set, a quantification declaration, an eligibility profile, a persistence profile, a surface contract, a mapping scheme, a form or a form's stated meaning is published as a version of its own lineage. Its references to other units are pinned to their versions. Publishing never copies another unit's content into it.
3. **A version's IRIs follow ADR-A51.** The lineage is the draft root's IRI. The version is `{lineage}/rev/1-{digest}`, the digest the first 16 hexadecimal digits of the RDFC-1.0 SHA-256 of its content, so unchanged content names the same version. The publication is a `prov:Activity` at `{lineage}/evt/e{epoch}/{seq}` with its principal, its time and every version it read, chained to the one before. A current pointer names the latest version. The root is rewritten to the version's IRI with `fnd:hasIdentity` to the lineage, and the nodes it owns keep their IRIs inside the version's own immutable graph.
4. **A registry holds the versions, and a port gives them out.** The registry is part of the studio's store, readable by every signed-in user from every workspace. A deployment takes a version through the port's adapters: the registry's read API, a bundle export of a version with everything it pins, and an adapter that writes into a deployment's store through the deployment's own write path. A version's graph name inside the studio is never part of its identity.
5. **A draft follows or pins.** A draft that names a lineage follows its latest version, and one that names a version is pinned to it. Publishing resolves every followed reference to the current version and rewrites the edge to it. A draft that refers to anything unpublished cannot be published.
6. **Imports are fenced.** What an import leaves in the graph is stored once by the digest of its content, read only, and can be referred to. It is unpublished until a user publishes it.
7. **A part decides where a statement is saved, never what is read.** A job reads its target part, the workspace's other parts, its fenced imports and the closure of its dependencies, and reports findings about the target part's subjects. A workspace's dependencies are published versions or lineages from any workspace. When an import is sorted, a concept goes with its scheme.
8. **Authentication is pluggable.** The default, `local`, offers named developer principals and refuses to start on any address but loopback. `oidc` validates the bearer tokens of an OpenID Connect provider against its published keys and reads administrators from a configured claim. Every command carries its principal.
9. **A workspace has an owner and a mode.** Its creator owns it. A locked workspace is read and written by its owner and administrators, a read-only one is read by everyone signed in and written by its owner and administrators, and a shared one is read and written by everyone signed in. A workspace from before this decision has no owner and is shared. The revision check holds in every mode.
10. **Artefacts name their sources.** A compiled artefact is a `fnd:DerivedArtefact` whose `fnd:DerivationRun` used the versions, or the draft revisions, it was compiled from.
11. **The studio moves onto its own substrate after publication.** Its working store's layout is then declared as persistence profiles and its write path generated, in a later phase with its own questions.
12. **The writer calls generated operations through a Java caller library.** `packages/persistence/java` ports ADR-A132's caller library, held to the same vectors, and the writer binds the operations the persistence compiler generates for the studio's profiles instead of building SPARQL Update by hand. The writer keeps what is not persistence, such as the access gate, the modes and the refusals of a publication.
13. **The studio's aggregates.** The workspace description, each part of a workspace and each document are named-graph aggregates under optimistic concurrency, every part keeping its history in the patch log. A published version is created once and never replaced, and a lineage is replaced under the guard of its current version. A command that writes several aggregates orders its operations so that a guard failing part way leaves nothing a reader acts on: a version before its lineage, the parts before the description on creation, the description first on deletion. Jobs are coordination data (PRI-52), so they are written outside the profiles.
14. **The studio reads through projections.** The registry listing, the workspace summaries, the jobs of each workspace, the holders of each lineage and import, and the terms of every published version are surface contracts over the store, derived and rebuilt from it, never authoritative. A write that changes a projection's source queues a refresh job, which the worker runs with the surface compiler over the aggregates the write changed, so a projection lags its source by a job, and a reader that must see its own write waits for the job. The registry listing, the jobs of each workspace, the holders and the terms are surface promotions. The workspace summary joins a workspace to its parts' version rows by their roots, which no surface read path expresses, so it is a query kept beside the promotions in the contract, run by the same job.

## Consequences

- A deployment can pin and fetch exactly what it runs, by IRI, and store it in its own layout.
- One published vocabulary serves every workspace, and a workspace that edits it holds one working copy until it publishes an edition.
- A job's input grows by the other parts and the dependency closure, and a cached compile is keyed on all of their revisions, not on one part's.
- The service needs an identity provider in production. The `local` provider keeps development free of one.
- Rewriting a root's IRI and its pinned edges makes a published version differ from its draft by those terms, which a reader of both must expect.
- Large drafts are stored whole. A draft held as a change over its base waits for a measured need.
- Each save also reads the part it replaces, to write the patch log's delta, and confirms its write by reading the transaction's claim, so a save costs two reads and one update where it cost one read and one update.
- Graph names change to the profiles' templates, so a store written before decision 13 is migrated once.
- A part's payload holds no blank node, so the store skolemises on write and reads a skolem IRI back as a blank node.

## Addendum, 2026-10-31

**Narrows decision 12.** The generated named-graph replace builds its payload once per stored triple, which took 28 s on Jena for a 3,000-triple part. Until a linear form is settled, the writer replaces a part and a document through a hand-written request that guards on the same version row and writes the same receipt and patch-log delta. It relies, as the writer did before this decision, on Fuseki applying one request in one transaction, and on the writer applying one command at a time. The writer runs the generated operations for every other family and every other operation (TD-136).

## Provenance

Raised by the maintainer on 2026-10-31, while deciding how a source's codes reach a mapping (TD-133). The maintainer answered PB-Q1 to PB-Q3, PB-Q6 and PB-Q7 the same day, asked for authentication now, and left PB-Q4's timing of modes and PB-Q5 to the unit, which chose decisions 9 and 11. They answered PB-Q8 to PB-Q11 the same day, which became decisions 12 to 14, and accepted three projections beyond the two first proposed in decision 14. The [sketch](../../developer/sketches/studio-publication.md) holds the questions.
