<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-S2f, `mork_rdf` compiles a derivation

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-S2f, built on 2026-11-24 in autonomous mode, from the [projection backend sketch](../sketches/projection-backend.md) and the Proposed addendum to ADR-A23.

## Invariant

`mork_rdf` reads a scheme whose root has the source-node identity and a mapping whose value is a value expression as a compiled case of its own, and writes one CONSTRUCT for it: the carrier iterated by its class, each distinct path bound once, the expression in a `BIND` cast to its result datatype, and the result written on the focus node itself. A carrier missing an operand writes nothing and is reported, and so is one whose result is undefined, such as a quotient by zero. The driver runs it like any other scheme.

## What changed

- `read.py` reads two new kinds, a source-node datum and a derivation. `compile.py` compiles a derivation and its checks, `OperandMissing` for each path and `ValueUndefined` for a carrier with every operand and no result. A float or double quotient divides by its divisor only where it is not zero, since MORK makes a quotient at zero undefined where Oxigraph gives infinity. New refusals are `DerivationIncomplete`, `IdentityRuleUnknown` and `ScaleOutOfRange`.
- The lowered ARR contract, compiled and run over a sample, gives 354 for a subscription and reports one missing its price.
- `mork_rdf`'s README gains the case, the source-node identity, value expressions and the new findings. Section 2.1 of the sketch shows the query as compiled, with full IRIs and the cast, where it had shown an abridged form.

## Tests

| ID | Given / When / Then | Level | The break tried | The failure it gave |
|---|---|---|---|---|
| S2f-T1 | the ARR scheme / compiled / the query pinned, modulo whitespace | L1 | | |
| S2f-T2 | four subscriptions on Oxigraph and rdflib / run / 354.00 and 400.40, a missing price reported, a price that is no number reported as undefined | L1 | | |
| S2f-T3 | about thirty operation cases on both engines / run / each operation, rounding at a positive, negative and zero scale, the six comparisons, typed literals, promotion, a quotient by zero for each datatype, and a division by zero in a taken and an untaken branch, each with its expected value | L1 | | |
| S2f-T4 | a literal holding a quote, refusals, a guard on a derivation, the triples shuffled / compiled / escaped, refused with their codes, guarded, the same query | L1 | | |

## Checks run

| Command | Result |
|---|---|
| `mise run check:mork-rdf` | 179 passed |
| `mise run check:mork` | 464 passed |
| `mise run check:mork-compilers` | 195 passed |
| `mise run check:python-root` | the phase 8 conformance passed |
| `mise run check:mork-transforms` | 6 passed |
| `mise run check:identifiers` | passed |

Each was run by the delegated developer and again by the reviewer.

## Left open

- Two engine differences, pinned by a test and described in `mork_rdf`'s README: a decimal product's lexical form, `354.00` on rdflib and `354` on Oxigraph, and a double divided by zero, infinity on Oxigraph and an error on rdflib, which the compiled guard hides. Neither is yet a finding in the triple-stores domain.
- A carrier with several values for an operand gets one result for each combination. No check reports it.
- A result datatype outside the four numeric ones is not cast.

## Placement

T0. `mork_rdf` is open substrate.
