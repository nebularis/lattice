<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Insure-O Applied Validation Package

This package is a clean-room applied validation layer built on LATTICE's generic substrate. It tests that a minimal insurance-style model can be expressed without importing any source product or proprietary scheme names. The package deliberately does not claim to be a full reimplementation of a specific market design.

## Scope

The package exercises the shared substrate across:

- Instrument: policy document, provision, obligation, qualifier
- Party: insurer, insured, claimant, loss payee, and their role occupancies
- Eligibility: admission profiles with exact, set, interval, and hierarchical matching
- Behaviour: capacity resources, guard checks, and sequential draw semantics
- Quantification: limits, retentions, triggers, and range-bounded fields
- Vocabulary: scheme contracts for business dimensions bound externally
- MORK: illustrative target sketch for mapping a limit resource to a behavioural allowance

## Explicit exclusions

This package explicitly excludes:

- Risk Capital Vehicles / Tower constructs
- ContractTowerBinding and tower linkage mechanics
- Claims-handling / CHO extension ideas
- CAT modelling
- Negotiation, procurement, and quotation workflows
- Named source-product constructs or acronyms from the source estate

## Namespace

The working namespace for this applied layer is:

```turtle
@prefix ino: <https://www.nebularis.org/neuro-semantic/lattice/examples/insure-o#> .
```

## Minimal mapping strategy

The package uses the minimal subclassing approach agreed in the plan:

- Structural classes are light subclasses of `ins:Element`, `ins:Provision`, `ins:Obligation`, and `ins:Qualifier`
- Party roles remain vocabulary individuals and `pty:RoleOccupancy` relationships
- Eligibility conditions are authored as `elg:Condition` individuals rather than a bespoke applied admission class
- Behaviour capacity resources are a small `ino:` family of classes layered on `bhv:AllowanceDefinition` and `bhv:EffectDefinition`
- External business dimensions are bound through `voc:SchemeContract` and `voc:ConceptScheme` declarations, rather than by hard-coding domain values into the substrate
- The concrete peril hierarchy example uses `skos:broader` to represent `Peril → Fire → Industrial Fire` and exercises `elg:HierarchicalMatch` through the scheme closure rule declared in the eligibility substrate

## Files

- `vocab/ino-vocab.ttl` — mechanism-intrinsic insurance vocabulary
- `projection/` — layer bindings and scheme contracts
- `spec/insure-o.ttl` — light insurance T-box
- `shapes/constraints.ttl` — local validation constraints
- `execution/` — shadow-compilation and operational profile examples
- `cases/` — worked scenarios
- `test/` — defect fixtures
