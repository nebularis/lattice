<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-2.2, peril characteristics

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Machine:** S (Copilot Business). **Branch:** `air/applied-reference`, commits `[AIR-2.2] …`
**Plan and test cases:** [Phase 2 plan](../plans/applied-insurance-reference-phase-2.md) (AIR-2.2 in detail)
**Decisions:** ADR-A98 (namespaces, addendum), ADR-A99

## Invariant

The seven characteristic schemes hold their reference concepts, the four shared characteristic properties specialise their `icm:` parents, and the `icm-voc:` contracts bind to the peril schemes.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root. S runs it before the handoff commit. R runs it again at verification,
after `mise run build:ontology-catalog` and `mise run build:ontology-releases`, which S cannot do.

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

Written by S in the `[AIR-2.2] Handoff` commit. S runs the checks itself, so say which ran.

- **Built:**
- **Run, with the result:**
- **Not run, and why:**
- **Versions used, if they differ from the plan's snapshot:**
- **Check first:**
- **Deviations from the plan:**

## Results

Written on machine R at verification.
