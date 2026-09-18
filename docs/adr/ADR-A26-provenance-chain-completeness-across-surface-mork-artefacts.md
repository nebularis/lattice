<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A26: Provenance chain completeness across Surface, MORK, and artefacts

**Status:** Accepted
**Date:** 2026-09-18
**Supersedes:** none
**Related:** ADR-A16 (derived-record tier), ADR-A22 (MORK governance and versioning), ADR-A23 (compiler family completion)
**Source plan:** [surface-mork-unified-projection-delivery-plan.md](../../surface/docs/surface-mork-unified-projection-delivery-plan.md)

## Context

ADR-A16's derived-record tier already records what a Surface mechanism generated, from which inputs, at which hashes, under which profile. Routing Projection through MORK lowering (ADR-A18) and out to five compiler backends (ADR-A23) adds hops the chain must survive. Each new hop that does not propagate provenance is a place a runtime decision stops being traceable to its source declaration.

## Decision

**Every generated artefact and runtime result exposes a complete provenance chain back to its Surface contract and originating declaration nodes.** This is mandatory at every stage the pipeline adds, not an optional field a backend may omit.

## Consequences

- Each compiler added under ADR-A23 must populate provenance fields as an acceptance criterion for that compiler, not as follow-up work after it ships.
- A single trace query must resolve any runtime decision to its source contract and declaration nodes across Surface, MORK, and the generated artefact, regardless of which backend produced it.
- Provenance completeness is checked in CI (ADR-A28), so a missing link is a build failure, not a documentation gap discovered later.
