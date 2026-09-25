<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AOR-6, hierarchical match and scheme resolution

**Unit:** [`applied-ontology-readiness`](../status/applied-ontology-readiness.md)
**Plan section:** [Phase B](../plans/applied-ontology-readiness.md#phase-b-executable-coverage)
**Decisions:** [ADR-A89](../../architecture/decisions/ADR-A89-eligibility-ir-concept-conditions-and-profile-aggregation.md) items 2 and 3, [ADR-A87](../../architecture/decisions/ADR-A87-eligibility-concept-inclusion-and-exclusion.md) L10 to L12, [ADR-A85](../../architecture/decisions/ADR-A85-vocabulary-scoped-temporal-binding-resolution.md), all but A-85 Proposed

## Invariant

A hierarchical or exclusion-only condition compiles only against the one
scheme its contract resolves to, under an explicit instant and scope when the
contract has bindings. Its SPARQL decides every member of that scheme as the
plan's own expansion of the ADR-A87 table does.

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AOR6-01 | solid tumours required, CNS excluded / lung tumour asked / `Permitted` | L1 | + |
| AOR6-02 | same / CNS tumour and glioma asked / both `Denied` (L10) | L1 | - |
| AOR6-03 | same / solid tumour asked / `Undetermined` (L11) | L1 | - |
| AOR6-04 | same / neoplasm and haematological asked / both `Denied` | L1 | - |
| AOR6-05 | same / a concept outside the scheme, and no candidate / both `Undetermined` | L1 | - |
| AOR6-06 | same / plan inspected / scheme recorded, fallback (no binding), contract and scheme in provenance | L1 | + |
| AOR6-07 | hierarchical, haematological excluded only / four candidates / `Permitted`, `Denied`, `Undetermined` (L11), `Undetermined` (outside) | L1 | + |
| AOR6-08 | flat, haematological excluded only / three candidates / `Permitted`, `Denied`, `Undetermined` | L1 | + |
| AOR6-09 | exclusion-only with no contract / compiled / refused | L1 | - |
| AOR6-10 | three conditions / every scheme member asked through SPARQL / equals the expansion | L2 | + |
| AOR6-11 | contract with bindings, no instant / compiled / refused | L1 | - |
| AOR6-12 | two editions, handover 2026-01-01 / compiled before and after / different scheme and binding, a concept new in 2026 `Undetermined` then `Permitted` | L1 | + |
| AOR6-13 | two equally specific applicable bindings / compiled / refused | L1 | - |
| AOR6-14 | a cycle in the scheme / compiled / refused (L9) | L1 | - |
| AOR6-15 | `hierarchical-match.ttl` / compiled and executed / `Permitted`, the decision the example records | L1 | + |

## One command

```bash
mise run check:mork-compilers
```

Pass: `42 passed`.

## Artefacts to inspect

- `eligibility_ir.py`: `ResolutionContext`, `SchemeResolution`,
  `_resolve_scheme`, `_expand`.
- `sparql_backend.py`: `_hierarchical_decision` and the scheme-membership
  guard.
- `ontology/eligibility/README.md` §4: a candidate outside the bound scheme,
  where the decision needs that scheme, is `Undetermined`. This reading is
  new and flagged in the status record.
- Dependencies: `tools/mork_compilers` now depends on
  `lattice-vocabulary-resolver`. `bootstrap:mork-compilers` and
  `bootstrap:surface` depend on `bootstrap:vocabulary`, and both workflows
  install `tools/vocabulary` first. Surface already needed this and was
  missing it.

## Adversarial probe (run by the agent)

| Mutation | Tests failed |
|---|---|
| SPARQL L11 branch replaced by `Permitted` | AOR6-03, AOR6-07, AOR6-10 |
| scheme-membership guard removed | AOR6-05, AOR6-07, AOR6-08, AOR6-12 |
| expansion's L11 branch replaced by `Permitted` | AOR6-10 |
| explicit-instant requirement disabled | AOR6-11 |

## Known limit

The SPARQL walk does not check that intermediate concepts belong to the
scheme. The expansion does. The two agree whenever a scheme's members are
broader only than other members, which AOR6-10 exercises. A scheme that
routes its hierarchy through a non-member would make them diverge.

## Deliberate non-coverage

- SHACL and SWRL for concept plans, which consume the expansion (AOR-7).
- How Surface treats the resolution instant (`temporal-binding-consumer-hardening`
  Finding 1). This compiler already takes it explicitly, which matches that
  unit's recommended Option B.
