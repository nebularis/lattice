<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: Asset class, a reference vocabulary of what assets are

**Unit ID:** `asset-class`
**Prefix:** ASC
**Status:** proposed 2026-11-08. ASC-Q1 to ASC-Q6 answered by the maintainer 2026-11-08, with leave to build ASC-1 to ASC-3 autonomously on `air/asset-classes` and commit locally. ADR-A98's and ADR-A126's addenda of 2026-11-08 are proposed and wait on the maintainer's approval.
**ADRs:** [ADR-A98](../../architecture/decisions/ADR-A98-applied-layout-and-insurance-modules.md) addendum of 2026-11-08, [ADR-A126](../../architecture/decisions/ADR-A126-literate-specification-layout-and-grammar.md) addendum of 2026-11-08, both proposed. [ADR-A99](../../architecture/decisions/ADR-A99-reference-vocabularies-and-peril-structure.md) and [ADR-A100](../../architecture/decisions/ADR-A100-hierarchical-match-over-flat-schemes.md) unchanged
**Sketch:** [a reference asset class vocabulary](../sketches/asset-class-vocabulary.md)

## Scope

A cross-domain applied module, `ontology/applied/asset-class/` with prefixes `asc:` and `asc-voc:`, that publishes:

- **the reference asset class edition**, one SKOS scheme with non-financial and financial branches after the System of National Accounts 2008, and the binding of `cls-voc:AssetClassContract` to it
- **mobility**, `asc:mobility`, a characteristic of an asset class concept with the values `Stationary` and `Mobile`, stated only where it holds for the whole class
- **the shapes** that keep the scheme a tree and keep mobility consistent down it

with the literate grammar it needs, and the exposure module's adoption of it.

Out of scope:

- **Crosswalks** to CBAA, OED, CIC, AIFMD or CFI (ASC-Q9). Each is a reviewed artefact of its own, sliced when a consumer needs it.
- **SNA 2025** (ASC-Q7).
- **Maturity, listing and fund type** as characteristics (ASC-Q8).
- **Lending's and investment's use** of the edition, which those domains take when they are built.

## Principles

- **One dimension per scheme.** Asset class answers what kind of thing an asset is, and nothing else. Use, construction, the value exposed, the stake held and a holding's terms each have their own place (sketch §3).
- **The edition is a fallback.** A deployment binds its own scheme and that wins (ADR-A99 decision 1). The edition says so in an editorial note.
- **Every concept cites its source,** in a `skos:note`, and every departure from SNA is stated beside the concept it affects.
- **No domain vocabulary.** The module's text and examples name no insurance, lending or investment term, so promotion stays possible (ADR-A98).

## Slices

| Slice | Deliverable | Depends on |
|---|---|---|
| ASC-1 | the literate grammar's property columns in individuals tables, the conventions document, and their tests | |
| ASC-2 | the module: README in ADR-A126's layout, spec, vocab, shapes, examples, tests and catalogue entries | ASC-1 |
| ASC-3 | exposure adopts it: examples use the edition's concepts, and the asset shape reads mobility | ASC-2 |

## Slices in detail

### ASC-1 in detail: property columns in individuals tables

`tools/literate_grammar.py`'s 6.4 tables accept a column whose header is one CURIE in backticks, with a declared prefix, as stating that property. Cells are comma-separated lists of CURIEs and Turtle literals. `docs/architecture/literate-specifications.md` describes it, and ADR-A126's addendum records it.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| ASC1-01 | an individuals table with a `skos:inScheme` column / extracted / one statement per row, its object expanded from the CURIE | L1 | + |
| ASC1-02 | a cell listing two CURIEs / extracted / two statements | L1 | + |
| ASC1-03 | cells holding a language-tagged literal and a typed literal / extracted / both literals as written | L1 | + |
| ASC1-04 | an empty cell / extracted / nothing stated for that row | L1 | + |
| ASC1-05 | a CURIE header whose prefix section 2 does not declare / extracted / an error naming the header | L1 | - |
| ASC1-06 | a cell entry that is neither a CURIE nor a Turtle literal / extracted / an error naming the entry | L1 | - |
| ASC1-07 | a CURIE column for a property an annotation column already states / extracted / an error | L1 | - |
| ASC1-08 | every literate README / `literate_extract.py --check` / no generated file changes | L2 | + |

### ASC-2 in detail: the module

`ontology/applied/asset-class/` with `README.md`, `spec/asset-class.ttl`, `vocab/asset-class-vocab.ttl`, `shapes/` with its own `.version`, `examples/`, `tools/test_asset_class.py`, its repository catalogue entry and its OWL catalog entries.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| ASC2-01 | the README / `literate_extract.py --check` / the spec, vocab and shapes, the axiom index and the class diagram are current | L2 | + |
| ASC2-02 | the vocab and `examples/well-formed.ttl` / validated with Vocabulary's shapes and the module's / conform | L3 | + |
| ASC2-03 | the edition / walked from its top concepts through `skos:narrower` / every concept is reached once, and every concept other than a top has exactly one broader concept in the scheme | L3 | + |
| ASC2-04 | a concept with two broader concepts / validated / refused | L3 | - |
| ASC2-05 | a narrower concept with no mobility, or another one, below a concept that states a mobility / validated / refused | L3 | - |
| ASC2-06 | a mobility value outside the mobility scheme / validated / refused | L3 | - |
| ASC2-07 | a top concept its scheme does not list as a top concept / validated / refused | L3 | - |
| ASC2-08 | `cls-voc:AssetClassContract` / validated with Vocabulary's contract shape / bound to the edition, once | L3 | + |
| ASC2-09 | every concept / read / has a preferred label, a definition and a `skos:note` citing its source in `@en` | L3 | + |
| ASC2-10 | the documents / `check:owl-profile`, `check:import-guard`, `check:ontology-catalog`, `check:catalogue` / exit 0 | L2 | + |

### ASC-3 in detail: exposure adopts the edition

The exposure examples name the edition's concepts as asset classes in place of the value types they borrowed, and `aeo:AssetShape` gains two rules that read `asc:mobility` on an asset's class.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| ASC3-01 | the exposure examples with the edition / validated with exposure's shapes / conform, and each asset's class is in `asc-voc:AssetClassScheme` | L3 | + |
| ASC3-02 | an asset of class `asc-voc:Vessel` with `aeo:locatedAt` / validated / refused | L3 | - |
| ASC3-03 | an asset of class `asc-voc:NonResidentialBuilding` with `aeo:presence` / validated / refused | L3 | - |
| ASC3-04 | an asset whose class states no mobility, with either / validated / accepted | L3 | + |
| ASC3-05 | `tools/test_exposure_ontology.py` / run / passes | L2 | + |

## Releases

The module's first release is 0.1.0, imports pinned to release 0.21.0 and classification 0.6.0. Exposure's change is a release note under Unreleased that may invalidate, since a mobile asset with a location, or a stationary one with presences, now fails where the class states a mobility. Version bumps happen at merge.

## Done when

ASC-1 to ASC-3 are built and verified, the two addenda are accepted, and `mise run check` passes.

## Effects on other units

- **Applied insurance reference.** Exposure's sketch planned an insurance asset class scheme crosswalked to CBAA. That scheme is this edition, and the crosswalk is ASC-Q9.
- **Lending and investment,** when built, bind their contracts' asset classes to this edition or to their own.

## Questions

ASC-Q1 to ASC-Q9 are in the [sketch](../sketches/asset-class-vocabulary.md) §8. ASC-Q1 to ASC-Q6 are answered, and ASC-Q7 to ASC-Q9 are open.
