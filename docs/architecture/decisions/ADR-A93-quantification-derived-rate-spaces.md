<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A93: Quantification derived rate spaces

**Status:** Proposed
**Date:** 2026-09-25
**Related:** Quantification open question 4, ADR-A24, ADR-A89
**Unit:** [`applied-ontology-readiness`](../../developer/plans/applied-ontology-readiness.md) (AOR-14)

## Context

Applied ontologies state rates. A dose ceiling is 2 mg per kg of body weight.
A service credit is 10% of the monthly fee. A tax rate is a share of income.
Quantification can declare a space for each, but nothing says a rate space is
the quotient of two others. A condition on "2 mg per kg" is then
indistinguishable from one on "2 mg", and nothing relates the rate to the base
it scales. Quantification's open question 4 deferred the decision, noting
that a deployment would otherwise invent its own.

## Decision

1. **`qnt:DerivedValueSpace ⊑ qnt:ValueSpace`**, with exactly one
   `qnt:numeratorSpace` and exactly one `qnt:denominatorSpace`. Its values are
   ordinary `qnt:Quantity` individuals on the derived space.
2. **A proportion is a derived space whose numerator and denominator are the
   same space.** A percentage is a proportion whose unit contract names a
   percent unit. Its values stay typed by the pair, so "10% of a fee" and "10%
   of an income" are different spaces.
3. **`qnt:Scale` joins the operation kinds.** Scaling a base value on the
   denominator space by a rate on the derived space yields a value on the
   numerator space. A deployment declares it as an `qnt:OperationCapability`
   with the two operands and the result space, as for any other operation.
   `qnt:Ratio` of a numerator value by a denominator value names the derived
   space as its result space.
4. **Units stay declared.** A derived space's unit contract names its own
   unit family (mg/kg, percent). Conversions between derived units are
   declared `qnt:Conversion`s. Nothing derives a compound conversion
   automatically.
5. **Eligibility is unchanged.** An interval condition on a derived space
   constrains its values like any other space.

## Consequences

- Quantification takes a MINOR bump, with the ADR-A86 cascade.
- Open question 4 closes.
- A shape checks that the numerator and denominator spaces are declared
  value spaces. Whether a `Scale` capability's operands match the derived
  space's pair is a static constraint, like period-space compatibility.
- Examples: a clinical dose per body weight and a subscription service credit.
