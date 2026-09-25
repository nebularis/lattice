<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Ontology Semantic Versioning - Status

**Unit ID:** `ontology-semantic-versioning`
**Status:** Planned, awaiting human review. Implementation has not started.
**Last updated:** 2026-09-25
**Trigger:** human request, 2026-09-25
**Plan:** [ontology-semantic-versioning.md](../plans/ontology-semantic-versioning.md)
**Sketch:** [ontology-semantic-versioning.md](../sketches/ontology-semantic-versioning.md)
**ADR:** [ADR-A86](../../architecture/decisions/ADR-A86-ontology-semantic-versioning.md), Proposed

## Current position

No ontology document, guidance document, or tooling has been changed by this
unit yet. Only the design artefacts exist: the sketch (full inventory of
every `owl:versionIRI` currently in the tree, and the anomalies it contains),
ADR-A86 (Proposed), this plan, and this status record.

The inventory found four distinct problems, not one: no documented bump rule
anywhere except a single ad hoc note in `vocabulary/README.md`; an
inconsistent versioning unit (`spec/*.ttl` and `vocab/*.ttl` already
independently versioned and already drifted); two ontologies (MORK, SPC) with
no version identity at all; and one (`applied/insurance/contract.ttl`) with
two disagreeing version signals plus a namespace base outside the `lattice/`
tree every other in-scope document uses.

## Planned slices

| Slice | Status | Scope |
|---|---|---|
| 1. Decision and documentation foundation | Planned | ADR-A86, sketch, plan, status record, ADR-index and INDEX.md entries (this slice, largely already done by authoring these documents) |
| 2. Developer/agent guidance | Planned | `docs/architecture/ontology-versioning-policy.md`, `CONTRIBUTING.md` and `ontology-architecture.md` §2 cross-references |
| 3. Baseline reset | Planned | Version numbers, base-URI normalisation, `owl:imports` cascade, per-layer changelog notes, across every in-scope document |
| 4. Narrow enforcement tooling | Planned | "Changed but not bumped" check, wired into `mise` |

## Decisions awaiting human confirmation

- **The baseline number.** `0.2.0` is recommended (safely above every current
  value, per `semver.md`'s own guidance on starting an initial-development
  series). Not settled until ratification.
- **Whether `owl:versionInfo` survives `applied/insurance/contract.ttl`'s
  reconciliation** as a human-readable label matching `owl:versionIRI`, or is
  dropped entirely now that one authoritative signal exists.
- **`applied/insurance/contract.ttl`'s namespace family** (`neuro-semantic/insurance`,
  outside `lattice/`) — deliberate applied-layer independence, or an
  oversight to fold into the `lattice/` tree alongside the version reset?
  This plan does not move it either way without that answer.
- **Import-pinning strategy.** Keep exact-IRI `owl:imports` pinning (this
  plan's working assumption), or invest now in a "latest-within-major"
  import convention to reduce the same-change cascade cost? The ADR
  recommends keeping exact pinning and revisiting only if the cascade becomes
  a real source of friction.
- **Where the Slice 4 check lives** — a new `check:ontology-versioning` `mise`
  task, or folded into the existing `topology:links`/`topology:preflight`
  tasks. Not decided until Slice 4 planning.

## Human validation gate

Before Slice 2 begins: review the sketch's inventory and anomaly list, the
MAJOR/MINOR/PATCH mapping table, the versioning-unit rule, and confirm or
amend the baseline number and the two applied-insurance questions above.
Before Slice 3 begins: confirm the exact set of files the baseline reset will
touch (the plan's deliverable 3 list) and the import-cascade enumeration for
each, since Slice 3 is the one slice in this unit with a mechanical blast
radius across many files at once.

## Blockers

Human review of the ADR and the two open decisions (baseline number,
applied-insurance namespace family) is the only blocker currently recorded.
No document or ontology file outside this unit's own governance records has
been changed.
