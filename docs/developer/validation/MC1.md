<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: MC1, blank nodes labelled by their subtree

**Unit:** [`improved-ontology-documentation`](../status/improved-ontology-documentation.md), slice MC1
([plan](../plans/improved-ontology-documentation.md#mc1-blank-nodes-labelled-by-their-subtree)).
**Closes:** TD-55. **Built autonomously**, 2026-10-19 (OD-D62).

## Invariant

The migration check labels each blank node by a digest of its own subtree, the triples reachable from it. A
change confined to one subtree changes only that subtree's labels and the triples that point at it, so a
reconciliation lists what changed and nothing else.

## What changed

- `tools/literate_migration_check.py`. `labelled()` writes a graph's triples with subtree labels, and
  `differences()` compares those sets in place of `graph_diff` over `to_isomorphic`.
- `tools/test_literate_migration_check.py`. MC1-T1 and MC1-T2.
- `docs/developer/validation/ELC-reconciliations.txt`, regenerated in the new labels: 102 differences where there
  were 126. The unchanged SPARQL shapes are gone from it.
- TD-55 removed from the register, its home being this slice.

## Decisions taken alone, for the maintainer

1. **Two blank nodes with the same subtree share a label.** Their triples then count once. A blank node added
   with the same content as an existing one is still found, through the triple that points at it.
2. **A cycle through blank nodes** is labelled `_:cycle` where it closes. No generated file has one.
3. **An RDF list still shows every cell** when one member changes, since each cell's subtree holds the rest of the
   list. ELC's disjointness list is an example. Labelling list members by position would shorten that, and is
   not done, since lists are short in every module.
4. **OD6's reconciliation file is left in the old labels.** It records the migration against `dab1c790` and no
   longer applies on this branch, since ELC changed the graphs after it.

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| MC1-T1 | two shapes, one with a SPARQL constraint / a third shape added / only the new shape's four triples differ | L1 | + |
| MC1-T2 | one blank node reached from two subjects / labelled, and rewritten as two equal blank nodes / one label, no difference | L1 | + |

OD6-T6, OD6-T7 and ELC-T1 still pass.

## Commands

```bash
mise exec -- python -m pytest tools/test_literate_migration_check.py -q
```

```bash
mise run check:literate-migration -- eligibility 82fc2b25 --reconciliations docs/developer/validation/ELC-reconciliations.txt
```

## Results

2026-10-19: 5 passed. The ELC check passes with 102 reconciled differences.

## Decisions answered

2026-10-20, by the maintainer: approved, with every decision taken alone.
