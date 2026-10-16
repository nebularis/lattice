<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-HO4, the ownership tree and the path compiler

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice HO4
([plan §3.5](../plans/formal-methods-track-h.md#ho4-the-ownership-tree-and-the-path-compiler)).
**Source:** [ADR-A122](../../architecture/decisions/ADR-A122-aggregate-ownership.md) decisions 1 to 3, and
[sketch §4, §6 and §10](../sketches/persistence-aggregate-ownership.md).
**Decisions needing confirmation:** none. Three small deviations, below.

## Invariant

Reading a boundary shape as a classified tree, and compiling its owned edges to one SPARQL property path,
must reach exactly the nodes an aggregate owns: the root and every node reached by a non-empty path of owned
edges, each in its declared direction, in the context of the shape it was reached in. Nothing calls the new
code from the compiler yet, so no generated SPARQL changes.

## What was built

- `persistence/paths.py`: the path expression tree (`Eps`, `Step`, `Seq`, `Alt`, `Star`, `Opt`), smart
  constructors that give one canonical form, `render`, and `eliminate`, which turns an automaton into one
  expression by state elimination.
- `persistence/boundary.py`, added beside the old walk (untouched): `Edge`, `OwnershipTree` and
  `walk_ownership`. Classification problems (a sequence path, an unclassified edge, ownership on a value
  property) are recorded and not raised, so the validator can name each as its own refusal in HO6.
- `persistence/terms.py`: `PropertyPath`, a `SparqlTerm` whose text is rendered through `Iri.encode` for every
  predicate and parsed as a path before it is returned.
- Fixtures: `ontology/persistence/examples/composite-project-ownership.ttl` (sketch §10.1) and
  `tools/persistence/tests/fixtures/project-data.ttl` (§10.2).

## Deviations, for the maintainer

1. **`Step` is defined once, in `paths.py`, and `boundary.py` imports it.** The sketch gives each module its own
   `Step` with the same fields. One definition removes the duplicate.
2. **A `?` or `*` over an alternative is not parenthesised twice.** The sketch's `render` wraps an `Alt`
   (already parenthesised) again. The path means the same, and the golden string is shorter.
3. **The new example is refused by the current compiler** as `CompositeBoundaryMultipleProperties`, since it has
   several owned edges. That is expected until HO5 switches the compiler to the tree. The test suites that
   iterate the examples treat a refusal as a fixture that does not compile, and the witness check counts it.

## Test cases

In `tools/persistence/tests/test_ownership_tree.py`. T6 runs once per seed, so there are 209 items.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| HO4-T1 | the reference shape / `walk_ownership` / the six shapes in order | L1 | + |
| HO4-T2 | as T1 / the owned edges / the six, `^onTask` the only inverse | L1 | + |
| HO4-T3 | as T1 / `member_classes()` / the five owned classes | L1 | + |
| HO4-T4 | the shape's triples reordered and its blank nodes relabelled, three times / walk and render / identical tree and path | L2 | + |
| HO4-T5 | the reference data / the path from `p1` / the golden text, and `p1` plus the 8 members of the sketch | L4 | + |
| HO4-T6 | 200 seeded random shape graphs (up to 5 shapes, 8 owned edges, inverse steps, self and mutual recursion, owned leaves, references and values) and random data (up to 12 nodes, 30 triples) / members by the path / equal to a breadth-first search of (node, shape) pairs over owned edges | L2 | + |
| HO4-T7 | a predicate containing `>` / `PropertyPath.encode` / `SparqlTermError` | L8 | − |
| HO4-T8 | a single self-recursive owned edge / compile and run on a chain / the text has `)*` and the members are `t2` and `t3` | L1 | + |
| HO4-T9 | a shape with only value, reference and vocabulary properties / `owned_path()` / `None` | L1 | + |
| HO4-T10 | a sequence path, an unclassified edge and ownership on a value / walk / each recorded, nothing raised | L1 | + |

## One command

Run from the repository root. A pass is `1216 passed, 1 xfailed` (1003 before the slice, 209 in the new file,
and 4 from the new example being picked up by the suites that iterate every example), with no new skip.

```bash
mise run check:persistence
```

## Adversarial probes

Run on 2026-10-10, each restored afterwards.

| Mutation | Result |
|---|---|
| state elimination ignores a state's self-loop (recursion lost) | 51 of the 209 items fail, mostly T6 |
| the walk queues the target of a reference edge as well | T1 and the T6 seeds with references fail |
| the inverse flag dropped when reading `[ sh:inversePath p ]` | T2 and T5 fail. T6 cannot catch this one, since it compares the path with the same tree |

## Deliberate non-coverage

- That the compiler uses the tree or the path. HO5.
- The refusals that name each recorded problem. HO6.
- That a path of this size is fast on a real store. HO5 measures a sweep through the generated update.
