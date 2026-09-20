<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# MORK Package Split Status

**Unit:** `mork-package-split`
**State:** Reference rewrite in progress
**Plan:** [Repository Topology and Documentation Governance Plan](../plans/repository-topology-and-documentation-governance.md)

## Completed

- Moved MORK semantic assets to `ontology/mork/`.
- Moved the MORK Python project to `tools/mork/python/`.
- Repointed root test discovery, phase-conformance fixtures, and direct Python fixture lookup paths.
- Updated the MCN decoder test to resolve the repository root from its new depth.
- Preserved both non-identical MORK-to-RML implementations. Consolidation remains a separate behavior-affecting decision.

## Remaining

- Complete the full link and reference audit with the repository-wide cleanup unit.
- Run ecosystem validation after the restructuring migration is complete.

## Next Action

Contribute remaining MORK path findings to `reference-rewrite-and-lock`.
