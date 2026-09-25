<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A95: Quantification alternative bounds

**Status:** Proposed
**Date:** 2026-09-25
**Related:** Quantification §9.2 (containment), §9.6 (conversion), ADR-A89
**Unit:** [`applied-ontology-readiness`](../../developer/plans/applied-ontology-readiness.md) (AOR-16)

## Context

A lending facility's limit may be stated as USD 10 million or EUR 9 million,
each figure authoritative in its own currency. A subscription may price a
tier at 20 USD or 18 EUR. Neither statement implies an exchange rate, and
converting one into the other would change the agreement. A `qnt:Bound` has
one value, so today the limit is stated in one currency and a candidate in
the other needs a contextual conversion the agreement never made.

## Decision

1. **`qnt:alternativeBound` (`qnt:Bound` → `qnt:Bound`)** links a bound to
   another statement of the same limit. Alternatives share the bound's
   `onSpace`, `boundSense` and `boundClosure`, and their values differ in
   `qnt:inUnit`. The relation is symmetric and not functional.
2. **Comparison uses the matching statement.** A candidate is compared with
   the bound, among the bound and its alternatives, whose unit is the
   candidate's own. No conversion is performed. If none matches, the
   comparison is `Undetermined` with the reason `qnt:NoBoundInUnit`, even when
   a conversion is declared, since converting would substitute a rate the
   limit's author did not choose.
3. **Structure is checked in SHACL.** A shape rejects alternatives on
   different spaces, senses or closures, and two alternatives in one unit.

## Consequences

- Quantification takes a MINOR bump, with the ADR-A86 cascade.
- The Eligibility IR's interval plan gains one required interval per unit.
  The compilers must select intervals by the candidate's unit, which they do
  not do today, so bounds with alternatives are refused until they do.
- Examples: a facility limit in two currencies and a tier price in two
  currencies.
