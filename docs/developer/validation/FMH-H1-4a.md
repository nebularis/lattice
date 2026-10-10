<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-H1.4a, refuse a composite boundary with several node properties

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice H1.4a, the first half
of [plan §3, H1.4](../plans/formal-methods-track-h.md). H1.4b, the gap report, follows.
**Decided by:** the human, 2026-10-09 (H-D4): the combination is left a documented, refused
combination until H2's typed IR makes the fix structural.
**Source finding:** [review](../notes/rdf-engine/persistence-fml.md) finding #9, and TD-03.
**Decisions needing confirmation:** H-D13, below.

## Invariant

A dangling subgraph must not be producible by a whole-replace. `cas-replace-composite-property`
deletes the aggregate's own triples and the triples of every member it can reach along **one**
property (`$root <p>+ ?member`). A member reached only through a different property keeps its
triples after the replace. The compiler therefore refuses a composite boundary whose shape reaches
other nodes through more than one property, and it binds the property that leads to a node.

## What was found

1. **The gap is real, and demonstrated on two engines.** Run on rdflib and on Oxigraph 0.5.11, which agree,
   with an order that has a line item and a payment, each a separate node:

   | Shape | Property bound | Triples left in the aggregate after a replace |
   |---|---|---|
   | one node property (`lineItem`) | `lineItem` | **none** |
   | two node properties | `lineItem` | the payment's `amount` |
   | two node properties | `payment` | the line item's `sku` |

2. **The shipped example is sound.** `composite-property-boundary-shacl.ttl` has one node property
   (`lineItem`). Its `sku` is a plain datatype property of the line item, swept with the member's
   own triples. The plan expected this example to show the gap, and it does not.
3. **The binding was wrong as well as incomplete.** The compiler bound the first property path it
   met while walking the shape, and the walk followed triple order. A shape that declared a plain
   property before the node property bound the plain one, and the line item was never swept. The
   result depended on how the shape's triples were written (law L1).

## What changed

- `boundary.py`: the walk is in path order, and `Closure.node_properties` lists the paths that lead
  to another node (`sh:node`), separately from every path reached.
- `validator.py`: more than one node property is refused as `CompositeBoundaryMultipleProperties`,
  naming the shape and the properties.
- `operations.py`: the bound property is the node property. A shape with none keeps binding its
  first path, as before, since it has no members to sweep.
- A witness, `refusal-CompositeBoundaryMultipleProperties.ttl` (the harness now has 87 rules, all
  witnessed), and the README's known-limitations entry is rewritten. TD-03 is reworded.

## H-D13, for the human

The decision you took (H-D4) was to refuse the combination. This slice also **changes what is bound
for a shape with exactly one node property**, from "the first path" to "the node property", and puts
the closure in path order. I judged this a defect fix and not a design choice, since the old binding
could pick a plain property and produced different output for the same shape. A reviewer who wants
H-D4 read narrowly can have the refusal alone, at the cost of keeping that order-dependent binding.

## Test cases

In `tools/persistence/tests/test_composite_boundary.py`.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| H1.4a-T1 | the shipped composite example / compile / binds `lineItem` | L4 | + |
| H1.4a-T2 | a plain property that sorts first, or is declared first / compile / still binds the node property | L2 | + |
| H1.4a-T3 | two node properties, in either order / compile / refused as `CompositeBoundaryMultipleProperties` | L3 | − |
| H1.4a-T4 | the two orders / compare / identical refusal, naming the shape and both properties | L2 | − |
| H1.4a-T5 | a node property on a member / compile / refused | L3 | − |
| H1.4a-T6 | a shape with only plain properties / compile / as before | L3 | + |
| H1.4a-T7 | the closure of every declaration order / compare / one result | L2 | + |
| H1.4a-T8 | the shipped example / read the closure / one node property, and `sku` among the paths | L1 | + |
| H1.4a-T9 | the new witness / observe / triggers exactly this refusal | L4 | + |
| H1.4a-T10 | one node property, replace run on rdflib / count what is left / nothing | L5 | + |
| H1.4a-T11 | two node properties bound either way / count what is left / the other member's triples | L5 | − |

T10 and T11 run the generated update on rdflib's in-memory store, so they need no extra dependency and
do not skip. The same scenarios were cross-checked on Oxigraph, with identical results
([`spikes/persistence-oxigraph`](../../../spikes/persistence-oxigraph/README.md)).

## One command

Run from the repository root. A pass is `908 passed, 1 xfailed`, with no skips. The expected failure
is TD-23.

```bash
mise run check:persistence
```


## Adversarial probes

Run by the agent on 2026-10-09, each reverted afterwards.

| Mutation | Result |
|---|---|
| the binding goes back to the first path | T2 fails for both orders. (My first version of T2 passed this mutation, because the sorted closure happened to put `lineItem` first. The test now uses a plain property that sorts before it.) |
| the refusal disabled | T3, T4, T5 and T9 fail, and the witness check fails |
| the closure walked in triple order again | T4 and T7 fail |
| `node_properties` made to include plain properties | T1 and T2 fail, with the refusal reported for the shipped example |

## Deliberate non-coverage

- A sweep over several properties. That is H2 (TD-03).
- A composite boundary with `dal:firstWrite dal:AbsentRow`, which generates no create operation
  (README, a separate limitation).
- Depth beyond `dal:maxTraversalDepth`. The walk stops there and a deeper node property is not seen.
- That a refusal is the right user experience. It is what H-D4 asked for.
