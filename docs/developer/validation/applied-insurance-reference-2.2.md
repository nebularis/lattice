<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-2.2, peril characteristics

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Machine:** S (Copilot Business). **Branch:** `air/2.2-characteristics`
**Plan and test cases:** [Phase 2 plan](../plans/applied-insurance-reference-phase-2.md) (AIR-2.2 in detail)
**Decisions:** ADR-A98 (namespaces, addendum), ADR-A99

## Invariant

The seven characteristic schemes hold their reference concepts, the four shared characteristic properties specialise their `icm:` parents, and the `icm-voc:` contracts bind to the peril schemes.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root on machine R, after `mise run build:ontology-catalog` and `mise run build:ontology-releases`.

```bash
mise run check:ontology-catalog && mise run check:ontology-versioning
```

## Artefacts to inspect

- `ontology/applied/insurance/peril/spec/peril.ttl`: the `common/` import and the four sub-property axioms.
- `vocab/peril-vocab.ttl`: the seven characteristic regions and the four `voc:boundScheme` bindings.
- `examples/well-formed.ttl` and `tools/test_peril_vocabulary.py`.

## Deliberate non-coverage

No cause concepts (AIR-2.3, AIR-2.4). No typical-characteristic links on cause concepts, which arrive with the causes. No shape changes.

## Handoff

Written by the building machine when the work is committed. S could not run the tests, so R runs them first.

- **Built:**
- **Not run:**
- **Check first:**
- **Deviations from the plan:**

## Results

Written on machine R at verification.
