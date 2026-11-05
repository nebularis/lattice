<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: VM-3, the thin layer

**Unit:** [vyvid-migration](../plans/vyvid-migration.md)
**Status record:** [vyvid-migration](../status/vyvid-migration.md)

## Invariant

LATTICE keeps only what Вивід has no notion of, the architectural quanta and the catalogue's units, as one extractor command `vyd build` runs in the checkout, and its knowledge tests prove the knowledge base consistent against the store `vyd build` writes ([ADR-A152](../../architecture/decisions/ADR-A152-vyvid-adoption.md) decisions 1 and 6). The modules and tests Вивід's own suite already holds are removed only after those tests pass (plan, decision 4).

## Tests

| ID | Given / When / Then | Level | Invariant | Pass | Kind |
|---|---|---|---|---|---|
| test_vm3_01 | this checkout / the extractor run on Вивід's request / every quad in the index graph, protocol 1, no problem, every text a subject it wrote | L4 | the extractor contract | assertions | positive |
| test_vm3_02 | the same / the substrate's data quantum / it includes modules under the IRI Вивід gives a declared unit | L4 | an Owner edge and a quantum's part meet | assertions | positive |
| test_vm3_03 | the same / the units declared / every module by name, every tool package by path and by name where no module shares it, every module kind | L4 | the catalogue is the one source of units | assertions | positive |
| test_knowledge_base.py, 24 tests | `vyd build` on this checkout / the store read / decisions carry status and pointer, statuses in the closed set, every entry has a claim, a pointer and its scope, standards have a stratum and a check or a reason, enforcement names a capability, evidence targets exist across the index graphs, the facet groups reach their values, every decision file and capability row is a node, every register table is a data table, and the build prints no note but the known ones | L4 | the knowledge base consistent | assertions | positive |
| test_the_release_is_one_data_quantum, test_a_governed_quantum_exists | the store with the extractor run / the quanta / the substrate is one data quantum and a standard governs one | L4 | the quanta derived | skipped with a reason until `vyd trust`, then assertions | positive |
| test_quanta.py, 7 tests | the rules of a quantum, unchanged | L1 | derived, never declared | assertions | positive |

Run by hand on 2026-11-05 and read in full: the extractor run against this checkout gave the same fifteen quanta, identifier for identifier, as `extract.py` built into a scratch store the same day. `mise run check:knowledge` passed with 34 passed and 2 skipped before and after the deletions. `mise run check:identifiers`, `check:hooks` and `check:agent-guidance` passed after them.

## One command

```bash
mise run check:knowledge
```

Run from the checkout's root. A pass is every test passing, with the two quanta tests skipped where the binding is not trusted, since the extractor is a command and runs only after `vyd trust`.

## Artefacts

`tools/knowledge/extractor.py`, `tools/knowledge/test_extractor.py`, `tools/knowledge/test_knowledge_base.py`, the `lattice-quanta` entry of `vyvid.toml`, the tasks `check:knowledge`, `check:identifiers` and `bootstrap:knowledge` in `mise.toml`, `tools/knowledge/README.md` rewritten for what stays, CAP-10 to CAP-12 and CAP-81 re-pointed, and the removal of `extract.py`, `ask.py`, `identifiers.py`, `facets.py`, `anchors.py`, `embed.py`, `knowledge.ttl` and their six test modules.

## Not covered here

The corpus checks the old suite made by reading the extractor's own problem list, every signpost resolving, every question an entry, a superseded decision naming its successor among them, are covered now by one test over the build's notes, since Вивід reports each as a note. A problem Вивід does not report is not caught, and its own suite is where that is tested. The owl-terms extractor names a module by its directory, so a term's owner and a quantum's part are different nodes for one module, which VM-4 or Вивід's side resolves. The board tasks, VM-4.
