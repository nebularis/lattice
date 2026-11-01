<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: DR1, the delta replace in the persistence compiler

**Unit:** [`persistence-delta-replace`](../status/persistence-delta-replace.md), slice DR1 of the [plan](../plans/persistence-delta-replace.md). Built and run in autonomous mode on 2026-11-01. Versions are deferred to the merge (STD-111), so the persistence README carries the change under its Unreleased note.

**For the maintainer:** accept or change ADR-A123's addendum of 2026-11-01, and read the decisions taken alone below.
**For countersignature (non-weakening rule):** one case of an earlier slice's test was removed and replaced by its inverse. H2.1's refusal of a payload slot in a `DELETE` template (`test_ir.py`, `SlotMisuse`, "payload in DELETE") is lifted by ADR-A123's addendum, and `test_dr1_a_payload_slot_in_a_delete_template_is_accepted_and_recorded_as_a_delete` asserts the new rule in its place. A slot in `WHERE` is still refused. Every test that exercised the whole replace on an example that now defaults to the delta replace reads a whole-state witness instead, so it tests what it tested before. Two counts that list builders grew by the new builders.

## Invariant

Under `dal:Optimistic`, a family written in place replaces a state by writing only what changed: the retracted triples deleted and the asserted ones inserted, guarded on the version row, with no sweep. Where a profile names `dal:WholeState`, or the family is not optimistic and in place, the replace is the whole replace as before. A delta replace leaves the state a whole replace leaves, and does nothing when its sequence is stale or its transaction was already applied (ADR-A123, addendum of 2026-11-01, DR-Q1 to DR-Q4).

## What changed

- **Vocabulary.** `dal:ReplaceEncoding`, `dal:ChangedTriples`, `dal:WholeState` and `dal:replaceEncoding` on `dal:WriteDisciplineProfile`, with a shape, in the persistence README (§5.6.12) and the generated spec and shapes.
- **Resolution and checks.** A new dimension, `replaceEncoding`, whose default follows the concurrency profile and the discipline (`default_replace_encoding`), and two refusals with witnesses, `ReplaceEncodingUnknown` and `ChangedTriplesNeedsOptimisticInPlace`.
- **Builders.** `cas-replace-named-graph-delta` with its patch-log, no-receipt and dataset-guard variants, and `cas-replace-composite-property-delta` with its patch-log and no-receipt variants and their dataset-guard variants, twelve in all. The IR accepts a payload slot in a `DELETE` template and records it as a delete.
- **Contract.** A delta replace has kind `Replace`, no payload contract, and a digest of its add and del parts alone (DR-Q3 (a)).
- **Fixtures.** Whole-state witnesses for each whole-replace builder, whole-state copies of the examples the composite tests read, the two refusal witnesses, and two whole-state profiles for the caller libraries' tests.
- **The studio.** Its profile declares `dal:WholeState` for every family until DR4 moves its writer onto the delta replace.
- **Documents.** ADR-A123's addendum, the persistence README, the compiler README.

## Tests

| ID | Given / When / Then | Level | Pass |
|---|---|---|---|
| DR1-T1 | a named graph of three triples, each receipt model / one triple retracted and one asserted by the delta replace, and the same change by the whole replace / both graphs and both version rows are equal | L4 | every engine, guards on and off |
| DR1-T2 | a patch-log family / a delta replace / the add and del graphs named from the receipt hold the asserted and the retracted triples | L4 | every engine |
| DR1-T3 | a stale sequence, or a transaction already claimed / a delta replace / no quad changes | L4, negative | every engine |
| DR1-T4 | a composite family whose shared data graph holds another aggregate / a delta replace / the other aggregate's triples are untouched | L4 | every engine |
| DR1-T5 | the dataset-guard variants / a delta replace / the same state as T1 | L4 | every engine |
| DR1-T6 | the rendered delta replace / read / no sweep, and the `DELETE` holds the retract slot alone | L1 | static |
| DR1-T7 | the baseline and composite examples, which declare no encoding / compile / their replace is the delta replace | L3 | |
| DR1-T8 | the baseline example with `dal:WholeState` / compile / its replace is the whole replace | L3 | |
| DR1-T9 | a `DELETE` template with a payload slot / check / accepted, recorded as a delete of `{payload}` | L1 | |
| DR1-W | the two refusals / compile their witnesses / each is refused by name | L3, negative | witness coverage |

**The one command:** `mise run check:persistence-conformance`, which runs the compiler's suite on rdflib, Oxigraph and Jena. `mise run check:persistence` and `mise run check:persistence-library` run the default engine and both caller libraries.

## Results, 2026-11-01

| Command | Result |
|---|---|
| `mise run check:persistence` | 4,312 passed |
| `mise run check:persistence-conformance` | 5,104 passed |
| `mise run check:persistence-library` | 91 vector checks, the Java library's tests and 113 Python tests passed |
| `PERSISTENCE_ENGINES=rdflib,oxigraph,jena`, `test_delta_replace.py` | 64 passed |

## Decisions taken alone, for the maintainer's review

1. **The default is derived after resolution,** in `default_replace_encoding`, since no static baseline can say "changed triples when optimistic and in place". The compiled profile records the value a family resolved to, declared or derived.
2. **`dal:ChangedTriples` is refused only where a profile declares it** for a family that is not optimistic and in place. The derived default never asks for it there.
3. **The composite delta relies on the caller's payload check over the next state,** since a shared data graph cannot tell one aggregate's triples from another's in the update. A guard in the update would need the delta's subjects as rows and a reachability test against the state before and after, which the store would pay on every write.
4. **The delta builders have kind `Replace`,** not a new kind, so a caller dispatches on the slots the contract names. A new kind would be one more term every caller and the compiled profile's vocabulary carry, and would answer no question differently.
5. **The studio keeps the whole replace until DR4,** by declaring `dal:WholeState`, so this slice changes no studio behaviour.

## Not covered

The callers filling the delta slots and the conformance vectors of a delta digest are DR3. `load-whole` and the state digest option are DR2. The studio's writer is DR4.
