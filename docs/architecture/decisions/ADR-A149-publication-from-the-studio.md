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

## Consequences

- A deployment can pin and fetch exactly what it runs, by IRI, and store it in its own layout.
- One published vocabulary serves every workspace, and a workspace that edits it holds one working copy until it publishes an edition.
- A job's input grows by the other parts and the dependency closure, and a cached compile is keyed on all of their revisions, not on one part's.
- The service needs an identity provider in production. The `local` provider keeps development free of one.
- Rewriting a root's IRI and its pinned edges makes a published version differ from its draft by those terms, which a reader of both must expect.
- Large drafts are stored whole. A draft held as a change over its base waits for a measured need.

## Provenance

Raised by the maintainer on 2026-10-31, while deciding how a source's codes reach a mapping (TD-133). The maintainer answered PB-Q1 to PB-Q3, PB-Q6 and PB-Q7 the same day, asked for authentication now, and left PB-Q4's timing of modes and PB-Q5 to the unit, which chose decisions 9 and 11. The [sketch](../../developer/sketches/studio-publication.md) holds the questions.
