<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Review Request: Applied Ontology Readiness, AOR-2 to AOR-9

**Unit:** `applied-ontology-readiness`
**Status record:** [applied-ontology-readiness.md](../status/applied-ontology-readiness.md)
**Plan:** [applied-ontology-readiness.md](../plans/applied-ontology-readiness.md)
**Date:** 2026-09-25
**Requested by:** agent, autonomous session.

## Scope

Eight slices, each with a Validation Pack:

| Slice | Subject | VP |
|---|---|---|
| AOR-2 | Eligibility examples and the declaration warning | [aor-2](../validation/applied-ontology-readiness-aor-2.md) |
| AOR-3 | Versioning guarantees | [aor-3](../validation/applied-ontology-readiness-aor-3.md) |
| AOR-4 | Consumer catalog and import resolution | [aor-4](../validation/applied-ontology-readiness-aor-4.md) |
| AOR-5 | Flat concept conditions | [aor-5](../validation/applied-ontology-readiness-aor-5.md) |
| AOR-6 | Hierarchical match and scheme resolution | [aor-6](../validation/applied-ontology-readiness-aor-6.md) |
| AOR-7 | SHACL, SWRL and diagnostics for concept plans | [aor-7](../validation/applied-ontology-readiness-aor-7.md) |
| AOR-8 | Profile aggregation and the conformance corpus | [aor-8](../validation/applied-ontology-readiness-aor-8.md) |
| AOR-9 | Candidate evidence bindings | [aor-9](../validation/applied-ontology-readiness-aor-9.md) |

AOR-2 to AOR-4 are committed (`6e36586`). AOR-5 to AOR-9 are one uncommitted
change set, which can be committed together or split by slice in the order
above. The human validation gate and `LOG.md` sign-off are pending for all
eight.

## Commands

Run from the repository root.

```bash
mise run bootstrap:python-root
```

```bash
mise run bootstrap:mork-compilers
```

```bash
mise run check:eligibility-examples
```

```bash
mise run check:ontology-versioning
```

```bash
mise run check:ontology-catalog
```

```bash
mise run check:mork-compilers
```

```bash
mise run check:python-root
```

## Pass criteria

| Command | Pass |
|---|---|
| `check:eligibility-examples` | `12 passed` |
| `check:ontology-versioning` | `7 passed`, then no unbumped changes across 33 documents |
| `check:ontology-catalog` | `11 passed`, then `ontology catalog consistent, 7 known defect(s) reported` |
| `check:mork-compilers` | `74 passed` |
| `check:python-root` | unittest `OK`, then `Phase 8 conformance passed: 3 Surface parity cases, 4 Eligibility cases (SPARQL and SHACL)` |

`mise run topology:links` fails at `HEAD` as well, on links none of these
slices wrote. `mise run check:mtp` is unaffected, but `build:mtp` rewrites a
stale pin (status record, "Discovered").

## Manual step

Open `ontology/behaviour/spec/behaviour.ttl` in Protégé and confirm the import
closure loads through the generated stub catalog (AOR-4 VP).

## Open questions

The status record's "Decisions awaiting the human" lists nine. The four that
gate further work:

1. How generated ontology documents are versioned (job-family regeneration).
2. The OWL encoding of exclusions over multi-step, multi-valued paths (AOR-10).
3. Whether Executable imports Foundation or aligns to `prov:` directly (AOR-13).
4. Drafting the Phase C ADRs (AOR-14 to AOR-17).
