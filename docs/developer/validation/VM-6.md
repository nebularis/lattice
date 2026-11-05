<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: VM-6, the copies removed

**Unit:** [vyvid-migration](../plans/vyvid-migration.md)
**Status record:** [vyvid-migration](../status/vyvid-migration.md)

## Invariant

The triple-store record and the thirty query-writing standards live in the Вивід domain `triple-stores`, pinned to its tag `v0.1.0`, and LATTICE keeps a page at the record's old path saying what each finding means for LATTICE, keyed to the domain's identifiers, so the published pages that link the path still reach it. Every mention of a moved identifier resolves to the domain by the moves `vyvid.toml` declares, on a clean build, and the copies go only after every branch has been compared ([ADR-A152](../../architecture/decisions/ADR-A152-vyvid-adoption.md) decision 7, plan decision 10). The facet values are Вивід's general scheme, identical to the register row for row before the register goes (plan decisions 14 and 19), and `find` ranks as it did at VM-1, hit@5 and MRR within 0.01.

## Tests

| ID | Given / When / Then | Level | Invariant | Pass | Kind |
|---|---|---|---|---|---|
| `vyd move check --ref <ref>`, 44 refs | every local and remote branch / the moved sources at commit 4b94c0f0 compared with each / nothing differs, or the one known drift | L4 | the copies are compared before they go | the table below | positive |
| `vyd check identifiers` on a clean store, before and after | the store removed and rebuilt / the check / 0 unresolved, the moved mentions resolving to the domain | L4 | every mention resolves | the summary lines below | positive |
| the anchors | the slugs other pages link into the record / the new page's headings / every one a heading | L1 | the published pages still reach the page | 27 of 29, two retargeted | positive |
| `test_the_build_reports_nothing_but_the_known_notes` | the page and the registers / `vyd build` / no new note | L4 | the knowledge base consistent | among the 38 of `check:knowledge` | positive |
| the facet comparison | the three tables of the register / the store's facets graph / every value, label, definition, scope note, broader, related and scheme equal | L4 | nothing lost before the register goes | 325 rows compared, 0 differences | positive |
| the bake-off | the 43 scored and 5 held-out questions / `vyd find` on this checkout / hit@5 and MRR within 0.01 of VM-1's | L7 | ranking kept | 0.884 and 0.806 on the 43, 0.800 and 0.567 on the 5, equal to VM-1's | positive |

## What ran, and what it showed

Run on 2026-11-05 and read in full. The domain's tag `v0.1.0` holds the 64 findings and the 30 query standards the moves name, the same identifier set as LATTICE's copy, so the moves need nothing it lacks. `vyd move check --ref` ran on 44 refs, every local branch and every branch of the two remotes that answer, since the `upstream` remote asks for credentials and was not fetched. Thirty-two refs print `nothing differs`. The local `vyvid-migration` prints `TSD TSD-34 changed`, which is VM-5's rename of the skill `lattice-triple-stores` to `lattice-probing` on two lines of LATTICE's copy, nothing of the finding. Eleven refs that predate the record or the standards print `file-absent` lines with exit 0, `persistence-mbt` and `upstream` for all three families and `spikes/pol-map` and `tutorial/guide` for the standards. No other difference exists on any branch.

The identifier check on a store removed and rebuilt passed before the removal, 2111 identifiers mentioned in 860 files and 0 unresolved, and after it, 2095 in 858 files and 0 unresolved, the TSD and the moved STD mentions resolving to the domain, and the build notes that 64 entries of LATTICE moved to the domain and are not indexed here. The page at the old path keeps a heading per finding with the domain's title, so 27 of the 29 slugs other pages link into the record are headings of the page, and the two that pointed at the record's sections 1 and 4.3, in `efficient-queries-and-shapes.md`, now point at those sections of the domain's `findings.md` at the tag. The thirty standards rows are gone from `standards.md`, and nothing outside it mentioned them.

The facet register's three tables and its schemes table, 325 rows, were compared with the store's facets graph on identifier, label, definition, scope note, broader and related values, scheme, group and ratified, and no row differed, so the register and its backup under `notes/` are removed, AGENTS.md, the lifecycle skill's source, the knowledge README and the three links to it say where the values live now, and ADR-A134 takes an addendum narrowing decision 26. The bake-off on this checkout, `vyd find` through the Вивід bench against VM-1's LATTICE figures, gave hit@5 0.884 and MRR 0.806 on the 43 scored questions and 0.800 and 0.567 on the 5 held out, equal to VM-1's, with the top five differing in 4 of 48 questions below the expected entries, as at VM-1. `mise run check:knowledge` 38 passed, `mise run check:agent-guidance` 9 passed, `vyd check skills` 15 composed and no problem, and the ten hook checks over the staged tree all passed. `mise run check` ran after the slice, unfiltered to a file, exit 0 from `mise` in 179 s, and its 3,447 lines were compared line by line with the VM-5 log, differing only in `check:identifiers` at 2095 identifiers in 859 files, the sources check's count of READMEs not yet migrated, 559 against 575, one warning's test name under `-n auto`, and timings.

After the copies went, `vyd move check` with no ref exits 1 and prints every moved entry, 64 TSD changed, 25 TSD-Q removed and 30 STD removed, since it compares the sources at commit 4b94c0f0 with a tree that no longer holds them. That is the end state decision 7 asks for, so the check needs a word for a source whose copy is gone, reported to Вивід's side. The writing rules stay in AGENTS.md (plan decision 19), no copy exists in Вивід's domains today to hold them against, and TD-146 records that the prose and `tools/writing_rules.py` are kept in step by hand.

## One command

```bash
mise run check:knowledge
```

Run from the checkout's root, with `mise run check:identifiers` beside it. A pass is 38 passed and an identifier check with 0 unresolved.

## Artefacts

`docs/architecture/triple-store-discovery.md` as the page at the old path, `docs/developer/standards.md` without STD-026 to STD-054 and STD-279, the two links of `docs/architecture/efficient-queries-and-shapes.md`, the removal of `docs/developer/facets.md` and `docs/developer/notes/facets-register-2026-11-05.md`, AGENTS.md's facets sentence and `.github/copilot-instructions.md`, the lifecycle skill's source and its composed copy, `tools/knowledge/README.md#facets`, the addendum of 2026-11-05 on ADR-A134 with its link, the two sketch links, STD-096's Does not cover cell, and TD-146.

## Not covered here

`vyd move check` after the removal, which reports the end state as differences. The `upstream` remote, which was not fetched. TD-2 in Вивід's register, cleared on its side. A page that names what each finding means for LATTICE from the registers that rest on it finds 51 findings nothing rests on, since the standards that cited most of them are the moved ones, so a reader of those goes to the domain.
