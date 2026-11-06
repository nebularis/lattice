<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: VM-1, bind

**Unit:** [vyvid-migration](../plans/vyvid-migration.md)
**Status record:** [vyvid-migration](../status/vyvid-migration.md)

## Invariant

LATTICE is a project of Вивід, declared by `vyvid.toml` at the root with LATTICE's families, extractor, recipe, moves and work settings, and Вивід answers every question LATTICE's own tooling answers today, from the same registers, with no removal yet ([ADR-A152](../../architecture/decisions/ADR-A152-vyvid-adoption.md) decisions 1 to 4 and 7). The tool is pinned, installed by `bootstrap`, and never written over a copy at the pinned version, and replaced at another version only where the tool's `uv` receipt shows a git install. Every difference between the two sides is written in the status record with its disposition.

## Tests

| ID | Given / When / Then | Level | Invariant | Pass | Kind |
|---|---|---|---|---|---|
| test_vm1_01 | the binding file / parsed / the project is `lattice` and public | L1 | the declaration | assertion | positive |
| test_vm1_02 | every family's `defined` path / expanded under the root / a file exists for each | L1 | the families | assertion | positive |
| test_vm1_03 | the families / compared with LATTICE's row families | L1 | the families | `STD`, `PRI`, `PAT`, `MEC`, `CAP`, `TD`, `PDD`, `BL` all named | positive |
| test_vm1_04 | the exceptions baseline / expanded / it is the one file LATTICE's check reads | L1 | one baseline | assertion | positive |
| test_vm1_05 | `vyd` at the pinned version / `bootstrap:vyvid` decides / nothing runs | L1 | never written over | no command | positive |
| test_vm1_06 | no `uv` / decides / a message naming the fix, no command | L1 | an absent tool never blocks | no command | negative |
| test_vm1_07 | an older `vyd` from a git install, and `uv` / decides / the pinned tag is installed | L1 | the pin | the command ends in `@v0.2.2` | positive |
| test_vm1_08 | the binding trusted / `vyd context` / it names LATTICE | L0 | the contract | exit 0 and `project: lattice` printed, skipped only where the binding is not trusted | positive |
| test_vm1_09 | an editable install at another version / `bootstrap:vyvid` decides / it is left alone and told how to move to the pin | L1 | never written over | no command, the message names the pin | positive |
| test_vm1_10 | a local-directory install at another version / decides / it is left alone and told how to move to the pin | L1 | never written over | no command, the message names the pin | positive |
| test_vm1_11 | a git install at another version / decides / the pinned tag replaces it | L1 | the pin | the command ends in `@v0.2.11`, the message says `replacing 0.2.10` | positive |
| test_vm1_12 | an installed `vyd` and no receipt, as pip or pipx leave it / read and decided / it is left alone | L1 | only a git install is replaced | a note naming the receipt, no command | negative |
| test_vm1_13 | an installed `vyd` and a receipt that does not parse / read and decided / it is left alone | L1 | only a git install is replaced | a note naming the receipt, no command | negative |
| test_vm1_14 | a receipt in a bad encoding / read / unreadable, no exception | L1 | only a git install is replaced | a note naming the receipt | negative |
| test_vm1_15 | no `vyd` and `uv` / decides / the pinned tag is installed with no receipt read | L1 | the pin | the command ends in `@v0.2.11` | positive |

The comparison in the status record is the rest of the validation, run by hand on 2026-11-05 and read in full: the bake-off, the board with every row and commit on both sides, the region checks, the hook check, `vyd move check --ref main`, the facet register row for row, and `vyd check identifiers` against `check:identifiers`.

## One command

```bash
mise run check:vyvid-binding
```

Run from the checkout's root. A pass is sixteen passed, the fifteen tests above and `test_vm3_05`, or fifteen passed and `test_vm1_08` skipped where `vyd` is missing. Eight passed on 2026-11-05 at `v0.2.3`, trusted.

## Artefacts

`vyvid.toml`, `.vyvid/`, `.claude/settings.json`, `.github/hooks/vyvid.json`, `mise.toml`'s `uv` and `VYVID_VERSION` pins and the tasks `bootstrap:vyvid` and `check:vyvid-binding`, `tools/bootstrap_vyvid.py`, `docs/developer/notes/facets-register-2026-11-05.md`, and the comparison table in the status record.

## Not covered here

The composition of the skills and `vyd check skills`, which VM-5 covers. The tasks over `vyd`, which VM-2 and VM-4 cover and test in `tools/test_hooks.py`.
