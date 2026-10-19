<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Ontology Root Relocation Review

**Unit:** `ontology-root-relocation`
**Status:** Closed
**Disposition:** Accepted on 2026-09-20
**Decision:** [ADR-A77](../../architecture/decisions/ADR-A77-repository-topology-and-documentation-governance.md)
**Status record:** [Ontology Root Relocation Status](../status/ontology-root-relocation.md)
**Governing ADR:** [ADR-A77](../../architecture/decisions/ADR-A77-repository-topology-and-documentation-governance.md)

## Review Outcome

The safety conditions were satisfied. The common LATTICE semantic roots were moved into `ontology/`. This review excludes the later MORK and SPC split units.

## Paths Proposed For This Move

```text
ontology/foundation/      -> ontology/foundation/
ontology/vocabulary/      -> ontology/vocabulary/
ontology/quantification/  -> ontology/quantification/
ontology/party/           -> ontology/party/
ontology/eligibility/     -> ontology/eligibility/
ontology/behaviour/       -> ontology/behaviour/
ontology/instrument/      -> ontology/instrument/
ontology/surface/         -> ontology/surface/
ontology/applied/         -> ontology/applied/
ontology/governance/      -> ontology/governance/
ontology/examples/        -> ontology/examples/
```

## Commands To Run

From the repository root:

```text
mise run topology:ready
mise run topology:links
```

## Pass Criteria

- `topology:ready` reports `repository topology migration check passed`.
- `topology:links` reports no broken local Markdown links.
- The status record contains any exceptions, their owner, and their resolution before the move begins.

## Deliberate Non-Coverage

This gate does not validate Python, Maven, Yarn, Mix, Compose, or semantic behavior. Those checks run after the physical relocation in the relevant topology and ecosystem validation units.
