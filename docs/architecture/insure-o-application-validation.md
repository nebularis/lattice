<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Insure-O Applied Validation Package

This note records the purpose and boundaries of the applied validation package under `examples/insure-o/`.

## Purpose

The package exercises LATTICE's generic substrate in an insurance-shaped domain without naming or recompiling any proprietary product, insurer, or source estate vocabulary. It is intentionally a clean-room validation layer used to confirm that structural, behavioural, and eligibility mechanisms work together in a realistic but not product-specific arrangement.

## Coverage

The package demonstrates the following substrate combinations:

- Instrument vocabulary for policy documents, coverage terms, limits, and retentions
- Party role occupancies for insurer, insured, claimant, and loss payee roles
- Eligibility conditions that use exact, set, interval, and hierarchical matching
- Behaviour allowance definitions and sequential consumption rules
- Vocabulary scheme-contract declarations for externally supplied business dimensions
- A small MORK target sketch for mapping a policy limit into a behavioural allowance resource

## Explicit exclusions

The applied validation package explicitly excludes:

- Risk Capital Vehicles and tower constructs
- ContractTowerBinding and other tower-linkage mechanics
- Claims-handling / CHO extension ideas
- CAT modelling
- Negotiation, procurement, and quotation workflows
- Source-product naming, acronyms, or proprietary concept values

## Realisation strategy

The package follows ADR-A15's neutrality position. The execution folder is presented as one legitimate but optional realisation strategy, not as a semantic requirement. The semantic source remains the Turtle substrate and the shapes defined in the package.

## Scope boundary

This package is intentionally a validation substrate and not a domain replacement. It is designed to prove that LATTICE can host an insurance-like arrangement, not to author a complete or final insurance ontology in the repository itself.
