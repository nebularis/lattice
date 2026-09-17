<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A14: Conformance-Level Framework

**Status:** Accepted
**Date:** 2026-09-17

## Context

"Does this graph conform to LATTICE" is not a single yes/no question. A graph mid-way through mapping is not invalid — it is simply not yet at the level a given operation requires. Without a graduated framework, every conversation about validation collapses onto one global gate, and ingestion/mapping activity that is correctly incomplete gets treated as a failure.

## Decision

An eight-level conformance ladder replaces any single global valid/invalid gate. Full detail, including per-level required checks, lives in the companion reference [../architecture/conformance-levels.md](../architecture/conformance-levels.md).

| Level | Description | Required for |
|---|---|---|
| L0 | RDF ingestible | Storage, discovery |
| L1 | Mapped/mapping-pending | MORK-style integration |
| L2 | Semantically classified | Exploratory query |
| L3 | Declaration-conformant | Declaration governance |
| L4 | Analysis-ready | Candidate detection, gap analysis |
| L5 | Operationally evaluable | Eligibility decisions |
| L6 | Authoritative execution-ready | Behaviour authoritative execution |
| L7 | Projection-conformant | External system integration |

A graph "failing LATTICE" is meaningless without naming a level. Ingestion and mapping activity routinely and correctly sit at L0–L2. SHACL shapes are organised by profile rather than as one monolithic shape graph: ingestion shapes, mapping shapes, declaration shapes, analysis shapes, operational Eligibility shapes, operational Behaviour shapes, projection-consistency shapes, and public-substrate neutrality shapes (enforcing empty substrate inventories) are each separate.

## Consequences

- Every test fixture used in validation states which level it targets (recorded in [../validation-and-test-plan.md](../validation-and-test-plan.md)).
- An L0–L2 fixture failing an L5+ check is expected behaviour, not a defect.
- Eligibility's operational profiles (E1–E6) and Behaviour's operational profiles (B-P1–B-P7), once authored in Gates 2 and 3, each state which conformance level they require and which they produce.
