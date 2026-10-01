<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS C4, Wording tables, assembly and variable values

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R (Claude Code). **Branch:** `ccs/c4-wording-assembly`
**Plan and test cases:** [CCS plan](../plans/computable-contract-substrate.md) (C4 in detail)
**Decisions:** ADR-A112 decision 3, CC-D6, ADR-A-C2 and its addendum. Questions C4-Q1 to C4-Q3 decided 2026-10-01

## Invariant

Wording gains tables, assembly and variable values, additively. Every new property states its subject and value and is checked by SHACL Core. Assembly is design time.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root on machine R, with the reasoning harness built where a row is L2.

```bash
mise run build:ontology-catalog && mise run check:ontology-versioning && mise run check:ontology-catalog
```

## Artefacts to inspect

- `ontology/wording/spec/wording.ttl`: the slot under C4-Q2 and the assembled wording under C4-Q1.
- `ontology/wording/examples/facility-form.ttl`: the form and its assembled facility.
- `ontology/wording/examples/trial-protocol.ttl`: one cell per row and arm.

## Deliberate non-coverage

The laws that need SPARQL (W3 to W6) and textual amendments (C5). Evaluating inclusion conditions, which is Eligibility's, in question form.

## Handoff

Written by the building machine when the work is committed.

- **Built:**
- **Not run:**
- **Check first:**
- **Deviations from the plan:**

## Results

Written on machine R at verification.
