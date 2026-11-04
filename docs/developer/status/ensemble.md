<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Ensemble: status

**Unit ID:** `ensemble`
**Plan:** [ensemble.md](../plans/ensemble.md)
**ADR:** [ADR-A130](../../architecture/decisions/ADR-A130-ensemble-layer.md), Proposed
**Status:** briefed. The plan is proposed with ADR-A130. ES-0 and ES-1 are briefed, their packs written, and ES-2 to ES-9 are planned.

## Board

| Slice | Deliverable | State | Blocked on |
|---|---|---|---|
| ES-0 | examples first, as data the model must accept or refuse | briefed 2026-10-21 | ADR-A130 accepted |
| ES-1 | the layer, its README, ens:Ensemble, ens:Relation and endpoints | briefed 2026-10-21 | ES-0 |
| ES-2 | the Instrument hook, a measured value or evidence as a recorded fact | planned | ES-1 |
| ES-3 | K2 and K3, dependency and priority, evaluation units below the instrument | planned | ES-2, Ledger LG-2 |
| ES-4 | K6, shared resources, the derivation from the terms that draw on an account | planned | ES-3, Ledger LG-2, LG-Q3, LG-Q4 |
| ES-5 | K4, portions and shares | planned | ES-3, LG-Q6 |
| ES-6 | K5 and the ensemble's life, formation, membership by rule | planned | ES-3, ES-Q5 |
| ES-7 | K8, representation, authorities one per subject | planned | ES-6, CCS C9's consent rules (HQ-5), the terms digest (evaluator plan EV-9) |
| ES-8 | K7, contribution, by addendum to ADR-A130 | planned | ES-4, Ledger LG-4 |
| ES-9 | comparison between instruments, where one replaces or completes another | planned | ES-2, CCS C16b |

## History

- 2026-11-04: this record created on `docs/placement-vehicles-structure`, so the plan's ten slices have a board and leave the identifier exceptions baseline (plan work-board, WB-7). ES-0 and ES-1 read briefed, since their Validation Packs were written on 2026-10-21 and no layer exists yet. The rest are planned, blocked as the plan's Depends on column says.
