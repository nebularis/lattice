<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A94: Quantification calendar binding

**Status:** Proposed
**Date:** 2026-09-25
**Related:** Quantification open question 2, §9.6 (conversion), §9.7
(recurrence), ADR-A85 (binding resolution)
**Unit:** [`applied-ontology-readiness`](../../developer/plans/applied-ontology-readiness.md) (AOR-15)

## Context

Notice periods of 20 business days, settlement two business days after trade,
screening visits within 3 business days of consent: each counts days that a
calendar says are working days. Which days those are depends on jurisdiction,
organisation and year, so LATTICE cannot ship calendars. Quantification's open
question 2 leaned towards binding the calendar through `qnt:UnitContract`,
reusing the conversion mechanism instead of adding a temporal contract.

## Decision

1. **A business day is a unit.** A business-day extent is a `qnt:Quantity` on
   an extent space, in a deployment-declared unit. `qnt:CalendarUnit ⊑
   qnt:Unit` marks a unit whose relation to elapsed time depends on a
   calendar.
2. **Relating it to elapsed time is a contextual conversion.** A conversion
   from or to a calendar unit has `conversionKind` `qnt:Contextual`. Its
   `qnt:ConversionContext` names the calendar with `qnt:underCalendar` and the
   position counted from with `qnt:fromPosition`. §9.6's existing rule
   applies unchanged: without the context, a comparison needing the
   conversion is `Undetermined`.
3. **`qnt:Calendar ⊑ fnd:Version, fnd:Governable`** identifies a calendar and
   its edition. Its content (which dates are working days) stays with the
   deployment, as a concept scheme, a dataset or a service. Quantification
   declares no content property. Which calendar applies in a context is chosen
   the way a scheme is: a `voc:SchemeContract` for calendars, resolved under
   ADR-A85 for scope and time.
4. **Recurrences reuse it.** A recurrence whose period is in a calendar unit
   names its calendar the same way, which is the "calendar binding" §9.7
   already lists among the inputs to bin-key stability.

## Consequences

- Quantification takes a MINOR bump, with the ADR-A86 cascade.
- Open question 2 closes, with the argument recorded here.
- The Eligibility compilers treat a condition needing a calendar conversion as
  `Undetermined` without a conversion context, which they do not yet supply.
  Supplying one is later compiler work.
- Examples: an employment notice period and a clinical screening window.
