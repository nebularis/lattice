<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AOR-17, provision attachment

**Unit:** [`applied-ontology-readiness`](../status/applied-ontology-readiness.md)
**Decision:** [ADR-A96](../../architecture/decisions/ADR-A96-instrument-provision-attachment.md), Accepted

## Invariant

An obligation may be expressed by several provisions without a reasoner
equating them. A deployment can still require single attachment.

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AOR17-01 | Instrument spec / parsed / `ins:inProvision` is not functional | L1 | + |
| AOR17-02 | an obligation in two provisions / optional `ins:SingleProvisionShape` / violation | L1 | - |

## One command

```bash
mise run check:ontology-catalog
```

## Artefacts to inspect

- `ontology/instrument/README.md` §4 and §7, `spec/instrument.ttl`, and the
  optional `shapes/single-provision.ttl`.
- ADR-A07b's disjointness text, corrected in the same change.
- Instrument 0.5.0 → 0.6.0 (MINOR, a widened cardinality).
