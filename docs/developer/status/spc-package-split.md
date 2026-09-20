<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# SPC Package Split Status

**Unit:** `spc-package-split`
**State:** Accepted
**Decision:** [ADR-A77](../../architecture/decisions/ADR-A77-repository-topology-and-documentation-governance.md)
**Governing ADRs:** [ADR-A77](../../architecture/decisions/ADR-A77-repository-topology-and-documentation-governance.md), [ADR-A29](../../architecture/decisions/ADR-A29-repository-toolchain-and-environment-boundary.md), [ADR-A30](../../architecture/decisions/ADR-A30-shared-semantic-platform-cross-runtime-boundary.md)

## Completed

- Moved SPC semantic assets to `ontology/spc/`.
- Moved the Python toolchain project to `tools/spc/python/`.
- Moved the Mix/Erlang runtime project to `tools/spc/erlang/`.
- Updated the retained `mise` Mix dispatch path to `tools/spc/erlang`.
- Preserved SPC's semantic non-integration boundary.

## Acceptance

The semantic/executable split, canonical path rewrite, and Python/Mix validation are accepted. SPC remains semantically unintegrated with LATTICE.
