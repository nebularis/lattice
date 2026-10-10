<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Spike: aggregate ownership and concurrency

**Status:** a spike, not production. It defines no interface and changes no tool. Nothing in
`tools/` or `platform/` imports it.
**Reviewed 2026-10-10:** [persistence-aggregate-ownership-review.md](../../docs/developer/notes/persistence-aggregate-ownership-review.md),
sections S1 to S6. Slice HO0 of the [Track H plan](../../docs/developer/plans/formal-methods-track-h.md#35-ho-aggregate-ownership)
applies its corrections here.
**Origin:** the [aggregate ownership note](../../docs/developer/notes/persistence-aggregate-ownership.md),
which asks whether `persistence` models an aggregate correctly. These experiments check claims the
note makes. They are read-only against the compiler, which they use only to obtain generated text.

## Contents

| File | Role |
|---|---|
| `placement.py` | the placement example (client, contacted markets, tower, layers, bindings, policy, vocabulary concepts) as an rdflib graph, and five ways of deciding which nodes a delete takes |
| `concurrency_model.py` | a model of two overlapping writers under snapshot isolation with statement-level first-committer-wins, and five version-row disciplines |
| `payload_graph.py` | runs the generated composite replace and reports which graph holds the new payload |
| `run.py` | prints all three |
| `test_spike.py` | seventeen checks that the printed results are the ones the note quotes |

## Running it

From the repository root, after `mise run bootstrap` for the persistence packages. Needs rdflib only.

```bash
mise exec -- python spikes/persistence-aggregate-ownership/run.py
mise exec -- python -m pytest spikes/persistence-aggregate-ownership -q
```

It is not wired into any `mise` task or into `check`, on purpose.

## What it does not show

- `concurrency_model.py` is a model of a rule, not a store. Its isolation assumption is the one the
  capability record names (`detectsWriteWriteConflict`, `statementLevelConflictDetection`). A store
  that detects at graph or page granularity conflicts more often, and one that detects nothing
  conflicts never. Neither is modelled.
- Only pairs of operations are tried, in the two commit orders, with both snapshots taken before
  either commit. Three or more writers and other interleavings are not.
- The closure experiments run on one hand-made graph. They show that a strategy can go wrong, not
  how often it does.
- Only rdflib is used. Unlike `persistence-oxigraph`, no second engine cross-checks them.
