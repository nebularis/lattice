<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-1.1, drop the legacy contract module, create the layout

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Machine:** S (Copilot Business). **Branch:** `air/1.1-layout`
**Plan and test cases:** [Phase 1 plan](../plans/applied-insurance-reference-phase-1.md) (AIR-1.1)
**Decisions:** ADR-A98 (decisions 1, 5, 6, 8, and its addendum)

## Invariant

The legacy module and its known defect are gone, no ontology or tool file refers to it, and the applied layer's READMEs describe the layout of ADR-A98.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root on machine R, after `mise run build:ontology-catalog`.

```bash
mise run check:ontology-catalog && mise run check:ontology-versioning && ! grep -rnE 'ontology/nsd|neuro-semantic/insurance/contract|structure-vocab' ontology tools
```

## Artefacts to inspect

- `ontology/applied/README.md` and `ontology/applied/insurance/domain-README.md` against ADR-A98.
- The `KNOWN_DEFECTS` table in `tools/ontology_catalog.py`.

## Deliberate non-coverage

No new module is created. `insurance/common/` and `classification/` are AIR-1.2.

## Handoff

Written by the building machine when the work is committed. S could not run the command, so R runs it first.

- **Built:** removed the legacy module (`git rm`: `spec/structure/{contract.ttl,README.md,catalog-v001.xml}`, `vocab/structure-vocab.ttl`, `shapes/{structural.ttl,constraints.ttl,.version}`). Deleted its `KNOWN_DEFECTS` entry in `tools/ontology_catalog.py`. Rewrote `ontology/applied/README.md` (three sharing levels, dependency direction, namespaces, module table). Wrote new `ontology/applied/insurance/domain-README.md` (module table, dependencies, namespaces, the dropped module's release tags, links to the epic and sketches). Added the applied insurance domain row to `docs/architecture/ontology-architecture.md` §3. Replaced the "Still open" paragraph in `docs/architecture/ontology-versioning-policy.md` with the ADR-A98 decision 6 answer.
- **Not run:** `mise run check:ontology-catalog`, `mise run check:ontology-versioning` (no runtime on this machine). I did confirm with a plain-text search that `ontology/nsd`, `neuro-semantic/insurance/contract` and `structure-vocab` no longer appear anywhere under `ontology/` or `tools/` (AIR11-03), which is the one check in this pack's command I could approximate without `mise`.
- **Check first:** `mise run build:ontology-catalog` needs to run before `check:ontology-catalog`, since the root catalog and any per-directory stub still name the removed `spec/structure/` and `vocab/` entries until regenerated (lanes §8: catalog regeneration is R-only). `tools/ontology_catalog.py`'s now-unused `_UNPARSEABLE` constant was left in place — the plan said nothing else in that file changes, and no other `KNOWN_DEFECTS` entry uses it, so it's dead but harmless; remove it separately if that bothers `check:ontology-catalog`'s own tests.
- **Deviations from the plan:** none. Every file listed in the plan's Remove/Edit tables was touched and nothing else was.

## Results

Run on machine R, 2026-09-26, on `air/1.1-layout` before its rebase onto `main`:

| Check | Result |
|---|---|
| `mise run build:ontology-catalog` | no catalog changed: the legacy files had no root catalog entries |
| `mise run check:ontology-catalog` | 57 tool tests passed, catalog consistent, known defects 3 → 2 (AIR11-01) |
| `mise run check:ontology-versioning` | 28 in-scope documents (29 before), no unbumped changes, every version listed (AIR11-02) |
| search for `ontology/nsd`, `neuro-semantic/insurance/contract`, `structure-vocab` in `ontology/` and `tools/` | no match (AIR11-03) |
| both READMEs against ADR-A98 | agree, after one fix below (AIR11-04) |

Fixes made on R:

1. `ontology/applied/README.md` said `spec/` and `vocab/` carry a `.version` file. They are versioned
   by `owl:versionIRI`, and only `shapes/` and `projection/` carry `.version`. Corrected.
2. `tools/ontology_catalog.py`: the `_UNPARSEABLE` constant, unused once its only entry went, is
   removed. Its tests pass (12).

After the rebase onto `main` (AIR-3.1 and the AIR-1.2 and AIR-3.2 briefs), clean, no conflicts:

| Check | Result |
|---|---|
| `mise run build:ontology-catalog` | no catalog changed |
| `mise run check:ontology-catalog` | 59 tool tests passed (57, plus AIR-3.1's two examples), catalog consistent, 2 known defects |
| `mise run check:ontology-versioning` | exit 0, 28 in-scope documents, no unbumped changes, every version listed |
| AIR11-03 search | no match |

Gate, run on R at the human's request, 2026-09-26:

1. Pack reviewed: AIR11-01 to 04 pin the invariant. The negative case (AIR11-03) is the one that
   matters, since a stale reference would keep the dropped namespaces alive.
2. The command passes (above).
3. Artefacts inspected: both READMEs agree with ADR-A98. The release tags the domain README cites
   (`insurance-contract-v0.2.0`, `applied-insurance-shapes-v0.1.0`) exist.
4. Adversarial probe: putting the removed `KNOWN_DEFECTS` entry back makes
   `python tools/ontology_catalog.py check` exit 1 ("listed in KNOWN_DEFECTS … but no longer
   defective"). Restored, it exits 0.
5. Sign-off in `LOG.md` is the human's.
