<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-HO6, the ownership refusals and the warning

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice HO6
([plan §3.5](../plans/formal-methods-track-h.md#ho6-the-refusals-and-the-warning)).
**Source:** [ADR-A122](../../architecture/decisions/ADR-A122-aggregate-ownership.md) decisions 1, 4, 5 and 6, and
[sketch §5](../sketches/persistence-aggregate-ownership.md#5-refusals-and-warnings-ho6).
**Decisions needing confirmation:** none. Three small deviations, below.

## Invariant

A boundary shape that leaves ownership unstated, ambiguous, or wrong for the data it describes is refused by
name, so a composite or named-graph aggregate never reaches a delete with an edge nobody classified. Reference
data is never owned unless the aggregate manages it, and no class belongs to two composite aggregates.

## What changed

In `validator.py`, in the order of sketch §5.

| Order | Kind | Refuses when |
|---|---|---|
| 2 | `ComplexBoundaryPath` | a property shape's `sh:path` is neither an IRI nor `[ sh:inversePath IRI ]` |
| 3 | `UnclassifiedBoundaryEdge` | a property shape leads to a node and declares no `dal:ownership` |
| 4 | `OwnershipOnValueProperty` | a value property (`sh:datatype`, or `sh:nodeKind sh:Literal`) carries `dal:ownership` |
| 5 | `CompositeBoundaryWithoutOwnedEdges` | a composite shape owns no edge (added in HO5, see FMH-HO5) |
| 6 | `OwnedReferenceData` | an owned edge leads to `skos:Concept`, `skos:ConceptScheme`, a class a `dal:ReferenceData` covers, or an asserted subclass, and the profile does not declare `dal:ownsReferenceData true` |
| 8 | `BoundaryConflict` | unchanged from HO5 |
| 9 | `OverlappingOwnership` | two composite profiles whose member classes meet, or one's members meet the other's root class. Checked after rule 8, so a profile owning another's root is `BoundaryConflict` every time |
| W | `ReferenceToOwnedClass` (warning) | a property shape outside the aggregate's owned shapes points at a member class that is not the root |

A `dal:NamedGraphBoundary` profile that names a `dal:boundaryShape` is checked by rules 2, 3, 4 and 6 and the
tree is recorded (ADR-A122 decision 6). It may own no edge.

Five witnesses are added for the refusals and one for the warning. The inventory is 96 of 96.

## Deviations, for the maintainer

1. **The messages name a property shape by its predicate and its shape, not by its blank node.** The sketch's text
   used `{ps}`. A blank node's label differs between loads, so a warning that carried it would make the compiled
   profile differ between runs and break H1.5. A shape with a complex path has no predicate and is named by its shape.
2. **Five new refusals, not six.** `CompositeBoundaryWithoutOwnedEdges` came in with HO5. Its test (HO6-T5)
   is here.
3. **`composite-property-boundary-shacl.ttl`'s `LineItemShape` gains `sh:targetClass ex:LineItem`.** The classes
   an overlap is detected on come from the target class of the owned shape, and that shape had none. The warning
   witness also carries a dataset-level epoch profile, so the discouraged row-level default does not appear
   beside the one warning it exists to show.

## Test cases

In `tools/persistence/tests/test_ownership_refusals.py`. T10 runs five times, T14 once per witness.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| HO6-T1 | a sequence `sh:path` / compile / `ComplexBoundaryPath` | L3 | − |
| HO6-T2 | a node property with no `dal:ownership` / compile / `UnclassifiedBoundaryEdge`, naming the shape and predicate | L3 | − |
| HO6-T3 | review F1's shape, `placedBy` with `sh:node` and no classification / compile / `UnclassifiedBoundaryEdge` | L3 | − |
| HO6-T4 | `dal:ownership` on an `sh:datatype` property, and on an `sh:nodeKind sh:Literal` one / compile / `OwnershipOnValueProperty` | L3 | − |
| HO6-T5 | a composite shape with only value and reference properties / compile / `CompositeBoundaryWithoutOwnedEdges` | L3 | − |
| HO6-T6 | a concept and a concept scheme classified `dal:Owned` / compile / `OwnedReferenceData` | L3 | − |
| HO6-T7 | as T6 with `dal:ownsReferenceData true` / compile / accepted | L3 | + |
| HO6-T8 | an owned edge to a class a `dal:ReferenceData` covers, and to its subclass / compile / `OwnedReferenceData` both times | L3 | − |
| HO6-T9 | two composite profiles owning `px:Document` / compile / `OverlappingOwnership`, naming both shapes and the class | L3 | − |
| HO6-T10 | a profile owning another composite profile's root class, five runs / compile / `BoundaryConflict` each time | L3 | − |
| HO6-T11 | the project fixture plus a shape pointing at `px:Milestone` / compile / the warning, and the compile succeeds | L3 | − |
| HO6-T12 | the project fixture / compile / no `ReferenceToOwnedClass` warning | L4 | + |
| HO6-T13 | a shape pointing at the root class / compile / no warning | L3 | + |
| HO6-T14 | each new witness / the witness check / triggers exactly its own rule | L4 | + |
| HO6-T15 | a named-graph profile that names a shape / compile / an unclassified edge is refused, a classified one accepted | L3 | +/− |
| HO6-T16 | the warning, compiled three times / message / identical | L2 | + |

## One command

Run from the repository root. A pass is `1252 passed, 1 xfailed` (1227 before the slice plus 25 items), with no new
skip. The expected failure is TD-23.

```bash
mise run check:persistence
```

## Adversarial probes

Run on 2026-10-10, each restored afterwards.

| Mutation | Result |
|---|---|
| rule 9 skipped (the overlap loop made empty) | T9 and the `OverlappingOwnership` witness fail |
| rule 4 disabled | T4 and the `OwnershipOnValueProperty` witness fail |
| `skos:ConceptScheme` removed from the reference data classes | T6 fails |

## Deliberate non-coverage

- A shape written with `sh:or`, `sh:and` or a path that is a union. Those are `ComplexBoundaryPath` and are not
  examined further.
- That `ReferenceToOwnedClass` is only a warning. ADR-A122 decision 5 chose that, and the roots-only rule is a
  convention the compiler cannot enforce on instance data.
- Create and tombstone delete. HO7.
