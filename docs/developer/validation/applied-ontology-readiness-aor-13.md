<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AOR-13, Executable aligned to PROV-O

**Unit:** [`applied-ontology-readiness`](../status/applied-ontology-readiness.md)
**Decision:** [ADR-A92](../../architecture/decisions/ADR-A92-derived-artefact-contract-and-prov-o-alignment.md) item 3, rewritten on acceptance

## Invariant

Executable plans and artefacts are PROV-O entities derived from their sources,
without Executable importing Foundation, and without adding any functional
restriction.

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AOR13-01 | Executable spec / parsed / imports PROV-O and no Foundation document, plans and artefacts `⊑ prov:Entity`, four derivation properties `⊑ prov:wasDerivedFrom` | L1 | + |
| AOR13-02 | a compiled concept plan plus Executable's closure / RDFS closure (`owlrl`) / the plan node and its condition are `prov:Entity` | L2 | + |

## One command

```bash
mise run check:ontology-catalog
```

Pass: every tool test passes, the four in `tools/test_provenance_alignment.py`
among them (with AOR-12).

## Artefacts to inspect

- `ontology/mork/spec/Executable.ttl`, the PROV-O alignment block.
- ADR-A92 item 3 and its consequences.

## Evidence for the condition on direct alignment

PROV-O (`http://www.w3.org/ns/prov-o-20130430`, fetched 2026-09-25) declares
no `owl:FunctionalProperty` and no `owl:InverseFunctionalProperty`. Its one
cardinality restriction is on `prov:ActivityInfluence`. It declares
`prov:Entity` disjoint with `prov:Activity`, which is the one restriction the
alignment passes on: a node a plan derives from cannot also be an activity.

## Adversarial probe (run by the agent)

Removing `exe:derivedFromEligibilityNode ⊑ prov:wasDerivedFrom` failed
AOR13-01 and AOR13-02.
