<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AOR-12, Foundation derived-artefact contract

**Unit:** [`applied-ontology-readiness`](../status/applied-ontology-readiness.md)
**Decision:** [ADR-A92](../../architecture/decisions/ADR-A92-derived-artefact-contract-and-prov-o-alignment.md) items 1 and 2, Accepted

## Invariant

Foundation offers a derived-artefact contract aligned with PROV-O, and
Surface's derived records are instances of it.

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AOR12-01 | Foundation spec and vocab / parsed / `fnd:DerivedArtefact ⊑ prov:Entity`, `fnd:DerivationRun ⊑ prov:Activity`, `fnd:derivationKind` not functional, exactly the eight kinds | L1 | + |
| AOR12-02 | Surface spec / parsed / `srf:DerivedArtefact ⊑ fnd:DerivedArtefact` | L1 | + |
| AOR12-03 | every importer / version check and catalog / each bumped MINOR, every import resolves | L1 | + |

## One command

```bash
mise run check:ontology-catalog
```

It runs `tools/test_provenance_alignment.py` with the other tool tests, then
the catalog check. Also `mise run check:ontology-versioning`.

## Artefacts to inspect

- `ontology/foundation/README.md` §6 to §8 and §11, `spec/foundation.ttl`,
  `vocab/foundation-vocab.ttl`. The README and spec agree except for the order
  of the `owl:AllDisjointClasses` member list, which carries no meaning.
- `ontology/surface/README.md` and `spec/surface.ttl`.
- ADR-A92's implementation notes: `srf:ReadSetEntry` is not aligned.
- Versions, all MINOR against `6e9acb1`: Foundation and its vocab 0.2.0 →
  0.3.0, Vocabulary 0.2.0 → 0.3.0, Quantification, Party and its vocab, Surface
  and its vocab 0.3.0 → 0.4.0, Eligibility, Instrument and Behaviour (spec and
  vocab) and the applied capacity execution spec 0.4.0 → 0.5.0, MORK 0.2.0 →
  0.3.0. `applied/insurance` is a sketch and was not touched.

## Deliberate non-coverage

- Layers subclassing `fnd:DerivedArtefact` beyond Surface (Quantification's
  recurrence bins, for example).
