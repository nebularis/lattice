<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: VM-0, the sketch, the plan and the record

**Unit:** [vyvid-migration](../plans/vyvid-migration.md)
**Status record:** [vyvid-migration](../status/vyvid-migration.md)

## Invariant

The unit's three documents exist, say where the work stands in the shape the lifecycle requires, and can be followed: their relative links resolve, the writing rules hold in each, and INDEX.md's region agrees with the board ([ADR-A152](../../architecture/decisions/ADR-A152-vyvid-adoption.md), STD-305). VM-0 delivers documents and no code, so its checks read those documents.

## Tests

| ID | Given / When / Then | Level | Invariant | Pass | Kind |
|---|---|---|---|---|---|
| VM0-1 | the sketch, the plan and the status record / listed / each exists | L0 | the documents | present | positive |
| VM0-2 | the three documents / every relative link followed / each target exists | L1 | they can be followed | no broken link | negative |
| VM0-3 | every line of the three documents / `writing_rules.check` / no finding | L1 | the writing rules | 0 findings | negative |
| VM0-4 | the status records / `vyd work build --check` / INDEX.md's region is current | L1 | STD-305 | exit 0 | negative |

VM0-3 runs over whole files, since the commit hook reads only added lines and the sketch has not been touched since it was written.

## One command

```bash
mise run check
```

That covers VM0-4 through its `work` tasks. VM0-1 to VM0-3 have no task of their own and were run by hand, as the results say. Writing a task for them would add a tool for one slice's documents, so we did not.

## Artefacts

`docs/developer/sketches/vyvid-migration.md`, `docs/developer/plans/vyvid-migration.md`, `docs/developer/status/vyvid-migration.md` and the generated region of `docs/developer/INDEX.md`.

## Results

Run 2026-11-06 on `main`. VM0-1 passed, all three exist. VM0-2 passed: 8 relative links in the sketch, 8 in the plan and 12 in the record, none broken. VM0-3 passed: 131, 74 and 106 lines with 0 findings each. VM0-4 passed, exit 0.

## Not covered here

Links to outside sites and to an anchor within a file, which VM0-2 does not follow. This pack was written a day after the slice was built, since the slice had none. No slice's tests were loosened by it.
