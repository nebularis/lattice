<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Repository Topology Migration Record

**Decision:** [ADR-A77](decisions/ADR-A77-repository-topology-and-documentation-governance.md)
**Machine-readable manifest:** [repository-topology-migration.json](repository-topology-migration.json)
**Status:** Structural relocation complete. Ecosystem validation pending.

## Migration Rules

- Use `git mv` for every relocation.
- Preserve ontology namespace IRIs and URL-based `owl:imports`.
- Move semantic content below `ontology/` and executable reference implementations below `tools/`.
- Keep `workers/`, `platform/`, `apps/`, `packages/`, `contracts/`, `deployment/`, and `test/` at the repository root.
- Update every current reference in source, configuration, CI, documentation, and website material in the same migration unit.
- Historical records may retain an old path only with a relocation note and canonical replacement link.

## Relocation Order

1. Architecture decisions: `docs/adr/` to `docs/architecture/decisions/`.
2. Developer work records: establish plans, status, and review locations and retire `docs/developer/current/`.
3. Common LATTICE semantic roots: layers, Surface, applied domains, governance, and cross-layer examples.
4. MORK semantic and implementation split.
5. SPC semantic and implementation split.
6. Full source, configuration, CI, and documentation reference rewrite.

## Required Evidence Per Unit

Each relocation unit records its source and destination paths and updates the matching status record. The completed structural migration has passing local Markdown-link evidence. Package discovery and ecosystem behavior remain post-migration validation work.
