---
published: true
---
<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A129: One release for the substrate and standalone ontologies

**Status:** Published, 2026-10-20. Accepted 2026-10-20.
**Described in:** [Ontology versioning policy](../ontology-versioning-policy.md)
**Date:** 2026-10-19
**Supersedes:** [ADR-A86](https://github.com/nebularis/lattice/blob/main/docs/architecture/decisions/ADR-A86-ontology-semantic-versioning.md)'s per-document versions and exact pins, for
the modules this decision names. ADR-A86 still governs the applied modules and the examples.
**Related:** [ADR-A113](https://github.com/nebularis/lattice/blob/main/docs/architecture/decisions/ADR-A113-breaking-changes-at-major-version-zero.md) (major version zero),
[ADR-A88](https://github.com/nebularis/lattice/blob/main/docs/architecture/decisions/ADR-A88-ontology-import-resolution-for-consumers.md) (import resolution),
[ADR-A121](ADR-A121-repository-catalogue.md) (the catalogue), [ADR-A01](https://github.com/nebularis/lattice/blob/main/docs/architecture/decisions/ADR-A01-layer-dependency-order.md)

## Context

Each of 33 ontology documents had its own semantic version, and each import named an exact version of another.
A change to Foundation re-versioned 29 documents in 16 modules, with a register row and a tag each. The model
also claimed something nobody tests, that a document at one version works beside others at versions other than
the ones it was released with. Every test, shape check and reasoner run in the repository loads the documents of
one commit together, and downstream projects pin LATTICE by commit or tag (ADR-A88). A version change also says
nothing reliable about data. A new restriction, shape, disjointness, domain or key can make a graph that was
valid invalid, inconsistent, or differently entailed, whatever the semantic version calls the change.

## Decision

1. **One release.** The modules of the kinds `substrate` and `standalone` (the layers of ADR-A01's order, and
   MORK, SPC, Surface and Persistence) are released together. Every one of their versioned documents carries the
   release's number in its version IRI, which keeps its path, for example `.../lattice/eligibility/0.18.0`. A
   change to any of them, including their shapes and projections, is a new release of all of them.
2. **One place for the number.** The repository catalogue's `[conventions.release]` holds it, with the kinds
   released. Shape and projection directories of the members have no `.version` file.
3. **Imports name the release.** A member's import of another member names the same release's version IRI. The
   import guard reads layers from these IRIs as before. MORK's `Executable.ttl`, which uses Eligibility's terms,
   imports Eligibility.
4. **Applied modules and examples pin a release.** They are not in the release, keep their own versions under
   ADR-A86, and name the release's version IRIs in their imports.
5. **Semantic versioning describes the set.** ADR-A113's major-zero rule applies to the release as a whole.
6. **Release notes class every change** by its effect on a graph that was valid under the previous release: no
   effect, may invalidate, or changes meaning. A release with a "changes meaning" change ships a migration once
   an adopter holds production data.
7. **Tooling.** `mise run release:prepare -- <version>` moves every member reference to the new number in one
   substitution and regenerates the XML catalogs and the release register. The versioning check holds every
   member and every reference to it to the catalogue's number, and fails when a member changed while the number
   did not. The register lists a release once, as `ontologies-vX.Y.Z`. The maintainer creates the tag.
8. **The first release** is 0.18.0, past every member document's own previous version.

## Consequences

- A change to Foundation makes one release, one register row and one tag.
- A member document unchanged since the previous release still takes a new version IRI, since its import
  closure is new. Its content is the same, and the release notes say which layers changed.
- The per-document version number no longer shows which layer changed. Each layer's release notes do.
- Mixed sets of members are not supported, since they are not tested.
- The 217 existing register rows and 220 tags stay as history.
- Tests that assert a specific version IRI are updated at each release, as before.

## Addendum (2026-10-26): the standalone modules leave the release

**Status:** Accepted 2026-10-26, proposed the same day.

**Narrows decisions 1, 2 and 3.** Nothing in the substrate imports MORK, SPC, Surface or Persistence, so the shared number released each of them whenever any substrate layer changed, and moved its version when nothing it depends on had. The number hid which releases changed a standalone module.

1. **The release is the substrate's.** `[conventions.release]` lists the kind `substrate` alone. Decisions 1 to 3 hold for the layers of ADR-A01's order and no longer for MORK, SPC, Surface or Persistence.
2. **Each standalone module is released on its own,** as the applied modules are under decision 4. Its documents keep their own version IRIs under ADR-A86, its shape directory has a `.version` file, and the release register lists each of them. Each import of a substrate layer names the substrate release it was built against.
3. **The starting point** is 0.19.0 for every standalone document and shape directory, the release they last shared with the substrate, so no IRI changes.

Consequences. A change to a substrate layer no longer moves a standalone module's version, and a standalone module moves the substrate pin of its imports when it adopts a new substrate release, as an applied module does. `release:prepare` still moves the substrate imports of every module, the standalone modules among them, which a standalone module whose own content is unchanged now takes as a bump under ADR-A86.

## Provenance

**Unit:** [`improved-ontology-documentation`](../../developer/plans/improved-ontology-documentation.md) (plan)

Proposed in the [release model sketch](../../developer/sketches/ontology-release-model.md) and decided as OD-D55
to OD-D59 and OD-D63 of the [`improved-ontology-documentation`](../../developer/plans/improved-ontology-documentation.md)
plan, from the maintainer's answers of 2026-10-19 to REL-Q1 to REL-Q6 and REL-Q2a. Built in its slice VER1.
