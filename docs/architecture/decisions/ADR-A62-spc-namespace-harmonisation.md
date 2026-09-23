<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A62: SPC Namespace Harmonisation and Integration Deferral

**Status:** Proposed
**Date:** 2026-09-23
**Related:** Architecture Review §4.14, G-19, `ontology-architecture.md`, ADR-A01
**Drafted by:** Agent, autonomous session (P0.1.12). Pending human ratification — see [phase-0-status.md](../../developer/status/phase-0-status.md). The namespace change itself has already been executed (see Consequences).

## Context

SPC (`ontology/spc/spec/spc.ttl`, ~1227 lines; `ontology/spc/README.md`, ~1393 lines) is a fully specified, session-typed process calculus sitting unintegrated with the rest of LATTICE. It uses a placeholder namespace (`http://example.org/spc#`) instead of the shared `nebularis.org` base, and its `projection/` directory is empty. `ontology-architecture.md` §3 previously stated only "integration is out of scope," which reads as neglect rather than a stated sequencing decision.

## Decision

Two coherent integration positions exist; this ADR picks one for now and names the other as future work, rather than leaving the choice implicit:

| Position | Consequence | When |
|---|---|---|
| Integrate SPC as the orchestration substrate | Author `ontology/spc/projection/party.ttl` and `behaviour.ttl`; model every workflow as an SPC session type | **Phase 4**, gated on the runtime planes (ingestion, query, behaviour) being stable |
| Defer SPC, with the reason stated | Workflows remain conventional state machines in `C-02`/`C-06`/`C-10`; each workflow is documented in a uniform shape so a later SPC lift is mechanical | **Phases 1–3**, on the explicit condition that every workflow is documented uniformly (audited at the Phase 3 gate) |

Adopt the second position now, the first later. The namespace harmonisation (a one-line change per file) is executed immediately, independent of the integration timeline, so no future dependency is built against `http://example.org/spc#`.

## Consequences

- `ontology/spc/spec/spc.ttl`, `ontology/spc/README.md`, and the executable mirror `tools/spc/python/src/spc/ontologies/spc.owl.ttl` now use `https://www.nebularis.org/neuro-semantic/lattice/spc#` in place of `http://example.org/spc#` (executed in this slice).
- `ontology-architecture.md` §3's SPC description is updated to state this ADR's position rather than "out of scope" (executed in this slice).
- ADR-A01 (layer dependency order) is unaffected: SPC remains outside the Foundation→...→Behaviour dependency chain: it does not import from, or get imported by, any layer in that order.
- Phase 3's gate audit (per the epic's own note) must confirm every workflow documented so far is in the uniform shape this ADR assumes, before Phase 4's SPC lift is attempted.
- This ADR does not author `ontology/spc/projection/`; that remains empty until Phase 4.
