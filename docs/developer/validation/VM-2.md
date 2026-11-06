<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: VM-2, switch

**Unit:** [vyvid-migration](../plans/vyvid-migration.md)
**Status record:** [vyvid-migration](../status/vyvid-migration.md)

## Invariant

The index tasks and hooks an agent is told to run keep their names and run over Вивід, and a checkout without `vyd`, or with a `vyd` that says it did not run, is told what was skipped and how to mend it and is never blocked ([ADR-A152](../../architecture/decisions/ADR-A152-vyvid-adoption.md) decisions 3 and 4, PRI-79). `graph:ask -- find` answers as it did before the switch.

## Tests

| ID | Given / When / Then | Level | Invariant | Pass | Kind |
|---|---|---|---|---|---|
| test_vm2_01 | no `vyd` on the path / the identifiers hook check / a note naming `mise run bootstrap`, nothing failed | L1 | never blocks | the check returns no failure and prints the note | negative |
| test_vm2_02 | no `vyd` on the path / the post-merge hook / "not rebuilt" with the note, exit 0 | L1 | never blocks | exit 0 and the note printed | negative |
| test_vm2_03 | a `vyd` that exits 2 saying the binding is not trusted / the identifiers hook check / its reason and `vyd trust` in the note, nothing failed | L1 | did not run is a skip | the check returns no failure and prints the reason | negative |
| test_vm2_04 | `vyd` present, a probe project whose document mentions standard 99 of a family whose register defines row 01 alone / the identifiers hook check / the mention named, and nothing once the mention is corrected | L4 | the check still judges | the undefined mention in the failure lines, then none | positive |

The rest of the validation is run by hand on 2026-11-05 and read in full. `mise run graph:ask -- find` on the bake-off's first three questions, Q01 to Q03 with `--activity ontology-design`, returned the same top five as the record of the run before the switch, `PRI-07 ADR-A104 MEC-61 PM-Q3 BL-12`, `PRI-02 MEC-01 PRI-06 STD-284 ADR-A82` and `MEC-03 STD-016 STD-014 PRI-31 MEC-02`. `mise run check:identifiers` passed with PRI-79 and its citations in place, `mise run check:agent-guidance` passed with the Copilot file regenerated, and a second `vyd build` on this checkout took 3.5 s, so the post-merge hook stays cheap.

## One command

```bash
mise run check:hooks
```

Run from the checkout's root. A pass is every test passing, `test_vm2_04` skipped where `vyd` is not installed, and `test_vm2_03` skipped on Windows, where the fake `vyd` is a shell script.

## Results

Re-checked 2026-11-06 on `main` at Вивід `v0.2.14`. `mise run check:hooks` passed 48 tests. With `vyd` off the path, `graph:ask` said what it skipped and exited 0. `mise run graph:ask -- find` on Q01 to Q03 with `--activity ontology-design` returned the same top five as the record of the run before the switch, in the same order, listed under Tests.

## Artefacts

`tools/vyd.py`, the `vyd` check and the post-merge rebuild in `tools/hooks.py`, the tasks `graph:ask`, `build:knowledge`, `check:identifiers` and `vyd` in `mise.toml`, AGENTS.md's "Asking the knowledge index" and `.github/copilot-instructions.md`, PRI-79 in `docs/developer/principles.md`, and the addenda of 2026-11-05 on ADR-A134 and ADR-A151.

## Not covered here

The board tasks and the `work` check over `vyd`, which VM-4 covers. LATTICE's knowledge tests against Вивід's store and the removal of `tools/knowledge/`, which VM-3 covers, so `check:knowledge` and `tools/knowledge/test_identifiers.py` still test LATTICE's own code here. Windows, pending the maintainer's run of Вивід's manual test script on a Windows machine (plan, decision 3).
