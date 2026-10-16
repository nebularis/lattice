<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: OD1, a fence-aware scanner, markers and the layout check

**Unit:** [`improved-ontology-documentation`](../status/improved-ontology-documentation.md), slice OD1
([plan](../plans/improved-ontology-documentation.md#slices)).
**Implements:** [ADR-A126](../../architecture/decisions/ADR-A126-literate-specification-layout-and-grammar.md)
decisions 1, 8 and 9, and [ADR-A120](../../architecture/decisions/ADR-A120-literate-specs-with-several-documents.md)'s
2026-10-17 addendum.
**Decisions needing confirmation:** three implementation choices, below.

## Invariant

Every README under `ontology/` yields exactly the blocks it yielded before, with the same tags, bodies and
line numbers, so no generated file changes. What is new applies only to markers and to READMEs in the new
layout, and none exist yet. A tagged block or a marker shown inside another fence or inside an ordinary HTML
comment is text. A malformed marker is refused, never ignored.

## What changed

- `tools/literate_extract.py`. `scan()` reads a README once and returns its blocks, its marker regions and
  its top-level sections. `parse_blocks()` keeps its signature and returns `scan().blocks`, so
  `check_formal_freshness.py` is unaffected. `Block` gains `output_file` (the JSON form) and `hidden`, both
  defaulted. One `_target()` replaces `_spec_target()` and `_vocab_target()`, with the same error messages,
  and handles both `output-file` forms for spec, vocab and shape blocks. A shape block that names its file
  takes no `--shapes` target. `layout_problems()` checks a README in the layout by section title, and
  `main()` prints its warnings, in yellow on a terminal, and fails on its errors.
- `tools/test_literate_extract.py`. Tests OD1-T1 to OD1-T11.
- `mise.toml`. `check:ontology-catalog` now runs `tools/test_literate_extract.py`, which no task ran before
  (see deviation 1).
- Documentation. `tools/README.md` describes the markers and the layout check, and links the conventions
  document. Its commands, and the ontology authoring skill's, now go through `mise exec`. The ontology
  architecture document, the glossary and the skill link to `literate-specifications.md`.

## Implementation choices, for the maintainer

1. **A README uses the layout when it has a "Description Logic Encoding" section.** Only then are its
   sections checked. Any other README is left alone, so the check cannot fail an unmigrated layer. The
   alternative, a flag in the catalogue entry, waits for RC1.
2. **A region holds exactly one key.** None of `exclude`, `output-file` and `generated` combines
   meaningfully with another, so a second key is refused.
3. **`output-file` from a region applies only to blocks that are extracted into `ontology/`** (spec, vocab
   and shapes). An example or `isabelle-spec` block inside such a region is unaffected. Given explicitly on a
   hidden example or `isabelle-spec` block, it is refused, since examples are never extracted (OD-D6) and an
   Isabelle theory has its own root.

## Deviations from the plan

1. **`tools/test_literate_extract.py` joins `check:ontology-catalog`.** It held the ADR-A120 and AIR-2.0
   tests, but no task ran it, so `mise run check` never did. It belongs with the other ontology tool tests.

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| OD1-T1 | every `README.md` under `ontology/` / scan / the same blocks as the scanner before OD1, and no region | L3 | + |
| OD1-T2 | a tagged block and a marker inside a four-backtick `markdown` fence / scan / no block and no region | L1 | + |
| OD1-T3 | ordinary comments, including "end of a table", and a tagged block inside a comment / scan / no region, and only the block outside is extracted | L1 | + |
| OD1-T4 | a hidden spec block with a JSON `output-file` / plan / it is marked hidden and goes to that file only | L1 | + |
| OD1-T5 | three regions, two nested / scan / each `end` closes the innermost, with the right lines | L1 | + |
| OD1-T6 | a spec block inside an `output-file` region and one after it / plan / the first goes to the region's file, the second to the default | L1 | + |
| OD1-T7 | a shape block with a first-line `output-file` and one without / plan / one `--shapes` target suffices, and two are refused | L1 | +/− |
| OD1-T8 | 15 malformed READMEs: an unclosed region, a stray `end`, an unknown key, two keys, a wrong type, bad JSON, a bare `start`, `-->` inside a hidden block, a hidden mermaid diagram, a hidden block of text, a hidden block not closed by `-->`, `output-file` from both a region and a hidden block, `output-file` on a hidden example, an unclosed fence, an unclosed comment / scan / each refused with its own message | L1 | − |
| OD1-T9 | a block with both `output-file` forms / plan / refused | L1 | − |
| OD1-T10 | a README in the layout, one misnumbered, one with a missing and an extra section, and one not migrated / layout check / nothing, a warning, two errors, nothing | L1 | +/− |
| OD1-T11 | the same through `main()` / `--check` / exit 0 with a warning, then exit 1 with the errors | L4 | +/− |

## One command

Run from the repository root. A pass is every test in the module passing, with no skip.

```bash
mise exec -- python -m pytest tools/test_literate_extract.py -q
```

Then the whole ontology tool suite, which now includes it, and every per-layer `--check` test. A pass is the
suite passing as it did before OD1, and the XML catalog check passing after it.

```bash
mise run check:ontology-catalog
```

## Adversarial probes, for the gate

| Mutation | Expected |
|---|---|
| `scan()` stops skipping other fences (remove the `ANY_FENCE_RE` branch) | OD1-T2 fails |
| `<!-- end -->` closes the outermost region (`open_regions.pop(0)`) | OD1-T5 fails |
| `_target()` stops refusing the second form | OD1-T9 fails |

## Deliberate non-coverage

- What an `exclude` or `generated` region does to output. Nothing reads them until OD2 (section 1) and OD5
  (generated regions). OD1 parses and checks them.
- Subsection checks inside section 6. They come with the grammar, in OD3.
- Any README migrated to the layout. The first is Eligibility, in OD6.
