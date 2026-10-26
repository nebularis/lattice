<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: OD3, section 6 to OWL

**Unit:** [`improved-ontology-documentation`](../status/improved-ontology-documentation.md), slice OD3
([plan](../plans/improved-ontology-documentation.md#slices)).
**Implements:** [ADR-A126](../../architecture/decisions/ADR-A126-literate-specification-layout-and-grammar.md)
decisions 3 to 6, and the OWL half of decision 5 (the SHACL half is OD4).
**Built autonomously**, at the maintainer's request of 2026-10-18. The decisions taken alone are listed below,
for the maintainer to keep or overrule.

## Invariant

For a README in the layout, every axiom of section 6 is written once, in its entry, in the 6.4 tables or in
6.5, and compiles to the OWL that ADR-A126 assigns it, in the document its region or default names. The
output does not depend on the order of entries. An expression the grammar cannot read, a label it does not
know or a paragraph it cannot place is refused, never ignored. A README not in the layout extracts as before.

## What changed

- `tools/literate_grammar.py`:
  - **`Manchester`:** a recursive-descent parser for the subset in use (`or`, `and`, `not`, parentheses,
    names, `some`, `only`, `value`, and `min`, `max` and `exactly`, qualified or not).
  - **`Section6`:** compiles the entries of 6.1 to 6.3, the individuals tables of 6.4, and the disjointness
    of 6.5.
  - **Kept for OD4:** each restriction row is recorded with its Asserted in and Message.
- `tools/test_literate_grammar.py`. Tests OD3-T1 to OD3-T10, and OD2's helper now builds section 6's seven
  subsections, which a migrated README needs.
- `tools/test_literate_extract.py`. OD1-T11's README gains the seven subsections.
- `docs/architecture/literate-specifications.md`. Section 6 describes the grammar as built.

## Decisions taken alone, for the maintainer

1. **Every paragraph of an entry starts with a label.** An unlabelled paragraph inside an entry is refused,
   so no prose sits in a normative entry unextracted. Prose before a subsection's first entry or table is
   allowed and not extracted.
2. **All seven subsections are required**, an empty one saying "None.", and an eighth is refused. Their
   numbers are not checked, only their titles.
3. **Where section 6 writes.** Entries and 6.5 go to the main spec document and 6.4's individuals to the main
   vocab document, unless an `output-file` region says otherwise. Either document must be a row of section 2's
   header table.
4. **An annotation written as a Turtle literal is used as written**, for example `"Wording node"@en`.
   Otherwise its text becomes plain text. This is how Wording's 73 language-tagged labels can migrate.
5. **`**Preferred label.**`** (`skos:prefLabel`) joins the annotation labels, since the vocabularies use it
   (77 times in spec and vocab files). The individuals tables take the same annotation columns.
6. **6.5 takes `**Disjoint.**` beside `**All disjoint.**`.** The layers state 34 `owl:disjointWith` and 22
   `owl:AllDisjointClasses`. Writing both forms keeps a migrated layer's graph the same as before (OD-D9).
   `**All disjoint.**` keeps its members in the order written, as an RDF list does.
7. **Unions, intersections and complements are written with `a owl:Class`**, as the layers write them, so a
   migrated graph matches. OD3-T7 checks two of SPC's axioms come out as SPC states them.
8. **Order.** The objects of one predicate are sorted by their text, so reordering a list of superclasses
   changes nothing. A key, a union and an `All disjoint` keep the order written, since RDF lists are ordered.
9. **One restriction per row.** Values must make a restriction on the row's property. A row asserted in SHACL
   alone writes no OWL and is kept for OD4, which also refuses a nested expression asserted in SHACL.
10. **Not supported, since nothing in the layers uses them:** a union of datatypes (it would be written as a
    class union), the property characteristics asymmetric, reflexive and irreflexive, and `oneOf`. Each is a
    small addition when a layer needs it.

## Test cases

In `tools/test_literate_grammar.py`.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| OD3-T1 | a class entry with every class label and a restriction table, and an equivalence / extract / the same graph as the expected Turtle, with no OWL for the SHACL-only rows | L3 | + |
| OD3-T2 | ten expressions: precedence, parentheses, complement, a nested restriction, `only` a datatype, qualified and unqualified cardinality, three kinds of value / parse / the expected OWL structures | L1 | + |
| OD3-T3 | seven malformed expressions / parse / each refused with its message | L1 | − |
| OD3-T4 | an object property and a datatype property with every property label / extract / the expected graph | L3 | + |
| OD3-T5 | an individuals table and an entry inside an `output-file` region / extract / the individual in the vocab document, the entry in the region's document only | L3 | + |
| OD3-T6 | `**All disjoint.**` and `**Disjoint.**` / extract / one `AllDisjointClasses` with its members in order, and one `disjointWith` | L3 | + |
| OD3-T7 | two of SPC's axioms written in the grammar / parse / isomorphic to the same axioms in `spec/spc.ttl` | L3 | + |
| OD3-T8 | 16 malformed sections 6, each wrong in one way: an unknown label, labels on the wrong kind, no Definition, an unlabelled paragraph, a heading with no CURIE, a second entry, a wrong table, Restrictions with no table, a bad Asserted in, values that are no restriction, an undeclared prefix, a wrong individuals table, and three wrong 6.5 paragraphs / compile / each refused | L1 | − |
| OD3-T9 | a missing subsection, an eighth, and a Utility with no `fnd:` prefix / compile / each refused | L1 | − |
| OD3-T10 | the same entries in two orders / extract / identical outputs | L2 | + |

## One command

Run from the repository root. A pass is every test passing.

```bash
mise exec -- python -m pytest tools/test_literate_grammar.py tools/test_literate_extract.py -q
```

## Results

2026-10-18, run while building, from this worktree:

- **`tools/test_literate_grammar.py`:** 64 passed.
- **`tools/test_literate_extract.py` and `tools/test_lattice_repo_catalogue.py`:** 131 passed.
- **The per-layer extraction tests, selected by name:** 9 passed.
- **`mise run check:formal-freshness` and `mise run check:catalogue`:** both pass.

`mise run check:ontology-catalog` was not run. The adversarial probes were not run.

## Adversarial probes, for the gate

| Mutation | Expected |
|---|---|
| `or` binds tighter than `and` (swap the two loops in `Manchester`) | OD3-T2's first two cases fail |
| SHACL-only rows also write OWL | OD3-T1 fails |
| statements keep README order (drop the sort in `Document.turtle`) | OD3-T10 fails |

## Deliberate non-coverage

- SHACL from the restriction tables, and refusing a nested expression asserted in SHACL. OD4.
- The Axiom Index and the class diagram. OD5.
- A real README in the layout, and the graph-isomorphism check against today's files. OD6, with Eligibility.

## Decisions answered

2026-10-18, by the maintainer: all ten agreed. Decision 4 raised multilingual support, recorded as PDD-10 in the
[pending design decisions](../pending-design-decisions.md). Decision 10's unsupported forms are in the plan's
unplanned backlog.

The maintainer ran every test suite on 2026-10-18, and all pass.
