<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: OD-REL, release 0.18.0

**Unit:** [`improved-ontology-documentation`](../status/improved-ontology-documentation.md), slice OD-REL
([plan](../plans/improved-ontology-documentation.md#od-rel-the-first-release)).
**Implements:** the first release on [ADR-A129](../../architecture/decisions/ADR-A129-one-release-for-the-substrate.md)'s
model (OD-D43, OD-D55 to OD-D59, OD-D63). **Built autonomously**, 2026-10-19 (OD-D62). The tag is the
maintainer's.

## Invariant

Every document of the substrate and standalone modules carries 0.18.0, every import of one names 0.18.0, none of
their shape or projection directories carries a `.version`, and the register lists the release once, as
`ontologies-v0.18.0`. The applied modules pin 0.18.0 and carry new versions of their own. Every check passes.

## What changed

- **Eligibility's laws L1 to L8** state their register, `elg:StaticConstraint`, written whole in 6.6 as L9 to L17
  are. The migration check against the commit before shows exactly the eight `elg:lawRegister` triples.
- **`mise run release:prepare -- 0.18.0`** rewrote 43 files: every member document, the literate READMEs' blocks
  and header tables, the applied modules' imports, the examples, and Surface's `SURFACE_ONTOLOGY` constant. It
  removed 15 `.version` files, and regenerated the XML catalog and the register. Only version IRIs changed in the
  Turtle and READMEs, checked line by line.
- **The applied modules**, re-pinned, take new versions under their own rules (ADR-A86): capacity execution
  0.16.0, classification and classification-vocab 0.3.0, insurance common and common-vocab 0.7.0, exposure and
  exposure-vocab 0.2.0, peril, peril-vocab and peril-intensity 0.6.0, each a MINOR. Ten register rows.
- **Release notes.** Each member README with a release-notes section has a 0.18.0 entry, every change classed by
  its effect on data. Eligibility's is the long one: the migration (no effect), the composition operation (changes
  meaning), the mechanism rules (may invalidate), `DimensionConsistent` and `E6` removed (changes meaning) and the
  laws' register (no effect).
- **Tests** that located a current version moved to the release. Seventeen test modules now read the release number from the catalogue, through a `RELEASE` constant, and tests that compared a member's `.version` assert it is gone. The applied modules' IRIs stay written out, since they keep their own versions. A Sonnet sub-agent made these changes, which were reviewed here.

## Decisions taken alone, for the maintainer

1. **The notes cite the versioning policy, not ADR-A129**, since ADR-A129 is Proposed and a migrated README cites
   only published decisions. Once it is accepted and published, the notes can name it.
2. **No migration ships.** OD-D55 owes a migration for a "changes meaning" change once an adopter holds production
   data. Eligibility's note says how a graph migrates, and the rewrite ELC used is not packaged.
3. **MORK, SPC, Surface, Persistence and Party have no release-notes section**, so they have no 0.18.0 entry. MORK
   changed: `Executable.ttl` imports Eligibility and names `exe:usesCompositionOperation`. Their sections come with
   their migrations to the layout.
4. **Applied modules bump MINOR** for a re-pin, as ADR-A86's cascade rule says, in two rounds, since peril-intensity
   and the vocab documents import the documents bumped in the first.

## Commands

From the repository root. A pass is each exiting 0.

```bash
mise exec -- python tools/ontology_version_check.py --base-ref main
```

```bash
mise exec -- python tools/ontology_releases.py check
```

```bash
mise run check:full-sweep
```

## Results

2026-10-20, from this worktree:

- **`mise run check:full-sweep`:** all 15 checks pass, the ontology versions check against `main` among them. Among
  the others, `check:ontology-catalog` 1129 passed, `check:persistence` 2549 passed, `check:mork-compilers` 126
  passed and `check:reference-eligibility` 60 passed.
- **The release register check:** every current version listed.
- **`check:catalogue`, `check:site-sections` and `check:import-guard`:** pass. The sweep now runs the first two
  as well.
- **Every literate layer's `--check`:** consistent.

## For the maintainer

- Accept ADR-A129, then create the tag on the commit that adds the release's row: `git tag ontologies-v0.18.0`,
  and the applied modules' tags the register lists.

## Decisions answered

2026-10-20, by the maintainer: approved, with every decision taken alone.

2026-10-20, later: ADR-A129 published, and the 0.18.0 release notes now cite it in place of the versioning policy
(decision 1 resolved).
