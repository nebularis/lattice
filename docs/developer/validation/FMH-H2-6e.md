<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-H2.6e, how references between versions are declared

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice H2.6e, planned in
[plan §4.11](../plans/formal-methods-track-h.md#411-h26e-how-references-between-versions-are-declared-planned-2026-10-20)
(H2.6e-Q1 to Q4), decided 2026-10-20 and built the same day for the maintainer's review. Authored and run in autonomous mode, not committed.
Versioning is ignored on this branch (TD-64), so no version IRI moved.

**For the maintainer:** re-approve the three expected profiles that changed (below), accept or change the ADR-A123 addendum (accepted with the
slice's plan, so the decisions taken alone are the part to read), and read the decisions taken alone.
**For countersignature (non-weakening rule):** no existing test was weakened, skipped or removed. Two helpers in the expected-profile tests gained an
argument (below).

## Invariant

A property shape of a boundary shape may declare `dal:referenceMode`, `dal:ByIdentity` or `dal:Pinned`, and absent means `dal:ByIdentity`. `compile`
records the mode of every edge that leads to a node, refuses `dal:Pinned` where the edge's target class is not a subclass of `fnd:Versioned`, and
warns `EvidenceEdgeByIdentity` for an edge by identity from an evidence class to a versioned one. The contract of each operation that takes a payload
carries the same edges and modes. The mode changes no generated operation.

## What changed

- **Vocabulary** (`spec/persistence.ttl`). `dal:ReferenceMode`, `dal:ByIdentity`, `dal:Pinned`, `dal:referenceMode` (no domain, as `dal:ownership`),
  and for the compiled profile `dal:ReferenceEdge`, `dal:referenceEdge`, `dal:edgeSource`, `dal:edgePredicate`, `dal:edgeInverse`,
  `dal:edgeOwnership` and `dal:edgeTargetClass`.
- **The walk** (`boundary.py`). `Edge.reference_mode`, `OwnershipTree.node_edges()` (every edge that leads to a node) and `unknown_modes`.
- **The checks** (`validator.py`). The refusals `PinnedReferenceToUnversionedClass` and `ReferenceModeUnknown`, in the tree check, and the warning
  `EvidenceEdgeByIdentity` from `check_reference_modes`, for composite and named-graph families that name a boundary shape. `_is_versioned` is the
  test `VersionedClassWrittenInPlace` used, now shared.
- **The profile** (`compiler.py`). One `dal:ReferenceEdge` per edge that leads to a node, in a total order, with blank nodes labelled from the
  profile's stem and the index.
- **The contract** (`contract.py`). `EdgeContract`, `edge_contracts(tree)`, `PayloadContract.edges`, and `contract_of(operation, edges=())`.
- **Expected profiles** (`tests/expected_profiles.py`). The payload contract links its edges as declaration nodes minted from the target, the
  operation and the index, and the enumerations file declares the new class and individuals.
- **Fixtures.** Three witnesses, `refusal-PinnedReferenceToUnversionedClass`, `refusal-ReferenceModeUnknown` and `warning-EvidenceEdgeByIdentity`.
- **Documents.** The ontology README §7.1 (what an edge names, the refusals and "when to pin"), `docs/aggregate-boundaries.md`, the compiler README,
  ADR-A123's addendum, and TD-67.

## Expected profiles (for re-approval)

| File | Change |
|---|---|
| `composite-project-ownership.expected.ttl` | gains the profile's `dal:ReferenceEdge` nodes and, on each payload contract, the edges with their modes (all by identity) |
| `write-discipline-composite-append-versions.expected.ttl` | the same |
| `kinds.expected.ttl` | declares `dal:ReferenceEdge`, `dal:ReferenceMode`, `dal:OwnershipKind` and the individuals `dal:ByIdentity`, `dal:Pinned`, `dal:Owned`, `dal:Reference`, `dal:Vocabulary` |

The other nine are unchanged, since no other example names a boundary shape. No example declares `dal:Pinned`, so the tests carry that case.

## Decisions taken alone, for the maintainer's review

1. **The compiled profile records every edge that leads to a node, with the default stated.** One `dal:ReferenceEdge` per edge carries its source
   shape, predicate, inverse flag, ownership, target class and mode, so a reader needs no default rule and no walk of the shape. The alternative,
   recording only declared modes, would leave an absent mode to be inferred by each reader. The owned path binding is unchanged.
2. **The contract carries the same edges, passed to `contract_of` and held on the payload contract.** An operation cannot know its family's shape,
   so the edges are a second argument and an operation with no payload has none. The profile and the contract state them twice, as the profile
   already does for a boundary shape.
3. **The check covers every edge that leads to a node,** owned, reference and vocabulary. A pinned edge on a value property is refused by the same
   rule, since it has no target class. A pinned owned edge to a versioned member is accepted.
4. **An unknown mode is refused at compile** (`ReferenceModeUnknown`) and not by a new SHACL shape. `compile` does not run the shapes, so a shape
   alone would let a typo become `dal:ByIdentity`.
5. **The evidence test reads the class of the edge's source shape** (its `sh:targetClass`, and the shape's root class for the root), not the
   target of the profile. A class the profile "names as a record" (Q3) is not built, since the profile has no way to name one (TD-67).
6. **The warning is per edge, with a witness that reuses the base example's own by-identity edge,** so the fixture is two `rdfs:subClassOf` triples.
7. **Versioned means a subclass of `fnd:Versioned` by IRI in the loaded graphs,** the same test as `VersionedClassWrittenInPlace`, with no import.
8. **No new example.** The refusals and the warning are tested by small graphs built on `composite-property-boundary-shacl`.

## Changes to existing tests

| Test | Change |
|---|---|
| `expected_profiles.contract_for` and the helpers of `test_expected_profiles.py` | take the family's edges, `_facts` and `_read_contract` read `dal:referenceEdge`, so the agreement tests (`test_h2_6_t4` and `t5`) compare the edges too |

## Test cases

`test_reference_modes.py`, 14 cases.

| ID | Checks |
|---|---|
| H2.6e-T1 | the vocabulary declares the property with no domain, and exactly the two individuals |
| H2.6e-T2 | an edge with no mode is by identity, and a declared one is read |
| H2.6e-T3 | the compiled profile records each edge with ownership, target class and mode |
| H2.6e-T4 | a pinned edge to a versioned class compiles, and the generated operations and bindings are those of the by-identity edge |
| H2.6e-T5 | a pinned edge to an unversioned class is refused |
| H2.6e-T6 | a pinned edge with no target class, and a pinned value property, are refused |
| H2.6e-T7 | an unknown mode is refused |
| H2.6e-T8 | a pinned owned edge is refused for an unversioned member and accepted for a versioned one |
| H2.6e-T9 | the warning for `fnd:Evidence`, `fnd:DerivedArtefact` and a subclass of either |
| H2.6e-T10 | no warning when the edge is pinned, the subject is not evidence or the target is not versioned, and one per edge |
| H2.6e-T11 | the warning is a `WARNING` and names the edge |
| H2.6e-T12 | the contract's payload carries the edges and modes in a total order |
| H2.6e-T13 | `contract_of` with no edges, and an operation with no payload, carry none |
| H2.6e-T14 | a family with no boundary shape records no edge |

The witness coverage tests cover the three new rules, and `test_expected_profiles` holds the files to the compile output and the builders.

## One command

```
mise run check:persistence
mise run check:persistence-oxigraph
mise run check:ontology-catalog
```

From the repository root. A pass is no failed test, and `check:persistence-expected-profiles` (part of the first) reporting that the profiles are
current. `mise run build:persistence-expected-profiles` regenerates them.

## Results

| Command | Result |
|---|---|
| `mise run check:persistence` | 3662 passed, 1 xfailed, no failures, expected profiles current (H2.6d recorded 3648 passed) |
| `mise run check:persistence-oxigraph` | 329 passed in the persistence tests marked for Oxigraph, none skipped |
| `mise run check:ontology-catalog` | 1136 passed, 7 skipped, consistent, two known defects reported |
| `mise run check:ontology-versioning` | not run here, which fails `UNBUMPED` as expected while this branch ignores versioning (TD-64) |

`build:persistence-execution` was not run, so no generated `execution` directory was left. Not run: `check:deny-terms` (needs a personal
deny-list, run before a commit).

## Adversarial probes

Each was run on the finished tree and then reverted. `validator.py` was restored from a copy and its diff is the slice's change.

1. **A pinned edge to an unversioned class accepted** (the check disabled). T5, T6 and T8 fail, and the witness coverage tests fail, since
   `PinnedReferenceToUnversionedClass` has no witness that raises.
2. **The warning suppressed** (the loop over edges emptied). T9, T10 and T11 fail, and the witness coverage tests fail, since the witness
   `warning-EvidenceEdgeByIdentity` no longer produces the diagnostic.

## Deliberate non-coverage

- The caller check of H2.8, that the object on a pinned edge is a version and on an identity edge is not a version of a versioned class (TD-67).
- A generated read that resolves an identity through a root version's membership (H2.6e-Q4).
- A class the profile names as a record, for the evidence warning (TD-67).
- Fuseki and the other stores, since no store sees the mode.
