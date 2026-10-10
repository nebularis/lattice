<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS C9b2, additivity in Quantification

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R (Claude Code). **Branch:** `ccs/c9b2-additivity`, in its own worktree, built by a
sub-agent that commits there, examples first (ADR-A-C2). Merged into `ccs/c9b-groundwork` after
C9b0 and before C9b1, which recomputes the cascade, then into `main` before release tags are created
**Plan:** [CCS plan](../plans/computable-contract-substrate.md), C9b2 in detail, and "How C9b0 to
C9b2 run"
**Decisions:** the [consent sketch](../sketches/consent-and-group-powers.md) §2.4 and §6, ADR-A93,
ADR-A94, ADR-A95, ADR-A115. C9b2-Q1 (a), with no subclasses, and C9b2-Q2 (p3), as answered on
2026-10-09. (p4) is held as HQ-12

## Invariant

A sum of values on one space is declared legitimate only where the space is extensive (law Q12),
and a sum over values whose units or bases differ, with no conversion, is Undetermined (law Q13).
Values in different units add only after each is converted at the reference time under §9.6, and
shares add only when their base roles resolve to one binding, compared by binding and never by
amount. A limit stated in several units is never converted (ADR-A95). A sum across two spaces, such
as a date plus a duration, and `Count` are unaffected.

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| C9b2-01 | Quantification's spec and vocab / parsed / `0.8.0`, `qnt:additivity` functional with range `qnt:Additivity` of exactly `qnt:Extensive` and `qnt:Intensive`, its utility telling authors to leave a stock undeclared, `qnt:baseRole`, `qnt:MixedBases`, and the role contract constraining both role properties | L1 | + |
| C9b2-02 | `examples/additivity.ttl` / every layer's shapes, and the reasoner where built / conform, consistent | L1 | + |
| C9b2-03 | a space with no additivity, with two values, with a value outside the two / shapes / conform, reported, reported | L1 | + − |
| C9b2-04 | a Sum within one space, on an Extensive, an Intensive and an undeclared space, with operands implied or stated / shapes / conforms only on Extensive (law Q12) | L1 | + − |
| C9b2-05 | a date plus a duration on an undeclared date space / shapes / conforms, while a same-space Sum on the durations, made undeclared, is reported | L1 | + − |
| C9b2-06 | a Count capability on an Intensive space / shapes / conforms | L1 | + |
| C9b2-07 | a base role on a proportion, on a plain value space, and two on one proportion / shapes / conforms, reported, reported | L1 | + − |
| C9b2-08 | two commitments in euros / summed / EUR 90m, with no conversion | L1 | + |
| C9b2-09 | commitments in euros and US dollars / summed at a reference time with a dated rate context / converted to the base currency, then summed, EUR 109.8m | L1 | + |
| C9b2-10 | the same commitments / summed at a reference time with no rate context / Undetermined, `qnt:ConversionContextAbsent` | L1 | − |
| C9b2-11 | the converted total and a sterling total / compared with a limit of EUR 110m or USD 120m / True against the euro statement, where converting the dollar one would give False. The sterling total is `qnt:NoBoundInUnit`, though a sterling rate context exists | L1 | + − |
| C9b2-12 | four written lines on one order, then one line from each of two orders of equal amount / summed / 160%, then Undetermined, `qnt:MixedBases` | L1 | + − |
| C9b2-13 | the over-written order / signed down by the declared `Ratio` and `Scale` / factor 0.625, signed lines 31.25%, 25%, 18.75%, 25% summing to 100%, line A EUR 3.125m, the factor's space Intensive | L1 | + |
| C9b2-14 | Quantification's README / the literate check, release notes, shapes version, worked examples / the source of all three files, 0.8.0 and shapes 0.3.0 (breaking) recorded, the corrected operations table, open question 7 answered in principle, the two same-space sums in `examples.md` declared Extensive | L1 | + |
| C9b2-15 | the cascade / nothing imports Quantification 0.7.0, and the versioning, catalog, import guard, MTP, Python, vocabulary, compiler, persistence and literate checks / pass | L1 | + |

Rows C9b2-08 to C9b2-13 read sums with `sum_of` and `at_most` in `tools/test_additivity.py`, a
reference reading of §9.9 and §9.2 over the example graph, as C9a's tests read agreement. There is
no evaluator of sums yet.

## One command

Run from the repository root of the worktree on machine R, with this checkout's packages first on
`PYTHONPATH` (skill `lattice-toolchain`).

```bash
mise run check:ontology-catalog && mise run check:ontology-versioning && mise run check:import-guard
```

`check:ontology-catalog` now runs `tools/test_additivity.py`.

## Artefacts to inspect

- `ontology/quantification/examples/additivity.ttl`: the multicurrency facility, lines on one order
  and on two, signing down, a date plus a duration and a Count of ratings, with the expected results
  in its header tables. Written before the model
- `ontology/quantification/README.md`: §4's twelfth decision, §5.1.3 (extensive and intensive
  spaces, the corrected table, sums over like values), §5.1.8 (a proportion's base, with a diagram),
  §9.9 (sums, with a diagram), laws Q12 and Q13, governance obligation 12, open question 7, release
  notes
- `ontology/quantification/shapes/constraints.ttl`: `qnt:AdditivityShape`, `qnt:BaseRoleShape`,
  `qnt:SumWithinOneSpaceShape`

## Deliberate non-coverage

- Whether an aggregate binding's measure permits Sum, and the grouping a sum must not cross, such as
  time for a balance (C9b3, Eligibility, which Quantification cannot see)
- Party's shares as measures with a base (C9b4)
- Composing shares, a product of two shares with different bases (HQ-12)
- A runtime evaluator of sums. Law Q13's discharge here is the reference reading in the tests (C12)
- `qnt:ExtensiveValueSpace` as a defined class, held until a studio asks for it (C9b2-Q1)
- The 31 value spaces outside Quantification declare no additivity. None declares a capability, so
  none is affected by the new shape

## Handoff

Phase 1, examples first (ADR-A-C2), 2026-10-09, commit `2be832be`:

- **Built:** `ontology/quantification/examples/additivity.ttl`
- **Run by the agent:** the example against the then model and every layer's shapes: conforms (the
  new terms were not yet declared)
- **Signing down needs no new operation.** The factor is a `Ratio` of two shares of one order (the
  whole order over the total written), on a derived space whose numerator and denominator are both
  the line share. `Scale` applies it to a written line, a value on that denominator space, giving a
  line share. No product of two derived values with different bases is needed, so HQ-12 stays held

Phase 2, the model, 2026-10-09, commit `4388e974`:

- **Built:** Quantification 0.8.0 and its vocab from the README, shapes 0.3.0, `tools/test_additivity.py`
  (24 tests over rows C9b2-01 to C9b2-15), added to `check:ontology-catalog`. The ontology
  architecture's Quantification row updated
- **Mutation probes:** with `?value qnt:additivity` broken in `qnt:SumWithinOneSpaceShape`, C9b2-02
  and C9b2-04 fail, and pass once restored. With the example's `qnt:baseRole` removed, C9b2-12 fails

Phase 3, the cascade, 2026-10-09: see Results.

- **Deviations from the plan:**
  - **Pack name.** Written as `computable-contract-substrate-c9b2.md`, beside C9a's, where the plan
    names `ccs-c9b2.md`
  - **A Sum with no operands stated is read as within its owning space.** `ex:mass-sum` in
    `examples.md` declares only a result space, so the shape treats the owning space, the operand
    spaces and the result space together, and reports when they are one space not declared
    Extensive
  - **The role contract constrains `qnt:baseRole` too**, so a base role is a concept from the same
    bound scheme as a context value's role, as ADR-A115 has it. This changes the vocab document
  - **Two shapes beyond the plan:** at most one additivity, from the two values (row C9b2-03 tests it
    at zero and two), and at most one base role, only on a derived space. The plan named only the Sum
    shape
  - **Additivity and base role join governance obligation 12**, the properties whose change needs a
    major declaration version
  - **The worked examples' mass and extent spaces now declare Extensive**, since their same-space
    Sums would otherwise be reported. `examples.md` is not loaded by any test
  - **A stock shares its currency's Extensive space**, corrected at merge (2026-10-09). The brief said
    to leave a stock undeclared, which contradicted C9b2-Q1's answer that semi-additivity belongs on
    the measure: balances add across accounts, and a payment adds to a balance. Not adding across
    dates is the measure's rule, stated by the consuming layer (C9b3, C9b4)
  - **The cascade bumps from `main`'s versions**, not C9b0's. Every importer takes an additive MINOR.
    Eligibility's and `eligibility-vocab`'s numbers collide with C9b0's, and Instrument's and
    Behaviour's with C9b1's, and the merge takes each once (plan, "How C9b0 to C9b2 run")

## Results

Run by the agent on 2026-10-09, with this worktree's packages first on `PYTHONPATH`.

| Row | Result | Evidence |
|---|---|---|
| C9b2-01 | pass | `test_c9b2_01_terms` |
| C9b2-02 | pass, reasoner row skipped | `test_c9b2_02_example_conforms_to_every_layer`. `test_c9b2_02_example_is_consistent` skips: the ADR-A83 harness jar is not built on this machine |
| C9b2-03 | pass | `test_c9b2_03_additivity_at_zero_and_two` (three cases) |
| C9b2-04 | pass | `test_c9b2_04_sum_within_one_space_needs_extensive` (five cases) |
| C9b2-05 | pass | `test_c9b2_05_date_plus_duration_is_still_valid` |
| C9b2-06 | pass | `test_c9b2_06_count_on_an_intensive_space_is_valid` |
| C9b2-07 | pass | `test_c9b2_07_a_proportions_base_role` (three cases) |
| C9b2-08 | pass | `test_c9b2_08_one_currency_sums` |
| C9b2-09 | pass | `test_c9b2_09_mixed_currencies_convert_at_the_reference_time_then_sum` |
| C9b2-10 | pass | `test_c9b2_10_mixed_currencies_with_no_context_are_undetermined` |
| C9b2-11 | pass | `test_c9b2_11_a_limit_in_two_currencies_is_never_converted` |
| C9b2-12 | pass | `test_c9b2_12_shares_of_one_base_sum_and_of_two_are_undetermined` |
| C9b2-13 | pass | `test_c9b2_13_signing_down_is_ratio_then_scale` |
| C9b2-14 | pass | `test_c9b2_14_readme_is_the_source_and_records_the_release`. Literate `--check` also passes for Behaviour, Instrument, Wording, Surface and Foundation |
| C9b2-15 | pass, with one earlier failure | `test_c9b2_15_nothing_still_imports_quantification_0_7_0`. `check:ontology-versioning`, `check:import-guard`, `build:mtp` (no change, MORK is outside the closure), `check:mtp`, `check:python-root`, `check:vocabulary` (16), `check:mork-compilers` (107), `check:persistence` (778), `check:agent-guidance` and `ontology_catalog.py check` pass. `check:ontology-catalog`: 572 passed, 68 skipped, 1 failed. The failure, `test_instrument.py::test_c6_10_no_retired_term_outside_history`, is on the branch's base before this slice: retired Instrument terms in `ontology/examples/insure-o/`, which this slice does not touch |

The README's three new or changed diagrams (§5.1.8, §5.1.10, §9.9) render with mermaid 10.9.1 in a
browser.
