<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-3.1, hierarchical match over flat schemes

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Machine:** R (Claude Code). **Branch:** `air/3.1-flat-hierarchy`
**Plan and test cases:** [Phase 3 plan](../plans/applied-insurance-reference-phase-3.md) (AIR-3.1 in detail)
**Decisions:** ADR-A100 and its implementation note

## Invariant

Under `elg:HierarchicalMatch`, a resolved scheme in which no member has a `skos:broader` link to another member decides only the concepts a condition names. Every other member is Undetermined with `exe:NoHierarchy` in every backend, and hierarchical schemes evaluate as before.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root on machine R, after `mise run build:ontology-catalog` and `mise run build:ontology-releases`.

```bash
mise run check:mork-compilers && mise run check:ontology-catalog && mise run check:ontology-versioning
```

## Artefacts to inspect

- The two examples in `ontology/eligibility/examples/` and their recorded decisions.
- `elg:L14` in the vocabulary and README, and `exe:NoHierarchy`.
- The flat branch in `eligibility_ir._expand` and `sparql_backend.concept_select`.

## Deliberate non-coverage

Set readings and negation (AIR-3.2, AIR-3.3). Kind-only matching (substrate S2).

## Handoff

Written by the building machine when the work is committed. R ran the command before handing over.

- **Built:**
- **Not run:**
- **Check first:**
- **Deviations from the plan:**

## Results

Written on machine R at verification.
