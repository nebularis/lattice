<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A92: Foundation derived-artefact contract and PROV-O alignment

**Status:** Accepted
**Date:** 2026-09-25 (proposed), 2026-09-25 (accepted, item 3 rewritten on acceptance)
**Related:** ADR-A12 (identity and derivation-authority model), ADR-A13
(dataset, graph-role and provenance model), ADR-A22 (MORK governance and
Foundation alignment), ADR-A26 (provenance chain completeness), ADR-A65
(provenance model, Proposed), ADR-A91
**Unit:** [`applied-ontology-readiness`](../../developer/plans/applied-ontology-readiness.md)

## Context

Foundation imports PROV-O and aligns its own evidence terms with it
(`fnd:Evidence ⊑ prov:Entity`, an attribution property under
`prov:wasAttributedTo`). The derived records that LATTICE's compilers write
are not aligned:

- Surface declares `srf:DerivedArtefact`, `srf:GeneratedSurface`,
  `srf:ReadSetEntry` and `srf:LawDischarge`, with no PROV-O superclass.
- Executable declares `exe:ExecutablePlan`, `exe:GeneratedArtefact`,
  `exe:derivedFromEligibilityNode`, `exe:derivedFromQuantificationNode` and
  `exe:compiledFromMapping`, and imports MORK only.
- ADR-A12 anticipates a Foundation-level derived-product contract. The Surface
  outstanding-items record lists its location as a decision needed (§1.3,
  §3.1), and Surface profile identity is blocked on it (§3.3).

An applied ontology that records its own provenance in PROV-O cannot ask one
question, such as "what was this decision derived from", across its own
records and the artefacts LATTICE generated for it.

## Decision

1. **Foundation** adds `fnd:DerivedArtefact ⊑ prov:Entity` and
   `fnd:DerivationRun ⊑ prov:Activity`. ADR-A12's derivation-product kinds
   (inferred, validated, materialised, projected, indexed, generated,
   compiled, decision or execution record) become a mechanism enumeration in
   `vocab/foundation-vocab.ttl`. Links use PROV-O properties directly
   (`prov:wasGeneratedBy`, `prov:used`, `prov:wasDerivedFrom`). Foundation
   declares no parallel properties.
2. **Surface** keeps its terms and adds `srf:DerivedArtefact ⊑
   fnd:DerivedArtefact`. Where `srf:ReadSetEntry` fits PROV-O's qualified
   usage pattern it is aligned, and the implementing slice records any part
   that does not fit.
3. **Executable** aligns directly to PROV-O and does not import Foundation.
   It imports PROV-O and adds `exe:ExecutablePlan ⊑ prov:Entity`,
   `exe:GeneratedArtefact ⊑ prov:Entity`, and `exe:derivedFromEligibilityNode`,
   `exe:derivedFromQuantificationNode`, `exe:derivedFromVocabularyNode` and
   `exe:compiledFromMapping ⊑ prov:wasDerivedFrom`. Direct alignment was
   accepted on the condition that it imposes no functional restriction on
   implementors. PROV-O declares no functional or inverse-functional property,
   so it imposes none.
4. No existing term is renamed or removed.

## Consequences

- One PROV-O query spans applied-ontology records, Surface outputs and
  compiled plans.
- Foundation, Surface and Executable each take a MINOR bump. Foundation's
  bump cascades to every layer under ADR-A86. ADR-A91 did not lift its
  step-list pattern to Foundation, so nothing else rides in this bump.
- Every node an executable plan derives from (a condition, a range, a concept,
  a mapping) is inferred to be a `prov:Entity`. PROV-O declares `prov:Entity`
  disjoint with `prov:Activity`, so an implementor must not also type such a
  node as an activity. This is the one restriction the alignment adds.
- Executable already reached Foundation, and PROV-O through it, via MORK's own
  import of Foundation. The direct PROV-O import states the dependency Executable
  relies on without depending on MORK's.
- Surface profile identity can proceed, as a Surface change, once this is
  accepted.
- The named-graph-per-batch model of ADR-A65 is compatible and unaffected.

## Implementation notes (2026-09-25, `applied-ontology-readiness` AOR-12, AOR-13)

- `srf:ReadSetEntry` is not aligned. PROV-O's `prov:Usage` qualifies an
  activity's use of an entity, while a read-set entry hangs off the derived
  artefact itself, so the two patterns do not match.
- `fnd:derivationKind` is not functional. ADR-A12 describes one kind per
  product, but nothing here needs a reasoner to enforce it.
- The kinds are `fnd:Inferred`, `fnd:Validated`, `fnd:Materialised`,
  `fnd:Projected`, `fnd:Indexed`, `fnd:Generated`, `fnd:Compiled` and
  `fnd:DecisionRecord`.
