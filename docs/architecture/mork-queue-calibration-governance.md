<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# MORK Queue, Calibration, and Governance

Phase 6 builds governance controls around the immutable Phase 5 review snapshots. `QueueEntry.ordering_key` sorts by descending yield score, then pack, profile, model, and entry ID. The stable tie-breakers make the Atlas queue replayable from the same snapshot population.

`CalibrationGate` is scoped to the exact pack, profile, and model. `require_bulk_gate` blocks bulk confirmation until precision meets the configured threshold for that same triple. A passing result cannot be reused across a model update, profile change, or pack.

Ontology minting uses a request naming the changed axiom and the affected approval IDs. `reopen_approvals` records a reopened state and named-axiom reason for each approval. It does not erase immutable prior review evidence.

Retrospective challenge opens a new record against an immutable decision ID and snapshot hash. It never mutates the challenged decision. This gives governance a path to consider later evidence while preserving the original review and learning audit.

`GovernanceLedger` appends calibration, bulk-gate, reopening, and challenge entries and replays them by immutable occurrence time and entry ID. Template-by-exception attaches an unusual snapshot to a named template with mandatory engineering review. The Review Bench fixture exposes both summaries without revealing source syntax or restricted pack internals.

The Review Bench fixture provides Atlas queue context, disabled bulk confirmation below calibration threshold, a Boundary minting impact, and privacy-safe Pack Studio metadata. It shows pack identity and calibration summary but does not show source syntax, MCN, lint diagnostics, or pack internals to Domain Stewards.