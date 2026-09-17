<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR A-07b: Minimal Instrument shape and versioning contract

## Status

Accepted

## Context

Behaviour depends on a stable target model for writing effects into document structure, and Party already forward-references an Instrument-side relation for obligation fulfilment. Instrument is currently empty, so a minimal, law-coherent shape is required before Behaviour authoring.

## Decision

Instrument defines the smallest required substrate-facing model:

- Classes: `ins:Element`, `ins:Provision`, `ins:Obligation`, `ins:Qualifier`.
- `ins:Element` subclasses `fnd:Version`.
- `ins:Provision`, `ins:Obligation`, and `ins:Qualifier` subclass `ins:Element`.
- These four classes are mutually disjoint.
- Cross-reference properties include:
  - `ins:hasProvision` / `ins:partOfInstrument`
  - `ins:hasObligation` / `ins:inProvision`
  - `ins:hasQualifier` / `ins:qualifies`
  - `ins:fulfilledBy` (to Party participation structures)

Versioning contract (R-B7):

- Instrument nodes are never updated in place.
- Any material change creates a new `fnd:Version` individual with the same `fnd:hasIdentity` and links the old version to the new one via `fnd:supersededBy`.
- Supersession is only legal between versions sharing the same identity.

## Consequences

- Behaviour can target a concrete minimal document model in Gate 3.
- Party forward references to obligation fulfilment are now grounded by a declared Instrument property.
- Instrument remains minimal and domain-neutral while preserving version-safe mutation semantics.
