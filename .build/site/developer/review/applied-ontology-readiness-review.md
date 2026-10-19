<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Review Request: Applied Ontology Readiness, AOR-10, AOR-11, AOR-14 to AOR-17 and the reasoning harness

**Unit:** `applied-ontology-readiness`
**Status record:** [applied-ontology-readiness.md](../status/applied-ontology-readiness.md)
**Plan:** [applied-ontology-readiness.md](../plans/applied-ontology-readiness.md)
**Date:** 2026-09-25 (refreshed after `54caeb6`)
**Requested by:** agent, autonomous session

AOR-2 to AOR-9, AOR-3b, AOR-12 and AOR-13 are committed and signed off in
[`LOG.md`](../validation/LOG.md). Every ADR this unit needs is Accepted.

## Scope

| Item | Subject | Record |
|---|---|---|
| ADR-A83 harness | `platform/reasoning-testkit`, the isolation guardrail, SWRL under HermiT (`eligibility-compiler` Part B) | [VP](../validation/eligibility-compiler-part-b.md) |
| ADR-A97 | Mork 0.4.0: GCI annotations repaired, order relations made OWL 2 DL, acyclicity shapes | [ADR](../../architecture/decisions/ADR-A97-mork-order-relations-in-owl-2-dl.md), [VP](../validation/eligibility-compiler-part-b.md) |
| AOR-10, AOR-11 | Design-time OWL classes, `elg:singleValued`, subsumption, satisfiability and overlap checks | [VP](../validation/applied-ontology-readiness-aor-10-11.md) |
| AOR-14 to AOR-16 | Derived rate spaces, calendar binding, alternative bounds with compiler unit selection | [VP](../validation/applied-ontology-readiness-aor-14-16.md) |
| AOR-17 | Provision attachment | [VP](../validation/applied-ontology-readiness-aor-17.md) |

## Commands

Run from the repository root. Build the harness first, or the reasoner tests
skip.

```bash
mise run bootstrap:reasoning-testkit
```

```bash
mise run check:reasoning-testkit
```

```bash
mise run check:reasoning-isolation
```

```bash
mise run check:mork-compilers
```

```bash
mise run check:ontology-versioning
```

```bash
mise run check:ontology-catalog
```

```bash
mise run check:python-root
```

```bash
mise run check:mtp
```

## Pass criteria

| Command | Pass |
|---|---|
| `bootstrap:reasoning-testkit` | exits 0, `platform/reasoning-testkit/target/reasoning-testkit.jar` exists |
| `check:reasoning-testkit` | exits 0 (3 JUnit tests) |
| `check:reasoning-isolation` | `reasoning engines are isolated in platform/reasoning-testkit` |
| `check:mork-compilers` | `92 passed`, none skipped |
| `check:ontology-versioning` | no unbumped changes across 29 documents |
| `check:ontology-catalog` | `53 passed`, then `ontology catalog consistent, 3 known defect(s) reported` |
| `check:python-root` | unittest `OK` (84 tests), then the Phase 8 line with 4 Eligibility cases |
| `check:mtp` | `MTP structural checks passed` |

## Open questions

1. MTP pins: whether `build` should stop rewriting `pins.lock.json`.
2. Whether to take up `literate_extract.py`'s stale root (status record).
