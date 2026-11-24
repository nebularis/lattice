<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-S2g, graph construction projections

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-S2g, built on 2026-11-24 in autonomous mode, from the [projection backend sketch](../sketches/projection-backend.md) as the maintainer answered SVA-Q31 to SVA-Q35 and as the maintainer decided on 2026-11-24 that `mork_rdf` gains two checks and no mapping kind.

## Invariant

A graph construction projection states the node it writes on its result-target role binding, a constructed node with a class, an identity and at least one written value, and lowers deterministically into a mapping scheme `mork_rdf` compiles with its existing cases. An instance contributes whole or not at all, since the guard sits on the contextual datum that mints the node and every query beneath inherits it. A keyed node is one node for each value of its key. An excluded instance and a keyed node whose instances disagree are reported by name, and a keyed node carries a mapping review finding.

## What changed

- **Surface**, from its README: `srf:ConstructedNode`, `srf:WrittenValue` and `srf:IdentityChoice` with the individuals `srf:PerInstance` and `srf:ByKey`, and the properties `srf:constructedAs`, `srf:constructedClass`, `srf:nodeIdentity`, `srf:keyBinding`, `srf:writes`, `srf:writesProperty` and `srf:fromBinding`. Laws `srf:P10` to `srf:P13` with 11 shapes, and `srf:P1` states how a node's class decides its signature scope. The README states the feature's boundary, that a natural key is spelled into an identifier, so a key that may be personal or may change is no key. The example is `order-supplier-construction-projection.ttl`. The release note says P10 may invalidate a graph construction that states no node.
- **The lowering**, `lowering.py`, `model.py` and `naming.py`: a graph construction lowers into a scheme with a source-node root, a contextual datum guarded by every required-evidence binding, an identity from the key or a hash, and an assertion for each value. `srf:producesMapping` is written as for a derivation. A join and an expansion keep the bare mapping.
- **`mork_rdf`**, from its README section 7.9: two checks, `InstanceExcluded` and `ValueDisagrees`, and a `MappingReview` warning on a keyed datum beneath a source-node datum. No mapping kind and no MORK term.
- **The addenda** to ADR-A18 and ADR-A23 for this kind, Proposed, beside the derivation's. The sketch's section 2.2 shows the contract, the scheme and the query as built.

## Choices the sketch did not settle

1. A written value is a blank node or an IRI of type `srf:WrittenValue`, and the shapes reach it through `srf:writes`. The lowering names the assertions by the order of the properties, so the contract's blank nodes never reach the output and a property written twice is refused.
2. A key of several bindings is the key values in the order of their properties, joined by a slash, each encoded for an IRI, so a value with a slash cannot blur two keys. A contract key or class that needs it is percent-encoded in the stem.
3. The guard holds every required-evidence binding of the contract, not only the key and the written ones, as SVA-Q33 reads. A contract with no required evidence has no guard.
4. `MappingReview` is a compile finding of `mork_rdf`, on any keyed contextual datum beneath a source-node datum. The studio's review requirement, `workers/src/lattice_workers/projection_policy.py`, reads only the projection kind, so a keyed construction needs that policy to read the finding or the contract before SVA-S2c acts on it.
5. `ValueDisagrees` compares RDF terms, so `1.0` and `1` disagree, and it has no check on a value the identity reads.

## Tests

| ID | Given / When / Then | Level | The break tried | The failure it gave |
|---|---|---|---|---|
| S2g-T1 | the example lowered / compared with the MORK shapes / a scheme they accept, for a key, a key of two values and a node for each instance | L1 | | |
| S2g-T2 | the example, repeated and in five orders of its triples / lowered / the same graph and the same compiled text | L1 | | |
| S2g-T3 | the example / compiled / the node's query as the sketch shows it, and three constructs | L1 | | |
| S2g-T4 | three orders on Oxigraph and rdflib / run / two supplier nodes keyed by code, each typed with its code, a link from each order, and the name on the first | L1 | | |
| S2g-T5 | an order with the key and without a required value, beside an order that made the node / run on both engines / no link, type or value for it, and the exclusion reported with the value it lacks | L1 | the guard removed from the scheme: the order links to the node and nothing is reported | |
| S2g-T6 | two orders that give one supplier two names / run on both engines / both written, and the node reported with each value | L1 | | |
| S2g-T7 | a keyed and a per-instance construction / compiled / the keyed carries `MappingReview`, a node for each order has none and no disagreement check | L1 | | |
| S2g-T8 | a model and a shape for each law's breach, such as no node, a node on a derivation, no class, no identity, a key on a node for each instance, a property written twice, a value from a subject or an unknown binding, and a key that is candidate evidence / read and validated / each refused by its law and its shape | L1 | | |

## Checks run

| Command | Result |
|---|---|
| `mise run check:python-root` | 191 passed, the phase 8 conformance passed |
| `mise run check:mork-rdf` | 197 passed, 18 of them new |
| `mise run check:mork` | 464 passed |
| `mise run check:mork-compilers` | 195 passed |
| `mise run check:ontology-catalog` | 1319 passed, consistent, the 2 known defects |
| `literate_extract --check` for Surface | 4 artefacts consistent |
| `mise run check:identifiers`, `check:published-decisions`, `check:owl-profile` | passed |

`check:mork` left `ontology/mork/mtp/data/pins.lock.json` as it was, and it was restored. No version was bumped, so Surface waits for `mise run version:bump` at the merge, with the derivation's changes.

## Left open

- Whether the studio's review requirement acts on `MappingReview` or on the contract (choice 4).
- A key spelled into an identifier is the author's to choose, which neither Surface nor `mork_rdf` can check.
- An instance with several values at the key's path gives several nodes, which `IdentityAmbiguous` reports, and one with several values at a written value's path gives its node all of them, which `ValueDisagrees` reports.

## Placement

T0. Surface, `mork_rdf` and the order and supplier example are open substrate, and the example is generic.
