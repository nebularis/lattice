<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: Applied Insurance Reference — Phase 2, Reference Peril Vocabulary

**Unit ID:** `applied-insurance-reference-phase-2`
**Epic:** [applied-insurance-reference](applied-insurance-reference.md)
**Status:** Rolling-wave outline. Detailed at the Phase 1 gate.
**Sketch:** [peril-vocabulary.md](../sketches/peril-vocabulary.md)

## Scope

`ontology/applied/insurance/peril/` (epic D9) as the sketch's §4 lays out: `prl:` properties,
the cause scheme, characteristic and companion schemes, collections, intensity measures and
pools, with the §10 well-formedness shapes. Market editions are out of scope except one small
example edition used by the binding tests.

## Slices

| Slice | Content | Sketch | Notes |
|---|---|---|---|
| AIR-2.1 | `prl:` spec: kind and part sub-properties of `skos:broader` aligned to `iso-thes:`, `prl:canTrigger` (⊑ `skos:semanticRelation`), `prl:overlaps`, characteristic properties, Quantification and exposure links. Shapes of §10. `vocab/peril-vocab.ttl` created with its regions (lanes §4) | §6, §10 | unblocks Phase 4 |
| AIR-2.2 | characteristic schemes (mechanism, agency, onset, definition basis, accumulation class) and companion schemes (consequence, harm subject), bound to their `insurance/common/` contracts | §3, §6.3 | precedes the cause families, whose concepts must carry the mandatory characteristics |
| AIR-2.3 | cause scheme, families N, T and E | §5.1 to §5.3 | reference codes, one primary parent per concept |
| AIR-2.4 | cause scheme, families H, P, C, F and L, and every link between the two family groups | §5.4 to §5.8 | parallel with 2.3, merges after it |
| AIR-2.5 | collections: bundles, standard sets, model groupings. The open-perils condition example | §7 | milestone M1 |
| AIR-2.6 | intensity measure scheme, value spaces, defining thresholds, customary event windows, all in `peril-intensity.ttl` | §6.4 | Quantification only, no substrate change |
| AIR-2.7 | pools scheme and the example market edition bound by a scoped `voc:SchemeBinding` | §9.1, §9.4 | precedence tests: scoped binding wins, reference is the fallback |

Order, lanes and branches: [lanes and merge order](applied-insurance-reference-lanes.md). 2.3 and 2.4 run in parallel, as do 2.6 and 2.7.

Each slice's pack includes an SKOS integrity case (no `skos:related` and no `prl:canTrigger`
within one `broaderTransitive` chain) and a reasoner-free parse and shapes run through
`check:ontology-catalog`.

## Documentation deltas

`ontology/applied/README.md` (module row), the module's own README (generated tables of §5),
`docs/architecture/ontology-architecture.md` §3 status row.

## Exit gate

M1 demonstrated. PV-O1 and PV-O2 closed in the module README.
