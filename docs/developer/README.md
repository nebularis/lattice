<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Developer Work Repository

`docs/developer/` is the repository for implementation guidance and units of work.

## Stable Guidance

Files directly under this directory describe durable contributor practices, environments, and toolchains. They are not live implementation status.

## Unit Documents

Every active unit has one stable identifier and uses these locations:

| Document | Path | Purpose |
|---|---|---|
| Plan | `plans/<unit>.md` | Scope, dependencies, decisions, work steps, and planned validation |
| Status | `status/<unit>.md` | Sole authoritative current state, evidence, blockers, and next action |
| Review | `review/<unit>-review.md` | Human review request, artifacts, exact `mise` commands, pass criteria, and status link |

Plans change only when planned work changes. Status changes after every material implementation or validation event. Review records are closed or archived after human disposition.

## Active Unit

| Unit | Plan | Status | Review |
|---|---|---|---|
| `repository-topology-a77` | [plan](plans/repository-topology-and-documentation-governance.md) | [status](status/repository-topology-a77.md) | [review](review/repository-topology-a77-review.md) |
| `lattice-platform-development` | [plan](plans/lattice-platform-agentic-development-v0.2.md) | [status](status/platform-continuation.md) | [review](review/platform-continuation-review.md) |
| `ontology-root-relocation` | [plan](plans/repository-topology-and-documentation-governance.md) | [status](status/ontology-root-relocation.md) | [review](review/ontology-root-relocation-review.md) |
| `mork-package-split` | [plan](plans/repository-topology-and-documentation-governance.md) | [status](status/mork-package-split.md) | — |
| `spc-package-split` | [plan](plans/repository-topology-and-documentation-governance.md) | [status](status/spc-package-split.md) | — |

## Architecture Decisions

Architecture decisions are catalogued in [Architecture Decisions](../architecture/decisions/README.md). New decisions do not belong in `docs/developer/`.
