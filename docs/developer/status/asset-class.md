<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Asset class — Status

**Unit ID:** `asset-class`
**Status:** built 2026-11-08. ASC-1 to ASC-3 built on machine S and committed locally.
**Last updated:** 2026-11-08
**Plan:** [asset-class.md](../plans/asset-class.md)
**Validation Packs:** [ASC-1](../validation/ASC-1.md), [ASC-2](../validation/ASC-2.md), [ASC-3](../validation/ASC-3.md)

---

## Is this unit complete?

**No.** ASC-1 to ASC-3 are built on machine S on `air/asset-classes` and committed locally, with nothing pushed, and wait for the maintainer's verification and the acceptance of the two addenda. The release adds the register rows and tags for the module's 0.1.0.

## Current state

**2026-11-08.** The maintainer asked for a SKOS vocabulary of asset classes for exposure's `aeo:assetClass`, asked whether it is insurance specific, and asked that it draw on other standards. The [sketch](../sketches/asset-class-vocabulary.md) set out six decisions and the maintainer answered all six the same day: a cross-domain module beside `classification/` (ASC-Q1), one scheme with physical, intangible and financial branches after SNA 2008 (ASC-Q2), a mobility characteristic stated only where a check reads it (ASC-Q3), the dimensions kept apart and right the first time, since Surface can combine them later for runtime efficiency (ASC-Q4), the literate tooling extended for SKOS (ASC-Q5), and this lifecycle, with the addenda waiting on the maintainer's approval (ASC-Q6). The unit's prefix is ASC, since `AC-01` to `AC-11` already name the word authoring plan's contract tests.

**Built the same day.** ASC-1 lets a 6.4 table state any property in a column headed by its CURIE, which the edition uses for scheme membership, hierarchy, notes, identity, governance state and mobility. ASC-2 is the module, `ontology/applied/asset-class/`, with 92 asset classes in one tree under two top concepts, every one citing the SNA 2008 category it follows or groups, and four shapes. ASC-3 has exposure import the edition and refuse an asset whose location contradicts its class's mobility. Each pack's handoff lists what was run.

**To check before release.** The SNA and IMF codes in the notes were written without the source PDFs, which could not be read on machine S, and should be checked against Annex 1 of the 2008 SNA. The README of the module cites no unpublished ADR, so ADR-A98's addendum is described there rather than linked.

## What is open

| | What | Owner |
|---|---|---|
| the addenda | ADR-A98's and ADR-A126's addenda of 2026-11-08 are proposed | the maintainer |
| the release | register rows and tags for `applied-asset-class-v0.1.0`, `applied-asset-class-vocab-v0.1.0` and `applied-asset-class-shapes-v0.1.0`, and exposure's next number for its Unreleased note | the maintainer, at merge |
| the SNA codes | checked against Annex 1 of the 2008 SNA | the maintainer |
| ASC-Q7 to ASC-Q9 | SNA 2025, holding characteristics, published crosswalks | the maintainer, when a consumer needs them |

## Board

| Slice | Deliverable | State | Blocked on |
|---|---|---|---|
| ASC-1 | the literate grammar's property columns in individuals tables, the conventions document and their tests | built 2026-11-08, building 2026-11-08, briefed 2026-11-08 |  |
| ASC-2 | the module `applied/asset-class/`, its README, spec, vocab, shapes, examples, tests and catalogue entries | built 2026-11-08, building 2026-11-08, briefed 2026-11-08 |  |
| ASC-3 | exposure adopts the edition, its examples and the asset shape's mobility rules | built 2026-11-08, building 2026-11-08, briefed 2026-11-08 |  |
