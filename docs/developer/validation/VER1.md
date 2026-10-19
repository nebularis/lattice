<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: VER1, one release for the substrate

**Unit:** [`improved-ontology-documentation`](../status/improved-ontology-documentation.md), slice VER1
([plan](../plans/improved-ontology-documentation.md#ver1-one-release-for-the-substrate)).
**Implements:** OD-D55 to OD-D59 and OD-D63, as
[ADR-A129](../../architecture/decisions/ADR-A129-one-release-for-the-substrate.md), Proposed for the maintainer
to accept. **Built autonomously**, 2026-10-19 (OD-D62).

## Invariant

The modules of the kinds the catalogue's `[conventions.release]` names are released together. Every member
document's version IRI ends with the release number, every reference under `ontology/` to a member's version IRI
names it, member artefact directories carry no `.version`, and a change to a member since the base ref needs a
new number. Applied modules and examples keep ADR-A86's per-document rules. `release:prepare` moves the whole
set in one substitution.

## What changed

- `repository-catalogue.md`. `[conventions.release]`, version 0.18.0, kinds substrate and standalone, with prose.
- `tools/lattice_repo_catalogue.py`. The release block is validated, and `release_version` and
  `release_members()` read it.
- `tools/ontology_version_check.py`. `check_release()` and `check_release_bumped()`, reported as `RELEASE` and
  `UNBUMPED`. The per-document and `.version` rules skip members.
- `tools/ontology_releases.py`. One register row per release, `ontologies-vX.Y.Z`, whose marker is the
  catalogue's number, listing every member file. Non-members keep a row per document.
- `tools/ontology_release.py` and `mise run release:prepare -- <X.Y.Z>`. Rewrites member references in Turtle and
  READMEs under `ontology/` and in tool package sources, sets the number, removes member `.version` files, then
  regenerates the XML catalogs and the register.
- `ontology/mork/spec/Executable.ttl` imports Eligibility, whose terms it uses (OD-D63).
- ADR-A129, Proposed. The versioning policy gains a section on the release, and the conventions document says
  each release-note change ends with its data class.

## Decisions taken alone, for the maintainer

1. **The tag is `ontologies-vX.Y.Z`**, matching the bundles sketch's leaning that the ontology release keeps its
   own number beside any product release.
2. **The release's members are named by kind**, not listed, so a new standalone module joins without an edit.
3. **`release:prepare` leaves tests alone.** Tests assert history as well as the present, so a release updates
   the ones that name a current version by hand, as before.
4. **The data class is written in brackets** at the end of each change in a release note, rather than as a
   table column, since release notes are lists today.
5. **The rehearsal is OD-REL itself.** The tests run the task over a fixture tree. OD-REL runs it over the
   repository, with every check after it, as the next commit.
6. **The catalogue says 0.18.0 from this commit**, so until OD-REL the check reports every member as off the
   release, which OD-D43 already allows on this branch.

## Test cases

In `tools/test_ontology_release.py`.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| VER1-T1 | a release block with a bad number, an unknown kind, a missing key / load / each refused | L1 | − |
| VER1-T2 | a member with a `.version`, then the catalogue moved on / check_release / the `.version`, the member's version IRI, an applied importer and a README flagged, the applied module's own version not | L3 | − |
| VER1-T3 | a member's shapes changed / at the same and at a new number, and a non-member changed / flagged, then passing, and the non-member held to its own rule | L3 | +/− |
| VER1-T4 | the fixture / prepare 0.2.0 / three files rewritten, the number set, the member's `.version` gone, the applied module's kept, every check passing, a bad number refused | L3 | +/− |
| VER1-T5 | the prepared fixture / the register written / one `ontologies` row with labelled files, and the applied module's own row | L3 | + |

## Commands

```bash
mise exec -- python -m pytest tools/test_ontology_release.py tools/test_ontology_version_check.py tools/test_ontology_releases.py tools/test_lattice_repo_catalogue.py -q
```

## Results

2026-10-19: 130 passed. `check:import-guard`, the XML catalog check and `check:mork-compilers` (126 passed) pass
with `Executable.ttl`'s new import. `check:published-decisions` passes.
