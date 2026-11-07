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

- 2026-11-07: the plan's ES-3 and ES-8 rows briefed further, and ES-Q10 raised, from the [waterfall proofs sketch](../sketches/waterfall-proofs-and-the-generality-gap.md) §5.2. No slice changed state, since this was design on the plan rather than a slice picked up. Three things landed. ES-3 now says that uniqueness needs acyclicity while a fold needs a total order, that ADR-A130 decision 5's independence-of-order bullet holds because positions totalise the graph and not merely because it is acyclic, that a unit reading only its declared predecessors is load-bearing for the composition law rather than an optimisation, and that the conformance kit needs a schedule-completeness case, since conservation cannot see a unit that never ran. ES-8 carries a withdrawal: an earlier reading of mine said the external development refuted decision 5's criterion for admitting a cyclic component, and it does not, because its counterexample solves a cycle over determined values where decision 5's least fixpoint is over the information order, in which a bare cycle gives Undetermined. ES-Q10 asks whether decision 5 states the positional-total-order condition before it is accepted, leaning yes.
- 2026-11-04: this record created on `docs/placement-vehicles-structure`, so the plan's ten slices have a board and leave the identifier exceptions baseline (plan work-board, WB-7). ES-0 and ES-1 read briefed, since their Validation Packs were written on 2026-10-21 and no layer exists yet. The rest are planned, blocked as the plan's Depends on column says.
