<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Review Request: Applied Ontology Readiness, AOR-3b, AOR-12, AOR-13 and ADRs

**Unit:** `applied-ontology-readiness`
**Status record:** [applied-ontology-readiness.md](../status/applied-ontology-readiness.md)
**Plan:** [applied-ontology-readiness.md](../plans/applied-ontology-readiness.md)
**Date:** 2026-09-25 (refreshed after `6e9acb1`)
**Requested by:** agent, autonomous session

AOR-2 to AOR-9 were reviewed by command run and committed (`6e36586`,
`6e9acb1`). Their `LOG.md` sign-offs remain open.

## Scope

| Item | Subject | Record |
|---|---|---|
| AOR-3b | Content-hash version IRIs for generated documents, git-trackable scanning, MTP re-pin | [VP](../validation/applied-ontology-readiness-aor-3b.md) |
| AOR-12 | Foundation derived-artefact contract, Surface alignment | [VP](../validation/applied-ontology-readiness-aor-12.md) |
| AOR-13 | Executable aligned directly to PROV-O | [VP](../validation/applied-ontology-readiness-aor-13.md) |
| ADR-A83 | Test-only reasoning engine isolation | [ADR](../../architecture/decisions/ADR-A83-test-only-reasoning-engine-isolation.md) |
| ADR-A93 to A-96 | Derived rates, calendar binding, alternative bounds, provision attachment | [catalogue](../../architecture/decisions/README.md) |
| Protégé | Manual check of AOR-4 | [walkthrough](../protege-import-walkthrough.md) |

## Commands

Run from the repository root.

```bash
mise run check:ontology-versioning
```

```bash
mise run check:ontology-catalog
```

```bash
mise run check:mtp
```

```bash
mise run check:python-root
```

```bash
mise run check:mork-compilers
```


## Pass criteria

| Command | Pass |
|---|---|
| `check:ontology-versioning` | no unbumped changes across 29 documents |
| `check:ontology-catalog` | `35 passed` (every `tools/test_*.py`: catalog, versioning, Eligibility examples, PROV-O alignment), then `ontology catalog consistent, 3 known defect(s) reported` |
| `check:mtp` | `MTP structural checks passed` |
| `check:python-root` | unittest `OK` (Surface now 63 tests), then the Phase 8 line with 4 Eligibility cases |
| `check:mork-compilers` | `74 passed` |

## Open questions

1. Ratify ADR-A83, and schedule its delivery.
2. Choose the OWL path encoding for AOR-10 (ADR-A90, open question of
   2026-09-25).
3. Ratify or amend ADRs A-93 to A-96.
