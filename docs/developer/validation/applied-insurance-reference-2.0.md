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

- **Built:** `tools/literate_extract.py` extended for nested module `--layer` paths and an
  `@output-file` directive on `turtle-vocab` blocks (ADR-A120 addendum), with AIR20-01 to AIR20-05
  added to `tools/test_literate_extract.py`. `insurance/common` and `insurance/peril` converted to
  literate READMEs (every current spec/vocab/shapes construct moved into a fenced block, the old
  `# ==== BEGIN/END REGION ====` comment markers replaced by README sections of the same name, one
  per characteristic/companion/cause region, each an empty `turtle-vocab` block until the slice
  that owns it fills it). `prl:DocumentationShape` added to `peril/shapes/constraints.ttl` (the
  AIR-2.0 documentation rule), shapes `.version` 0.1.0 → 0.2.0. `skos:note` added to every concept
  `examples/well-formed.ttl` declares, to satisfy the new shape. ADR-A120's addendum, `tools/README.md`,
  the developer guide §3 and this skill updated to match.
- **Run, with the result:**
  - `python -m pytest tools/test_literate_extract.py -q`: 19 passed (6 pre-existing + AIR20-01 to
    AIR20-05, the latter parametrised over every literate layer of `main`: foundation,
    quantification, wording, behaviour, instrument, eligibility).
  - `python -m pytest tools/test_peril_vocabulary.py tools/test_applied_shared_contracts.py -q`:
    41 passed.
  - `mise run check:ontology-catalog`: 743 passed, 7 failed. All 7 are pre-existing and unrelated
    (confirmed on a clean, unedited checkout before this slice): six `tools/test_import_guard.py`
    fixture/order-table cases and one `tools/test_reasoning_stalled_import.py` case, all because
    `platform/reasoning-testkit`'s jar hangs past pytest's 60s subprocess timeout in this
    environment, not because of anything this slice touches.
  - `mise run check:ontology-versioning`: reports `UNBUMPED` for all four of `insurance/common`'s
    and `insurance/peril`'s spec and vocab documents. This is the expected, accepted case the plan's
    "Deliberate non-coverage" names ("No version changes"), not a real defect: the checker does a
    literal git-text diff, and the literate conversion is a pure reformatting (the old `# ====
    BEGIN/END REGION ====` banner comments move out of the `.ttl` files into README section
    headings). Verified with an isomorphism comparison against `HEAD` (see below), not with
    `--check`, since the README intentionally restructures the comments.
- **Not run, and why:** nothing. `tools/literate_extract.py --check` substitutes for the full
  `check:ontology-catalog` run's literate coverage (that task's test file list does not include
  `tools/test_literate_extract.py` — a pre-existing gap, not introduced here, left unfixed since
  widening that task's scope is outside this slice).
- **Versions used, if they differ from the plan's snapshot:** none differ; `insurance/common` and
  `insurance/peril` stay at their current `main` versions (`0.5.0`/`0.4.0`/`0.4.0`/`0.4.0`
  respectively for common spec/vocab and peril spec/vocab). Only `peril/shapes/.version` bumps,
  `0.1.0` → `0.2.0`.
- **Check first:** `check:ontology-versioning`'s four `UNBUMPED` lines for `insurance/common` and
  `insurance/peril`'s spec/vocab documents, per the note above.
- **Deviations from the plan:**
  1. Found a real, generalisable bug while regenerating: `tools/literate_extract.py`'s
     `target.write_text(content, encoding="utf-8")` (no `newline=` argument) lets Python's text-mode
     write translate embedded `\n` inside a multi-line SPARQL string literal to `\r\n` on Windows,
     changing that literal's value, not just insignificant whitespace. Fixed with `newline="\n"`.
     Unrelated to AIR but found and fixed in the same file this slice already touches.
  2. Verifying the conversion's isomorphism against `HEAD` found `rdflib.compare.to_isomorphic`/
     `graph_diff` unreliable for `peril/shapes/constraints.ttl`, which has several `sh:NodeShape`s
     sharing the same local blank-node shape around `sh:sparql`. Verified instead with a
     deterministic skolemization (each shape's `sh:sparql` blank node renamed from its own IRI plus
     the sorted order of its `sh:message` text) before a plain set comparison. Both methods and
     scripts are recorded in session memory, not committed (one-off verification aids).
  3. `prl:DocumentationShape` is placed in `shapes/constraints.ttl`, per the brief, even though its
     per-concept shape resembles `structural.ttl`'s convention more closely. Noted, not changed,
     since the brief is explicit.

## Results

Written on machine R at verification.
