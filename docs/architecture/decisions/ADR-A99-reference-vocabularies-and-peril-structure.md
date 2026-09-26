<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A99: Reference vocabularies and peril structure

**Status:** Proposed
**Date:** 2026-09-26 (proposed)
**Related:** ADR-A85 (scoped binding resolution), ADR-A87 (concept exclusion), ADR-A98, ADR-A100
**Unit:** [`applied-insurance-reference`](../../developer/plans/applied-insurance-reference.md) (AIR-0.1)
**Sketches:** [peril-vocabulary.md](../../developer/sketches/peril-vocabulary.md), [peril-structure-whitepaper.md](../../developer/sketches/peril-structure-whitepaper.md)

## Context

What a peril means in a contract is fixed by the contract's drafter (a carrier, an MGA, a broker)
or by its market, which may publish its own list. Consumers bring those lists, most of them flat
or two-level. LATTICE's applied insurance domain still needs a reference peril vocabulary: a
default where nothing else is bound, a target for crosswalks, and the structure that contract
checks need. The whitepaper shows that a SKOS hierarchy alone cannot carry that structure: kinds
and parts differ, triggering is directed, some perils overlap without subsumption, cyber and
flood wordings select by mechanism and agency, bundles are sets, and some perils are defined by
thresholds.

Vocabulary resolves scoped bindings by one rule (ADR-A85): among applicable bindings, one whose
scopes are a strict superset of another's wins, and any remaining tie is a governance conflict.
Bindings at agreement, organisation and market level therefore need a declared scope pattern,
or they tie.

## Decision

1. **A reference edition is the unscoped fallback.** LATTICE publishes reference editions,
   marked as such by `skos:editorialNote` on each scheme, and binds each as `voc:boundScheme` on
   its contract in `insurance/common/`. A reference edition is never presented as a market
   standard. Any other edition, flat or structured, may be bound instead, and need not extend the
   reference.
2. **Scopes nest.** Bindings above the fallback name nested scopes, so that ADR-A85's rule orders
   them without further logic:

   | Binding | Names the scopes |
   |---|---|
   | market (a market-published edition, for example) | market, and a legal regime where the edition is regime-specific |
   | drafting organisation | the market scopes, and the organisation |
   | agreement | the organisation binding's scopes, and the agreement |

   A binding outside this pattern that ties with another is reported as a conflict, as Vocabulary
   already specifies.
3. **The peril vocabulary names causes only.** Consequences, harm subjects, lines of business and
   liability direction (ADR-A102) are other schemes.
4. **Structure beyond SKOS is expressed as sub-properties and separate schemes,** so a consumer
   reading only SKOS sees ordinary broader, related and semantic relations:

   | Structure | Expression |
   |---|---|
   | kind and part | `prl:broaderGeneric`, `prl:broaderPartitive` ⊑ `skos:broader`, aligned to the thesaurus standard's `iso-thes:broaderGeneric` and `iso-thes:broaderPartitive`. `skos:broader` is materialised |
   | triggering | `prl:canTrigger` ⊑ `skos:semanticRelation`, irreflexive, neither symmetric nor transitive. SKOS has no directed associative relation, and `skos:related` is symmetric |
   | overlap | `prl:overlaps` ⊑ `skos:related`, declared symmetric and irreflexive itself |
   | integrity | neither `prl:canTrigger` nor `prl:overlaps` links two concepts in one `skos:broaderTransitive` chain, checked by shape |
   | characteristics | one scheme per axis (mechanism, agency, onset, definition basis, accumulation class), linked from cause concepts for typical values and from occurrences for facts. The name is "characteristic". "Facet" is not used |
   | collections | `skos:Collection` sub-classes for bundles, standard sets and model groupings, expanded at bind time |
   | thresholds and windows | links to Quantification: intensity measure, defining threshold as a `qnt:RangeSet`, customary event window |

5. **Crosswalks from other lists are reviewed MORK artefacts** under ADR-A100, never edits to the
   reference.

## Consequences

- No substrate change. Vocabulary's scoped binding and precedence are used as they stand.
- A drafter's two-level list and the reference coexist under one contract. Checks against the
  drafter's list run at the structure it has (ADR-A100).
- Every concept states its link kind and mandatory characteristics, which is an authoring cost
  the shapes enforce.
- Matching over kind links only, and concept lifecycle across editions, need upstream changes
  (substrate track S1, S2). Neither blocks a first release.
- `insurance/peril/` is built in Phase 2 of the epic. Its layout is in the peril vocabulary
  sketch §4, with paths per ADR-A98.
