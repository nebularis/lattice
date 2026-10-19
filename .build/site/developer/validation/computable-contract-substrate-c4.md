<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS C4, Wording tables, assembly and variable values

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R. **Branch:** `ccs/c4-wording-assembly`
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

- **Built:** `wording` 0.2.0 (rows, inclusion modes, variation slots as elements, inclusion
  conditions, assembled wordings, variable values), `wording-vocab` 0.2.0 (the four inclusion modes
  and eight population methods as closed sets), `wording-shapes` 0.2.0 (a subject and a class shape
  per new property, the value rule, the column rule), the README sections §5.10 to §5.12, the
  extended trial protocol and the new facility form, and 15 tests in `tools/test_wording.py`.
- **Not run:** nothing skipped. The reasoner rows ran.
- **Check first:**
  - A slot asserts `wrd:hasVariant` (a sub-property of `wrd:directlyComprises`). The shapes read
    `hasVariant` directly, so no check needs the derived part-whole edge.
  - `wrd:forColumn` is checked in SHACL Core by a sequence path: a record with a column must be for
    a variable some row declares.
  - The facility form's variants carry no inclusion condition: the drafter chooses between them.
    The conditional clause shows conditions over a governing variable.
- **Deviations from the plan:** none.
- **Tags for the maintainer:** `wording-v0.2.0`, `wording-vocab-v0.2.0`, `wording-shapes-v0.2.0`.

## Results

Verified on machine R, 2026-10-01, with the reasoning harness built.

| ID | Result |
|---|---|
| C4-01 | pass: imports unchanged, `0.2.0` |
| C4-02 | pass: all three examples conform |
| C4-03 | pass: all three examples consistent (C3-05 over every example) |
| C4-04 | pass: eight cases each reported on their focus node (the brief's six, a column on a non-row variable, a value in no wording) |
| C4-05 | pass: three rows by two arms, one cell each |
| C4-06 | pass (C3-17, over every property) |
| C4-07 | pass: four modes and eight methods, each set declared all different |
| C4-08 | pass (C3-09, spec, vocab and shapes) |
| C4-09 | pass: three release rows. `check:ontology-versioning` passes once committed |
| C4-10 | pass: `3b3732b` commits the examples alone, before the model |
| C4-11 | pass: `check:ontology-catalog`, 154 tests |

`mise run topology:links`: 427, the baseline.
