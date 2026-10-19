<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Repository Topology A77 Status

**Unit:** `repository-topology-a77`
**State:** Accepted - structural migration complete
**Decision:** [ADR-A77](../../architecture/decisions/ADR-A77-repository-topology-and-documentation-governance.md)
**Review:** [Repository Topology A77 Review](../review/repository-topology-a77-review.md)
**Governing ADR:** [ADR-A77](../../architecture/decisions/ADR-A77-repository-topology-and-documentation-governance.md)

## Current Position

The architecture-decision catalogue, developer work repository, semantic roots, and MORK/SPC executable projects have moved to their canonical locations. The local Markdown link audit is clean.

## Completed

- Classified semantic assets, executable tooling, runtime packages, and infrastructure roots.
- Chosen `ontology/` as the semantic-content root.
- Chosen semantic and executable ownership splits for MORK and SPC.
- Retained `workers/` as the deployable asynchronous runtime package.
- Defined the plans, status, and review document lifecycle.
- Created the proposed companion agent guide.
- Accepted ADR-A77 and created the topology migration manifest.
- Moved the ADR catalogue to `docs/architecture/decisions/` and repointed functional repository and website links.
- Established `docs/developer/plans/`, `status/`, and `review/`, then retired `docs/developer/current/`.
- Moved active plans, continuation state, handoffs, validation records, and the handoff template into their lifecycle locations.
- Added the `mise run topology:preflight` guard for ADR-A77 prerequisites.
- Moved the common LATTICE semantic roots under `ontology/`.
- Split MORK into `ontology/mork/` semantic assets and `tools/mork/` implementation assets.
- Split SPC into `ontology/spc/` semantic assets and `tools/spc/` Python and Erlang implementation assets.
- Repaired topology-caused documentation links. The local Markdown audit reports no broken links.
- Ran `git diff --check` successfully after removing the reported trailing whitespace.

## Evidence

- Root tooling uses `mise` as orchestration, with Maven, Yarn, Python, and Mix as native dependency authorities.
- `mise run topology:preflight` completed successfully on 2026-09-20.
- ADR links now resolve through `docs/architecture/decisions/`, including website entry points.
- Developer plans, status, and review records now have canonical locations, and `docs/developer/current/` has been removed.

## Pending Validation

- Build, test, package-discovery, and Mix validation are deferred because this restructuring environment cannot run the repository toolchains in place.
- MORK-to-RML consolidation is deliberately deferred because the two existing implementations have different content hashes and that work would change behavior rather than structure.

## Next Action

Run focused ecosystem validation from a suitable environment, then resolve the remaining MORK-to-RML ownership decision in its own reviewed unit.
