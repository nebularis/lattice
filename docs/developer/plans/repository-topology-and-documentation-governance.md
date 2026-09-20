<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Repository Topology and Documentation Governance Plan

**Status:** In progress
**Decision:** ADR-A77, accepted
**Supersedes for this scope:** The repository-layout position in `docs/architecture/updated-plan-ammendment.md` AM-05

## Purpose

Move semantic assets under `ontology/`, separate executable MORK and SPC implementations into `tools/`, and establish an agent-maintained documentation lifecycle. This is a repository migration, not a semantic or runtime architecture change.

## Scope

Included:

- Move semantic content to `ontology/`.
- Split MORK and SPC semantic assets from their executable implementations.
- Move the ADR catalogue to `docs/architecture/decisions/`.
- Establish `docs/developer/plans/`, `status/`, and `review/` as the authoritative unit-of-work repository.
- Repoint all repository references, including website navigation and checked-in HTML.
- Add the proposed companion agent guide at `.github/copilot-instructions-2.md`.

Excluded:

- Ontology namespace IRI changes.
- Ontology semantic changes.
- Runtime architecture, app, Maven-module, or dependency-manager changes.
- Relocation of `workers/`, `platform/`, `apps/`, `packages/`, `contracts/`, `deployment/`, or `test/`.

## Target Topology

```text
ontology/
  foundation/ vocabulary/ quantification/ party/ eligibility/ behaviour/
  instrument/ surface/ applied/ governance/ examples/
  mork/                         # semantic vocabulary, shapes, fixtures, semantic docs
  spc/                          # semantic vocabulary, shapes, fixtures, semantic docs

tools/
  surface/ mork_compilers/
  mork/python/                  # MORK Python implementation and executable tests
  spc/python/ spc/erlang/       # SPC implementation projects and executable tests

workers/                         # deployable asynchronous runtime package, unchanged
platform/ apps/ packages/ contracts/ deployment/ test/ docs/  # unchanged roots
```

## Work Units

| Unit | Scope | Dependency | Review outcome |
|---|---|---|---|
| `repository-topology-a77` | Approve topology, ADR location, documentation lifecycle, and path manifest | None | ADR-A77 accepted |
| `adr-catalogue-relocation` | Move `docs/adr/` to `docs/architecture/decisions/` and repoint every link | `repository-topology-a77` | No stale ADR paths or broken website links |
| `developer-work-repository` | Implement plans, status, and review taxonomy and migrate developer records | `repository-topology-a77` | Exactly one active status record per active unit |
| `ontology-root-relocation` | Move common LATTICE semantic roots into `ontology/` | Path manifest and safety checks | Native validation commands discover relocated assets |
| `mork-package-split` | Separate MORK semantic assets and Python implementation | Path manifest and safety checks | Semantic and executable ownership checks pass |
| `spc-package-split` | Separate SPC semantic assets and Python/Erlang implementation | Path manifest and safety checks | Python and Mix projects resolve from new roots |
| `reference-rewrite-and-lock` | Complete full reference sweep and enable permanent topology checks | All prior units | No unresolved canonical-path references |

## Documentation Lifecycle

Every active unit uses one identifier, for example `iri-policy-p013`.

| Document | Location | Required content | Update rule |
|---|---|---|---|
| Plan | `docs/developer/plans/<unit>.md` | Scope, decisions, dependencies, implementation steps, validation design | Only when the planned work changes |
| Status | `docs/developer/status/<unit>.md` | Current state, completed work, evidence, blockers, next action, linked plan and review | After every material implementation or validation event |
| Review | `docs/developer/review/<unit>-review.md` | Review scope, artifacts, exact `mise` commands, pass criteria, open questions, linked status | Refresh before handoff. Close or archive after human disposition |

`docs/developer/` itself contains durable implementation guidance only. The former `current/` directory is removed after all of its documents are classified and migrated.

## Implementation Sequence

1. Approve ADR-A77 and this plan.
2. Move ADRs and rewrite all ADR links, including the website index and book.
3. Create the documentation lifecycle index and migrate existing developer material.
4. Create a machine-readable old-to-new path manifest and path/documentation validation checks.
5. Move common semantic roots into `ontology/` using `git mv`.
6. Split MORK, then SPC, into semantic and executable ownership roots.
7. Rewrite all current references in source, tests, configuration, CI, documentation, and generated website artifacts.
8. Update `mise` dispatch paths and package metadata without changing tool ownership.
9. Enable permanent stale-path, link, ownership, and documentation-lifecycle checks.

## Required Path Manifest

Before any semantic or implementation directory move, create `docs/architecture/repository-topology-migration.md` and a machine-readable manifest. They must include old path, new path, owner, classification, affected build/config files, affected documentation, and migration validation.

The path manifest includes at least:

| Old root | New root | Classification |
|---|---|---|
| `foundation/` through `surface/` | `ontology/<name>/` | LATTICE semantic content |
| `applied/`, `governance/`, `examples/` | `ontology/<name>/` | Semantic content |
| `mork/spec`, `shapes`, `targets`, semantic examples/docs | `ontology/mork/` | MORK semantic content |
| `mork/src/python` and executable tests | `tools/mork/` | MORK implementation |
| `spc/spec`, `shapes`, `vocab`, semantic examples/docs | `ontology/spc/` | SPC semantic content |
| `spc/src/python`, `spc/src/erlang` | `tools/spc/python`, `tools/spc/erlang` | SPC implementation |
| `docs/adr/` | `docs/architecture/decisions/` | Architecture decisions, completed |

## Validation Design

The migration adds checks for:

- stale paths, with documented exceptions only for archived historical records
- working Markdown, Jekyll, and checked-in website links
- ADR links resolving only through `docs/architecture/decisions/`
- no executable implementation source below `ontology/`
- no normative semantic source below `tools/`
- each active unit having exactly one plan and one status record
- each review record resolving to its matching status record
- root `mise` tasks dispatching through the existing Maven, Yarn, Python, and Mix owners

## Human Review Gate

ADR-A77 and the ADR catalogue relocation are complete. Review the matching status and review records before the next source-tree relocation unit begins.
