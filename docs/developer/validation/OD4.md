<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: OD4, section 6 to SHACL

**Unit:** [`improved-ontology-documentation`](../status/improved-ontology-documentation.md), slice OD4
([plan](../plans/improved-ontology-documentation.md#slices)).
**Implements:** [ADR-A126](../../architecture/decisions/ADR-A126-literate-specification-layout-and-grammar.md)
decision 5, the SHACL half.
**Built autonomously**, at the maintainer's request of 2026-10-18, with the four design leanings the maintainer
agreed that day. The further decisions taken alone are listed below, for the maintainer to keep or overrule.

## Invariant

Every restriction row checked in SHACL (Asserted in blank or SHACL) appears in the module's generated
`shapes/structural.ttl` as the SHACL its flat form maps to, under one shape for its class. A row asserted in
OWL alone writes no shape. A nested expression checked in SHACL, a constraint stated twice for one property
shape, and a hand-written shape block that names no file or names the generated file are refused. A README
not in the layout extracts as before.

## The four agreed leanings, as built

1. **Generated SHACL lands in `shapes/structural.ttl`, generated whole.** Hand-written shapes go in section 7
   blocks for other files.
2. **One `<Class>Shape` per class**, named by appending `Shape` to the class's CURIE, as Eligibility's are.
3. **Property shapes are blank nodes**, with no `sh:severity` (so each is a violation) and the row's message.
4. **Versioning is unchanged.** A change to the generated file bumps the shapes directory's `.version`, as any
   shape change does.

## What changed

- `tools/literate_grammar.py`:
  - **`shacl_constraints()`** maps one row's flat form to SHACL.
  - **`structural_shapes()`** writes the shapes file, sorted.
  - **`compile_layout()`** now returns a `Compiled`, holding the documents' openings and the generated shapes.
- `tools/literate_extract.py`. `plan()` writes the generated shapes file, and refuses a shape block of a
  migrated README that names no file or names the generated one. `main()` passes both on.
- `tools/test_literate_grammar.py`. Tests OD4-T1 to OD4-T7, and the `extract` helper takes the generated
  shapes.
- `docs/architecture/literate-specifications.md`. The restriction section describes the shapes as built.

## Decisions taken alone, for the maintainer

1. **Rows for one property with the same message, or none, share one property shape.** Eligibility writes
   `[ sh:path elg:negated ; sh:maxCount 1 ; sh:datatype xsd:boolean ]` from what are two rows (`max 1`,
   `only xsd:boolean`), so merging keeps a migrated graph the same. Two such rows that state the same
   constraint, for example two `sh:maxCount`, are refused, and a different message gives a row its own shape.
2. **`only` maps to `sh:datatype`** when its filler is an `xsd:` datatype, `rdfs:Literal` or `rdf:langString`,
   and to `sh:class` otherwise.
3. **`some C` maps to a qualified shape** with `sh:qualifiedMinCount 1`, and `value v` to `sh:hasValue`.
4. **In a migrated README every shape block names its file.** A positional shape block would otherwise take
   the generated file's place in the catalogue's contract. The catalogue entry still lists
   `shapes/structural.ttl`, so RC1-T3 holds the declared and generated files equal.
5. **No structural file is generated** when no row is checked in SHACL.
6. **Not supported in the table:** a severity other than violation (Behaviour has one `sh:Warning` shape),
   SPARQL constraints, and constraints on a property path rather than a property. Those shapes stay
   hand-written in section 7.

## Test cases

In `tools/test_literate_grammar.py`.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| OD4-T1 | one row of each flat form, a SHACL-only row with a message, an OWL-only row / extract / the expected shapes graph, with no shape for the OWL-only row | L3 | + |
| OD4-T2 | three rows on one property, two without a message and one with / extract / one merged property shape and one of its own, and two rows stating `sh:maxCount` refused | L3 | +/− |
| OD4-T3 | three nested expressions / checked in SHACL, then marked OWL / refused, then accepted with no shapes file | L1 | +/− |
| OD4-T4 | a hand-written shape block naming `shapes/constraints.ttl`, one naming no file, one naming `shapes/structural.ttl` / extract / written beside the generated file, then two refusals | L1 | +/− |
| OD4-T5 | no row checked in SHACL / extract / no structural file | L1 | + |
| OD4-T6 | the same entries and rows in two orders / extract / identical shapes files | L2 | + |
| OD4-T7 | Eligibility's `EligibilityDecision` restrictions written as a table / extract / its shape isomorphic to `elg:EligibilityDecisionShape` in Eligibility's `shapes/structural.ttl` | L3 | + |

## One command

Run from the repository root. A pass is every test passing.

```bash
mise exec -- python -m pytest tools/test_literate_grammar.py tools/test_literate_extract.py -q
```

## Results

2026-10-18, run while building, from this worktree:

- **`tools/test_literate_grammar.py`:** 75 passed.
- **`tools/test_literate_extract.py` and `tools/test_lattice_repo_catalogue.py`:** 131 passed.
- **The per-layer extraction tests, selected by name:** 9 passed.
- **`mise run check:formal-freshness`:** passes.

`mise run check:ontology-catalog` was not run. The adversarial probes were not run.

## Adversarial probes, for the gate

| Mutation | Expected |
|---|---|
| map a qualified restriction to `sh:class` with counts | OD4-T1 fails |
| stop merging rows on one property | OD4-T2 and OD4-T7 fail |
| allow a nested filler through `_named()` | OD4-T3 fails |

## Deliberate non-coverage

- The Axiom Index and the class diagram. OD5.
- A real README in the layout. OD6, with Eligibility, whose hand-written structural shapes beyond its tables
  are reconciled then.

## Decisions answered

2026-10-18, by the maintainer: decisions 2 to 6 agreed. Decision 1 (merging rows for one property and message)
agreed after its consequences were set out: it keeps migrated graphs identical, changes no validation outcome,
and refuses two rows that state the same constraint.
