<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Architecture Decision Records

This directory holds the ADRs that govern LATTICE's substrate architecture. An ADR is the authoritative record of a decision, its context, and its consequences. Layer READMEs describe *what* a layer is; ADRs describe *why* the layers are shaped, ordered, and bounded the way they are.

## Convention

- Filename: `ADR-{id}-{slug}.md`, for example `ADR-A01-layer-dependency-order.md`.
- IDs are stable once assigned and are never reused, even if an ADR is superseded.
- Each ADR uses the same shape: Status, Context, Decision, Consequences.
- Status is one of `Proposed`, `Accepted`, `Superseded by ADR-{id}`.
- An ADR may be amended in place for clarifications that do not change the decision. A change to the decision itself is a new ADR that supersedes the old one.

## Index

| ADR | Title | Status |
|---|---|---|
| [A-01](ADR-A01-layer-dependency-order.md) | Layer dependency order and import direction | Accepted |
| [A-12](ADR-A12-identity-and-derivation-model.md) | Identity and derivation-authority model | Accepted |
| [A-13](ADR-A13-dataset-graph-role-model.md) | Dataset, graph-role, and provenance model | Accepted |
| [A-14](ADR-A14-conformance-levels.md) | Conformance-level framework | Accepted |
| [A-15](ADR-A15-realisation-strategy-neutrality.md) | Realisation-strategy neutrality | Accepted |
| [A-03](ADR-A03-condition-taxonomy.md) | Eligibility condition taxonomy | Accepted |
| [A-04](ADR-A04-interval-overlap-law-split.md) | Interval containment and overlap law split | Accepted |
| [A-05](ADR-A05-compatibility-vocabulary.md) | Compatibility operation vocabulary | Accepted |
| [A-06](ADR-A06-wildcard-semantics.md) | Wildcard semantics and limits | Accepted |
| [A-07](ADR-A07-eligibility-authoring-direction.md) | Eligibility authoring direction and extraction contract | Accepted |
| [A-07b](ADR-A07b-minimal-instrument-shape.md) | Minimal Instrument shape and versioning contract | Accepted |
| [A-08](ADR-A08-behaviour-four-tier-model.md) | Behaviour four-tier model | Accepted |
| [A-09](ADR-A09-behaviour-selection-policy.md) | Behaviour selection policy | Accepted |
| [A-10](ADR-A10-behaviour-activation-policy.md) | Behaviour activation policy | Accepted |
| [A-11](ADR-A11-effect-and-target-binding.md) | Effect payload and target binding contract | Accepted |
| [A-C1](ADR-AC1-applied-layer-theorem-restatement.md) | Applied-layer theorem restatement policy | Accepted |
| [A-C2](ADR-AC2-clean-room-authoring-procedure.md) | Clean-room authoring procedure for substrate content | Accepted |

ADR numbering deliberately skips A-02 through A-11: those IDs are reserved for the Eligibility (A-03–A-07) and Behaviour (A-08–A-11) decisions authored in Gates 2 and 3, plus A-02 for the document-hierarchy question folded into [../GOVERNANCE.md](../GOVERNANCE.md) instead of a standalone ADR. This index is updated as each is added.
