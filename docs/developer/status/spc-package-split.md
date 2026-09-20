<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# SPC Package Split Status

**Unit:** `spc-package-split`
**State:** Reference rewrite in progress
**Plan:** [Repository Topology and Documentation Governance Plan](../plans/repository-topology-and-documentation-governance.md)

## Completed

- Moved SPC semantic assets to `ontology/spc/`.
- Moved the Python toolchain project to `tools/spc/python/`.
- Moved the Mix/Erlang runtime project to `tools/spc/erlang/`.
- Updated the retained `mise` Mix dispatch path to `tools/spc/erlang`.
- Preserved SPC's semantic non-integration boundary.

## Remaining

- Complete the full link and reference audit with the repository-wide cleanup unit.
- Run Python and Mix validation after the restructuring migration is complete.

## Next Action

Contribute remaining SPC path findings to `reference-rewrite-and-lock`.
