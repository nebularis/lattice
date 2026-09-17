<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR A-04: Interval containment and overlap law split

## Status

Accepted

## Context

Eligibility previously treated interval overlap as interchangeable with interval containment in some profiles. That is not law-coherent for admissibility. Overlap can be true while containment is false, and overlap does not provide a safe basis for determining admissibility where full inclusion is required.

## Decision

Eligibility adopts `IntervalContainment` as the only interval strategy for admissibility decisions in the substrate model.

- `IntervalContainment` uses `qnt:Range` and `qnt:RangeSet` from Quantification.
- `IntervalOverlap` is excluded from the admissibility strategy algebra.
- Any profile needing overlap for screening must model it as a separate, non-admissibility pre-check outside eligibility decision laws.

## Consequences

- End-to-end admissibility remains law-coherent.
- Quantification supplies all required interval structures, so no exemption or bootstrap mechanism is needed.
- Screening use cases still remain possible, but they cannot be represented as admissibility outcomes in Eligibility.
