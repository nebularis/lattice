<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A92: Foundation derived-artefact contract and PROV-O alignment

**Status:** Proposed
**Date:** 2026-09-25
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
3. **Executable** imports Foundation and adds `exe:ExecutablePlan ⊑
   fnd:DerivedArtefact`, `exe:GeneratedArtefact ⊑ fnd:DerivedArtefact`, and
   `exe:derivedFromEligibilityNode`, `exe:derivedFromQuantificationNode` and
   `exe:compiledFromMapping ⊑ prov:wasDerivedFrom`.
4. No existing term is renamed or removed.

## Consequences

- One PROV-O query spans applied-ontology records, Surface outputs and
  compiled plans.
- Foundation, Surface and Executable each take a MINOR bump. Foundation's
  bump cascades to every layer under ADR-A86, so other pending Foundation
  additions should ride in the same change. The step-list lift proposed in
  ADR-A91 is one candidate.
- Surface profile identity can proceed, as a Surface change, once this is
  accepted.
- The named-graph-per-batch model of ADR-A65 is compatible and unaffected.
