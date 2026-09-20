<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A77: Repository Topology and Documentation Governance

**Status:** Accepted
**Date:** 2026-09-20
**Supersedes:** The repository-layout position in `docs/architecture/updated-plan-ammendment.md` AM-05
**Related:** ADR-A29, repository topology and documentation governance plan

## Context

The repository currently exposes ontology layers, MORK, SPC, applied domains, governance material, examples, developer plans, handoffs, status records, and architecture decisions through several unrelated roots. This makes semantic ownership unclear, places MORK and SPC implementation code beside their semantic assets, and leaves `docs/developer/current/` unable to distinguish a plan from the current state of implementation.

The repository needs a topology that separates semantic assets from executable implementations while retaining the current toolchain boundaries. It also needs a documentation lifecycle that gives human and agent implementors one authoritative status record and one review request for every active unit of work.

## Decision

### Repository roots

1. `ontology/` is the sole root for semantic assets. It contains the existing LATTICE layers, Surface, applied domains, governance assets, cross-layer examples, and the semantic portions of MORK and SPC.
2. `tools/` is the root for reference implementations and developer-facing executable toolchains. It contains existing Surface and MORK compiler tools, plus MORK Python and SPC Python/Erlang executable projects.
3. `workers/` remains a top-level deployable asynchronous runtime package.
4. `platform/`, `apps/`, `packages/`, `contracts/`, `deployment/`, and `test/` remain top-level roots. This ADR does not rename applications or change package-manager, build, or deployment ownership.
5. The migration uses `git mv`, does not change ontology namespace IRIs or URL-based imports, and is driven by an approved path manifest before any source root moves.

### MORK and SPC

1. MORK semantic vocabulary, shapes, targets, semantic examples, fixtures, and semantic documentation move to `ontology/mork/`.
2. MORK Python source, executable tests, package metadata, CLIs, and implementation documentation move to `tools/mork/python/`.
3. SPC semantic vocabulary, shapes, vocabulary, semantic examples, and semantic documentation move to `ontology/spc/`.
4. SPC Python and Erlang executable projects move to `tools/spc/python/` and `tools/spc/erlang/`.
5. SPC remains semantically unintegrated with LATTICE unless another accepted decision changes that boundary.

### Architecture decisions

1. The canonical architecture-decision location is `docs/architecture/decisions/`.
2. All existing ADRs and their index move from `docs/adr/` to that location in one relocation unit.
3. Every repository reference, including website navigation and checked-in HTML, is repointed immediately.
4. `docs/adr/` is removed after relocation. No duplicate ADR source is retained.

### Developer work repository

1. `docs/developer/plans/` holds plans and changes only when the plan changes.
2. `docs/developer/status/` holds the one authoritative current state for each active unit and changes after every material implementation or validation event.
3. `docs/developer/review/` holds the current human review request for each active unit, including exact `mise` commands, pass criteria, artifacts, and the matching status link.
4. Unit identifiers are stable and shared by matching plan, status, and review files.
5. `docs/developer/current/` is removed once existing records are classified and migrated.
6. `docs/developer/` root retains durable implementation guidance only.

### Toolchain

ADR-A29 remains in force. `mise` is the sole orchestration entry point. Maven, Yarn 4, Python project tooling, and Mix remain dependency authorities.

## Consequences

- Every semantic asset gains a common discoverable root.
- MORK and SPC implementation dependency surfaces stop being mixed with ontology assets.
- A repository-wide link and path rewrite is required, including `docs/index.html`, `docs/book.html`, and documentation includes.
- The migration requires path-manifest, ownership, and documentation-lifecycle validation before source roots move.
- Agents must follow the new plans, status, and review lifecycle once the proposed companion instructions are approved and activated.
