<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: OD5, the generated regions

**Unit:** [`improved-ontology-documentation`](../status/improved-ontology-documentation.md), slice OD5
([plan](../plans/improved-ontology-documentation.md#slices)).
**Implements:** [ADR-A126](../../architecture/decisions/ADR-A126-literate-specification-layout-and-grammar.md)
decision 7, and decision 8's `generated` marker.
**Built autonomously**, at the maintainer's request of 2026-10-18. The decisions taken alone are listed below,
for the maintainer to keep or overrule.

## Invariant

A README in the layout holds its Axiom Index (in 6.7) and its class diagram (in section 4) in generated
regions, written from what section 6 compiles to, and never edited by hand. Extraction rewrites them, and
`--check` reports a README whose regions are out of date. The regions are not read as section 6, so
refreshing twice changes nothing, and they do not depend on the order of entries.

## What changed

- `tools/literate_grammar.py`:
  - **`Views`** reads the compiled statements and restriction rows and writes the Axiom Index and the class
    diagram.
  - **`manchester()`** writes a term back in Manchester syntax.
  - **`verbalise()`** puts a restriction in the diagram's words.
  - **`refresh()`** rewrites the README's regions, each required once in its place.
  - **`Compiled`** gains the refreshed README.
- `tools/literate_extract.py`. `main()` writes the refreshed README, or reports it as drift under `--check`.
- `tools/test_literate_grammar.py`. Tests OD5-T1 to OD5-T7. The helpers add both regions, which a migrated
  README now needs.
- `tools/test_literate_extract.py`. OD1-T11's README gains both regions.
- `docs/architecture/literate-specifications.md`. The generated views are described as built.

## Decisions taken alone, for the maintainer

1. **Both regions are required**, once each, the Axiom Index inside 6.7 and the diagram inside section 4. A
   region of another name is refused.
2. **The README is an output.** The extractor writes the refreshed README to the path given, not under
   `--root`, and `--check` lists it as drift.
3. **The views are derived from the compiled statements**, plus the restriction rows, which also carry the
   SHACL-only rows. So they show what the grammar wrote, not a second reading of the README.
4. **The Axiom Index's columns are Term, Kind and Summary.** Terms are sorted by kind (class, object
   property, datatype property, individual) and then by name. A summary is short sentences in a fixed order,
   with restrictions sorted, so reordering a table's rows changes nothing. Annotations are left out, since
   they are in the entries.
5. **The diagram's conventions**, from the maintainer's walkthrough of 2026-10-15:
   - restrictions are members in ORM-style words, with numbers to ten written out
   - a datatype property with a domain is a member `name (range)`
   - an object property with named domain and range is an arrow
   - a property with no named domain is a box of its own
   - subclassing is `<|--`, including to classes outside the module, which appear as empty boxes
   - there are no composition arrows
   - a domain or range that is an expression is left out of the drawing, and stays in the index
6. **Names in the diagram** are local names, qualified as `prefix_local` where two classes share one. Mermaid
   reads `code (xsd:string)` as a method, so it is drawn as `code(xsd:string)`. It still reads correctly.

## Test cases

In `tools/test_literate_grammar.py`.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| OD5-T1 | classes, properties, an individual and disjointness / compile / the exact Axiom Index | L3 | + |
| OD5-T2 | the same / compile / the exact class diagram | L3 | + |
| OD5-T3 | two classes with one local name / compile / both qualified by prefix | L1 | + |
| OD5-T4 | a README extracted, checked, edited inside a region, and checked / `main()` / regions written, no drift, then drift naming the regions | L4 | +/− |
| OD5-T5 | a refreshed README / compiled again / the same README, documents and shapes | L2 | + |
| OD5-T6 | a missing index region, a diagram region outside section 4, two diagram regions, an unknown region / compile / each refused | L1 | − |
| OD5-T7 | the same entries in two orders / compile / identical regions | L2 | + |

The generated diagram of OD5-T2 was rendered with mermaid 10.9.1 in a browser on 2026-10-18, with no error,
the standalone property box included.

## One command

Run from the repository root. A pass is every test passing.

```bash
mise exec -- python -m pytest tools/test_literate_grammar.py tools/test_literate_extract.py -q
```

## Results

2026-10-18, run while building, from this worktree:

- **`tools/test_literate_grammar.py`:** 85 passed.
- **`tools/test_literate_extract.py` and `tools/test_lattice_repo_catalogue.py`:** 131 passed.
- **The per-layer extraction tests, selected by name:** 9 passed.
- **`mise run check:formal-freshness`:** passes.
- **The diagram render check:** passes.

`mise run check:ontology-catalog` was not run. The adversarial probes were not run.

## Adversarial probes, for the gate

| Mutation | Expected |
|---|---|
| `refresh()` stops checking where a region sits | OD5-T6's second case fails |
| `Readme.paragraphs()` stops leaving out generated regions | OD5-T5 fails |
| the index keeps README order | OD5-T7 fails |

## Deliberate non-coverage

- A real README's regions. OD6 adds them to Eligibility, whose existing hand-drawn diagram is replaced.
- Diagrams for unions in domains and ranges, and for individuals. They stay in the index only.

## Decisions answered

2026-10-18, by the maintainer: decisions 1 and 3 to 6 agreed. Decision 2 (the README as an output) agreed after a
detailed explanation. Only what lies between a `generated` region's markers is rewritten. Everything else in
the README is its source, so a concept is added by writing its entry in section 6, and the next extraction
writes its Turtle and its place in the Axiom Index and the class diagram.
