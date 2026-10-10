<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-HO5, switch the compiler to the ownership tree

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice HO5
([plan §3.5](../plans/formal-methods-track-h.md#ho5-switch-the-compiler-to-the-tree)).
**Source:** [ADR-A122](../../architecture/decisions/ADR-A122-aggregate-ownership.md) decisions 1 to 3,
[sketch §4.3, §5 and §7.1](../sketches/persistence-aggregate-ownership.md), and review findings F1, F4 and F10.
**Closes:** TD-03, TD-35, TD-37 and TD-40 (removed from the register).
**Decisions needing confirmation:** none. Four deviations from the plan, below, and the list of removed and
rewritten tests, which the plan asks the maintainer to countersign.

## Invariant

A composite aggregate is exactly the root and the nodes reached from it by the owned edges of its
boundary shape, in the direction and context each edge declares. A replace deletes the triples whose subject
is one of those nodes and writes the payload, both in the profile's data graph, and touches nothing else:
not a reference, not a vocabulary node, not another aggregate, and not the default graph.

## What changed

- `resolver.py` stores the `OwnershipTree` as `boundary_dim.extra["ownershipTree"]`, and reads `dataGraph` and
  `ownsReferenceData`. It no longer writes `compositeProperties`, `compositeEdgeProperties` or `maxTraversalDepth`.
- `operations.py` binds `ownedPath` (a `PropertyPath`) and `dataGraph` (an `Iri`) for the composite replace, and
  no longer binds `compositeProperty`.
- The two composite replace templates sweep with `$root {{{ownedPath}}} ?s . ?s ?p ?o` and write the payload, all
  inside `GRAPH {{{dataGraph}}}`. The default graph is not read or written.
- `validator.py`: `MissingDataGraph` is checked first among the boundary rules. `UniquenessOutsideBoundary` reads
  `tree.predicates()`. `BoundaryConflict` reads the member classes of the tree at every depth.
  `CompositeBoundaryWithoutOwnedEdges` is new (deviation 1). `CompositeBoundaryMultipleProperties` is deleted.
- `boundary.py` loses `walk_boundary_shape`, `Closure`, `reachable_properties` and `BoundaryCycleError`.
- Witnesses: `refusal-MissingDataGraph.ttl` and `refusal-CompositeBoundaryWithoutOwnedEdges.ttl` are added.
  `refusal-CompositeBoundaryMultipleProperties.ttl` and `refusal-BoundaryCycleError.ttl` are deleted. The inventory
  stays at 90 of 90.
- `gaps.py` loses the three rules this closes (`CompositeOwnershipAssumed`, `CompositeInversePathMisread`,
  `CompositeUsesDefaultGraph`), with their expectations in `test_gaps.py`.
- Spikes. `persistence-oxigraph` is rewritten for the new binding and gains the project fixture. The
  aggregate-ownership spike's payload test now expects the data graph.
- Register and README: TD-03, TD-35, TD-37 and TD-40 removed, and the known-limitations entry rewritten.

## Deviations from the plan, for the maintainer

1. **`CompositeBoundaryWithoutOwnedEdges` is added here and not in HO6.** A composite shape with no owned edge
   has no path to bind, and the plan's HO5 leaves it to compile with nothing to sweep. Rewriting H1.4a-T6, which
   asserted that such a shape compiled, needed a decision, and a refusal with a witness is the smaller one. HO6
   keeps its test (T5) and loses only the witness and the rule.
2. **HO5-T8's example would not be refused.** The plan keys a constraint on `ex:name` of `ex:Organisation` and
   expects `UniquenessOutsideBoundary`. A key names a property, not a class, and `ex:name` is a value property of the
   project itself, so it is in `tree.predicates()`. The test uses `ex:serialNumber`, which no shape declares.
3. **The HO1 tests move from the default graph to the data graph.** `test_composite_sweep.py` loads its data into
   `urn:g:orders` and looks for the payload there. The property each asserts is unchanged (the payload lands where
   the sweep deletes from, the sweep is linear, a stale sequence changes nothing).
4. **The Oxigraph spike ran, in a Python 3.13 virtual environment**, since this machine's default Python (3.14)
   has no `pyoxigraph` wheel. Seven checks pass, and the two engines agree on every scenario, including the
   project fixture. The environment is local to this machine and is not recorded in the repository.

## Removed and rewritten tests, for the maintainer to countersign

Each removal is justified by ADR-A122 decision 1, which supersedes the rule the test asserted.

| H1.4a test | Fate | Replacement |
|---|---|---|
| T1, the shipped example binds its one node property | rewritten | HO5-T1a, the owned path `(<lineItem>)?` and the data graph |
| T2, a plain property that sorts first is not the bound property | rewritten | HO5-T2a, a value property is not followed |
| T3, two node properties are refused | **deleted** | HO5-T6, both owned edges sweep |
| T4, the refusal is identical in either order | **deleted** | HO5-T7, the owned path is identical in every declaration order |
| T5, a node property on a member counts too | **deleted** | HO5-T1, T4 and the project fixture, where owned edges sit on members at three levels |
| T6, a shape with only plain properties compiles | rewritten | HO5-T11, it is refused as `CompositeBoundaryWithoutOwnedEdges` |
| T7, the closure is independent of triple order | rewritten | HO5-T7, six shuffles and relabellings of the project shape |
| T8, node properties hold only the paths that lead to a node | rewritten | `test_boundary.py`, owned edges and predicates of the shipped example |
| T9, the witness triggers exactly this refusal | **deleted** | HO5-T12, the two new witnesses |
| T10, one node property leaves nothing behind | rewritten | HO5-T5 |
| T11, the other member is left behind | rewritten | HO5-T6, now both are swept |

Also removed: `test_boundary.py`'s cycle test (recursion is allowed, so a shape that leads back to itself is
walked once), its two walk tests (rewritten for the tree), the two deleted witnesses, and the HO1 tests'
default-graph expectation (deviation 3).

## Test cases

In `tools/persistence/tests/test_composite_boundary.py`, on rdflib's `Dataset` with the project fixture.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| HO5-T0 | the project fixture / its delete set / 28 triples, written by hand from the sketch | L1 | + |
| HO5-T1 | the project aggregate, a payload equal to it but for `t3`'s status / replace / exactly the 28 triples removed, the payload present, everything outside unchanged | L5 | + |
| HO5-T2 | as T1, an empty payload / replace / no triple of the project or its members, the rest unchanged | L5 | + |
| HO5-T3 | a reference given `sh:node` beside an owned `lineItem` / replace / the customer's triples are unchanged (review F1) | L5 | − |
| HO5-T4 | the comment linked by `^onTask` / replace dropping it / all three of its triples are gone (review F4) | L5 | + |
| HO5-T5 | the shipped composite example / replace / nothing left | L5 | + |
| HO5-T6 | two owned edges from the root / replace / both members' triples gone | L5 | + |
| HO5-T7 | six shuffles of the project shape's triples with relabelled blank nodes / compile / the same `ownedPath` | L2 | + |
| HO5-T8 | a key on `ex:title`, then on `ex:serialNumber` / compile / accepted, then `UniquenessOutsideBoundary` | L3 | +/− |
| HO5-T9 | a member class at depth 3 with its own named-graph boundary / compile / `BoundaryConflict` | L3 | − |
| HO5-T10 | a composite profile without `dal:dataGraph` / compile / `MissingDataGraph`. And with the data copied into the default graph / replace / the copy is untouched | L3, L5 | − |
| HO5-T11 | a composite shape with only a value property / compile / `CompositeBoundaryWithoutOwnedEdges` | L3 | − |
| HO5-T12 | each new witness / the witness check / triggers exactly its own rule | L4 | + |
| HO5-T13 | the validator source and the witness directory / the old refusals are gone | L1 | + |

## One command

Run from the repository root. A pass is `1227 passed, 1 xfailed`, with no new skip. The expected failure
is TD-23. The aggregate-ownership spike passes with `18 passed`.

```bash
mise run check:persistence && python -m pytest spikes/persistence-aggregate-ownership -q
```

The Oxigraph spike, if `pyoxigraph` is installed, passes with `7 passed`.

## Adversarial probes

Run on 2026-10-10, each restored afterwards.

| Mutation | Result |
|---|---|
| the replace reads the aggregate outside the data graph | T1 to T6 fail, and two of the HO1 tests |
| the owned path drops the inverse flag | T2 and T4 fail (the comment is left behind) |
| `BoundaryConflict` stops reading the deeper member classes | T9 fails |

## Deliberate non-coverage

- The refusals for an unclassified edge, a sequence path, ownership on a value, owned reference data and
  overlapping ownership. HO6. Until then an edge with no `dal:ownership` is simply not followed.
- Create and tombstone delete for the composite strategy. HO7.
- `ontology/persistence/docs/aggregate-boundaries.md` still describes a cycle-checked closure. HO9 rewrites it.
