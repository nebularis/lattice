<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: Asset class ASC-1, property columns in individuals tables

**Unit:** `asset-class` ([plan](../plans/asset-class.md), [status](../status/asset-class.md))
**Machine:** S. **Branch:** `air/asset-classes`. Commits are local, and pushing is the maintainer's.
**Plan and test cases:** [Asset class plan](../plans/asset-class.md) (ASC-1 in detail)
**Decisions:** ASC-Q5, ADR-A126's addendum of 2026-11-08

## Invariant

A 6.4 column headed by a CURIE states that property for each row, one statement per cell entry, and no generated file of a module that does not use such a column changes.

## Test cases

The table in the plan. Each row's result is recorded under Results at verification.

## One command

Run from the repository root.

```bash
mise exec -- python -m pytest tools/test_literate_grammar.py tools/test_literate_extract.py
```

## Artefacts to inspect

`tools/literate_grammar.py`, `tools/test_literate_grammar.py`, `docs/architecture/literate-specifications.md`, ADR-A126's addendum.

## Deliberate non-coverage

Property columns outside 6.4. Blank nodes in cells.

## Handoff

Built on machine S, 2026-11-08, on `air/asset-classes`, committed locally and not pushed.

**What was built.** `Section6.individuals()` in `tools/literate_grammar.py` reads each column after Individual and Type through `individual_columns()`: an annotation column as before, or a CURIE in backticks as a property column. `property_values()` reads a property cell through `split_values()`, which splits at commas outside quoted literals, and accepts CURIEs, Turtle literals (checking a typed literal's datatype prefix), numbers and booleans. The conventions document's section on individuals describes the columns with an example, and now lists Meaning bearing among the annotation columns, which it had left out.

**What was run.**

- `pytest tools/test_literate_grammar.py`: 129 passed, ten of them new (`-k asc1`).
- `pytest tools/test_literate_extract.py tools/test_literate_migration_check.py`: 76 passed.
- `literate_extract.py --check` on every README in ADR-A126's layout (eligibility with `--reference-root tools/reference`, ledger, MORK, persistence, vocabulary) and on six others with an extraction contract section (insurance common, exposure, Behaviour, Instrument, Surface, Wording): every one consistent.

| Row | Result |
|---|---|
| ASC1-01 to ASC1-04 | pass, `test_asc1_01_to_04_a_curie_column_states_its_property_for_each_row` |
| ASC1-05 to ASC1-07 | pass, `test_asc1_05_to_07_a_malformed_property_column_is_refused` (seven cases) and `test_asc1_07_a_property_in_two_columns_is_refused` |
| ASC1-08 | pass, every check consistent |
