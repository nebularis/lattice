<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-P1c, `dal:LandingPlace`

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-P1c, built on 2026-11-19 in autonomous mode. Asked for by the multi-store unit and agreed by the maintainer, who named the class, on 2026-11-19, before the persistence module's next version.

## Invariant

A write access lands in exactly one `dal:LandingPlace`, the place where a realisation keeps the resource it names. `dal:GraphPlace` is the SPARQL realisation's subclass, and another realisation states its places in a subclass of its own, so a profile compiled for a relational store passes the access's shape. Nothing in the class's text ties a place to an operation's SPARQL.

## What changed

- `ontology/persistence/README.md`, the source, from which the vocabulary, the shapes and the README's generated regions were extracted: `dal:LandingPlace`, `dal:GraphPlace rdfs:subClassOf dal:LandingPlace`, the range of `dal:landsIn`, the class `ResourceAccessShape` requires, the class diagram, and the Unreleased release note. The constraint that a write access lands in exactly one place, and `GraphPlaceShape`, are unchanged.
- A compiled profile still types each place `dal:GraphPlace` only. Every validation of a compiled profile in the repository puts the vocabulary in the data graph and runs with `inference="none"`, so `sh:class dal:LandingPlace` follows the subclass axiom there. The README says that a reader validating a compiled profile includes the vocabulary.
- No fixture changed.

## Tests

| ID | Given / When / Then | Level | The break tried | The failure it gave |
|---|---|---|---|---|
| P1c-T1 | a write access landing in a graph place / validated with the vocabulary / conforms | L1 | | |
| P1c-T2 | a place typed by another subclass of `dal:LandingPlace` and not `dal:GraphPlace` / validated / conforms | L1 | | |
| P1c-T3 | a place of an unrelated class, and one typed only `rdfs:Resource` / validated / the access fails with the class constraint | L1 | | |
| P1c-T4 | a graph place validated without the vocabulary / validated / the access fails, which pins that validation needs the vocabulary | L1 | | |

## Checks run

| Command | Result |
|---|---|
| `mise run check:persistence-expected-profiles` | expected profiles are current |
| `mise run check:persistence` | 4946 passed |
| `mise run check:persistence-library` | vectors 136 passed and 0 failed, Python 136 passed, Java verify exit 0 |
| `mise run check:identifiers` | passed, run by the delegated developer |

The first three were run by the delegated developer and again by the reviewer.

## Left open

- `ContractDeclarationIsIriShape` and `ContractHoldsNoSparqlTextShape` target `dal:GraphPlace` alone. A relational place class needs them to target it as well, which is the multi-store unit's to add with its class.
- The studio reads places by `dal:GraphPlace`, which is right while only SPARQL profiles compile.

## Placement

T0. The persistence vocabulary and shapes are open substrate.
