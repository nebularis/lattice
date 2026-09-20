<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# MORK Package Split Status

**Unit:** `mork-package-split`
**State:** Accepted
**Decision:** [ADR-A77](../../architecture/decisions/ADR-A77-repository-topology-and-documentation-governance.md)
**Governing ADRs:** [ADR-A77](../../architecture/decisions/ADR-A77-repository-topology-and-documentation-governance.md), [ADR-A22](../../architecture/decisions/ADR-A22-mork-governance-and-versioning-foundation-alignment.md), [ADR-A23](../../architecture/decisions/ADR-A23-mork-compiler-family-completion-policy.md), [ADR-A24](../../architecture/decisions/ADR-A24-eligibility-executable-semantics-backend-strategy.md)

## Completed

- Moved MORK semantic assets to `ontology/mork/`.
- Moved the MORK Python project to `tools/mork/` with a conventional `src/` layout.
- Repointed root test discovery, phase-conformance fixtures, direct Python fixture lookup paths, and package installation tasks.
- Updated the MCN decoder test to resolve the repository root from its new depth.
- Preserved both non-identical MORK-to-RML implementations. Consolidation remains a separate behavior-affecting decision.

## Acceptance

The package split, canonical path rewrite, and ecosystem validation are accepted. MORK-to-RML consolidation remains explicitly out of scope and requires a separate behavior-affecting decision.
