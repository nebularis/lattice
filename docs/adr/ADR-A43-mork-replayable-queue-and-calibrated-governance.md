<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A43: MORK replayable queue and calibrated governance

**Status:** Accepted
**Date:** 2026-09-20
**Related:** Phase 6, ADR-A22, ADR-A42

## Context

MORK bulk review actions need a reproducible queue and calibration evidence that cannot be borrowed across packs, profiles, or models. Ontology changes must preserve prior approval history while reopening the approvals their named axiom affects. Pack visibility must not bypass the evidence restrictions established for Domain Stewards.

## Decision

Order review entries by deterministic yield-derived keys with stable pack, profile, model, and entry tie-breakers. Permit a bulk action only with a passing calibration gate for the exact pack, profile, and model. Treat ontology minting as a named-axiom request that reopens affected approvals without deleting prior evidence. Retain a replayable append-only governance ledger and require engineering review for template-by-exception. Pack Studio exposes identity and calibration summary, never source syntax or pack internals to restricted roles.

## Consequences

- Queue ordering can be replayed from the same inputs.
- A calibration pass in one model or profile does not authorize another.
- Governance Ledger records approval reopening causality by named axiom.
- Template exceptions preserve snapshot identity and cannot bypass engineering review.
- Atlas, Boundary, and Pack Studio remain evidence projections, not unrestricted graph browsers.
