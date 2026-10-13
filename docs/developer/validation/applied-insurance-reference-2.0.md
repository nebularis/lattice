<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-2.0, literate modules and the documentation rule

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Machine:** S (Copilot Business). **Branch:** `air/applied-reference`, commits `[AIR-2.0] …`
**Plan and test cases:** [Phase 2 plan](../plans/applied-insurance-reference-phase-2.md) (AIR-2.0 in detail)
**Decisions:** ADR-A98 (namespaces, addendum), ADR-A99

## Invariant

`insurance/common` and `insurance/peril` are literate: extracting either README reproduces its committed Turtle up to formatting, and a test fails when they diverge. The extractor handles nested modules and several vocabulary documents, and every published concept carries a note on the standards it follows.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root. S runs it before the handoff commit. R runs it again at verification,
after `mise run build:ontology-catalog` and `mise run build:ontology-releases`, which S cannot do.

```bash
mise run check:ontology-catalog && mise run check:ontology-versioning && mise exec -- python -m pytest tools/test_literate_extract.py -q
```

## Artefacts to inspect

- `tools/literate_extract.py` and `tools/test_literate_extract.py`.
- Both module READMEs: extraction contracts, Sources consulted, the region sections.
- The isomorphism comparison with `HEAD`, recorded in the Handoff.
- ADR-A120's addendum.

## Deliberate non-coverage

No new concepts. No version changes except the peril shapes' `.version`.

## Handoff

Written by S in the `[AIR-2.0] Handoff` commit. S runs the checks itself, so say which ran.

- **Built:**
- **Run, with the result:**
- **Not run, and why:**
- **Versions used, if they differ from the plan's snapshot:**
- **Check first:**
- **Deviations from the plan:**

## Results

Written on machine R at verification.
