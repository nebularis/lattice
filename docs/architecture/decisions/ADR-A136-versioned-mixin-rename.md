<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A136: The mixin `fnd:Version` is renamed `fnd:Versioned`

**Status:** Proposed 2026-10-28
**Date:** 2026-10-28
**Related:** [ADR-A113](ADR-A113-breaking-changes-at-major-version-zero.md) (a breaking change at major version zero), [ADR-A129](ADR-A129-one-release-for-the-substrate.md) (one release for the substrate)
**Described in:** [Foundation](../../../ontology/foundation/README.md), §2 and the release notes

## Context

Foundation's mixin for identity that survives change was named `fnd:Version`. Its members are classes whose instances are versions of a persistent identity, carrying `fnd:hasIdentity` and chained by `fnd:supersededBy`. The name made prose say that an instrument is a Version, which reads as nonsense, while Foundation's other mixins read as adjectives (`fnd:Evidenced`, `fnd:TemporallyScoped`, `fnd:Governable`), and the writing rules already said to call such a class "versioned". The debt was recorded as TD-20 on 2026-10-07, with 199 uses in 66 files. On 2026-10-28 there were 307 uses in 100 tracked files, across every substrate layer's spec and README, two applied modules, the Persistence compiler and its tests.

## Decision

1. **The name.** `fnd:Version` becomes `fnd:Versioned`, in Foundation's spec and README, in every layer and applied module that subclasses or names it, in every example, shape, tool and test, and in the Persistence compiler's check that a pinned edge targets a versioned class.
2. **No alias.** No `owl:equivalentClass` from the old name is kept. No adopter has pinned a release, so an alias would only make two names rank together in every tool for a release.
3. **One breaking line.** The change is breaking and takes a minor bump under ADR-A113, marked in Foundation's release notes. Under ADR-A129 every substrate and standalone module, and the applied modules that import Foundation, move together at the next release.
4. **The meaning is unchanged.** The class's restriction (exactly one `fnd:hasIdentity`), the chain, the disjointness list and the identity guide's account of a version chain are as they were.

## Consequences

- Prose reads "a class that is versioned" and "a versioned thing", and the writing rule needs no exception.
- Data written against a release before the rename is invalid against the next, which is the cost ADR-A113 accepts at major version zero.
- The knowledge index finds the term under its new name after the next rebuild.

## Provenance

The maintainer asked for the rename on 2026-10-28 while ruling on the ontology design review, and chose no alias. Built as slice OR-4 of the [ontology remediation plan](../../developer/plans/ontology-remediation.md).
