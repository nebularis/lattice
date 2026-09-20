<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Repository Topology A77 Review

**Unit:** `repository-topology-a77`
**Disposition:** Accepted on 2026-09-20
**Status record:** [Repository Topology A77 Status](../status/repository-topology-a77.md)
**Plan:** [Repository Topology and Documentation Governance Plan](../plans/repository-topology-and-documentation-governance.md)

## Review Request

Approved. This record preserves the decision request and its acceptance evidence. Follow-on relocation units receive their own review records.

## Decisions Requested

1. Semantic assets move under `ontology/`.
2. MORK and SPC separate semantic assets from executable implementations.
3. `workers/` remains top-level as a deployable runtime package.
4. ADRs move from `docs/adr/` to `docs/architecture/decisions/`, with every link and website entry point repointed in the same relocation unit.
5. `docs/developer/plans`, `status`, and `review` become the required unit-of-work structure. `docs/developer/current` is removed after migration.
6. `.github/copilot-instructions.md` remains the active repository instruction file.

## Artifacts To Inspect

- [Repository Topology and Documentation Governance Plan](../plans/repository-topology-and-documentation-governance.md)
- [ADR-A77](../../architecture/decisions/ADR-A77-repository-topology-and-documentation-governance.md)
- [Repository instructions](../../../.github/copilot-instructions.md)

## Commands To Run

No build or test command is required for this documentation-only decision gate.

## Pass Criteria

- The target topology assigns every moved asset to one canonical owner.
- The semantic versus executable split is clear for MORK and SPC.
- No toolchain authority changes are introduced.
- The documentation lifecycle supplies exactly one authoritative status path for each active unit.
- The ADR relocation is explicitly immediate and repository-wide, including the website.

## Open Questions

- None. Amend ADR-A77 if a later decision changes the accepted topology.
