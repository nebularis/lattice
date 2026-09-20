<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Ontology Root Relocation Review

**Unit:** `ontology-root-relocation`
**Status:** Open
**Plan:** [Repository Topology and Documentation Governance Plan](../plans/repository-topology-and-documentation-governance.md)
**Status record:** [Ontology Root Relocation Status](../status/ontology-root-relocation.md)

## Review Request

Review the safety conditions before moving the common LATTICE semantic roots into `ontology/`. This request excludes the later MORK and SPC split units.

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
