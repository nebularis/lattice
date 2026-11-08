<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: Asset class ASC-2, the module

**Unit:** `asset-class` ([plan](../plans/asset-class.md), [status](../status/asset-class.md))
**Machine:** S. **Branch:** `air/asset-classes`. Commits are local, and pushing is the maintainer's.
**Plan and test cases:** [Asset class plan](../plans/asset-class.md) (ASC-2 in detail)
**Decisions:** ASC-Q1 to ASC-Q4, ADR-A98's addendum of 2026-11-08, ADR-A99 decision 1

## Invariant

The reference edition is one tree of SKOS concepts under its top concepts, every concept with one broader concept other than a top, a source note and a definition. A mobility stated on a concept is stated alike on every concept below it, and `cls-voc:AssetClassContract` is bound to the edition.

## Test cases

The table in the plan. Each row's result is recorded under Results at verification.

## One command

Run from the repository root.

```bash
mise exec -- python -m pytest tools/test_asset_class.py
```

## Artefacts to inspect

`ontology/applied/asset-class/` (the README, `spec/asset-class.ttl`, `vocab/asset-class-vocab.ttl`, `shapes/`, `examples/`), `tools/test_asset_class.py`, `ontology/catalog-v001.xml`, ADR-A98's addendum.

## Deliberate non-coverage

Crosswalks (ASC-Q9). SNA 2025 (ASC-Q7). Holding characteristics (ASC-Q8). The SNA and IMF codes cited in the notes are to be checked against the published classification by the maintainer, since the PDFs could not be read on machine S.

## Handoff

Built on machine S, 2026-11-08, on `air/asset-classes`, committed locally and not pushed.

**What was built.**

- **`ontology/applied/asset-class/README.md`** in ADR-A126's layout, the source of `spec/asset-class.ttl` (`asc:mobility`), `vocab/asset-class-vocab.ttl` (the two schemes, 92 asset class concepts and two mobility concepts, written as 6.4 tables with ASC-1's property columns, and the contract binding as a 6.6 block) and `shapes/constraints.ttl` (four SHACL-SPARQL shapes, each targeting its nodes by name or by `asc:mobility`). `shapes/.version` is 0.1.0.
- **Examples.** `well-formed.ttl` and `refusal-mobility.ttl`.
- **Tests.** `tools/test_asset_class.py`, 15 tests, added to `check:ontology-catalog`'s list. `tools/test_lattice_repo_catalogue.py` counts 21 modules.
- **Wiring.** The repository catalogue lists `applied/asset-class` after `applied/classification`, `ontology/applied/README.md` lists the module and its dependency, and `tools/ontology_catalog.py write` added its catalog entries.
- **What it does not cite.** The README cites no unpublished ADR, as `check:published-decisions` requires, so ADR-A98, ADR-A99 and ADR-A100 are described in its text rather than linked.

**What was run.**

- `pytest tools/test_asset_class.py`: 15 passed.
- `mise run check:ontology-catalog`: the suite passed except `test_rc1_t1`, which counted 20 modules and now counts 21, then 133 passed in `tools/test_lattice_repo_catalogue.py`, and `tools/ontology_catalog.py check` is consistent.
- `check:catalogue`, `check:owl-profile`, `check:import-guard`, `check:identifiers`, `check:site-sections`, `check:deny-terms`, `check:published-decisions`: exit 0.
- `check:ontology-releases` and `check:ontology-versioning -- --base-ref origin/main`: exit 1, asking for register rows and tags for `applied-asset-class-v0.1.0`, `applied-asset-class-vocab-v0.1.0` and `applied-asset-class-shapes-v0.1.0`. Rows and tags are added at release, and only a person creates tags. The same run asks for `persistence-store-v0.19.0`, which this slice did not cause.

| Row | Result |
|---|---|
| ASC2-01 | pass, `test_asc2_01` runs the extractor's check |
| ASC2-02 | pass, no result |
| ASC2-03 | pass, 92 concepts each reached once from the two top concepts |
| ASC2-04 to ASC2-07 | pass, each mutation fails the shape the row names, and a cycle that reaches no top concept is refused too |
| ASC2-08 | pass, bound once, and a second binding is refused by Vocabulary's contract shape |
| ASC2-09 | pass, and a concept with no note is refused |
| ASC2-10 | pass, but for the release rows above |

**For the maintainer.** The SNA 2008 and IMF codes in the notes were written from the classification's known structure, since the SNA, ESA and IMF PDFs could not be read on machine S. Each should be checked against Annex 1 of the 2008 SNA before the edition is released. The FIBO licence, believed MIT, is to be confirmed before a FIBO crosswalk.
