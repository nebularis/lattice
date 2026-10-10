<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-HO7, composite create and tombstone delete

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice HO7
([plan §3.5](../plans/formal-methods-track-h.md#ho7-composite-create-and-tombstone-delete-td-04)).
**Source:** [ADR-A122](../../architecture/decisions/ADR-A122-aggregate-ownership.md) decision 3 and
[sketch §7.2 and §7.3](../sketches/persistence-aggregate-ownership.md). **Closes:** TD-04 (removed from the register).
**Decisions needing confirmation:** none. One deviation from the plan's wording, below.

## Invariant

A composite aggregate can be created exactly once and deleted as a whole. A create writes the payload to the
data graph and a version row, and does nothing if the row exists or if anything of the root is already in the
data graph. A tombstone delete removes the root and every member the owned path reaches, keeps the version row
and tombstones it, and writes a deletion revision. Neither touches the default graph.

## What changed

- Four templates: `create-if-absent-composite` and `tombstone-delete-composite`, each with a `-dataset-guard`
  variant. They are the named-graph templates with `GRAPH ?g` replaced by `GRAPH {{{dataGraph}}}` and the
  `?g` binding removed. The create adds the guard `FILTER NOT EXISTS { GRAPH {{{dataGraph}}} { $root ?anyP ?anyO } }`.
  The tombstone sweeps with `$root {{{ownedPath}}} ?s . ?s ?p ?o`.
- `operations.py`: a composite family with `dal:firstWrite dal:AbsentRow` (the default) generates
  `create-if-absent`. Every optimistic composite family generates `tombstone-delete`. A pre-created row gets a
  bootstrap and no create, as for a named graph.
- `templatecheck.py`: the tombstone's `prevRev`, left unbound for a pre-created row, joins the reviewed allowances.
- `gaps.py`: the rule `CompositeNoLifecycleOperations` is removed, and the composite example now reports no
  composite gap.
- Register and README: TD-04 and the `AbsentRow` limitation removed.
- The Oxigraph spike gains two scenarios, a composite tombstone and a create run twice. rdflib and Oxigraph agree.

## Deviation from the plan, for the maintainer

The plan's tests read "the payload in the default graph" (T2) and "everything outside unchanged". After AO-Q14
the aggregate lives in the data graph, so the tests look there and assert the default graph holds nothing.
HO7-T7b adds a check the plan did not list: a tombstone leaves a copy of the data in the default graph alone.

## Test cases

In `tools/persistence/tests/test_composite_lifecycle.py`, on rdflib's `Dataset` with the project fixture.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| HO7-T1 | the project config, and the dataset-guard config, with `AbsentRow` / compile / the create and tombstone templates of each variant | L4 | + |
| HO7-T1b | the same with `PreCreatedRow` / compile / a bootstrap and a tombstone, and no create | L4 | + |
| HO7-T2 | an empty dataset / create `p1` with its aggregate as the payload / the payload in the data graph, a version row at sequence 1, one revision, nothing in the default graph | L5 | + |
| HO7-T3 | as T2, run twice with different transaction ids / the second create / changes nothing | L5 | − |
| HO7-T4 | the root has triples in the data graph but no version row / create / changes nothing | L5 | − |
| HO7-T5 | the project data and a version row at sequence 1 / tombstone delete / the 28 delete-set triples gone, `pat:deleted true`, sequence 2, one `pat:Deletion`, everything outside unchanged | L5 | + |
| HO7-T6 | as T5 with `expectedSeq` 7 / tombstone / nothing changes | L5 | − |
| HO7-T7 | after T5 / replace / refused by the tombstone guard, nothing changes | L5 | − |
| HO7-T7b | a copy of the data in the default graph / tombstone / the copy is untouched | L5 | − |
| HO7-T8 | both configurations / S-3 and S-4 over the compiled profile / no finding | L1 | + |

## One command

Run from the repository root. A pass is `1333 passed, 1 xfailed`, with no new skip. The expected failure is TD-23.
The Oxigraph spike, if `pyoxigraph` is installed, passes with `8 passed`.

```bash
mise run check:persistence
```

## Adversarial probes

Run on 2026-10-10, each restored afterwards.

| Mutation | Result |
|---|---|
| the data-graph guard removed from the create | T4 fails |
| the tombstone no longer sets `pat:deleted` | T5 and T7 fail |

## Deliberate non-coverage

- A tombstone followed by an explicit recreate, which the guide's section 24.1 describes as a distinct operation
  that requires the tombstone. It is not generated for either strategy.
- Erasure of personal data, which follows its own procedure (ADR-A122 consequences).
