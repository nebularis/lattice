<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-H2.4a, the composite family's builders

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice H2.4a, planned in
[plan §4.2](../plans/formal-methods-track-h.md#42-h24-the-composite-family-and-what-each-store-does-planned-2026-10-12)
under [ADR-A123](../../architecture/decisions/ADR-A123-typed-operation-ir.md) and its addenda.
**For countersignature (non-weakening rule):** one item, below. **Open decisions:** none.

## Invariant

The six composite templates render the query their builders do, apart from the guard. A replace or tombstone with no `$root`
writes nothing. Every ported operation of every family can be encoded structurally and decoded to an equal value, builds
equal twice, and builds without reading a file, the clock or the environment (SI-1, SI-2), so a stored IR stays possible
(PDD-06).

## What changed

- **Six templates ported** in `builders.py`: `create-if-absent-composite`, `cas-replace-composite-property` and
  `tombstone-delete-composite`, each with its dataset-guard variant. The path is read with `Bindings.path`, the data graph
  with `b.graph("dataGraph")`, and the receipt's `?logGraph2` is kept (plan §4.2, fact 4). The replace and tombstone share
  their `WHERE` with the named-graph writers through `_row_where`, which now takes the sweep as an argument. The harness
  covers the new stems, and the harness, binding, guard and role cases (H2.2-T1 to T6, H2.3-T32) run over them.
- **`test_composite_builders.py`**, 14 cases, below.
- Nothing in `instantiate`, the CLI or the IR changed.

### For countersignature

**Test inputs changed in three files** (`test_composite_boundary.py`, `test_composite_lifecycle.py`,
`test_composite_sweep.py`). They bound `$epoch` as an `xsd:integer`, and stored the row's and the dataset graph's epoch the
same way, so the request matched the store by term. The composite operations now carry the parameter guard, which refuses an
`xsd:integer` epoch (the README says it is a different term and never matches), so the request and the stored epochs are
`xsd:long`. The assertions are unchanged. This is the same change as FMH-H2-3's second countersignature item, now for the
composite tests.

## Test cases

In `test_composite_builders.py`, with the harness cases of H2.2 and the lifecycle tests of HO1, HO5 and HO7, which run on
the builders.

| ID | Given / When / Then | Level | Invariant | +/- |
|---|---|---|---|---|
| H2.4a-T1 | a replace / its derived sets / the sweep is a `closure` read with the path's text, the writes are the data graph's `?s ?p ?o`, the payload and the row | L3 | the sets H5 reads | + |
| H2.4a-T2 | a tombstone, and a create / their sets / no payload write, no closure, and the create reads the root's triples | L3 | as T1 | + |
| H2.4a-T3 | a replace with no `$root` over two stored aggregates / executed with and without the guard / guarded writes nothing, unguarded sweeps both aggregates, writes the payload once and moves both rows | L4 | the guard before any pattern binds `$root` (F1) | − |
| H2.4a-T4 | a replay of a replace and of a tombstone / executed / nothing changes | L4 | retry is a no-op | + |
| H2.4a-T5 | a row whose aggregate has no triples / replaced / the payload is written and the row moves | L4 | the sweep is optional | + |
| H2.4a-T6 | a path that may match no steps, and an inverse step / executed on rdflib / the root is reached, and a node is reached against the edge | L4 | the engine rules the sweep relies on | + |
| H2.4a-T7 | a payload keeping a triple the aggregate has / executed on rdflib, which applies each solution in turn / the triple survives | L4 | R0 is right whatever order an engine applies a result in | + |
| H2.4a-T8 | every ported operation, guards on and off, both graph-naming forms / encoded structurally and decoded / equal to itself | L2 | SI-1 | + |
| H2.4a-T9 | every ported operation / built twice / equal | L2 | SI-2 | + |
| H2.4a-T10 | every ported operation / built with `open`, `time.time`, `os.getenv` and `os.environ` refused / built and equal | L2 | SI-2: no file, clock or environment | + |
| H2.4a-T11 | an operation holding a callable, a list, an rdflib node or a dict / encoded / `TypeError` | L2 | SI-1 is enforced | − |

The behaviour of a composite create, replace and tombstone on the ADR-A122 fixture is covered by HO1-T1 to T7, HO5-T1 to T10
and HO7-T2 to T7, unchanged apart from the epoch type. They now run on the builders.

## One command

Run from the repository root. A pass is `2035 passed, 1 xfailed`, the 2003 of H2.3 and 32 new cases. The harness now compares
more operations, and 14 of the new cases are in `test_composite_builders.py`.

```bash
mise run check:persistence
```

## Artefacts to inspect

- `builders.py`, `_composite_create`, `_composite_replace` and `_composite_tombstone`, beside their templates.
- `test_composite_builders.py`, `encode` and `decode`, the structural encoding that SI-1 and SI-2 use.

## Adversarial probe

Run on 2026-10-12, restored afterwards.

| Mutation | Result |
|---|---|
| the path replaced by one that matches nothing | the harness fails (10 cases) |
| the sweep moved out of its `OPTIONAL` | the harness fails (25 cases) |
| the guard at the top level of `WHERE` | 37 cases fail, T3 among them |
| a builder reads the clock | T10 fails |
| a builder keeps a list | T8 fails |
| the create's check that the root has no triples removed | the harness fails |

## Deliberate non-coverage

- The measurements, Oxigraph and the benchmark, H2.4b.
- The payload check against the boundary shape, H2.8.
- Recording the path or the read set in the compiled profile, H2.7.
- A stored IR itself. SI-5 (paths hold text) is open until PDD-06.
- Removing `?logGraph2`, a change for later.
