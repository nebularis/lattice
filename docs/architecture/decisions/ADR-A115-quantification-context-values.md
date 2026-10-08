<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A115: Quantification context values

**Status:** Accepted
**Date:** 2026-10-05 (proposed), 2026-10-05 (accepted)
**Related:** ADR-A94 (calendar binding), ADR-A85 (binding resolution), ADR-A86 (versioning),
ADR-A104 and its 2026-10-05 addendum (terms in time), the
[terms in time sketch](../../developer/sketches/terms-in-time.md) Part A
**Unit:** [`computable-contract-substrate`](../../developer/plans/computable-contract-substrate.md) (C7b, TQ1)

## Context

Many values are stated once and resolve differently for every subject. "Within 30 days of each
invoice", "within 10 business days after the end of each month", "each year from the subscription
start", "not less than six months before the Expiry Date". The statement names its anchor: the
arising, the end of a period, a start date. The value differs for every instrument, occasion or
subscriber, and is known only when something is evaluated for one of them.

Quantification has the structures these need. `qnt:Recurrence` takes any `qnt:Value` as its
anchor, and its period is a `qnt:Quantity` with a unit, including a `qnt:CalendarUnit`. A
`qnt:Range` may be `qnt:relativeToAnchor` a `qnt:AnchorBinding`, whose anchor is any `qnt:Value`.
Two things are missing:

- **a value supplied by context.** A value is definite (`qnt:Quantity`, `qnt:OrdinalValue`) or
  missing (`qnt:UnresolvedValue`, a required value that is unavailable, with a reason and
  evidence). Nothing names a value that is complete as stated and resolved per evaluation
- **offsets with units.** An anchor binding's `qnt:lowerOffset` and `qnt:upperOffset` are unitless
  decimals in the anchor's own space, so they cannot be counted in business days or months

The need is not Instrument's alone. Behaviour's allowance resets and an applied capacity model's
"reset each policy year from inception" have the same shape as an obligation's reporting period.
The construct therefore belongs in Quantification (CCS C7b, TQ1, answered 2026-10-05).

## Decision

1. **`qnt:ContextValue ⊑ qnt:Value`.** A value supplied by an evaluation context under a named
   role. It has exactly one `qnt:contextRole`, a concept, and, as every value, exactly one
   `qnt:onSpace`. It is complete as stated: it is not an unresolved value, and has no reason or
   evidence. An evaluation that binds no value to its role is Undetermined, with a diagnostic
   naming the role.
2. **Roles are deployment content, under a contract.** `qnt:ContextRoleContract`, a
   `voc:SchemeContract` in Quantification's vocabulary, constrains `qnt:contextRole`. Quantification
   ships no roles, as it ships no units or calendars. A layer or deployment binds its own scheme
   (Instrument binds its baseline: the arising, inception, ending, and a period's start and end).
3. **Unit-bearing offsets.** `qnt:lowerOffsetBy` and `qnt:upperOffsetBy` give an anchor binding's
   offsets as `qnt:Quantity`s, signed, in any unit the offset's space allows, including calendar
   units. They sit beside the decimal offsets, which stay for proportional and unitless offsets.
   One binding uses one form or the other, and a shape checks it. With `qnt:offsetKind`
   `qnt:Absolute`, a quantity offset is added to the anchor value, and counting it in a calendar
   unit is a contextual conversion (ADR-A94).
4. **Resolution belongs to the evaluator.** The evaluation context binds each role, and the
   resolved anchor and bounds are recorded with what they were derived from. Quantification states
   what is resolved, not how a runtime finds the binding.

## Consequences

- Quantification takes an additive MINOR (0.6.0 → 0.7.0) and its shapes 0.1.0 → 0.2.0, with the
  ADR-A86 re-pin cascade to every importer.
- Quantification's README is restored as its literate source first, with no graph change.
- Business day conventions (following, modified following) and times of day in a zone are held
  (CCS held design question HQ-3), to be decided with the first business continuity examples.
- Combinations of anchors ("the earlier of") wait for the evaluation context.
- Example: a subscription's allowance year and grace period
  (`ontology/quantification/examples/context-anchor.ttl`).
