<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: OD2, sections 1 to 3 of a README in the layout

**Unit:** [`improved-ontology-documentation`](../status/improved-ontology-documentation.md), slice OD2
([plan](../plans/improved-ontology-documentation.md#slices)).
**Implements:** [ADR-A126](../../architecture/decisions/ADR-A126-literate-specification-layout-and-grammar.md)
decisions 1 (section 3), 10 and 13, and RC1-C5's section 3 rule.
**Built autonomously**, at the maintainer's request of 2026-10-18. The decisions taken alone are listed below,
for the maintainer to keep or overrule.

## Invariant

For a README in the layout, each document its section 2 header table names opens with exactly what sections
1 and 2 state: its prefixes, its ontology header, `dct:description` from section 1 as plain text, its creators
and contributors by IRI and never by name, and the Dublin Core terms it uses declared locally. A README not in
the layout extracts exactly as before. A migrated README holds one catalogue entry, in section 3.

## What changed

- `tools/literate_grammar.py`, new, standard library only. A Turtle writer for terms, blank nodes and lists,
  with a fixed predicate order. Markdown to plain text with links at the release tag. Section 2's three
  tables. `compile_layout()`, which returns each document's opening text.
- `tools/literate_extract.py`. `scan()` also records the prose lines and where catalogue blocks open.
  `plan()` takes the compiled openings and puts each document's blocks after them, refusing a block for a
  document the header table does not name. The version checks now read every output document. `main()`
  compiles a README in the layout, and the layout check requires its one catalogue entry in section 3.
- `tools/test_literate_grammar.py`, new, with tests OD2-T1 to OD2-T9.
- `tools/test_literate_extract.py`. OD1-T11's README gains a header table and a catalogue entry, which a
  migrated README now needs, and the test writes instead of checking, since there is no committed file to
  check against. It tests the same thing as before, a warning on a misnumbered section and an error on a
  missing one.
- `mise.toml`. `check:ontology-catalog` runs `tools/test_literate_grammar.py`.
- `docs/architecture/literate-specifications.md`. Sections 1 to 3 describe the header table as built, the
  prefixes added, the order of a document, and the section 3 rule.

## Decisions taken alone, for the maintainer

1. **The header table has one row per document**, with the columns Document, Ontology IRI, Version IRI and
   Imports. This replaces the Field and Value table first drafted in the conventions document. A module with
   several documents (ADR-A120) needs a row each. The version IRI is written in full because it does not
   always extend the ontology IRI. For example, Eligibility's ontology IRI is `.../neuro-semantic/eligibility`
   and its version IRI `.../neuro-semantic/lattice/eligibility/0.12.0`.
2. **Section 1 becomes the `dct:description` of every document the README generates**, not only the main
   spec document, so each document describes itself.
3. **`rdf:`, `rdfs:`, `owl:`, `xsd:` and `dct:` are added** with their standard namespaces when the prefix
   table omits them, and a different binding for one of them is refused.
4. **Only the header table is required** in section 2. The prefix and contributor tables are optional, so a
   module can migrate before its contributor table is agreed. The display name column is optional too.
5. **A document's order** is its ontology header, then every other generated statement sorted by subject,
   then anonymous statements, then the README's blocks for it in document order. Blocks are verbatim
   Turtle, which a standard-library extractor cannot sort.
6. **The repository's blob URL is a constant** (`https://github.com/nebularis/lattice/blob/`), marked as a
   shortcut, so a downstream README's links would point at LATTICE. It moves to the catalogue's conventions
   when downstream catalogues exist (RC4).
7. **Link targets.** The release tag comes from the main spec document's version IRI, by the versioning
   policy's naming rule, and a relative link with no main spec document is refused. A link to an anchor alone
   resolves to the README at that tag. A link that leaves the repository is refused. An image in section 1 is
   refused, as tables and headings are.
8. **In a migrated README, every document takes the prefix table's prefixes.** The extractor no longer copies
   the main spec document's prefixes into its other documents, as it does for an unmigrated README.

## Test cases

In `tools/test_literate_grammar.py`.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| OD2-T1 | a README in the layout / extract / the header's type, version IRI, import, description, creator, the Dublin Core declarations and the standard prefixes are present, and the display name is not | L3 | + |
| OD2-T2 | section 1 with code, emphasis, a snake_case word, two paragraphs, list items, links into the repository, to an anchor and outside it, and an excluded sentence / extract / the exact plain text, with links at `x-v0.2.0` | L1 | + |
| OD2-T3 | a table, a heading, an image and a link out of the repository in section 1 / compile / each refused | L1 | − |
| OD2-T4 | every version IRI in a tracked spec or vocab document / the release tag / equal to `ontology_releases.release_name` | L3 | + |
| OD2-T5 | nine malformed sections 2 (no header table, an unknown table, a path outside `spec/` and `vocab/`, an unknown role, a name for an identifier, `xsd:` rebound, a prefix twice, a version IRI with no version, two header tables) / compile / each refused | L1 | − |
| OD2-T6 | two documents with blocks for each / extract / each opens with its own header and holds its own blocks, and different versions are refused | L1 | +/− |
| OD2-T7 | a block for a document the header table does not name / extract / refused | L1 | − |
| OD2-T8 | one, none and two catalogue entries in section 3, and one outside it / the layout check / accepted, then three errors | L1 | +/− |
| OD2-T9 | a README in the layout / extract to a directory, then check / written, then no drift | L4 | + |

## One command

Run from the repository root. A pass is every test passing.

```bash
mise exec -- python -m pytest tools/test_literate_grammar.py tools/test_literate_extract.py -q
```

## Results

2026-10-18, run while building, from this worktree:

- **The grammar and extractor tests:** `tools/test_literate_grammar.py` and `tools/test_literate_extract.py`
  together, 87 passed.
- **`tools/test_lattice_repo_catalogue.py`:** 67 passed.
- **The per-layer extraction tests:** Instrument, Wording, Keys, Additivity, Behaviour nested and Eligibility,
  selected by name, 9 passed.
- **`mise run check:formal-freshness`:** passes.

`mise run check:ontology-catalog` was not run. The adversarial probes were not run.

## Deliberate non-coverage

- Section 6. OD3 compiles it.
- Shapes from section 6, and the generated regions. OD4 and OD5.
- Any real README in the layout. The first is Eligibility, in OD6.

## Decisions answered

2026-10-18, by the maintainer: decisions 2, 3, 4, 6, 7 and 8 agreed.

- **Decision 1** agreed. The header table lists ontology documents only, the spec and vocab documents.
  Shape and projection files have no ontology header, and their targets are in the catalogue entry. The
  header table's documents and the entry's `extract.spec` and `extract.vocab` name the same files. Both
  stay, held equal by RC1-T3 now and by every extraction after RC4 (OD2-Q1, option a).
- **Decision 5** changed (OD2-Q5, option b). A document's blocks are ordered by their own text, not their
  place in the README, and a block of a migrated README may not declare a prefix. OD-D18 then holds in full.
  ADR-A126 decision 10 is clarified in place to say so. Tests OD2-T10 and OD2-T11 were added and pass. A
  later change is planned so that the versioning check considers only a document's graph (TD-51).

The maintainer ran every test suite on 2026-10-18, before this change, and all pass.
