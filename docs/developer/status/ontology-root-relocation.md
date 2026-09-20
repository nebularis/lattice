<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Ontology Root Relocation Status

**Unit:** `ontology-root-relocation`
**State:** Accepted
**Decision:** [ADR-A77](../../architecture/decisions/ADR-A77-repository-topology-and-documentation-governance.md)
**Review:** [Ontology Root Relocation Review](../review/ontology-root-relocation-review.md)
**Governing ADR:** [ADR-A77](../../architecture/decisions/ADR-A77-repository-topology-and-documentation-governance.md)

## Scope

Move the common LATTICE semantic roots to `ontology/`:

`foundation`, `vocabulary`, `quantification`, `party`, `eligibility`, `behaviour`, `instrument`, `surface`, `applied`, `governance`, and `examples`.

This unit excludes MORK and SPC, which have their own semantic and executable split units.

## Completed

- ADR-A77 was accepted.
- The decision catalogue and developer work repository have moved to their canonical locations.
- `mise run topology:preflight`, `mise run topology:ready`, and `mise run topology:links` completed successfully.
- The topology checker exposes pre-move readiness and documentation-link checks.
- Moved all common LATTICE semantic roots into `ontology/` using `git mv`.
- Repointed CI extraction, conformance fixtures, root Python test discovery, and direct Surface and Eligibility fixture lookups.

## Acceptance

The common semantic roots, documentation references, and topology checks are accepted. Ecosystem validation is recorded in the dependent package and platform handoffs.
